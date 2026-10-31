"""Tests for intent.py: the Assist/LLM-tool wrapping search_instruments
(ENH-015) - plain Python + a fake hass, no full `hass` fixture needed (see
tests/test_binary_sensor.py's module docstring: importing homeassistant
helper modules and instantiating their plain dataclasses works fine on
Windows; only the full `hass` test *fixture* needs the POSIX-only
`homeassistant.runner`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from homeassistant.core import Context
from homeassistant.helpers import intent as ha_intent

from custom_components.marketsentry.intent import (
    INTENT_SEARCH_INSTRUMENTS,
    SearchInstrumentsIntentHandler,
    async_setup_intents,
)
from custom_components.marketsentry.providers.base import InstrumentRef


@dataclass
class _FakeHass:
    """Just enough of `HomeAssistant` for `intent.async_register`/`async_get`."""

    data: dict[str, Any] = field(default_factory=dict)


def _make_intent(slots: dict[str, Any]) -> ha_intent.Intent:
    return ha_intent.Intent(
        hass=_FakeHass(),
        platform="test",
        intent_type=INTENT_SEARCH_INSTRUMENTS,
        slots=slots,
        text_input=None,
        context=Context(),
        language="en",
    )


def _tool_slots(**kwargs: Any) -> dict[str, Any]:
    """Shape `llm.IntentTool.async_call` builds from an LLM's tool_args."""
    return {key: {"value": val} for key, val in kwargs.items()}


def test_async_setup_intents_registers_the_handler() -> None:
    hass = _FakeHass()
    async_setup_intents(hass)

    handlers = list(ha_intent.async_get(hass))
    assert len(handlers) == 1
    assert handlers[0].intent_type == INTENT_SEARCH_INSTRUMENTS
    assert isinstance(handlers[0], SearchInstrumentsIntentHandler)


def test_async_setup_intents_is_idempotent() -> None:
    hass = _FakeHass()
    async_setup_intents(hass)
    async_setup_intents(hass)

    handlers = list(ha_intent.async_get(hass))
    assert len(handlers) == 1


async def test_async_handle_speaks_single_match(monkeypatch: pytest.MonkeyPatch) -> None:
    refs = [
        InstrumentRef(
            provider="coingecko",
            id="bitcoin",
            symbol="BTC",
            name="Bitcoin",
            kind="crypto",
            unit="USD",
            url="https://coingecko.com/bitcoin",
        )
    ]

    async def _fake_search(hass: Any, provider_key: str, query: str, limit: int) -> list[InstrumentRef]:
        assert provider_key == "coingecko"
        assert query == "bitcoin"
        assert limit == 5
        return refs

    monkeypatch.setattr("custom_components.marketsentry.intent.async_search_instruments", _fake_search)

    handler = SearchInstrumentsIntentHandler()
    intent_obj = _make_intent(_tool_slots(provider="coingecko", query="bitcoin"))

    response = await handler.async_handle(intent_obj)

    assert response.speech["plain"]["speech"] == "Found Bitcoin (BTC)."


async def test_async_handle_speaks_multiple_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    refs = [
        InstrumentRef(provider="finnhub", id="AAPL", symbol="AAPL", name="Apple Inc.", kind="stock", unit="USD"),
        InstrumentRef(
            provider="finnhub", id="AAPL.L", symbol="AAPL.L", name="Apple Inc. (LSE)", kind="stock", unit="GBP"
        ),
    ]

    async def _fake_search(hass: Any, provider_key: str, query: str, limit: int) -> list[InstrumentRef]:
        return refs

    monkeypatch.setattr("custom_components.marketsentry.intent.async_search_instruments", _fake_search)

    handler = SearchInstrumentsIntentHandler()
    intent_obj = _make_intent(_tool_slots(provider="finnhub", query="AAPL", limit=10))

    response = await handler.async_handle(intent_obj)

    assert response.speech["plain"]["speech"] == (
        "Found 2 matches: Apple Inc. (AAPL), Apple Inc. (LSE) (AAPL.L)."
    )


async def test_async_handle_speaks_no_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_search(hass: Any, provider_key: str, query: str, limit: int) -> list[InstrumentRef]:
        return []

    monkeypatch.setattr("custom_components.marketsentry.intent.async_search_instruments", _fake_search)

    handler = SearchInstrumentsIntentHandler()
    intent_obj = _make_intent(_tool_slots(provider="coingecko", query="nonexistent-coin-xyz"))

    response = await handler.async_handle(intent_obj)

    assert "couldn't find" in response.speech["plain"]["speech"]


async def test_async_handle_sets_error_response_on_lookup_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_search(hass: Any, provider_key: str, query: str, limit: int) -> list[InstrumentRef]:
        raise ValueError("No configured finnhub account found")

    monkeypatch.setattr("custom_components.marketsentry.intent.async_search_instruments", _fake_search)

    handler = SearchInstrumentsIntentHandler()
    intent_obj = _make_intent(_tool_slots(provider="finnhub", query="AAPL"))

    response = await handler.async_handle(intent_obj)

    assert response.response_type == ha_intent.IntentResponseType.ERROR
    assert response.error_code == ha_intent.IntentResponseErrorCode.FAILED_TO_HANDLE
