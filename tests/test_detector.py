"""Tests for detector.py: thresholds+hysteresis, windowed moves, cooldown."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.marketsentry.detector import (
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


class TestPriceMoveDetectorRelativeMode:
    def test_relative_mode_fires_on_percent_change(self) -> None:
        det = PriceMoveDetector(delta_pp=2.0, window_min=60, relative=True)
        det.update("AAPL", "AAPL", 100.0, NOW)
        events = det.update("AAPL", "AAPL", 103.0, NOW + timedelta(minutes=10))

        assert len(events) == 1
        assert events[0].extra["change_pct"] == 3.0

    def test_relative_mode_does_not_fire_below_percent_threshold(self) -> None:
        det = PriceMoveDetector(delta_pp=5.0, window_min=60, relative=True)
        det.update("AAPL", "AAPL", 100.0, NOW)
        events = det.update("AAPL", "AAPL", 103.0, NOW + timedelta(minutes=10))

        assert events == []

    def test_absolute_mode_unaffected_by_price_scale(self) -> None:
        # Same 3-point absolute move at a much higher price scale: absolute
        # mode (Polymarket default) must not be fooled into relative terms.
        det = PriceMoveDetector(delta_pp=5.0, window_min=60, relative=False)
        det.update("Yes", "tok", 1000.0, NOW)
        events = det.update("Yes", "tok", 1003.0, NOW + timedelta(minutes=10))

        assert events == []  # 3pp absolute move, below 5pp threshold


class TestDailyChangeDetector:
    def test_fires_against_supplied_previous_close(self) -> None:
        det = DailyChangeDetector(change_pct=2.0)
        events = det.update("AAPL", "AAPL", 103.0, NOW, previous_close=100.0)

        assert len(events) == 1
        assert events[0].extra["change_pct"] == 3.0

    def test_does_not_fire_below_threshold(self) -> None:
        det = DailyChangeDetector(change_pct=5.0)
        events = det.update("AAPL", "AAPL", 103.0, NOW, previous_close=100.0)

        assert events == []

    def test_fires_at_most_once_per_day(self) -> None:
        det = DailyChangeDetector(change_pct=2.0)
        det.update("AAPL", "AAPL", 103.0, NOW, previous_close=100.0)
        again = det.update("AAPL", "AAPL", 110.0, NOW + timedelta(minutes=5), previous_close=100.0)

        assert again == []

    def test_resets_and_refires_on_a_new_day(self) -> None:
        det = DailyChangeDetector(change_pct=2.0)
        det.update("AAPL", "AAPL", 103.0, NOW, previous_close=100.0)
        next_day = det.update(
            "AAPL", "AAPL", 110.0, NOW + timedelta(days=1), previous_close=105.0
        )

        assert len(next_day) == 1

    def test_falls_back_to_first_value_seen_without_previous_close(self) -> None:
        det = DailyChangeDetector(change_pct=2.0)
        first = det.update("EUR/ILS", "fx1", 4.00, NOW)
        assert first == []  # first observation becomes the day's reference

        events = det.update("EUR/ILS", "fx1", 4.10, NOW + timedelta(hours=1))
        assert len(events) == 1


class TestMarketOpenGapDetector:
    def test_fires_once_on_regular_hours_gap(self) -> None:
        det = MarketOpenGapDetector(gap_pct=2.0)
        events = det.check("AAPL", "AAPL", 103.0, previous_close=100.0, market_state="regular", now=NOW)

        assert len(events) == 1
        assert events[0].extra["change_pct"] == 3.0

    def test_ignored_outside_regular_hours(self) -> None:
        det = MarketOpenGapDetector(gap_pct=2.0)
        events = det.check("AAPL", "AAPL", 103.0, previous_close=100.0, market_state="pre", now=NOW)

        assert events == []

    def test_fires_at_most_once_per_session(self) -> None:
        det = MarketOpenGapDetector(gap_pct=2.0)
        det.check("AAPL", "AAPL", 103.0, previous_close=100.0, market_state="regular", now=NOW)
        again = det.check(
            "AAPL", "AAPL", 110.0, previous_close=100.0, market_state="regular",
            now=NOW + timedelta(minutes=5),
        )

        assert again == []


class TestOfficialRatePublishedDetector:
    def test_does_not_fire_on_first_observation(self) -> None:
        det = OfficialRatePublishedDetector()
        events = det.check("EUR/ILS", "fx1", 4.00, published_date=NOW.date())

        assert events == []

    def test_fires_on_a_new_publication_date(self) -> None:
        det = OfficialRatePublishedDetector()
        det.check("EUR/ILS", "fx1", 4.00, published_date=NOW.date())
        events = det.check("EUR/ILS", "fx1", 4.02, published_date=(NOW + timedelta(days=1)).date())

        assert len(events) == 1

    def test_does_not_refire_for_the_same_publication_date(self) -> None:
        det = OfficialRatePublishedDetector()
        det.check("EUR/ILS", "fx1", 4.00, published_date=NOW.date())
        det.check("EUR/ILS", "fx1", 4.02, published_date=(NOW + timedelta(days=1)).date())
        again = det.check("EUR/ILS", "fx1", 4.03, published_date=(NOW + timedelta(days=1)).date())

        assert again == []
