"""Diagnostics for MarketSentry Pro.

Credentials (Finnhub/Alpaca) are the only sensitive data this integration
holds; everything else is public market data read without auth.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import MarketSentryConfigEntry
from .const import CONF_API_KEY, CONF_KEY_ID, CONF_PROVIDER, CONF_SECRET_KEY

TO_REDACT = {CONF_API_KEY, CONF_KEY_ID, CONF_SECRET_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MarketSentryConfigEntry
) -> dict[str, Any]:
    runtime = entry.runtime_data

    trackers_diag = {
        subentry_id: {
            "kind": tracker.ref.kind,
            "symbol": tracker.ref.symbol,
            "last_price": tracker.last_quote.price,
            "last_update": tracker.last_quote.ts.isoformat() if tracker.last_quote.ts else None,
            "last_trade_price": tracker.last_trade.price if tracker.last_trade else None,
        }
        for subentry_id, tracker in runtime.trackers.items()
    }

    polymarket_metadata_diag = {
        slug: {"last_update_success": coordinator.last_update_success}
        for slug, coordinator in runtime.polymarket_metadata.items()
    }

    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "provider": entry.data.get(CONF_PROVIDER),
        "snapshot_coordinator_last_update_success": runtime.snapshot_coordinator.last_update_success,
        "stream_connected": runtime.stream_connected,
        "stream_phase": runtime.stream_phase,
        "stream_reconnect_count": runtime.stream_reconnect_count,
        "trackers": trackers_diag,
        "polymarket_metadata": polymarket_metadata_diag,
    }
