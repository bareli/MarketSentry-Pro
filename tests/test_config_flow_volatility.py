"""Tests for config_flow.py's ENH-017 volatility-hint helpers: pure
Python / plain-`Provider`-stub, no `hass` fixture needed (see
tests/test_sensor.py's module docstring - importing `homeassistant`
modules at module load time works fine on Windows; only the full `hass`
test *fixture* used by tests/config_flow/ needs the POSIX-only
`homeassistant.runner`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from custom_components.marketsentry.config_flow import (
    VOLATILITY_HINT_TIMEOUT_SEC,
    _async_volatility_hint,
    _format_volatility_hint,
    _volatility_hint_pct,
)
from custom_components.marketsentry.providers.base import (
    CannotConnect,
    InstrumentRef,
    PricePoint,
    Provider,
    Quote,
)


def _point(day: int, price: float) -> PricePoint:
    return PricePoint(ts=datetime(2026, 10, day, 12, 0, tzinfo=UTC), price=price)


def _ref(kind: str = "stock") -> InstrumentRef:
    return InstrumentRef(provider="test", id="X", symbol="X", name="X", kind=kind, unit="USD")


def test_volatility_hint_pct_needs_at_least_two_points() -> None:
    assert _volatility_hint_pct([], "stock") is None
    assert _volatility_hint_pct([_point(1, 100.0)], "stock") is None


def test_volatility_hint_pct_needs_at_least_two_distinct_days() -> None:
    # Multiple points on the same day collapse to one - still not enough.
    points = [_point(1, 100.0), _point(1, 101.0), _point(1, 99.0)]
    assert _volatility_hint_pct(points, "stock") is None


def test_volatility_hint_pct_stock_is_relative_percent_change() -> None:
    # Day 1 -> 100, day 2 -> 110 (+10%), day 3 -> 99 (-10% from 110).
    points = [_point(1, 100.0), _point(2, 110.0), _point(3, 99.0)]
    assert _volatility_hint_pct(points, "stock") == pytest.approx(10.0)


def test_volatility_hint_pct_outcome_is_percentage_points_not_relative() -> None:
    # Probability 0.40 -> 0.44 -> 0.33, same raw 0-1 scale Quote.price uses
    # for outcome (sensor.py's `is_outcome` convention). A relative percent
    # change would read ~10% / ~25%; percentage-point deltas read 4 / 11.
    points = [_point(1, 0.40), _point(2, 0.44), _point(3, 0.33)]
    assert _volatility_hint_pct(points, "outcome") == pytest.approx(7.5)


def test_volatility_hint_pct_sorts_out_of_order_points() -> None:
    points = [_point(3, 99.0), _point(1, 100.0), _point(2, 110.0)]
    assert _volatility_hint_pct(points, "stock") == pytest.approx(10.0)


class _StubProvider(Provider):
    key = "stub"
    name = "Stub"
    requires_api_key = False
    supports_streaming = False

    def __init__(self, history: list[PricePoint] | None = None, error: Exception | None = None) -> None:
        self._history = history or []
        self._error = error

    async def validate(self, credentials: dict[str, Any]) -> None:
        return None

    async def search(self, query: str, limit: int) -> list[InstrumentRef]:
        return []

    async def resolve(self, user_input: str) -> list[InstrumentRef]:
        return []

    async def fetch_snapshot(self, refs: list[InstrumentRef]) -> dict[str, Quote]:
        return {}

    async def fetch_history(self, ref: InstrumentRef, hours: int) -> list[PricePoint]:
        if self._error is not None:
            raise self._error
        return self._history


async def test_async_volatility_hint_renders_when_history_available() -> None:
    history = [_point(1, 100.0), _point(2, 102.0)]
    provider = _StubProvider(history=history)
    hint = await _async_volatility_hint(provider, _ref("stock"), "en")
    assert "X moved ~2.0%" in hint
    assert "last week" in hint


def test_format_volatility_hint_is_localized_per_language() -> None:
    """ENH-017 follow-up: the sentence itself must be localized, not just the
    {name}/{symbol} placeholders - a hardcoded English clause injected into
    an otherwise-translated confirm dialog (e.g. Hebrew, this project's other
    primary locale) would read as broken, mixed-language text."""
    en = _format_volatility_hint("en", "X", 2.0, "%")
    he = _format_volatility_hint("he", "X", 2.0, "%")
    assert "moved" in en
    assert "last week" in en
    assert he != en
    assert "X" in he and "2.0" in he


def test_format_volatility_hint_falls_back_to_english_for_unknown_language() -> None:
    assert _format_volatility_hint("xx", "X", 2.0, "%") == _format_volatility_hint("en", "X", 2.0, "%")


def test_format_volatility_hint_is_case_insensitive_and_handles_region_variants() -> None:
    assert _format_volatility_hint("PT-BR", "X", 2.0, "%") == _format_volatility_hint("pt-br", "X", 2.0, "%")


async def test_async_volatility_hint_empty_when_provider_raises() -> None:
    provider = _StubProvider(error=CannotConnect("down"))
    hint = await _async_volatility_hint(provider, _ref("stock"), "en")
    assert hint == ""


async def test_async_volatility_hint_empty_when_provider_returns_too_little_data() -> None:
    provider = _StubProvider(history=[_point(1, 100.0)])
    hint = await _async_volatility_hint(provider, _ref("stock"), "en")
    assert hint == ""


async def test_async_volatility_hint_empty_on_unexpected_error() -> None:
    # Anything a provider can raise - not just CannotConnect/InvalidAuth -
    # must degrade to no hint rather than bubble up into the confirm step.
    provider = _StubProvider(error=ValueError("boom"))
    hint = await _async_volatility_hint(provider, _ref("stock"), "en")
    assert hint == ""


async def test_async_volatility_hint_empty_on_timeout() -> None:
    class _SlowProvider(_StubProvider):
        async def fetch_history(self, ref: InstrumentRef, hours: int) -> list[PricePoint]:
            raise TimeoutError("simulated slow provider")

    hint = await _async_volatility_hint(_SlowProvider(), _ref("stock"), "en")
    assert hint == ""
    # Sanity: the bound is a real, short timeout - not accidentally disabled.
    assert 0 < VOLATILITY_HINT_TIMEOUT_SEC <= 10
