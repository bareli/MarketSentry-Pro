"""Tests for market_calendar.py: NYSE/NASDAQ session state, holidays, DST."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.marketsentry.market_calendar import (
    is_trading_day,
    market_state,
)

EASTERN = ZoneInfo("America/New_York")


def _et(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=EASTERN)


def test_regular_hours_on_a_normal_weekday() -> None:
    assert market_state(_et(2026, 6, 10, 10, 0)) == "regular"


def test_pre_market_before_open() -> None:
    assert market_state(_et(2026, 6, 10, 5, 0)) == "pre"


def test_post_market_after_close() -> None:
    assert market_state(_et(2026, 6, 10, 17, 0)) == "post"


def test_closed_overnight() -> None:
    assert market_state(_et(2026, 6, 10, 2, 0)) == "closed"


def test_closed_on_weekend() -> None:
    assert market_state(_et(2026, 6, 13, 10, 0)) == "closed"  # Saturday


def test_closed_on_holiday() -> None:
    assert market_state(_et(2026, 1, 1, 10, 0)) == "closed"  # New Year's Day
    assert not is_trading_day(_et(2026, 1, 1, 10, 0).date())


def test_early_close_day_regular_ends_at_1pm() -> None:
    day_after_thanksgiving = _et(2026, 11, 27, 12, 30)
    assert market_state(day_after_thanksgiving) == "regular"
    assert market_state(_et(2026, 11, 27, 13, 30)) == "post"


def test_trading_day_excludes_weekends_and_holidays() -> None:
    assert is_trading_day(_et(2026, 6, 10, 0).date())  # Wednesday
    assert not is_trading_day(_et(2026, 6, 13, 0).date())  # Saturday
    assert not is_trading_day(_et(2026, 12, 25, 0).date())  # Christmas


def test_dst_spring_forward_transition_regular_hours() -> None:
    # 2026-03-08: US spring-forward DST transition. 9:30am ET must still be
    # "regular" regardless of the UTC offset shift that day.
    assert market_state(_et(2026, 3, 9, 10, 0)) == "regular"


def test_dst_fall_back_transition_regular_hours() -> None:
    # 2026-11-01: US fall-back DST transition.
    assert market_state(_et(2026, 11, 2, 10, 0)) == "regular"


def test_utc_input_converts_correctly_to_eastern() -> None:
    from datetime import UTC

    # 14:30 UTC on a summer day = 10:30 ET (EDT, UTC-4) -> regular hours.
    utc_dt = datetime(2026, 6, 10, 14, 30, tzinfo=UTC)
    assert market_state(utc_dt) == "regular"
