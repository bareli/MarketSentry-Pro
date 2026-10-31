"""HA `event` platform entities for MarketSentry Pro detections."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SIGNAL_DETECTED_EVENT, InstrumentTracker, MarketSentryConfigEntry
from .const import EVENT_TYPES_BY_KIND
from .detector import DetectedEvent
from .entity import instrument_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: MarketSentryConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    runtime = entry.runtime_data
    for subentry_id, tracker in runtime.trackers.items():
        async_add_entities(
            [DetectionEvent(entry.entry_id, tracker)], config_subentry_id=subentry_id
        )


class DetectionEvent(EventEntity):
    """Fires for every detection type that applies to this instrument's kind."""

    _attr_has_entity_name = True
    _attr_translation_key = "detections"

    def __init__(self, entry_id: str, tracker: InstrumentTracker) -> None:
        self._tracker = tracker
        self._attr_unique_id = f"{tracker.subentry_id}_detections"
        self._attr_device_info = instrument_device_info(entry_id, tracker.ref)
        self._attr_event_types = EVENT_TYPES_BY_KIND[tracker.ref.kind]

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_DETECTED_EVENT}_{self._tracker.subentry_id}",
                self._handle_detected_event,
            )
        )

    @callback
    def _handle_detected_event(self, event: DetectedEvent, payload: dict[str, Any]) -> None:
        self._trigger_event(event.event_type, payload)
        self.async_write_ha_state()
