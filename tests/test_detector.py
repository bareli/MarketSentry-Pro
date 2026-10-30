"""Tests for detector.py: thresholds+hysteresis, windowed moves, cooldown."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.marketsentry.detector import (
    ClosingSoonDetector,
    CooldownGate,
    DetectedEvent,
    LargeTradeDetector,
    PriceMoveDetector,
    ResolvedDetector,
    ThresholdDetector,
    VolumeSpikeDetector,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class TestThresholdDetector:
    def test_fires_on_upward_crossing(self) -> None:
        det = ThresholdDetector(thresholds=[50.0], hysteresis_pp=0.5)
        det.update("Yes", "tok", 45.0)
        events = det.update("Yes", "tok", 55.0)

        assert len(events) == 1
        assert events[0].direction == "up"
        assert events[0].extra["threshold"] == 50.0

    def test_fires_on_downward_crossing(self) -> None:
        det = ThresholdDetector(thresholds=[50.0], hysteresis_pp=0.5)
        det.update("Yes", "tok", 55.0)
        events = det.update("Yes", "tok", 45.0)

        assert len(events) == 1
        assert events[0].direction == "down"

    def test_hysteresis_prevents_flapping(self) -> None:
        det = ThresholdDetector(thresholds=[50.0], hysteresis_pp=1.0)
        det.update("Yes", "tok", 45.0)
        first = det.update("Yes", "tok", 50.5)  # crosses up, fires
        assert len(first) == 1

        # Small wobble back and forth within the hysteresis band must not re-fire.
        second = det.update("Yes", "tok", 50.2)
        third = det.update("Yes", "tok", 50.8)
        assert second == []
        assert third == []

    def test_rearms_after_retreating_past_hysteresis_band(self) -> None:
        det = ThresholdDetector(thresholds=[50.0], hysteresis_pp=1.0)
        det.update("Yes", "tok", 45.0)
        det.update("Yes", "tok", 51.0)  # fires up, disarmed

        det.update("Yes", "tok", 48.5)  # retreats past 50 - 1.0, re-arms
        events = det.update("Yes", "tok", 51.0)  # fires up again

        assert len(events) == 1
        assert events[0].direction == "up"

    def test_no_event_on_first_update(self) -> None:
        det = ThresholdDetector(thresholds=[50.0], hysteresis_pp=0.5)
        assert det.update("Yes", "tok", 60.0) == []

    def test_multiple_thresholds_independent(self) -> None:
        det = ThresholdDetector(thresholds=[30.0, 70.0], hysteresis_pp=0.5)
        det.update("Yes", "tok", 20.0)
        events = det.update("Yes", "tok", 80.0)

        fired_thresholds = {e.extra["threshold"] for e in events}
        assert fired_thresholds == {30.0, 70.0}


class TestPriceMoveDetector:
    def test_fires_when_delta_exceeds_threshold_within_window(self) -> None:
        det = PriceMoveDetector(delta_pp=5.0, window_min=60)
        det.update("Yes", "tok", 50.0, NOW)
        events = det.update("Yes", "tok", 56.0, NOW + timedelta(minutes=10))

        assert len(events) == 1
        assert events[0].direction == "up"
        assert events[0].delta_pp == 6.0

    def test_does_not_fire_below_threshold(self) -> None:
        det = PriceMoveDetector(delta_pp=5.0, window_min=60)
        det.update("Yes", "tok", 50.0, NOW)
        events = det.update("Yes", "tok", 53.0, NOW + timedelta(minutes=10))

        assert events == []

    def test_old_points_fall_out_of_window(self) -> None:
        det = PriceMoveDetector(delta_pp=5.0, window_min=60)
        det.update("Yes", "tok", 50.0, NOW)
        # 90 minutes later: the first point should have fallen out of the window.
        events = det.update("Yes", "tok", 56.0, NOW + timedelta(minutes=90))

        assert events == []

    def test_resets_window_after_firing(self) -> None:
        det = PriceMoveDetector(delta_pp=5.0, window_min=60)
        det.update("Yes", "tok", 50.0, NOW)
        det.update("Yes", "tok", 56.0, NOW + timedelta(minutes=10))  # fires

        # Immediately after firing, should not re-fire on the same baseline.
        events = det.update("Yes", "tok", 56.5, NOW + timedelta(minutes=11))
        assert events == []


class TestLargeTradeDetector:
    def test_fires_when_notional_meets_threshold(self) -> None:
        det = LargeTradeDetector(threshold_usd=10_000.0)
        events = det.check("Yes", "tok", price=0.5, size=20_000)

        assert len(events) == 1
        assert events[0].extra["notional_usd"] == 10_000.0

    def test_does_not_fire_below_threshold(self) -> None:
        det = LargeTradeDetector(threshold_usd=10_000.0)
        assert det.check("Yes", "tok", price=0.5, size=100) == []


class TestVolumeSpikeDetector:
    def test_fires_on_growth_above_threshold(self) -> None:
        det = VolumeSpikeDetector(spike_pct=50.0)
        det.update("Yes", "tok", 1000.0)
        events = det.update("Yes", "tok", 1600.0)

        assert len(events) == 1
        assert events[0].extra["growth_pct"] == 60.0

    def test_no_fire_on_first_poll(self) -> None:
        det = VolumeSpikeDetector(spike_pct=50.0)
        assert det.update("Yes", "tok", 1000.0) == []

    def test_no_fire_below_threshold(self) -> None:
        det = VolumeSpikeDetector(spike_pct=50.0)
        det.update("Yes", "tok", 1000.0)
        assert det.update("Yes", "tok", 1100.0) == []


class TestClosingSoonDetector:
    def test_fires_once_when_within_threshold(self) -> None:
        det = ClosingSoonDetector(hours=24)
        end_date = NOW + timedelta(hours=12)

        first = det.check("Yes", "tok", end_date, NOW)
        second = det.check("Yes", "tok", end_date, NOW + timedelta(minutes=1))

        assert len(first) == 1
        assert second == []

    def test_does_not_fire_when_outside_threshold(self) -> None:
        det = ClosingSoonDetector(hours=24)
        end_date = NOW + timedelta(hours=48)

        assert det.check("Yes", "tok", end_date, NOW) == []


class TestResolvedDetector:
    def test_fires_once_on_resolution(self) -> None:
        det = ResolvedDetector()
        first = det.check("Yes", "tok", resolved=True, winning_outcome="Yes")
        second = det.check("Yes", "tok", resolved=True, winning_outcome="Yes")

        assert len(first) == 1
        assert first[0].extra["winning_outcome"] == "Yes"
        assert second == []

    def test_no_fire_when_not_resolved(self) -> None:
        det = ResolvedDetector()
        assert det.check("Yes", "tok", resolved=False, winning_outcome=None) == []


class TestCooldownGate:
    def test_suppresses_repeated_event_within_cooldown(self) -> None:
        gate = CooldownGate(cooldown_min=15)
        event = DetectedEvent(event_type="threshold_crossed", outcome="Yes", token_id="tok", old=1, new=2)

        first = gate.filter_events([event], NOW)
        second = gate.filter_events([event], NOW + timedelta(minutes=5))

        assert len(first) == 1
        assert second == []

    def test_allows_after_cooldown_expires(self) -> None:
        gate = CooldownGate(cooldown_min=15)
        event = DetectedEvent(event_type="threshold_crossed", outcome="Yes", token_id="tok", old=1, new=2)

        gate.filter_events([event], NOW)
        later = gate.filter_events([event], NOW + timedelta(minutes=20))

        assert len(later) == 1

    def test_different_outcomes_are_independent(self) -> None:
        gate = CooldownGate(cooldown_min=15)
        yes_event = DetectedEvent(event_type="threshold_crossed", outcome="Yes", token_id="tok1", old=1, new=2)
        no_event = DetectedEvent(event_type="threshold_crossed", outcome="No", token_id="tok2", old=1, new=2)

        gate.filter_events([yes_event], NOW)
        result = gate.filter_events([no_event], NOW)

        assert len(result) == 1
