"""NYSE/NASDAQ market-hours calendar: pre/regular/post/closed state.

Pure Python, no HA imports. Uses `zoneinfo` (stdlib) for America/New_York,
so DST transitions are handled by the tz database, not by hand.

The holiday table is a bundled, manually-maintained list (NYSE publishes
its schedule a few years ahead); it is NOT fetched from a live source.
Update `NYSE_HOLIDAYS` / `NYSE_EARLY_CLOSE_DAYS` when adding years.
"""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

MarketState = str  # "pre" | "regular" | "post" | "closed"

_EASTERN = ZoneInfo("America/New_York")

_PRE_MARKET_START = time(4, 0)
_REGULAR_START = time(9, 30)
_REGULAR_END = time(16, 0)
_POST_MARKET_END = time(20, 0)
_EARLY_CLOSE_END = time(13, 0)

# Full-closure NYSE/NASDAQ holidays, 2025-2027 (New Year's Day, MLK Day,
# Washington's Birthday, Good Friday, Memorial Day, Juneteenth, Independence
# Day, Labor Day, Thanksgiving, Christmas). Source: NYSE's published holiday
# calendar as of this session; re-verify/extend for years beyond 2027.
NYSE_HOLIDAYS: frozenset[date] = frozenset(
    {
        date(2025, 1, 1),
        date(2025, 1, 20),
        date(2025, 2, 17),
        date(2025, 4, 18),
        date(2025, 5, 26),
        date(2025, 6, 19),
        date(2025, 7, 4),
        date(2025, 9, 1),
        date(2025, 11, 27),
        date(2025, 12, 25),
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 2, 16),
        date(2026, 4, 3),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 3),  # observed; July 4 falls on a Saturday
        date(2026, 9, 7),
        date(2026, 11, 26),
        date(2026, 12, 25),
        date(2027, 1, 1),
        date(2027, 1, 18),
        date(2027, 2, 15),
        date(2027, 3, 26),
        date(2027, 5, 31),
        date(2027, 6, 18),  # observed; Juneteenth falls on a Saturday
        date(2027, 7, 5),  # observed; July 4 falls on a Sunday
        date(2027, 9, 6),
        date(2027, 11, 25),
        date(2027, 12, 24),  # observed; Christmas falls on a Saturday
    }
)

# Early-close (1:00pm ET) days: day after Thanksgiving, Christmas Eve when
# it's a trading day.
NYSE_EARLY_CLOSE_DAYS: frozenset[date] = frozenset(
    {
        date(2025, 7, 3),
        date(2025, 11, 28),
        date(2025, 12, 24),
        date(2026, 11, 27),
        date(2026, 12, 24),
        date(2027, 11, 26),
    }
)


def is_trading_day(day: date) -> bool:
    return day.weekday() < 5 and day not in NYSE_HOLIDAYS


def market_state(now: datetime) -> MarketState:
    """Return "pre" | "regular" | "post" | "closed" for the given instant."""
    eastern_now = now.astimezone(_EASTERN)
    today = eastern_now.date()

    if not is_trading_day(today):
        return "closed"

    current_time = eastern_now.time()
    regular_end = _EARLY_CLOSE_END if today in NYSE_EARLY_CLOSE_DAYS else _REGULAR_END

    if _PRE_MARKET_START <= current_time < _REGULAR_START:
        return "pre"
    if _REGULAR_START <= current_time < regular_end:
        return "regular"
    if regular_end <= current_time < _POST_MARKET_END:
        return "post"
    return "closed"


def is_regular_hours(now: datetime) -> bool:
    return market_state(now) == "regular"
