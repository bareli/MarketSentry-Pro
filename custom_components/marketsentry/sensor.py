"""Sensor platform for MarketSentry Pro."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SIGNAL_QUOTE_UPDATE, SIGNAL_TRADE, MarketSentryConfigEntry, OutcomeTracker
from .const import (
    STATUS_CLOSED,
    STATUS_DISPUTED,
    STATUS_OPEN,
    STATUS_PROPOSED,
    STATUS_RESOLVED,
)
from .coordinator import PolymarketMetadataCoordinator
from .entity import PolymarketEntity
from .models import Quote, Trade


async def async_setup_entry(
    hass: HomeAssistant, entry: MarketSentryConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tracker = entry.runtime_data.tracker
    coordinator = tracker.coordinator

    entities: list[SensorEntity] = []
    for outcome_tracker in tracker.outcomes.values():
        entities.append(
            OutcomeProbabilitySensor(coordinator, tracker.market_slug, entry.title, outcome_tracker)
        )
        entities.append(
            OutcomeLastTradePriceSensor(coordinator, tracker.market_slug, entry.title, outcome_tracker)
        )
        entities.append(
            OutcomeSpreadSensor(coordinator, tracker.market_slug, entry.title, outcome_tracker)
        )

    entities.append(Volume24hrSensor(coordinator, tracker.market_slug, entry.title))
    entities.append(TotalVolumeSensor(coordinator, tracker.market_slug, entry.title))
    entities.append(LiquiditySensor(coordinator, tracker.market_slug, entry.title))
    entities.append(EndDateSensor(coordinator, tracker.market_slug, entry.title))
    entities.append(ResolutionStatusSensor(coordinator, tracker.market_slug, entry.title))
    entities.append(WinningOutcomeSensor(coordinator, tracker.market_slug, entry.title))

    async_add_entities(entities)


class OutcomeProbabilitySensor(PolymarketEntity, SensorEntity):
    """Live probability (midpoint) for one outcome, in percent."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 1
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_unrecorded_attributes = frozenset({"best_bid", "best_ask", "spread"})

    def __init__(
        self,
        coordinator: PolymarketMetadataCoordinator,
        market_slug: str,
        question: str,
        outcome_tracker: OutcomeTracker,
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._outcome_tracker = outcome_tracker
        self._attr_unique_id = f"{market_slug}_{outcome_tracker.token_id}_probability"
        self._attr_translation_key = "probability"
        self._attr_translation_placeholders = {"outcome": outcome_tracker.outcome_name}
        self._attr_name = f"{outcome_tracker.outcome_name} probability"

    @property
    def native_value(self) -> float | None:
        mid = self._outcome_tracker.quote.midpoint
        return round(mid * 100, 1) if mid is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        quote: Quote = self._outcome_tracker.quote
        spread = None
        if quote.best_bid is not None and quote.best_ask is not None:
            spread = round((quote.best_ask - quote.best_bid) * 100, 2)
        return {
            "token_id": quote.token_id,
            "best_bid": quote.best_bid,
            "best_ask": quote.best_ask,
            "spread": spread,
            "last_update": quote.timestamp.isoformat() if quote.timestamp else None,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_QUOTE_UPDATE}_{self._outcome_tracker.token_id}",
                self._handle_quote_update,
            )
        )

    @callback
    def _handle_quote_update(self, quote: Quote) -> None:
        mid = quote.midpoint
        new_value = round(mid * 100, 1) if mid is not None else None
        if self._should_write_throttled(new_value):
            self.async_write_ha_state()


class OutcomeLastTradePriceSensor(PolymarketEntity, SensorEntity):
    """Last traded price for one outcome, in percent."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 1
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = True

    def __init__(
        self,
        coordinator: PolymarketMetadataCoordinator,
        market_slug: str,
        question: str,
        outcome_tracker: OutcomeTracker,
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._outcome_tracker = outcome_tracker
        self._attr_unique_id = f"{market_slug}_{outcome_tracker.token_id}_last_trade_price"
        self._attr_translation_key = "last_trade_price"
        self._attr_translation_placeholders = {"outcome": outcome_tracker.outcome_name}
        self._attr_name = f"{outcome_tracker.outcome_name} last trade price"

    @property
    def native_value(self) -> float | None:
        price = self._outcome_tracker.quote.last_trade_price
        return round(price * 100, 1) if price is not None else None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_TRADE}_{self._outcome_tracker.token_id}",
                self._handle_trade,
            )
        )

    @callback
    def _handle_trade(self, trade: Trade) -> None:
        new_value = round(trade.price * 100, 1)
        if self._should_write_throttled(new_value):
            self.async_write_ha_state()


class OutcomeSpreadSensor(PolymarketEntity, SensorEntity):
    """Bid/ask spread for one outcome, in percentage points. Diagnostic."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 2
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: PolymarketMetadataCoordinator,
        market_slug: str,
        question: str,
        outcome_tracker: OutcomeTracker,
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._outcome_tracker = outcome_tracker
        self._attr_unique_id = f"{market_slug}_{outcome_tracker.token_id}_spread"
        self._attr_translation_key = "spread"
        self._attr_translation_placeholders = {"outcome": outcome_tracker.outcome_name}
        self._attr_name = f"{outcome_tracker.outcome_name} spread"

    @property
    def native_value(self) -> float | None:
        quote = self._outcome_tracker.quote
        if quote.best_bid is None or quote.best_ask is None:
            return None
        return round((quote.best_ask - quote.best_bid) * 100, 2)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_QUOTE_UPDATE}_{self._outcome_tracker.token_id}",
                self._handle_quote_update,
            )
        )

    @callback
    def _handle_quote_update(self, _quote: Quote) -> None:
        if self._should_write_throttled(self.native_value):
            self.async_write_ha_state()


class _MetadataSensor(PolymarketEntity, SensorEntity):
    """Base for sensors sourced purely from the Gamma metadata coordinator."""

    def __init__(
        self, coordinator: PolymarketMetadataCoordinator, market_slug: str, question: str
    ) -> None:
        super().__init__(coordinator, market_slug, question)


class Volume24hrSensor(_MetadataSensor):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "volume_24hr"

    def __init__(
        self, coordinator: PolymarketMetadataCoordinator, market_slug: str, question: str
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._attr_unique_id = f"{market_slug}_volume_24hr"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.market.volume_24hr if self.coordinator.data else None


class TotalVolumeSensor(_MetadataSensor):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_translation_key = "total_volume"

    def __init__(
        self, coordinator: PolymarketMetadataCoordinator, market_slug: str, question: str
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._attr_unique_id = f"{market_slug}_total_volume"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.market.volume if self.coordinator.data else None


class LiquiditySensor(_MetadataSensor):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "liquidity"

    def __init__(
        self, coordinator: PolymarketMetadataCoordinator, market_slug: str, question: str
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._attr_unique_id = f"{market_slug}_liquidity"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.market.liquidity if self.coordinator.data else None


class EndDateSensor(_MetadataSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "end_date"

    def __init__(
        self, coordinator: PolymarketMetadataCoordinator, market_slug: str, question: str
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._attr_unique_id = f"{market_slug}_end_date"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data.market.end_date if self.coordinator.data else None


class ResolutionStatusSensor(_MetadataSensor):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [STATUS_OPEN, STATUS_PROPOSED, STATUS_DISPUTED, STATUS_RESOLVED, STATUS_CLOSED]
    _attr_translation_key = "resolution_status"

    def __init__(
        self, coordinator: PolymarketMetadataCoordinator, market_slug: str, question: str
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._attr_unique_id = f"{market_slug}_resolution_status"

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        market = self.coordinator.data.market
        status = (market.uma_resolution_status or "").lower()
        if status in (STATUS_PROPOSED, STATUS_DISPUTED, STATUS_RESOLVED):
            return status
        if market.closed:
            return STATUS_CLOSED
        return STATUS_OPEN


class WinningOutcomeSensor(_MetadataSensor):
    _attr_translation_key = "winning_outcome"

    def __init__(
        self, coordinator: PolymarketMetadataCoordinator, market_slug: str, question: str
    ) -> None:
        super().__init__(coordinator, market_slug, question)
        self._attr_unique_id = f"{market_slug}_winning_outcome"

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        market = self.coordinator.data.market
        if (market.uma_resolution_status or "").lower() != STATUS_RESOLVED:
            return None
        for outcome in market.outcomes:
            if outcome.price is not None and outcome.price >= 0.99:
                return outcome.name
        return None
