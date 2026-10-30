"""Binary sensor platform for Polymarket Watch."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SIGNAL_WS_STATE, PolymarketWatchConfigEntry, PolymarketWatchGlobalData
from .const import DOMAIN
from .coordinator import PolymarketMetadataCoordinator
from .entity import PolymarketEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: PolymarketWatchConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tracker = entry.runtime_data.tracker
    coordinator = tracker.coordinator

    async_add_entities(
        [
            ClosedBinarySensor(coordinator, tracker.market_slug, entry.title),
            AcceptingOrdersBinarySensor(coordinator, tracker.market_slug, entry.title),
            WebSocketConnectedBinarySensor(coordinator, tracker.market_slug, entry.title, hass),
        ]
    )


class ClosedBinarySensor(PolymarketEntity, BinarySensorEntity):
    _attr_translation_key = "closed"

    def __init__(
        self, coordinator: PolymarketMetadataCoordinator, market_slug: str, question: str
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._attr_unique_id = f"{market_slug}_closed"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.market.closed if self.coordinator.data else None


class AcceptingOrdersBinarySensor(PolymarketEntity, BinarySensorEntity):
    _attr_translation_key = "accepting_orders"

    def __init__(
        self, coordinator: PolymarketMetadataCoordinator, market_slug: str, question: str
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._attr_unique_id = f"{market_slug}_accepting_orders"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.market.accepting_orders if self.coordinator.data else None


class WebSocketConnectedBinarySensor(PolymarketEntity, BinarySensorEntity):
    """Integration-level WS health, exposed as a diagnostic on each tracked market's device."""

    _attr_translation_key = "ws_connected"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: PolymarketMetadataCoordinator,
        market_slug: str,
        question: str,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._attr_unique_id = f"{market_slug}_ws_connected"
        self._hass = hass
        self._is_on: bool | None = None

    @property
    def is_on(self) -> bool | None:
        global_data: PolymarketWatchGlobalData | None = self._hass.data.get(DOMAIN)
        if global_data is None:
            return None
        return global_data.ws_manager.connected

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self._hass, SIGNAL_WS_STATE, self._handle_ws_state)
        )

    @callback
    def _handle_ws_state(self, _connected: bool) -> None:
        self.async_write_ha_state()
