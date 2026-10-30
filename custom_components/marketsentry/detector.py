"""Pure-Python change detection for Polymarket markets.

No HA imports. Every function/class here is unit-testable in isolation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .const import (
    EVENT_CLOSING_SOON,
    EVENT_LARGE_TRADE,
    EVENT_PRICE_MOVE,
    EVENT_RESOLVED,
    EVENT_THRESHOLD_CROSSED,
    EVENT_VOLUME_SPIKE,
)


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
    """Fires `price_move` when |change| >= delta_pp within a rolling window."""

    def __init__(self, delta_pp: float, window_min: int) -> None:
        self._delta_pp = delta_pp
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

        oldest_time, oldest_price = self._history[0]
        delta = price - oldest_price
        if abs(delta) >= self._delta_pp:
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
