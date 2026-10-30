"""The Polymarket Watch integration."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .api import PolymarketApiClient, PolymarketApiError, PolymarketNotFoundError
from .const import (
    CONF_OUTCOME_TOKEN_IDS,
    CONF_SLUG,
    DEFAULT_CLOSING_SOON_HOURS,
    DEFAULT_COOLDOWN_MIN,
    DEFAULT_HYSTERESIS_PP,
    DEFAULT_LARGE_TRADE_USD,
    DEFAULT_MOVE_DELTA_PP,
    DEFAULT_MOVE_WINDOW_MIN,
    DEFAULT_THRESHOLDS,
    DEFAULT_VOLUME_SPIKE_PCT,
    DOMAIN,
    METADATA_UPDATE_INTERVAL_SEC,
    OPT_CLOSING_SOON_HOURS,
    OPT_COOLDOWN_MIN,
    OPT_HYSTERESIS_PP,
    OPT_LARGE_TRADE_USD,
    OPT_MOVE_DELTA_PP,
    OPT_MOVE_WINDOW_MIN,
    OPT_THRESHOLDS,
    OPT_VOLUME_SPIKE_PCT,
    REST_FALLBACK_POLL_INTERVAL_SEC,
    WS_DOWN_FALLBACK_THRESHOLD_SEC,
)
from .coordinator import PolymarketMetadataCoordinator
from .detector import (
    ClosingSoonDetector,
    CooldownGate,
    DetectedEvent,
    LargeTradeDetector,
    PriceMoveDetector,
    ResolvedDetector,
    ThresholdDetector,
    VolumeSpikeDetector,
)
from .models import Quote, Trade
from .services import async_setup_services
from .ws import PolymarketWsManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "event"]

SIGNAL_QUOTE_UPDATE = f"{DOMAIN}_quote_update"
SIGNAL_TRADE = f"{DOMAIN}_trade"
SIGNAL_WS_STATE = f"{DOMAIN}_ws_state"
SIGNAL_DETECTED_EVENT = f"{DOMAIN}_detected_event"


@dataclass(slots=True)
class OutcomeTracker:
    """Per-outcome detector state, keyed under a MarketTracker."""

    outcome_name: str
    token_id: str
    threshold: ThresholdDetector
    move: PriceMoveDetector
    large_trade: LargeTradeDetector
    quote: Quote = field(default_factory=lambda: Quote(token_id=""))


@dataclass(slots=True)
class MarketTracker:
    """Runtime state for a single tracked market (one config entry)."""

    market_slug: str
    coordinator: PolymarketMetadataCoordinator
    outcomes: dict[str, OutcomeTracker]
    volume_spike: VolumeSpikeDetector
    closing_soon: ClosingSoonDetector
    resolved: ResolvedDetector
    cooldown: CooldownGate


@dataclass(slots=True)
class PolymarketWatchRuntimeData:
    """Stored on entry.runtime_data."""

    api: PolymarketApiClient
    tracker: MarketTracker


@dataclass(slots=True)
class PolymarketWatchGlobalData:
    """Shared singleton state across all config entries, in hass.data."""

    ws_manager: PolymarketWsManager
    token_to_entries: dict[str, set[str]] = field(default_factory=dict)
    fallback_task: asyncio.Task[None] | None = None
    ws_down_since: float | None = None


type PolymarketWatchConfigEntry = ConfigEntry[PolymarketWatchRuntimeData]


def _build_options(entry: ConfigEntry) -> dict[str, Any]:
    opts = entry.options
    return {
        OPT_THRESHOLDS: opts.get(OPT_THRESHOLDS, DEFAULT_THRESHOLDS),
        OPT_HYSTERESIS_PP: opts.get(OPT_HYSTERESIS_PP, DEFAULT_HYSTERESIS_PP),
        OPT_MOVE_DELTA_PP: opts.get(OPT_MOVE_DELTA_PP, DEFAULT_MOVE_DELTA_PP),
        OPT_MOVE_WINDOW_MIN: opts.get(OPT_MOVE_WINDOW_MIN, DEFAULT_MOVE_WINDOW_MIN),
        OPT_LARGE_TRADE_USD: opts.get(OPT_LARGE_TRADE_USD, DEFAULT_LARGE_TRADE_USD),
        OPT_VOLUME_SPIKE_PCT: opts.get(OPT_VOLUME_SPIKE_PCT, DEFAULT_VOLUME_SPIKE_PCT),
        OPT_CLOSING_SOON_HOURS: opts.get(OPT_CLOSING_SOON_HOURS, DEFAULT_CLOSING_SOON_HOURS),
        OPT_COOLDOWN_MIN: opts.get(OPT_COOLDOWN_MIN, DEFAULT_COOLDOWN_MIN),
    }


async def async_setup_entry(hass: HomeAssistant, entry: PolymarketWatchConfigEntry) -> bool:
    """Set up a Polymarket Watch config entry (one tracked market)."""
    session = async_get_clientsession(hass)
    api = PolymarketApiClient(session)

    market_slug: str = entry.data[CONF_SLUG]
    token_ids: list[str] = entry.data.get(CONF_OUTCOME_TOKEN_IDS, [])

    try:
        market = await api.get_market_by_slug(market_slug)
    except PolymarketNotFoundError as err:
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"market_not_found_{market_slug}",
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key="market_not_found",
            translation_placeholders={"slug": market_slug},
        )
        raise ConfigEntryNotReady(f"Market '{market_slug}' not found") from err
    except PolymarketApiError as err:
        raise ConfigEntryNotReady(str(err)) from err

    opts = _build_options(entry)

    outcomes: dict[str, OutcomeTracker] = {}
    for outcome in market.outcomes:
        if token_ids and outcome.token_id not in token_ids:
            continue
        outcomes[outcome.token_id] = OutcomeTracker(
            outcome_name=outcome.name,
            token_id=outcome.token_id,
            threshold=ThresholdDetector(opts[OPT_THRESHOLDS], opts[OPT_HYSTERESIS_PP]),
            move=PriceMoveDetector(opts[OPT_MOVE_DELTA_PP], opts[OPT_MOVE_WINDOW_MIN]),
            large_trade=LargeTradeDetector(opts[OPT_LARGE_TRADE_USD]),
            quote=Quote(token_id=outcome.token_id),
        )

    coordinator = PolymarketMetadataCoordinator(hass, api, market_slug)
    await coordinator.async_config_entry_first_refresh()

    tracker = MarketTracker(
        market_slug=market_slug,
        coordinator=coordinator,
        outcomes=outcomes,
        volume_spike=VolumeSpikeDetector(opts[OPT_VOLUME_SPIKE_PCT]),
        closing_soon=ClosingSoonDetector(opts[OPT_CLOSING_SOON_HOURS]),
        resolved=ResolvedDetector(),
        cooldown=CooldownGate(opts[OPT_COOLDOWN_MIN]),
    )

    entry.runtime_data = PolymarketWatchRuntimeData(api=api, tracker=tracker)

    global_data = await _async_get_or_create_global_data(hass)
    for token_id in outcomes:
        global_data.token_to_entries.setdefault(token_id, set()).add(entry.entry_id)
    await global_data.ws_manager.subscribe(list(outcomes.keys()))

    async def _handle_metadata_interval(_now: datetime) -> None:
        await _async_check_metadata_events(hass, entry)

    entry.async_on_unload(
        async_track_time_interval(
            hass,
            _handle_metadata_interval,
            timedelta(seconds=METADATA_UPDATE_INTERVAL_SEC),
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PolymarketWatchConfigEntry) -> bool:
    """Unload a config entry and unsubscribe its tokens from the shared WS."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if DOMAIN in hass.data:
        global_data: PolymarketWatchGlobalData = hass.data[DOMAIN]
        tracker = entry.runtime_data.tracker
        tokens_to_unsubscribe: list[str] = []
        for token_id in tracker.outcomes:
            entries = global_data.token_to_entries.get(token_id)
            if entries is None:
                continue
            entries.discard(entry.entry_id)
            if not entries:
                tokens_to_unsubscribe.append(token_id)
                del global_data.token_to_entries[token_id]
        if tokens_to_unsubscribe:
            await global_data.ws_manager.unsubscribe(tokens_to_unsubscribe)

        if not global_data.token_to_entries:
            await global_data.ws_manager.stop()
            if global_data.fallback_task is not None:
                global_data.fallback_task.cancel()
            del hass.data[DOMAIN]

    return unload_ok


async def _async_get_or_create_global_data(hass: HomeAssistant) -> PolymarketWatchGlobalData:
    if DOMAIN in hass.data:
        return cast(PolymarketWatchGlobalData, hass.data[DOMAIN])

    session = async_get_clientsession(hass)

    async def on_message(message: dict[str, Any]) -> None:
        await _async_handle_ws_message(hass, message)

    @callback
    def on_connection_state_change(connected: bool) -> None:
        global_data = hass.data.get(DOMAIN)
        if global_data is None:
            return
        if connected:
            global_data.ws_down_since = None
        else:
            global_data.ws_down_since = time.monotonic()
        async_dispatcher_send(hass, SIGNAL_WS_STATE, connected)

    ws_manager = PolymarketWsManager(session, on_message, on_connection_state_change)
    await ws_manager.start()

    global_data = PolymarketWatchGlobalData(ws_manager=ws_manager)
    hass.data[DOMAIN] = global_data

    await async_setup_services(hass)

    global_data.fallback_task = hass.async_create_task(_async_fallback_poll_loop(hass))

    return global_data


async def _async_fallback_poll_loop(hass: HomeAssistant) -> None:
    """Poll /midpoint via REST for subscribed tokens whenever WS has been down too long."""
    try:
        while True:
            await asyncio.sleep(REST_FALLBACK_POLL_INTERVAL_SEC)
            global_data: PolymarketWatchGlobalData | None = hass.data.get(DOMAIN)
            if global_data is None:
                continue
            if (
                global_data.ws_down_since is None
                or time.monotonic() - global_data.ws_down_since < WS_DOWN_FALLBACK_THRESHOLD_SEC
            ):
                continue

            session = async_get_clientsession(hass)
            api = PolymarketApiClient(session)
            for token_id in list(global_data.token_to_entries.keys()):
                try:
                    mid = await api.get_midpoint(token_id)
                except PolymarketApiError as err:
                    _LOGGER.debug("Fallback poll failed for %s: %s", token_id, err)
                    continue
                if mid is not None:
                    await _async_apply_quote(hass, token_id, best_bid=mid, best_ask=mid)
    except asyncio.CancelledError:
        pass


async def _async_handle_ws_message(hass: HomeAssistant, message: dict[str, Any]) -> None:
    """Route one WS event_type message to quote/trade/resolution handling."""
    event_type = message.get("event_type")

    if event_type == "price_change":
        for change in message.get("price_changes", []):
            token_id = change.get("asset_id")
            if not token_id:
                continue
            await _async_apply_quote(
                hass,
                token_id,
                best_bid=_to_float(change.get("best_bid")),
                best_ask=_to_float(change.get("best_ask")),
            )
    elif event_type == "best_bid_ask":
        token_id = message.get("asset_id")
        if token_id:
            await _async_apply_quote(
                hass,
                token_id,
                best_bid=_to_float(message.get("best_bid")),
                best_ask=_to_float(message.get("best_ask")),
            )
    elif event_type == "last_trade_price":
        token_id = message.get("asset_id")
        if token_id:
            trade = Trade(
                token_id=token_id,
                price=_to_float(message.get("price")) or 0.0,
                size=_to_float(message.get("size")) or 0.0,
                side=str(message.get("side", "")),
            )
            await _async_apply_trade(hass, trade)
    elif event_type == "market_resolved":
        for token_id in message.get("assets_ids", []):
            await _async_apply_resolution(hass, token_id, message.get("winning_asset_id"))


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _find_entries_for_token(hass: HomeAssistant, token_id: str) -> list[PolymarketWatchConfigEntry]:
    global_data: PolymarketWatchGlobalData | None = hass.data.get(DOMAIN)
    if global_data is None:
        return []
    entry_ids = global_data.token_to_entries.get(token_id, set())
    entries = []
    for entry_id in entry_ids:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is not None:
            entries.append(entry)
    return entries


async def _async_apply_quote(
    hass: HomeAssistant, token_id: str, best_bid: float | None, best_ask: float | None
) -> None:
    now = datetime.now(UTC)
    for entry in _find_entries_for_token(hass, token_id):
        tracker = entry.runtime_data.tracker
        outcome_tracker = tracker.outcomes.get(token_id)
        if outcome_tracker is None:
            continue
        if best_bid is not None:
            outcome_tracker.quote.best_bid = best_bid
        if best_ask is not None:
            outcome_tracker.quote.best_ask = best_ask
        outcome_tracker.quote.timestamp = now

        mid = outcome_tracker.quote.midpoint
        if mid is None:
            continue
        mid_pct = mid * 100

        events: list[DetectedEvent] = []
        events += outcome_tracker.threshold.update(outcome_tracker.outcome_name, token_id, mid_pct)
        events += outcome_tracker.move.update(outcome_tracker.outcome_name, token_id, mid_pct, now)
        events = tracker.cooldown.filter_events(events, now)

        async_dispatcher_send(hass, f"{SIGNAL_QUOTE_UPDATE}_{token_id}", outcome_tracker.quote)
        for event in events:
            _async_fire_detected_event(hass, entry, event)


async def _async_apply_trade(hass: HomeAssistant, trade: Trade) -> None:
    now = datetime.now(UTC)
    for entry in _find_entries_for_token(hass, trade.token_id):
        tracker = entry.runtime_data.tracker
        outcome_tracker = tracker.outcomes.get(trade.token_id)
        if outcome_tracker is None:
            continue
        outcome_tracker.quote.last_trade_price = trade.price
        trade.timestamp = now

        events = outcome_tracker.large_trade.check(
            outcome_tracker.outcome_name, trade.token_id, trade.price, trade.size
        )
        events = tracker.cooldown.filter_events(events, now)

        async_dispatcher_send(hass, f"{SIGNAL_TRADE}_{trade.token_id}", trade)
        for event in events:
            _async_fire_detected_event(hass, entry, event)


async def _async_apply_resolution(hass: HomeAssistant, token_id: str, winning_asset_id: str | None) -> None:
    now = datetime.now(UTC)
    for entry in _find_entries_for_token(hass, token_id):
        tracker = entry.runtime_data.tracker
        outcome_tracker = tracker.outcomes.get(token_id)
        if outcome_tracker is None:
            continue
        winning_outcome = outcome_tracker.outcome_name if token_id == winning_asset_id else None
        events = tracker.resolved.check(outcome_tracker.outcome_name, token_id, True, winning_outcome)
        events = tracker.cooldown.filter_events(events, now)
        for event in events:
            _async_fire_detected_event(hass, entry, event)


async def _async_check_metadata_events(hass: HomeAssistant, entry: PolymarketWatchConfigEntry) -> None:
    """Check volume-spike / closing-soon / resolved against the latest Gamma metadata."""
    tracker = entry.runtime_data.tracker
    data = tracker.coordinator.data
    if data is None:
        return
    market = data.market
    now = datetime.now(UTC)

    for outcome_tracker in tracker.outcomes.values():
        events: list[DetectedEvent] = []
        events += tracker.volume_spike.update(outcome_tracker.outcome_name, outcome_tracker.token_id, market.volume_24hr)
        if market.end_date is not None:
            events += tracker.closing_soon.check(outcome_tracker.outcome_name, outcome_tracker.token_id, market.end_date, now)
        if market.closed and market.uma_resolution_status == "resolved":
            events += tracker.resolved.check(outcome_tracker.outcome_name, outcome_tracker.token_id, True, None)
        events = tracker.cooldown.filter_events(events, now)
        for event in events:
            _async_fire_detected_event(hass, entry, event)


def _async_fire_detected_event(hass: HomeAssistant, entry: PolymarketWatchConfigEntry, event: DetectedEvent) -> None:
    tracker = entry.runtime_data.tracker
    payload = {
        "entry_id": entry.entry_id,
        "market_slug": tracker.market_slug,
        "question": entry.title,
        "outcome": event.outcome,
        "token_id": event.token_id,
        "old": event.old,
        "new": event.new,
        "delta_pp": event.delta_pp,
        "direction": event.direction,
        "window_min": event.window_min,
        "url": f"https://polymarket.com/market/{tracker.market_slug}",
        **event.extra,
    }
    hass.bus.async_fire(f"polymarket_watch_{event.event_type}", payload)
    async_dispatcher_send(hass, f"{SIGNAL_DETECTED_EVENT}_{entry.entry_id}", event, payload)
