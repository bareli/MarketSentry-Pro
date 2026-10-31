"""Tests for history.py: bounded per-instrument ring buffer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.marketsentry.history import PriceRingBuffer


def test_append_and_get_roundtrip() -> None:
    buf = PriceRingBuffer(max_points=10)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    buf.append("AAPL", now, 150.0)
    buf.append("AAPL", now + timedelta(minutes=5), 151.0)

    points = buf.get("AAPL")
    assert [p.price for p in points] == [150.0, 151.0]


def test_get_unknown_instrument_returns_empty() -> None:
    buf = PriceRingBuffer()
    assert buf.get("unknown") == []


def test_buffer_is_bounded() -> None:
    buf = PriceRingBuffer(max_points=3)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(5):
        buf.append("AAPL", now + timedelta(minutes=i), float(i))

    points = buf.get("AAPL")
    assert [p.price for p in points] == [2.0, 3.0, 4.0]


def test_instruments_are_independent() -> None:
    buf = PriceRingBuffer()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    buf.append("AAPL", now, 150.0)
    buf.append("EUR/ILS", now, 3.9)

    assert [p.price for p in buf.get("AAPL")] == [150.0]
    assert [p.price for p in buf.get("EUR/ILS")] == [3.9]


def test_discard_removes_instrument() -> None:
    buf = PriceRingBuffer()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    buf.append("AAPL", now, 150.0)
    buf.discard("AAPL")

    assert buf.get("AAPL") == []
