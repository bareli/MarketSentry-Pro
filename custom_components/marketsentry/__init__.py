"""The MarketSentry Pro integration.

One config entry = one provider account (Polymarket/FX need no credentials;
Finnhub/Alpaca do). Each tracked instrument is a config *subentry* under
that entry, so adding/removing instruments never re-asks for credentials.
Subentry changes trigger Home Assistant's default reload-the-entry
behavior, so `async_setup_entry` always rebuilds its trackers from
`entry.subentries` rather than patching them in place.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .api import PolymarketApiClient
from .const import (
    BUS_EVENT_PREFIX,
    CONF_EXTRA,
    CONF_INSTRUMENT_ID,
    CONF_INSTRUMENT_KIND,
    CONF_INSTRUMENT_NAME,
    CONF_OPTIONS,
    CONF_PROVIDER,
    CONF_SYMBOL,
    CONF_UNIT,
    CONF_URL,
    DOMAIN,
    OPT_CLOSING_SOON_HOURS,
    OPT_COOLDOWN_MIN,
    OPT_DAILY_CHANGE_PCT,
    OPT_HYSTERESIS,
    OPT_LARGE_TRADE_USD,
    OPT_MARKET_OPEN_GAP_PCT,
    OPT_MOVE_DELTA,
    OPT_MOVE_WINDOW_MIN,
    OPT_THRESHOLDS,
    OPT_VOLUME_SPIKE_PCT,
    SUBENTRY_TYPE_INSTRUMENT,
)
from .coordinator import PolymarketMetadataCoordinator, ProviderSnapshotCoordinator
from .detector import (
    ClosingSoonDetector,
    CooldownGate,
    DailyChangeDetector,
    DetectedEvent,
    LargeTradeDetector,
    MarketOpenGapDetector,
    OfficialRatePublishedDetector,
    PriceMoveDetector,
    ResolvedDetector,
    ThresholdDetector,
    VolumeSpikeDetector,
)
from .market_calendar import market_state as calc_market_state
from .providers import PROVIDERS, build_provider
from .providers.base import InstrumentRef, Provider, ProviderEvent, Quote, Trade
from .services import async_setup_services
from .websocket_api import async_get_history_buffer, async_setup_websocket_api

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "event"]

SIGNAL_QUOTE_UPDATE = f"{DOMAIN}_quote_update"
SIGNAL_TRADE_UPDATE = f"{DOMAIN}_trade_update"
SIGNAL_DETECTED_EVENT = f"{DOMAIN}_detected_event"
SIGNAL_STREAM_STATE = f"{DOMAIN}_stream_state"


@dataclass(slots=True)
class InstrumentDetectors:
    """The subset of detectors that applies to one instrument's kind."""

    threshold: ThresholdDetector
    move: PriceMoveDetector
    daily_change: DailyChangeDetector | None = None
    large_trade: LargeTradeDetector | None = None
    volume_spike: VolumeSpikeDetector | None = None
    market_open_gap: MarketOpenGapDetector | None = None
    closing_soon: ClosingSoonDetector | None = None
    resolved: ResolvedDetector | None = None
    official_rate_published: OfficialRatePublishedDetector | None = None


@dataclass(slots=True)
class InstrumentTracker:
    """Runtime state for one tracked instrument (one subentry)."""

    subentry_id: str
    ref: InstrumentRef
    options: dict[str, Any]
    detectors: InstrumentDetectors
    cooldown: CooldownGate
    last_quote: Quote = field(default_factory=Quote)
    last_trade: Trade | None = None


@dataclass(slots=True)
class MarketSentryRuntimeData:
    """Stored on entry.runtime_data."""

    provider: Provider
    provider_name: str
    snapshot_coordinator: ProviderSnapshotCoordinator
    trackers: dict[str, InstrumentTracker]
    polymarket_metadata: dict[str, PolymarketMetadataCoordinator]
    stream_task: asyncio.Task[None] | None = None
    stream_connected: bool = False


type MarketSentryConfigEntry = ConfigEntry[MarketSentryRuntimeData]


def _ref_from_subentry_data(provider_key: str, data: Mapping[str, Any]) -> InstrumentRef:
    return InstrumentRef(
        provider=provider_key,
        id=data[CONF_INSTRUMENT_ID],
        symbol=data[CONF_SYMBOL],
        name=data[CONF_INSTRUMENT_NAME],
        kind=data[CONF_INSTRUMENT_KIND],
        unit=data.get(CONF_UNIT, ""),
        url=data.get(CONF_URL),
        extra=data.get(CONF_EXTRA, {}),
    )


def _build_detectors(kind: str, opts: dict[str, Any]) -> InstrumentDetectors:
    detectors = InstrumentDetectors(
        threshold=ThresholdDetector(opts.get(OPT_THRESHOLDS, []), opts.get(OPT_HYSTERESIS, 0.0)),
        move=PriceMoveDetector(
            opts.get(OPT_MOVE_DELTA, 5.0),
            opts.get(OPT_MOVE_WINDOW_MIN, 60),
            relative=kind != "outcome",
        ),
    )
    if OPT_DAILY_CHANGE_PCT in opts:
        detectors.daily_change = DailyChangeDetector(opts[OPT_DAILY_CHANGE_PCT])
    if kind in ("outcome", "stock") and OPT_LARGE_TRADE_USD in opts:
        detectors.large_trade = LargeTradeDetector(opts[OPT_LARGE_TRADE_USD])
    if kind == "outcome":
        detectors.volume_spike = VolumeSpikeDetector(opts.get(OPT_VOLUME_SPIKE_PCT, 50.0))
        detectors.closing_soon = ClosingSoonDetector(opts.get(OPT_CLOSING_SOON_HOURS, 24))
        detectors.resolved = ResolvedDetector()
    if kind == "stock" and OPT_MARKET_OPEN_GAP_PCT in opts:
        detectors.market_open_gap = MarketOpenGapDetector(opts[OPT_MARKET_OPEN_GAP_PCT])
    if kind == "fx":
        detectors.official_rate_published = OfficialRatePublishedDetector()
    return detectors


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, _config: Any) -> bool:
    """Domain-wide setup: WS command + the bundled marketsentry-card, once."""
    async_setup_websocket_api(hass)

    card_file = Path(__file__).parent / "www" / "marketsentry-card.js"
    if card_file.exists():
        url_path = f"/{DOMAIN}_static/marketsentry-card.js"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(url_path, str(card_file), cache_headers=False)]
        )
        add_extra_js_url(hass, url_path)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: MarketSentryConfigEntry) -> bool:
    """Set up a MarketSentry Pro config entry (one provider account)."""
    session = async_get_clientsession(hass)
    provider_key = entry.data[CONF_PROVIDER]
    provider = build_provider(session, provider_key, dict(entry.data))

    snapshot_coordinator = ProviderSnapshotCoordinator(hass, provider, entry.title)
    trackers: dict[str, InstrumentTracker] = {}
    polymarket_metadata: dict[str, PolymarketMetadataCoordinator] = {}
    polymarket_api: PolymarketApiClient | None = None

    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_INSTRUMENT:
            continue
        ref = _ref_from_subentry_data(provider_key, subentry.data)
        opts = subentry.data.get(CONF_OPTIONS, {})
        trackers[subentry_id] = InstrumentTracker(
            subentry_id=subentry_id,
            ref=ref,
            options=opts,
            detectors=_build_detectors(ref.kind, opts),
            cooldown=CooldownGate(opts.get(OPT_COOLDOWN_MIN, 15)),
        )

        market_slug = ref.extra.get("market_slug") if ref.kind == "outcome" else None
        if market_slug and market_slug not in polymarket_metadata:
            if polymarket_api is None:
                polymarket_api = PolymarketApiClient(session)
            metadata_coordinator = PolymarketMetadataCoordinator(hass, polymarket_api, market_slug)
            await metadata_coordinator.async_refresh()
            if not metadata_coordinator.last_update_success:
                ir.async_create_issue(
                    hass,
                    DOMAIN,
                    f"market_not_found_{market_slug}",
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="market_not_found",
                    translation_placeholders={"slug": market_slug},
                )
            polymarket_metadata[market_slug] = metadata_coordinator

    snapshot_coordinator.refs = [tracker.ref for tracker in trackers.values()]
    await snapshot_coordinator.async_config_entry_first_refresh()

    runtime = MarketSentryRuntimeData(
        provider=provider,
        provider_name=PROVIDERS[provider_key].name,
        snapshot_coordinator=snapshot_coordinator,
        trackers=trackers,
        polymarket_metadata=polymarket_metadata,
    )
    entry.runtime_data = runtime

    @callback
    def _handle_snapshot_update() -> None:
        hass.async_create_task(_async_process_snapshot(hass, entry))

    entry.async_on_unload(snapshot_coordinator.async_add_listener(_handle_snapshot_update))
    await _async_process_snapshot(hass, entry)

    await _async_start_streaming(hass, entry)
    await async_setup_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MarketSentryConfigEntry) -> bool:
    """Unload a config entry and stop its streaming task, if any."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    runtime = entry.runtime_data
    if runtime is not None and runtime.stream_task is not None:
        runtime.stream_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await runtime.stream_task

    return unload_ok


def _find_tracker_by_instrument_id(
    runtime: MarketSentryRuntimeData, instrument_id: str
) -> InstrumentTracker | None:
    for tracker in runtime.trackers.values():
        if tracker.ref.id == instrument_id:
            return tracker
    return None


async def _async_start_streaming(hass: HomeAssistant, entry: MarketSentryConfigEntry) -> None:
    runtime = entry.runtime_data
    if not runtime.provider.supports_streaming or not runtime.trackers:
        return

    refs = [tracker.ref for tracker in runtime.trackers.values()]

    async def on_quote(instrument_id: str, quote: Quote) -> None:
        tracker = _find_tracker_by_instrument_id(runtime, instrument_id)
        if tracker is not None:
            await _async_process_quote(hass, entry, tracker, quote)

    async def on_trade(instrument_id: str, trade: Trade) -> None:
        tracker = _find_tracker_by_instrument_id(runtime, instrument_id)
        if tracker is not None:
            await _async_process_trade(hass, entry, tracker, trade)

    async def on_event(instrument_id: str, provider_event: ProviderEvent) -> None:
        tracker = _find_tracker_by_instrument_id(runtime, instrument_id)
        if tracker is not None:
            await _async_process_provider_event(hass, entry, tracker, provider_event)

    async def run() -> None:
        runtime.stream_connected = True
        async_dispatcher_send(hass, f"{SIGNAL_STREAM_STATE}_{entry.entry_id}", True)
        try:
            await runtime.provider.stream(refs, on_quote, on_trade, on_event)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Stream for entry %s ended: %s", entry.entry_id, type(err).__name__)
        finally:
            runtime.stream_connected = False
            async_dispatcher_send(hass, f"{SIGNAL_STREAM_STATE}_{entry.entry_id}", False)

    runtime.stream_task = hass.async_create_task(run())


async def _async_process_quote(
    hass: HomeAssistant, entry: MarketSentryConfigEntry, tracker: InstrumentTracker, quote: Quote
) -> None:
    tracker.last_quote = quote
    now = datetime.now(UTC)
    events: list[DetectedEvent] = []

    if quote.price is not None:
        value = quote.price * 100 if tracker.ref.kind == "outcome" else quote.price
        async_get_history_buffer(hass).append(tracker.ref.id, quote.ts or now, value)
        events += tracker.detectors.threshold.update(tracker.ref.symbol, tracker.ref.id, value)
        events += tracker.detectors.move.update(tracker.ref.symbol, tracker.ref.id, value, now)

        if tracker.detectors.daily_change is not None:
            events += tracker.detectors.daily_change.update(
                tracker.ref.symbol, tracker.ref.id, value, now, previous_close=quote.previous_close
            )

        if tracker.detectors.market_open_gap is not None:
            state = calc_market_state(now)
            events += tracker.detectors.market_open_gap.check(
                tracker.ref.symbol, tracker.ref.id, value, quote.previous_close, state, now
            )

        if tracker.detectors.official_rate_published is not None:
            events += tracker.detectors.official_rate_published.check(
                tracker.ref.symbol, tracker.ref.id, value, published_date=(quote.ts or now).date()
            )

    events = tracker.cooldown.filter_events(events, now)
    async_dispatcher_send(hass, f"{SIGNAL_QUOTE_UPDATE}_{tracker.subentry_id}", quote)
    for event in events:
        _fire_detected_event(hass, entry, tracker, event)


async def _async_process_trade(
    hass: HomeAssistant, entry: MarketSentryConfigEntry, tracker: InstrumentTracker, trade: Trade
) -> None:
    tracker.last_trade = trade
    async_dispatcher_send(hass, f"{SIGNAL_TRADE_UPDATE}_{tracker.subentry_id}", trade)

    if tracker.detectors.large_trade is None:
        return
    now = datetime.now(UTC)
    events = tracker.detectors.large_trade.check(tracker.ref.symbol, tracker.ref.id, trade.price, trade.size)
    events = tracker.cooldown.filter_events(events, now)
    for event in events:
        _fire_detected_event(hass, entry, tracker, event)


async def _async_process_provider_event(
    hass: HomeAssistant, entry: MarketSentryConfigEntry, tracker: InstrumentTracker, provider_event: ProviderEvent
) -> None:
    if provider_event.type != "resolved" or tracker.detectors.resolved is None:
        return
    now = datetime.now(UTC)
    winning = bool(provider_event.data.get("winning"))
    events = tracker.detectors.resolved.check(
        tracker.ref.symbol, tracker.ref.id, True, tracker.ref.symbol if winning else None
    )
    events = tracker.cooldown.filter_events(events, now)
    for event in events:
        _fire_detected_event(hass, entry, tracker, event)


async def _async_process_snapshot(hass: HomeAssistant, entry: MarketSentryConfigEntry) -> None:
    """Run every tracker's detectors against the latest REST snapshot poll.

    Also the only place `volume_spike`/`closing_soon`/`resolved` (which need
    Polymarket metadata, not a live quote) and are checked.
    """
    runtime = entry.runtime_data
    quotes = runtime.snapshot_coordinator.data or {}
    now = datetime.now(UTC)

    for tracker in runtime.trackers.values():
        quote = quotes.get(tracker.ref.id)
        if quote is not None:
            await _async_process_quote(hass, entry, tracker, quote)

        market_slug = tracker.ref.extra.get("market_slug")
        if not market_slug:
            continue
        metadata_coordinator = runtime.polymarket_metadata.get(market_slug)
        if metadata_coordinator is None or metadata_coordinator.data is None:
            continue
        market = metadata_coordinator.data.market

        events: list[DetectedEvent] = []
        if tracker.detectors.volume_spike is not None:
            events += tracker.detectors.volume_spike.update(
                tracker.ref.symbol, tracker.ref.id, market.volume_24hr
            )
        if tracker.detectors.closing_soon is not None and market.end_date is not None:
            events += tracker.detectors.closing_soon.check(
                tracker.ref.symbol, tracker.ref.id, market.end_date, now
            )
        if (
            tracker.detectors.resolved is not None
            and market.closed
            and (market.uma_resolution_status or "").lower() == "resolved"
        ):
            events += tracker.detectors.resolved.check(tracker.ref.symbol, tracker.ref.id, True, None)

        events = tracker.cooldown.filter_events(events, now)
        for event in events:
            _fire_detected_event(hass, entry, tracker, event)


def _fire_detected_event(
    hass: HomeAssistant, entry: MarketSentryConfigEntry, tracker: InstrumentTracker, event: DetectedEvent
) -> None:
    payload = {
        "entry_id": entry.entry_id,
        "subentry_id": tracker.subentry_id,
        "provider": tracker.ref.provider,
        "kind": tracker.ref.kind,
        "symbol": tracker.ref.symbol,
        "instrument_id": tracker.ref.id,
        "unit": tracker.ref.unit,
        "name": tracker.ref.name,
        "old": event.old,
        "new": event.new,
        "delta": event.delta_pp,
        "direction": event.direction,
        "window_min": event.window_min,
        "url": tracker.ref.url,
        **event.extra,
    }
    hass.bus.async_fire(f"{BUS_EVENT_PREFIX}{event.event_type}", payload)
    async_dispatcher_send(hass, f"{SIGNAL_DETECTED_EVENT}_{tracker.subentry_id}", event, payload)
