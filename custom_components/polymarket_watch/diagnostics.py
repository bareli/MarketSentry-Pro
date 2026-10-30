"""Diagnostics for Polymarket Watch. Nothing sensitive to redact (read-only, no auth)."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import PolymarketWatchConfigEntry
from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PolymarketWatchConfigEntry
) -> dict[str, Any]:
    tracker = entry.runtime_data.tracker
    global_data = hass.data.get(DOMAIN)

    outcomes_diag = {
        token_id: {
            "outcome_name": ot.outcome_name,
            "best_bid": ot.quote.best_bid,
            "best_ask": ot.quote.best_ask,
            "last_trade_price": ot.quote.last_trade_price,
            "last_update": ot.quote.timestamp.isoformat() if ot.quote.timestamp else None,
        }
        for token_id, ot in tracker.outcomes.items()
    }

    ws_diag: dict[str, Any] = {"available": global_data is not None}
    if global_data is not None:
        ws_diag.update(
            {
                "connected": global_data.ws_manager.connected,
                "subscribed_token_count": global_data.ws_manager.subscribed_token_count,
                "last_message_age_sec": global_data.ws_manager.last_message_age_sec,
                "ws_down_since": global_data.ws_down_since,
            }
        )

    return {
        "market_slug": tracker.market_slug,
        "coordinator_last_update_success": tracker.coordinator.last_update_success,
        "outcomes": outcomes_diag,
        "websocket": ws_diag,
    }
