"""Sensor platform for MarketSentry Pro, kind-conditional per instrument."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SIGNAL_QUOTE_UPDATE, SIGNAL_TRADE_UPDATE, InstrumentTracker, MarketSentryConfigEntry
from .const import (
    MARKET_STATE_CLOSED,
    MARKET_STATE_POST,
    MARKET_STATE_PRE,
    MARKET_STATE_REGULAR,
    OPT_COST_BASIS,
    OPT_QUANTITY,
    STATUS_CLOSED,
    STATUS_DISPUTED,
    STATUS_OPEN,
    STATUS_PROPOSED,
    STATUS_RESOLVED,
)
from .coordinator import PolymarketMetadataCoordinator, ProviderSnapshotCoordinator
from .entity import (
    InstrumentEntity,
    card_attributes,
    instrument_device_info,
    provider_connection_device_info,
)
from .market_calendar import market_state as calc_market_state
from .providers.base import InstrumentRef, Quote, Trade


def _position_value(ref: InstrumentRef, quantity: float | None, price: float | None) -> float | None:
    """quantity x the same current-price value this instrument's primary
    sensor already exposes as its native state (ENH-011): percent-scaled
    for `outcome` so it matches `ProbabilitySensor.native_value`, the raw
    quote price otherwise. `None` when quantity isn't set or there's no
    live price yet - never 0, so an untracked position reads "unknown"
    rather than a misleading zero."""
    if quantity is None or price is None:
        return None
    native_price = price * 100 if ref.kind == "outcome" else price
    return quantity * native_price


def _unrealized_pnl(
    quantity: float | None, cost_basis: float | None, price: float | None, is_outcome: bool
) -> tuple[float | None, float | None]:
    """Unrealized P&L (absolute, then percent) for ENH-012. Same
    percent-scaling convention as `_position_value`: for `outcome`, `price`
    is scaled to the same 0-100 percent terms `cost_basis` is entered in
    (matching `ProbabilitySensor.native_value`), raw otherwise. `None, None`
    when quantity or cost_basis isn't set - cost_basis is what makes P&L
    computable at all, so it gates this the way price alone gates
    `_position_value`."""
    if quantity is None or cost_basis is None or price is None:
        return None, None
    native_price = price * 100 if is_outcome else price
    pnl = quantity * (native_price - cost_basis)
    cost = quantity * cost_basis
    pnl_pct = (pnl / cost) * 100 if cost else None
    return pnl, pnl_pct


# Per-kind translated name for the entry-level position-value total
# sensors below. Per D-017/D-028: per-kind subtotals only, no cross-kind
# normalization.
_POSITION_VALUE_TOTAL_TRANSLATION_KEY = {
    "outcome": "outcomes_total",
    "stock": "stocks_total",
    "crypto": "crypto_total",
    "fx": "fx_total",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: MarketSentryConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    runtime = entry.runtime_data
    coordinator = runtime.snapshot_coordinator

    for subentry_id, tracker in runtime.trackers.items():
        entities: list[SensorEntity] = []
        kind = tracker.ref.kind

        if kind == "outcome":
            entities.append(ProbabilitySensor(coordinator, entry.entry_id, tracker))
            entities.append(LastTradePriceSensor(coordinator, entry.entry_id, tracker))
            entities.append(SpreadSensor(coordinator, entry.entry_id, tracker))

            market_slug = tracker.ref.extra.get("market_slug")
            metadata_coordinator = (
                runtime.polymarket_metadata.get(market_slug) if market_slug else None
            )
            if metadata_coordinator is not None:
                entities.extend(
                    [
                        Volume24hrSensor(metadata_coordinator, entry.entry_id, tracker),
                        TotalVolumeSensor(metadata_coordinator, entry.entry_id, tracker),
                        LiquiditySensor(metadata_coordinator, entry.entry_id, tracker),
                        EndDateSensor(metadata_coordinator, entry.entry_id, tracker),
                        ResolutionStatusSensor(metadata_coordinator, entry.entry_id, tracker),
                        WinningOutcomeSensor(metadata_coordinator, entry.entry_id, tracker),
                    ]
                )
        elif kind == "stock":
            entities.append(PriceSensor(coordinator, entry.entry_id, tracker))
            entities.append(PreviousCloseSensor(coordinator, entry.entry_id, tracker))
            entities.append(MarketStateSensor(coordinator, entry.entry_id, tracker))
        elif kind == "crypto":
            entities.append(PriceSensor(coordinator, entry.entry_id, tracker))
        else:  # fx
            entities.append(RateSensor(coordinator, entry.entry_id, tracker))

        async_add_entities(entities, config_subentry_id=subentry_id)

    # Entry-level aggregate totals (ENH-011): one per (kind, unit) actually
    # present among this entry's instruments, not per subentry - grouped by
    # unit as well as kind so a provider account that ever mixes quote
    # currencies within one kind (e.g. an fx entry with both EUR/ILS and
    # EUR/USD pairs) never silently sums two currencies together. This
    # naturally tracks the entry's reload-on-subentry-change: added/removed
    # as whole groups appear/disappear, not per quantity edit.
    position_value_groups: dict[tuple[str, str], list[InstrumentTracker]] = {}
    for tracker in runtime.trackers.values():
        position_value_groups.setdefault((tracker.ref.kind, tracker.ref.unit), []).append(tracker)

    aggregate_entities = [
        PositionValueTotalSensor(entry, runtime.provider_name, kind, unit, group)
        for (kind, unit), group in position_value_groups.items()
    ]
    if aggregate_entities:
        async_add_entities(aggregate_entities)


class ProbabilitySensor(InstrumentEntity, SensorEntity):
    """Live probability (midpoint) for one Polymarket outcome, in percent."""

    _attr_native_unit_of_measurement = "%"
    _attr_suggested_display_precision = 1
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "probability"
    _attr_unrecorded_attributes = frozenset(
        {"best_bid", "best_ask", "spread", "change_pp", "position_value", "unrealized_pnl", "unrealized_pnl_pct"}
    )

    def __init__(self, coordinator: ProviderSnapshotCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker.ref)
        self._tracker = tracker
        self._attr_unique_id = f"{tracker.subentry_id}_probability"

    @property
    def native_value(self) -> float | None:
        price = self._tracker.last_quote.price
        return round(price * 100, 1) if price is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        quote = self._tracker.last_quote
        spread = None
        if quote.bid is not None and quote.ask is not None:
            spread = round((quote.ask - quote.bid) * 100, 2)
        move = self._tracker.detectors.move.last_delta
        position_value = _position_value(
            self._tracker.ref, self._tracker.options.get(OPT_QUANTITY), quote.price
        )
        pnl, pnl_pct = _unrealized_pnl(
            self._tracker.options.get(OPT_QUANTITY),
            self._tracker.options.get(OPT_COST_BASIS),
            quote.price,
            is_outcome=True,
        )
        return {
            **card_attributes(self._tracker.ref),
            "best_bid": quote.bid,
            "best_ask": quote.ask,
            "spread": spread,
            "last_update": quote.ts.isoformat() if quote.ts else None,
            # The exact windowed delta (percentage points) PriceMoveDetector
            # uses to decide whether to fire `price_move` - not a card-side
            # approximation from the sparkline buffer (ENH-009).
            "change_pp": round(move, 1) if move is not None else None,
            # quantity x price (ENH-011), None until a quantity is set.
            "position_value": round(position_value, 2) if position_value is not None else None,
            # quantity x (price - cost_basis) (ENH-012), None until both
            # quantity and cost_basis are set.
            "unrealized_pnl": round(pnl, 2) if pnl is not None else None,
            "unrealized_pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_QUOTE_UPDATE}_{self._tracker.subentry_id}",
                self._handle_quote_update,
            )
        )

    @callback
    def _handle_quote_update(self, quote: Quote) -> None:
        new_value = round(quote.price * 100, 1) if quote.price is not None else None
        if self._should_write_throttled(new_value):
            self.async_write_ha_state()


class LastTradePriceSensor(InstrumentEntity, SensorEntity):
    """Last traded price for one Polymarket outcome, in percent."""

    _attr_native_unit_of_measurement = "%"
    _attr_suggested_display_precision = 1
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "last_trade_price"

    def __init__(self, coordinator: ProviderSnapshotCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker.ref)
        self._tracker = tracker
        self._attr_unique_id = f"{tracker.subentry_id}_last_trade_price"

    @property
    def native_value(self) -> float | None:
        trade = self._tracker.last_trade
        return round(trade.price * 100, 1) if trade is not None else None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_TRADE_UPDATE}_{self._tracker.subentry_id}",
                self._handle_trade,
            )
        )

    @callback
    def _handle_trade(self, trade: Trade) -> None:
        if self._should_write_throttled(round(trade.price * 100, 1)):
            self.async_write_ha_state()


class SpreadSensor(InstrumentEntity, SensorEntity):
    """Bid/ask spread for one Polymarket outcome, in percentage points. Diagnostic."""

    _attr_native_unit_of_measurement = "%"
    _attr_suggested_display_precision = 2
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "spread"

    def __init__(self, coordinator: ProviderSnapshotCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker.ref)
        self._tracker = tracker
        self._attr_unique_id = f"{tracker.subentry_id}_spread"

    @property
    def native_value(self) -> float | None:
        quote = self._tracker.last_quote
        if quote.bid is None or quote.ask is None:
            return None
        return round((quote.ask - quote.bid) * 100, 2)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_QUOTE_UPDATE}_{self._tracker.subentry_id}",
                self._handle_quote_update,
            )
        )

    @callback
    def _handle_quote_update(self, _quote: Quote) -> None:
        if self._should_write_throttled(self.native_value):
            self.async_write_ha_state()


class PriceSensor(InstrumentEntity, SensorEntity):
    """Live price for one stock, in its quote currency (USD)."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "price"
    _attr_unrecorded_attributes = frozenset(
        {"change_pct", "position_value", "unrealized_pnl", "unrealized_pnl_pct"}
    )

    def __init__(self, coordinator: ProviderSnapshotCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker.ref)
        self._tracker = tracker
        self._attr_unique_id = f"{tracker.subentry_id}_price"
        self._attr_native_unit_of_measurement = tracker.ref.unit

    @property
    def native_value(self) -> float | None:
        return self._tracker.last_quote.price

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        daily_change = self._tracker.detectors.daily_change
        change_pct = daily_change.last_change_pct if daily_change is not None else None
        position_value = _position_value(
            self._tracker.ref, self._tracker.options.get(OPT_QUANTITY), self._tracker.last_quote.price
        )
        pnl, pnl_pct = _unrealized_pnl(
            self._tracker.options.get(OPT_QUANTITY),
            self._tracker.options.get(OPT_COST_BASIS),
            self._tracker.last_quote.price,
            is_outcome=False,
        )
        return {
            **card_attributes(self._tracker.ref),
            # The exact windowed change (%) DailyChangeDetector uses to
            # decide whether to fire `daily_change` - not a card-side
            # approximation from the sparkline buffer (ENH-009).
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            # quantity x price (ENH-011), None until a quantity is set.
            "position_value": round(position_value, 2) if position_value is not None else None,
            # quantity x (price - cost_basis) (ENH-012), None until both
            # quantity and cost_basis are set.
            "unrealized_pnl": round(pnl, 2) if pnl is not None else None,
            "unrealized_pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_QUOTE_UPDATE}_{self._tracker.subentry_id}",
                self._handle_quote_update,
            )
        )

    @callback
    def _handle_quote_update(self, quote: Quote) -> None:
        if self._should_write_throttled(quote.price):
            self.async_write_ha_state()


class PreviousCloseSensor(InstrumentEntity, SensorEntity):
    """Previous session's close price for one stock."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "previous_close"

    def __init__(self, coordinator: ProviderSnapshotCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker.ref)
        self._tracker = tracker
        self._attr_unique_id = f"{tracker.subentry_id}_previous_close"
        self._attr_native_unit_of_measurement = tracker.ref.unit

    @property
    def native_value(self) -> float | None:
        return self._tracker.last_quote.previous_close


class MarketStateSensor(InstrumentEntity, SensorEntity):
    """NYSE/NASDAQ session state for one stock: pre/regular/post/closed."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [MARKET_STATE_PRE, MARKET_STATE_REGULAR, MARKET_STATE_POST, MARKET_STATE_CLOSED]
    _attr_translation_key = "market_state"

    def __init__(self, coordinator: ProviderSnapshotCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker.ref)
        self._tracker = tracker
        self._attr_unique_id = f"{tracker.subentry_id}_market_state"

    @property
    def native_value(self) -> str:
        return calc_market_state(datetime.now(UTC))


class RateSensor(InstrumentEntity, SensorEntity):
    """Live exchange rate for one FX pair, in the quote currency."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 4
    _attr_translation_key = "rate"
    _attr_unrecorded_attributes = frozenset(
        {"change_pct", "position_value", "unrealized_pnl", "unrealized_pnl_pct"}
    )

    def __init__(self, coordinator: ProviderSnapshotCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker.ref)
        self._tracker = tracker
        self._attr_unique_id = f"{tracker.subentry_id}_rate"
        self._attr_native_unit_of_measurement = tracker.ref.unit

    @property
    def native_value(self) -> float | None:
        return self._tracker.last_quote.price

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        source, _base, _quote = self._tracker.ref.id.split(":")
        quote = self._tracker.last_quote
        daily_change = self._tracker.detectors.daily_change
        change_pct = daily_change.last_change_pct if daily_change is not None else None
        position_value = _position_value(
            self._tracker.ref, self._tracker.options.get(OPT_QUANTITY), quote.price
        )
        pnl, pnl_pct = _unrealized_pnl(
            self._tracker.options.get(OPT_QUANTITY),
            self._tracker.options.get(OPT_COST_BASIS),
            quote.price,
            is_outcome=False,
        )
        return {
            **card_attributes(self._tracker.ref),
            "source": "official (Bank of Israel)" if source == "boi" else "market (Frankfurter)",
            "published_date": quote.ts.date().isoformat() if quote.ts else None,
            # The exact windowed change (%) DailyChangeDetector uses to
            # decide whether to fire `daily_change` - not a card-side
            # approximation from the sparkline buffer (ENH-009).
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            # quantity x price (ENH-011), None until a quantity is set.
            "position_value": round(position_value, 2) if position_value is not None else None,
            # quantity x (price - cost_basis) (ENH-012), None until both
            # quantity and cost_basis are set.
            "unrealized_pnl": round(pnl, 2) if pnl is not None else None,
            "unrealized_pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_QUOTE_UPDATE}_{self._tracker.subentry_id}",
                self._handle_quote_update,
            )
        )

    @callback
    def _handle_quote_update(self, quote: Quote) -> None:
        if self._should_write_throttled(quote.price):
            self.async_write_ha_state()


class _MetadataSensor(CoordinatorEntity[PolymarketMetadataCoordinator], SensorEntity):
    """Base for sensors sourced from Polymarket's Gamma market metadata."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: PolymarketMetadataCoordinator, entry_id: str, tracker: InstrumentTracker
    ) -> None:
        super().__init__(coordinator)
        self._tracker = tracker
        self._attr_device_info = instrument_device_info(entry_id, tracker.ref)


class Volume24hrSensor(_MetadataSensor):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "volume_24hr"

    def __init__(self, coordinator: PolymarketMetadataCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker)
        self._attr_unique_id = f"{tracker.subentry_id}_volume_24hr"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.market.volume_24hr if self.coordinator.data else None


class TotalVolumeSensor(_MetadataSensor):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_translation_key = "total_volume"

    def __init__(self, coordinator: PolymarketMetadataCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker)
        self._attr_unique_id = f"{tracker.subentry_id}_total_volume"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.market.volume if self.coordinator.data else None


class LiquiditySensor(_MetadataSensor):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "liquidity"

    def __init__(self, coordinator: PolymarketMetadataCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker)
        self._attr_unique_id = f"{tracker.subentry_id}_liquidity"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.market.liquidity if self.coordinator.data else None


class EndDateSensor(_MetadataSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "end_date"

    def __init__(self, coordinator: PolymarketMetadataCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker)
        self._attr_unique_id = f"{tracker.subentry_id}_end_date"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data.market.end_date if self.coordinator.data else None


class ResolutionStatusSensor(_MetadataSensor):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [STATUS_OPEN, STATUS_PROPOSED, STATUS_DISPUTED, STATUS_RESOLVED, STATUS_CLOSED]
    _attr_translation_key = "resolution_status"

    def __init__(self, coordinator: PolymarketMetadataCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker)
        self._attr_unique_id = f"{tracker.subentry_id}_resolution_status"

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        market = self.coordinator.data.market
        status = (market.uma_resolution_status or "").lower()
        if status in (STATUS_PROPOSED, STATUS_DISPUTED, STATUS_RESOLVED):
            return status
        return STATUS_CLOSED if market.closed else STATUS_OPEN


class WinningOutcomeSensor(_MetadataSensor):
    _attr_translation_key = "winning_outcome"

    def __init__(self, coordinator: PolymarketMetadataCoordinator, entry_id: str, tracker: InstrumentTracker) -> None:
        super().__init__(coordinator, entry_id, tracker)
        self._attr_unique_id = f"{tracker.subentry_id}_winning_outcome"

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


class PositionValueTotalSensor(SensorEntity):
    """Entry-level: sum of `position_value` across this provider account's
    instruments of one kind (and quote unit) that have a quantity set
    (ENH-011). Not tied to any one instrument's device - it aggregates
    across all of them, so it lives on the provider's own connection
    device, like `StreamConnectedBinarySensor`.

    Grouped by (kind, unit) rather than kind alone: stock/crypto/outcome
    each only ever produce one unit for their kind today (USD/USD/%), so
    this is invisible for them, but an fx provider account could mix
    quote currencies (e.g. EUR/ILS and EUR/USD) - grouping by unit too
    means that case gets two totals instead of one sensor silently
    summing two currencies, which per-kind subtotals (D-017/D-028) never
    intended to do.

    Added/removed per whole (kind, unit) group, which already happens
    for free via the entry reload that runs on every subentry add/
    remove/reconfigure (see `__init__.py`'s module docstring) - not
    recreated just because one instrument's quantity is edited.

    `native_value` is `None` - not 0 - until at least one instrument in
    the group has both a quantity set and a live price, so a group with
    no quantities set yet reads "unknown" rather than a misleading zero.
    """

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        entry: MarketSentryConfigEntry,
        provider_name: str,
        kind: str,
        unit: str,
        trackers: list[InstrumentTracker],
    ) -> None:
        self._trackers = trackers
        self._attr_unique_id = f"{entry.entry_id}_position_value_{kind}_{unit or 'none'}"
        self._attr_device_info = provider_connection_device_info(entry, provider_name)
        self._attr_translation_key = _POSITION_VALUE_TOTAL_TRANSLATION_KEY.get(kind, f"{kind}_total")
        if unit and unit != "%":
            self._attr_device_class = SensorDeviceClass.MONETARY
        if unit:
            self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> float | None:
        values = [
            value
            for tracker in self._trackers
            if (
                value := _position_value(
                    tracker.ref, tracker.options.get(OPT_QUANTITY), tracker.last_quote.price
                )
            )
            is not None
        ]
        return round(sum(values), 2) if values else None
