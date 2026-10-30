"""Tests for config_flow.py: URL, slug, invalid input, multi-market event."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.polymarket_watch.const import DOMAIN
from custom_components.polymarket_watch.models import Market

from ..conftest import (
    GAMMA_EVENT_MULTI_MARKET_FIXTURE,
    GAMMA_EVENT_SINGLE_MARKET_FIXTURE,
    GAMMA_MARKET_FIXTURE,
)


async def test_user_flow_with_market_url(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    with patch(
        "custom_components.polymarket_watch.api.PolymarketApiClient.get_market_by_slug",
        return_value=Market.from_gamma(GAMMA_MARKET_FIXTURE),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"url_or_slug": "https://polymarket.com/market/will-x-happen"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "confirm_market"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["slug"] == "will-x-happen"


async def test_user_flow_invalid_input(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"url_or_slug": "https://polymarket.com/"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_url"


async def test_user_flow_slug_not_found(hass: HomeAssistant) -> None:
    from custom_components.polymarket_watch.api import PolymarketNotFoundError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.polymarket_watch.api.PolymarketApiClient.get_event_by_slug",
        side_effect=PolymarketNotFoundError("nope"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"url_or_slug": "does-not-exist"}
        )
    assert result["errors"]["base"] == "not_found"


async def test_user_flow_single_market_event_skips_selection(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.polymarket_watch.api.PolymarketApiClient.get_event_by_slug",
        return_value=GAMMA_EVENT_SINGLE_MARKET_FIXTURE,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"url_or_slug": "some-event"}
        )
    assert result["step_id"] == "confirm_market"


async def test_user_flow_multi_market_event_shows_selection(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.polymarket_watch.api.PolymarketApiClient.get_event_by_slug",
        return_value=GAMMA_EVENT_MULTI_MARKET_FIXTURE,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"url_or_slug": "multi-event"}
        )
    assert result["step_id"] == "select_markets"
    assert result["data_schema"] is not None


async def test_multi_market_selection_creates_multiple_entries(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.polymarket_watch.api.PolymarketApiClient.get_event_by_slug",
        return_value=GAMMA_EVENT_MULTI_MARKET_FIXTURE,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"url_or_slug": "multi-event"}
        )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"markets": ["sub-a", "sub-b"]}
    )
    await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    entries = hass.config_entries.async_entries(DOMAIN)
    slugs = {e.data["slug"] for e in entries}
    assert slugs == {"sub-a", "sub-b"}


async def test_options_flow_parses_comma_separated_thresholds(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.polymarket_watch.api.PolymarketApiClient.get_market_by_slug",
        return_value=Market.from_gamma(GAMMA_MARKET_FIXTURE),
    ):
        entry_result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        entry_result = await hass.config_entries.flow.async_configure(
            entry_result["flow_id"],
            {"url_or_slug": "https://polymarket.com/market/will-x-happen"},
        )
        entry_result = await hass.config_entries.flow.async_configure(entry_result["flow_id"], {})

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    options_result = await hass.config_entries.options.async_init(entry.entry_id)
    options_result = await hass.config_entries.options.async_configure(
        options_result["flow_id"],
        {
            "thresholds": "20, 40, 60",
            "hysteresis_pp": 0.5,
            "move_delta_pp": 5.0,
            "move_window_min": 60,
            "large_trade_usd": 10000.0,
            "volume_spike_pct": 50.0,
            "closing_soon_hours": 24,
            "cooldown_min": 15,
        },
    )
    assert options_result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert options_result["data"]["thresholds"] == [20.0, 40.0, 60.0]
