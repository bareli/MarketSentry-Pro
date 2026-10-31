"""WebSocket API for the marketsentry-card frontend: sparkline history.

The card's instrument list itself is read directly from `hass.states` /
`hass.entities` (standard HA card pattern - see each primary sensor's
`kind`/`provider`/`url` extra_state_attributes), so only history needs a
custom command.
"""

from __future__ import annotations

from typing import Any, cast

import voluptuous as vol
from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.const import ERR_NOT_FOUND
from homeassistant.components.websocket_api.decorators import websocket_command
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .history import PriceRingBuffer
from .services import _find_tracker_for_device

_HISTORY_BUFFER_KEY = "history_buffer"


@callback
def async_get_history_buffer(hass: HomeAssistant) -> PriceRingBuffer:
    """Return the shared ring buffer, creating it on first use."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    buffer = domain_data.get(_HISTORY_BUFFER_KEY)
    if buffer is None:
        buffer = PriceRingBuffer()
        domain_data[_HISTORY_BUFFER_KEY] = buffer
    return cast(PriceRingBuffer, buffer)


@callback
def async_setup_websocket_api(hass: HomeAssistant) -> None:
    """Register the `marketsentry/history` WS command. Safe to call once."""
    async_register_command(hass, websocket_history)


@websocket_command(
    {
        vol.Required("type"): "marketsentry/history",
        vol.Required("device_id"): str,
    }
)
@callback
def websocket_history(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None:
    """Return the sparkline ring-buffer history for one tracked instrument."""
    try:
        _entry, tracker = _find_tracker_for_device(hass, msg["device_id"])
    except ValueError as err:
        connection.send_error(msg["id"], ERR_NOT_FOUND, str(err))
        return

    points = async_get_history_buffer(hass).get(tracker.ref.id)
    connection.send_result(
        msg["id"],
        {"history": [{"t": point.ts.isoformat(), "p": point.price} for point in points]},
    )
