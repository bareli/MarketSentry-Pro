"""Pure-Python change detection, generic across providers (Polymarket
outcomes, stocks, FX pairs).

No HA imports. Every function/class here is unit-testable in isolation.
`ClosingSoonDetector` and `ResolvedDetector` are Polymarket-specific
(callers simply don't use them for other kinds); everything else operates
on plain numeric values and is kind-agnostic.

The three event types below aren't wired into any HA entity yet (that
lands with the generic coordinator/entity rewrite); they're kept here,
not in const.EVENT_TYPES, so they don't appear as triggers HA can't fire.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .const import (
    EVENT_CLOSING_SOON,
    EVENT_LARGE_TRADE,
    EVENT_PRICE_MOVE,
    EVENT_RESOLVED,
    EVENT_THRESHOLD_CROSSED,
    EVENT_VOLUME_SPIKE,
)

EVENT_DAILY_CHANGE = "daily_change"
EVENT_MARKET_OPEN_GAP = "market_open_gap"
EVENT_OFFICIAL_RATE_PUBLISHED = "official_rate_published"


@dataclass(slots=True)
class DetectedEvent:
    """A single fired detection, ready to become a bus event / HA event entity."""

    event_type: str
    outcome: str
    token_id: str
    old: float | None
    new: float | None
    delta_pp: float | None = None
    direction: str | None = None  # "up" / "down"
    window_min: int | None = None
    extra: dict[str, object] = field(default_factory=dict)


class ThresholdDetector:
    """Fires `threshold_crossed` when a probability crosses a configured level.

    Hysteresis prevents flapping: once a threshold has fired in one direction,
    it will not re-fire until price moves back past `threshold - hysteresis`
    (if crossed up) or `threshold + hysteresis` (if crossed down).
    """

    def __init__(self, thresholds: list[float], hysteresis_pp: float) -> None:
        self._thresholds = sorted(thresholds)
        self._hysteresis = hysteresis_pp
        self._last_price: float | None = None
        self._armed: dict[float, bool] = {t: True for t in self._thresholds}

    def update(self, outcome: str, token_id: str, new_price: float) -> list[DetectedEvent]:
        events: list[DetectedEvent] = []
        old_price = self._last_price

        if old_price is not None:
            for threshold in self._thresholds:
                crossed_up = old_price < threshold <= new_price
                crossed_down = old_price > threshold >= new_price

                if crossed_up and self._armed[threshold]:
                    events.append(
                        DetectedEvent(
                            event_type=EVENT_THRESHOLD_CROSSED,
                            outcome=outcome,
                            token_id=token_id,
                            old=old_price,
                            new=new_price,
                            delta_pp=new_price - old_price,
                            direction="up",
                            extra={"threshold": threshold},
                        )
                    )
                    self._armed[threshold] = False
                elif crossed_down and self._armed[threshold]:
                    events.append(
                        DetectedEvent(
                            event_type=EVENT_THRESHOLD_CROSSED,
                            outcome=outcome,
                            token_id=token_id,
                            old=old_price,
                            new=new_price,
                            delta_pp=new_price - old_price,
                            direction="down",
                            extra={"threshold": threshold},
                        )
                    )
                    self._armed[threshold] = False

                # Re-arm once price retreats past threshold +/- hysteresis.
                if not self._armed[threshold] and (
                    new_price <= threshold - self._hysteresis
                    or new_price >= threshold + self._hysteresis
                ):
                    self._armed[threshold] = True

        self._last_price = new_price
        return events


class PriceMoveDetector:
    """Fires `price_move` when |change| >= threshold within a rolling window.

    `relative=False` (default, Polymarket outcomes): threshold is in
    percentage points of the 0-100 value, matching the original behavior.
    `relative=True` (stocks/FX): threshold is a percent change relative to
    the window's starting price; the percent change is reported in
    `extra["change_pct"]` alongside the raw `delta_pp`.
    """

    def __init__(self, delta_pp: float, window_min: int, relative: bool = False) -> None:
        self._delta_pp = delta_pp
        self._relative = relative
        self._window = timedelta(minutes=window_min)
        self._window_min = window_min
        self._history: deque[tuple[datetime, float]] = deque()

    def update(self, outcome: str, token_id: str, price: float, now: datetime) -> list[DetectedEvent]:
        self._history.append((now, price))
        cutoff = now - self._window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        if not self._history:
            return []

        _oldest_time, oldest_price = self._history[0]
        delta = price - oldest_price
        change_pct = (delta / oldest_price * 100) if oldest_price else 0.0
        magnitude = abs(change_pct) if self._relative else abs(delta)

        if magnitude >= self._delta_pp:
            # Reset window so we don't immediately re-fire on the same move.
            self._history.clear()
            self._history.append((now, price))
            return [
                DetectedEvent(
                    event_type=EVENT_PRICE_MOVE,
                    outcome=outcome,
                    token_id=token_id,
                    old=oldest_price,
                    new=price,
                    delta_pp=delta,
                    direction="up" if delta > 0 else "down",
                    window_min=self._window_min,
                    extra={"change_pct": change_pct},
                )
            ]
        return []


class LargeTradeDetector:
    """Fires `large_trade` when price * size (notional USD) >= threshold."""

    def __init__(self, threshold_usd: float) -> None:
        self._threshold = threshold_usd

    def check(self, outcome: str, token_id: str, price: float, size: float) -> list[DetectedEvent]:
        notional = price * size
        if notional >= self._threshold:
            return [
                DetectedEvent(
                    event_type=EVENT_LARGE_TRADE,
                    outcome=outcome,
                    token_id=token_id,
                    old=None,
                    new=price,
                    extra={"size": size, "notional_usd": notional},
                )
            ]
        return []


class VolumeSpikeDetector:
    """Fires `volume_spike` when 24h volume grows by >= pct between polls."""

    def __init__(self, spike_pct: float) -> None:
        self._spike_pct = spike_pct
        self._last_volume: float | None = None

    def update(self, outcome: str, token_id: str, volume_24hr: float) -> list[DetectedEvent]:
        events: list[DetectedEvent] = []
        if self._last_volume is not None and self._last_volume > 0:
            growth_pct = (volume_24hr - self._last_volume) / self._last_volume * 100
            if growth_pct >= self._spike_pct:
                events.append(
                    DetectedEvent(
                        event_type=EVENT_VOLUME_SPIKE,
                        outcome=outcome,
                        token_id=token_id,
                        old=self._last_volume,
                        new=volume_24hr,
                        extra={"growth_pct": growth_pct},
                    )
                )
        self._last_volume = volume_24hr
        return events


class DailyChangeDetector:
    """Fires `daily_change` when |change| vs a reference value >= pct.

    The reference is the previous close/official rate when the caller
    supplies one (e.g. Finnhub's `pc` field); otherwise it falls back to
    the first value seen each UTC calendar day. Fires at most once per day.
    """

    def __init__(self, change_pct: float) -> None:
        self._change_pct = change_pct
        self._reference: float | None = None
        self._reference_day: date | None = None
        self._fired_today = False

    def update(
        self,
        outcome: str,
        token_id: str,
        price: float,
        now: datetime,
        previous_close: float | None = None,
    ) -> list[DetectedEvent]:
        today = now.date()
        if self._reference_day != today:
            self._reference_day = today
            self._reference = previous_close if previous_close is not None else price
            self._fired_today = False
        elif previous_close is not None:
            self._reference = previous_close

        if self._fired_today or not self._reference:
            return []

        change_pct = (price - self._reference) / self._reference * 100
        if abs(change_pct) >= self._change_pct:
            self._fired_today = True
            return [
                DetectedEvent(
                    event_type=EVENT_DAILY_CHANGE,
                    outcome=outcome,
                    token_id=token_id,
                    old=self._reference,
                    new=price,
                    extra={"change_pct": change_pct},
                )
            ]
        return []


class MarketOpenGapDetector:
    """Fires `market_open_gap` once per session: first regular-hours price
    vs the previous close, when the gap is >= gap_pct (stocks only)."""

    def __init__(self, gap_pct: float) -> None:
        self._gap_pct = gap_pct
        self._last_session_day: date | None = None
        self._fired_this_session = False

    def check(
        self,
        outcome: str,
        token_id: str,
        price: float,
        previous_close: float | None,
        market_state: str,
        now: datetime,
    ) -> list[DetectedEvent]:
        today = now.date()
        if self._last_session_day != today:
            self._last_session_day = today
            self._fired_this_session = False

        if market_state != "regular" or self._fired_this_session or not previous_close:
            return []

        self._fired_this_session = True
        gap_pct = (price - previous_close) / previous_close * 100
        if abs(gap_pct) >= self._gap_pct:
            return [
                DetectedEvent(
                    event_type=EVENT_MARKET_OPEN_GAP,
                    outcome=outcome,
                    token_id=token_id,
                    old=previous_close,
                    new=price,
                    extra={"change_pct": gap_pct},
                )
            ]
        return []


class OfficialRatePublishedDetector:
    """FX-only: fires `official_rate_published` once per new BOI publication date."""

    def __init__(self) -> None:
        self._last_published_date: date | None = None

    def check(
        self, outcome: str, token_id: str, rate: float, published_date: date
    ) -> list[DetectedEvent]:
        if self._last_published_date == published_date:
            return []
        is_first_observation = self._last_published_date is None
        self._last_published_date = published_date
        if is_first_observation:
            return []
        return [
            DetectedEvent(
                event_type=EVENT_OFFICIAL_RATE_PUBLISHED,
                outcome=outcome,
                token_id=token_id,
                old=None,
                new=rate,
                extra={"published_date": published_date.isoformat()},
            )
        ]


class ClosingSoonDetector:
    """Fires `closing_soon` once when time to end_date <= threshold hours."""

    def __init__(self, hours: int) -> None:
        self._threshold = timedelta(hours=hours)
        self._fired = False

    def check(self, outcome: str, token_id: str, end_date: datetime, now: datetime) -> list[DetectedEvent]:
        if self._fired:
            return []
        remaining = end_date - now
        if remaining <= self._threshold:
            self._fired = True
            return [
                DetectedEvent(
                    event_type=EVENT_CLOSING_SOON,
                    outcome=outcome,
                    token_id=token_id,
                    old=None,
                    new=None,
                    extra={"remaining_seconds": remaining.total_seconds()},
                )
            ]
        return []

    def reset(self) -> None:
        self._fired = False


class ResolvedDetector:
    """Fires `resolved` once on market_resolved or Gamma closed+resolved."""

    def __init__(self) -> None:
        self._fired = False

    def check(self, outcome: str, token_id: str, resolved: bool, winning_outcome: str | None) -> list[DetectedEvent]:
        if self._fired or not resolved:
            return []
        self._fired = True
        return [
            DetectedEvent(
                event_type=EVENT_RESOLVED,
                outcome=outcome,
                token_id=token_id,
                old=None,
                new=None,
                extra={"winning_outcome": winning_outcome},
            )
        ]


class CooldownGate:
    """Suppresses repeated firing of the same event type per outcome within a window."""

    def __init__(self, cooldown_min: int) -> None:
        self._cooldown = timedelta(minutes=cooldown_min)
        self._last_fired: dict[tuple[str, str], datetime] = {}

    def allow(self, event_type: str, outcome: str, now: datetime) -> bool:
        key = (event_type, outcome)
        last = self._last_fired.get(key)
        if last is not None and now - last < self._cooldown:
            return False
        self._last_fired[key] = now
        return True

    def filter_events(self, events: list[DetectedEvent], now: datetime) -> list[DetectedEvent]:
        return [e for e in events if self.allow(e.event_type, e.outcome, now)]
