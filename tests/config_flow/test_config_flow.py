"""Tests for config_flow.py: provider picker, credentials, instrument subentries."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

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
    assert result["errors"]["base"] == "invalid_auth_finnhub"


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


async def test_first_instrument_ever_notifies_dashboard_strategy(hass: HomeAssistant) -> None:
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

    with patch(
        "custom_components.marketsentry.config_flow.async_create_notification"
    ) as mock_notify:
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {"thresholds": "", "hysteresis": 0.0, "move_delta": 2.0, "move_window_min": 60, "cooldown_min": 15},
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    mock_notify.assert_called_once()
    assert mock_notify.call_args.kwargs["notification_id"] == "marketsentry_dashboard_strategy"


async def test_second_instrument_does_not_renotify(hass: HomeAssistant) -> None:
    entry = await _create_finnhub_entry(hass)
    ref1 = _ref()
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data={"instrument_id": ref1.id, "symbol": ref1.symbol},
            subentry_type=SUBENTRY_TYPE_INSTRUMENT,
            title=ref1.name,
            unique_id=ref1.id,
        ),
    )

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_INSTRUMENT), context={"source": "user"}
    )
    with patch(
        "custom_components.marketsentry.providers.finnhub.FinnhubProvider.resolve",
        return_value=[_ref("MSFT", "MSFT")],
    ):
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"url_or_query": "MSFT"}
        )

    with patch(
        "custom_components.marketsentry.config_flow.async_create_notification"
    ) as mock_notify:
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {"thresholds": "", "hysteresis": 0.0, "move_delta": 2.0, "move_window_min": 60, "cooldown_min": 15},
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    mock_notify.assert_not_called()


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


async def test_adding_instrument_subentry_reloads_entry_and_creates_entities(
    hass: HomeAssistant,
) -> None:
    """Adding a subentry must reload the entry so sensor.py actually runs for it.

    Regression test: async_setup_entry rebuilds trackers from entry.subentries,
    but without an update listener HA never re-invokes it after a subentry is
    added, so the new instrument silently got zero entities.
    """
    entry = await _create_finnhub_entry(hass)
    ref = _ref()

    with (
        patch(
            "custom_components.marketsentry.providers.finnhub.FinnhubProvider.resolve",
            return_value=[ref],
        ),
        patch(
            "custom_components.marketsentry.providers.finnhub.FinnhubProvider.fetch_snapshot",
            return_value={},
        ),
        patch(
            "custom_components.marketsentry.providers.finnhub.FinnhubProvider.stream",
            return_value=None,
        ),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_INSTRUMENT), context={"source": "user"}
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"url_or_query": "AAPL"}
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {"thresholds": "", "hysteresis": 0.0, "move_delta": 2.0, "move_window_min": 60, "cooldown_min": 15},
        )
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entries_for_entry = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    assert any((e.unique_id or "").endswith("_price") for e in entries_for_entry)


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


async def test_instrument_subentry_quantity_option_round_trips(hass: HomeAssistant) -> None:
    """ENH-011: the optional "quantity held" field, same string-encoded-in-
    the-form/parsed-to-float-or-None pattern as `thresholds`. A blank value
    must parse to `None` (not 0), so a pure-watchlist instrument is
    unaffected, and a previously-set value must come back as the
    reconfigure form's own default (`_options_schema` reading back what
    `_parse_options_form` stored)."""
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
        {
            "thresholds": "",
            "hysteresis": 0.0,
            "move_delta": 2.0,
            "move_window_min": 60,
            "cooldown_min": 15,
            "quantity": "12.5",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["options"]["quantity"] == 12.5

    live_entry = hass.config_entries.async_get_entry(entry.entry_id)
    subentry = next(iter(live_entry.subentries.values()))

    reconfig = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_INSTRUMENT),
        context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
    )
    assert reconfig["step_id"] == "reconfigure"
    # The 12.5 just stored is re-offered as the form's own default.
    assert reconfig["data_schema"]({})["quantity"] == "12.5"

    cleared = await hass.config_entries.subentries.async_configure(
        reconfig["flow_id"],
        {
            "thresholds": "",
            "hysteresis": 0.0,
            "move_delta": 2.0,
            "move_window_min": 60,
            "cooldown_min": 15,
            "quantity": "",
        },
    )
    assert cleared["type"] == data_entry_flow.FlowResultType.ABORT
    assert cleared["reason"] == "reconfigure_successful"

    updated = hass.config_entries.async_get_entry(entry.entry_id).subentries[subentry.subentry_id]
    assert updated.data["options"]["quantity"] is None


async def test_instrument_subentry_cost_basis_option_round_trips(hass: HomeAssistant) -> None:
    """ENH-012: the optional "cost basis per unit" field, same
    string-encoded-in-the-form/parsed-to-float-or-None pattern as
    `quantity` (D-031: shares the field's shape). A blank value must parse
    to `None` (not 0), and a previously-set value must come back as the
    reconfigure form's own default."""
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
        {
            "thresholds": "",
            "hysteresis": 0.0,
            "move_delta": 2.0,
            "move_window_min": 60,
            "cooldown_min": 15,
            "quantity": "",
            "cost_basis": "142.75",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["options"]["cost_basis"] == 142.75

    live_entry = hass.config_entries.async_get_entry(entry.entry_id)
    subentry = next(iter(live_entry.subentries.values()))

    reconfig = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_INSTRUMENT),
        context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
    )
    assert reconfig["step_id"] == "reconfigure"
    # The 142.75 just stored is re-offered as the form's own default.
    assert reconfig["data_schema"]({})["cost_basis"] == "142.75"

    cleared = await hass.config_entries.subentries.async_configure(
        reconfig["flow_id"],
        {
            "thresholds": "",
            "hysteresis": 0.0,
            "move_delta": 2.0,
            "move_window_min": 60,
            "cooldown_min": 15,
            "quantity": "",
            "cost_basis": "",
        },
    )
    assert cleared["type"] == data_entry_flow.FlowResultType.ABORT
    assert cleared["reason"] == "reconfigure_successful"

    updated = hass.config_entries.async_get_entry(entry.entry_id).subentries[subentry.subentry_id]
    assert updated.data["options"]["cost_basis"] is None
