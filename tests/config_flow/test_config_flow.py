"""Tests for config_flow.py: provider picker, credentials, instrument subentries."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.marketsentry.const import CONF_PROVIDER, DOMAIN, SUBENTRY_TYPE_INSTRUMENT
from custom_components.marketsentry.providers.base import CannotConnect, InstrumentRef, InvalidAuth


def _ref(instrument_id: str = "AAPL", symbol: str = "AAPL", kind: str = "stock") -> InstrumentRef:
    return InstrumentRef(
        provider="finnhub",
        id=instrument_id,
        symbol=symbol,
        name=f"{symbol} Inc",
        kind=kind,
        unit="USD",
    )


async def test_polymarket_entry_needs_no_credentials(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.marketsentry.providers.polymarket.PolymarketProvider.validate",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PROVIDER: "polymarket"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_PROVIDER: "polymarket"}


async def test_duplicate_provider_entry_aborts(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.marketsentry.providers.fx.FxProvider.validate", return_value=None
    ):
        await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PROVIDER: "fx"})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PROVIDER: "fx"})
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_finnhub_credentials_invalid_auth(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROVIDER: "finnhub"}
    )
    assert result["step_id"] == "finnhub_credentials"

    with patch(
        "custom_components.marketsentry.providers.finnhub.FinnhubProvider.validate",
        side_effect=InvalidAuth("bad key"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "bad"}
        )
    assert result["errors"]["base"] == "invalid_auth"


async def test_finnhub_credentials_success_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROVIDER: "finnhub"}
    )

    with patch(
        "custom_components.marketsentry.providers.finnhub.FinnhubProvider.validate",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "good-key"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["api_key"] == "good-key"


async def test_alpaca_credentials_cannot_connect(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROVIDER: "alpaca"}
    )
    assert result["step_id"] == "alpaca_credentials"

    with patch(
        "custom_components.marketsentry.providers.alpaca.AlpacaProvider.validate",
        side_effect=CannotConnect("down"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"key_id": "k", "secret_key": "s"}
        )
    assert result["errors"]["base"] == "cannot_connect"


async def _create_finnhub_entry(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROVIDER: "finnhub"}
    )
    with patch(
        "custom_components.marketsentry.providers.finnhub.FinnhubProvider.validate",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "good-key"}
        )
    await hass.async_block_till_done()
    return hass.config_entries.async_entries(DOMAIN)[0]


async def test_instrument_subentry_single_match_flow(hass: HomeAssistant) -> None:
    entry = await _create_finnhub_entry(hass)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_INSTRUMENT), context={"source": "user"}
    )
    with patch(
        "custom_components.marketsentry.providers.finnhub.FinnhubProvider.resolve",
        return_value=[_ref()],
    ):
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"url_or_query": "AAPL"}
        )
    assert result["step_id"] == "confirm"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"thresholds": "", "hysteresis": 0.0, "move_delta": 2.0, "move_window_min": 60, "cooldown_min": 15},
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["symbol"] == "AAPL"


async def test_instrument_subentry_multiple_matches_shows_select(hass: HomeAssistant) -> None:
    entry = await _create_finnhub_entry(hass)
    refs = [_ref("AAPL", "AAPL"), _ref("AAPL.MX", "AAPL.MX")]

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_INSTRUMENT), context={"source": "user"}
    )
    with patch(
        "custom_components.marketsentry.providers.finnhub.FinnhubProvider.resolve",
        side_effect=CannotConnect("ambiguous"),
    ), patch(
        "custom_components.marketsentry.providers.finnhub.FinnhubProvider.search",
        return_value=refs,
    ):
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"url_or_query": "apple"}
        )
    assert result["step_id"] == "select"


async def test_instrument_subentry_duplicate_aborts(hass: HomeAssistant) -> None:
    entry = await _create_finnhub_entry(hass)
    ref = _ref()
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data={"instrument_id": ref.id, "symbol": ref.symbol},
            subentry_type=SUBENTRY_TYPE_INSTRUMENT,
            title=ref.name,
            unique_id=ref.id,
        ),
    )

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_INSTRUMENT), context={"source": "user"}
    )
    with patch(
        "custom_components.marketsentry.providers.finnhub.FinnhubProvider.resolve",
        return_value=[ref],
    ):
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"url_or_query": "AAPL"}
        )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_instrument_subentry_reconfigure_updates_options(hass: HomeAssistant) -> None:
    entry = await _create_finnhub_entry(hass)
    subentry = ConfigSubentry(
        data={
            "instrument_id": "AAPL",
            "symbol": "AAPL",
            "instrument_name": "AAPL Inc",
            "instrument_kind": "stock",
            "unit": "USD",
            "options": {"thresholds": [], "cooldown_min": 15},
        },
        subentry_type=SUBENTRY_TYPE_INSTRUMENT,
        title="AAPL Inc",
        unique_id="AAPL",
    )
    hass.config_entries.async_add_subentry(entry, subentry)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_INSTRUMENT),
        context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
    )
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"thresholds": "150,160", "hysteresis": 0.0, "move_delta": 2.0, "move_window_min": 60, "cooldown_min": 30},
    )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    updated = hass.config_entries.async_get_entry(entry.entry_id).subentries[subentry.subentry_id]
    assert updated.data["options"]["thresholds"] == [150.0, 160.0]
    assert updated.data["options"]["cooldown_min"] == 30
