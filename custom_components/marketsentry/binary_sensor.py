"""Binary sensor platform for MarketSentry Pro."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SIGNAL_STREAM_STATE, InstrumentTracker, MarketSentryConfigEntry
from .coordinator import PolymarketMetadataCoordinator
from .entity import instrument_device_info, provider_connection_device_info
from .providers.base import StreamStatus

_RECONNECTING_PHASES = {"reconnecting", "backing_off"}


async def async_setup_entry(
    hass: HomeAssistant, entry: MarketSentryConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    runtime = entry.runtime_data

    for subentry_id, tracker in runtime.trackers.items():
        if tracker.ref.kind != "outcome":
            continue
        market_slug = tracker.ref.extra.get("market_slug")
        metadata_coordinator = runtime.polymarket_metadata.get(market_slug) if market_slug else None
        if metadata_coordinator is None:
            continue
        async_add_entities(
            [
                ClosedBinarySensor(metadata_coordinator, entry.entry_id, tracker),
                AcceptingOrdersBinarySensor(metadata_coordinator, entry.entry_id, tracker),
            ],
            config_subentry_id=subentry_id,
        )

    if runtime.provider.supports_streaming:
        async_add_entities([StreamConnectedBinarySensor(entry)])


class _MetadataBinarySensor(CoordinatorEntity[PolymarketMetadataCoordinator], BinarySensorEntity):
    """Base for outcome binary sensors sourced from Polymarket's Gamma metadata."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: PolymarketMetadataCoordinator, entry_id: str, tracker: InstrumentTracker
    ) -> None:
        super().__init__(coordinator)
        self._tracker = tracker
        self._attr_device_info = instrument_device_info(entry_id, tracker.ref)


class ClosedBinarySensor(_MetadataBinarySensor):
    _attr_translation_key = "closed"

    def __init__(self, coordinator: PolymarketMetadataCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker)
        self._attr_unique_id = f"{tracker.subentry_id}_closed"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.market.closed if self.coordinator.data else None


class AcceptingOrdersBinarySensor(_MetadataBinarySensor):
    _attr_translation_key = "accepting_orders"

    def __init__(self, coordinator: PolymarketMetadataCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker)
        self._attr_unique_id = f"{tracker.subentry_id}_accepting_orders"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.market.accepting_orders if self.coordinator.data else None


class StreamConnectedBinarySensor(BinarySensorEntity):
    """Entry-level: is this provider account's streaming connection up?

    `is_on` reflects the real connection phase each provider's `stream()`
    loop reports via its `on_status` callback (ENH-007), not just "the
    asyncio task hasn't died" - it reads False while connecting, reconnecting,
    or backing off, and True only once a connection is actually established.
    The `reconnecting`/`reconnect_count` attributes surface the finer-grained
    phase without adding a third on/off state, keeping the existing binary
    on/off contract backward compatible for anyone templating on it.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "stream_connected"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: MarketSentryConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_stream_connected"
        self._attr_device_info = provider_connection_device_info(entry, entry.runtime_data.provider_name)

    @property
    def is_on(self) -> bool:
        return self._entry.runtime_data.stream_connected

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        runtime = self._entry.runtime_data
        return {
            "reconnecting": runtime.stream_phase in _RECONNECTING_PHASES,
            "reconnect_count": runtime.stream_reconnect_count,
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{SIGNAL_STREAM_STATE}_{self._entry.entry_id}", self._handle_stream_state
            )
        )

    @callback
    def _handle_stream_state(self, _status: StreamStatus) -> None:
        self.async_write_ha_state()
