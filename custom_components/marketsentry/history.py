"""Bounded in-memory price history per instrument, for the card's sparkline.

Independent of the recorder (which may purge, exclude these entities, or
simply not have accumulated enough history yet) and of any provider's
rate-limited history API. Populated on every quote update; read by
websocket_api.py. Not persisted across HA restarts.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime

DEFAULT_MAX_POINTS = 288  # ~24h at one point per 5 minutes


@dataclass(slots=True)
class HistoryPoint:
    ts: datetime
    price: float


class PriceRingBuffer:
    """One bounded deque of (ts, price) per instrument id."""

    def __init__(self, max_points: int = DEFAULT_MAX_POINTS) -> None:
        self._max_points = max_points
        self._buffers: dict[str, deque[HistoryPoint]] = {}

    def append(self, instrument_id: str, ts: datetime, price: float) -> None:
        buf = self._buffers.get(instrument_id)
        if buf is None:
            buf = deque(maxlen=self._max_points)
            self._buffers[instrument_id] = buf
        buf.append(HistoryPoint(ts=ts, price=price))

    def get(self, instrument_id: str) -> list[HistoryPoint]:
        return list(self._buffers.get(instrument_id, ()))

    def discard(self, instrument_id: str) -> None:
        self._buffers.pop(instrument_id, None)
