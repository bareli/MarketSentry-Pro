"""HA `event` platform entities for Polymarket Watch detections."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SIGNAL_DETECTED_EVENT, PolymarketWatchConfigEntry
from .const import EVENT_TYPES
from .detector import DetectedEvent
from .entity import market_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: PolymarketWatchConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tracker = entry.runtime_data.tracker
    async_add_entities([PolymarketDetectionEvent(entry, tracker.market_slug)])


class PolymarketDetectionEvent(EventEntity):
    """Fires for every detected change: threshold_crossed, price_move, etc."""

    _attr_has_entity_name = True
    _attr_translation_key = "detections"
    _attr_event_types = EVENT_TYPES

    def __init__(self, entry: PolymarketWatchConfigEntry, market_slug: str) -> None:
        self._entry = entry
        self._market_slug = market_slug
        self._attr_unique_id = f"{market_slug}_detections"
        self._attr_device_info = market_device_info(market_slug, entry.title)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_DETECTED_EVENT}_{self._entry.entry_id}",
                self._handle_detected_event,
            )
        )

    @callback
    def _handle_detected_event(self, event: DetectedEvent, payload: dict[str, Any]) -> None:
        self._trigger_event(event.event_type, payload)
        self.async_write_ha_state()
