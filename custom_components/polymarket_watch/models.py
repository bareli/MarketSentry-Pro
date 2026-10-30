"""Plain dataclasses for Polymarket domain objects. No HA imports here."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def parse_json_field(value: Any) -> list[Any]:
    """Parse a field that may be a JSON-encoded string or already a list.

    Gamma's schema types `outcomes`, `outcomePrices`, `clobTokenIds` as strings,
    but they are most likely JSON-encoded arrays. Handle both shapes defensively.
    """
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
        if isinstance(parsed, list):
            return parsed
        return []
    return []


@dataclass(slots=True)
class Outcome:
    """A single outcome of a market (e.g. "Yes" / "No")."""

    name: str
    token_id: str
    price: float | None = None
    best_bid: float | None = None
    best_ask: float | None = None
    last_trade_price: float | None = None


@dataclass(slots=True)
class Market:
    """A single Polymarket market (one question with N outcomes)."""

    id: str
    slug: str
    question: str
    condition_id: str
    active: bool
    closed: bool
    accepting_orders: bool
    end_date: datetime | None
    volume: float
    volume_24hr: float
    liquidity: float
    closed_time: datetime | None
    uma_resolution_status: str | None
    outcomes: list[Outcome] = field(default_factory=list)

    @classmethod
    def from_gamma(cls, data: dict[str, Any]) -> Market:
        """Build a Market from a Gamma API /markets/slug/{slug} response."""
        names = parse_json_field(data.get("outcomes"))
        prices = parse_json_field(data.get("outcomePrices"))
        token_ids = parse_json_field(data.get("clobTokenIds"))

        outcomes: list[Outcome] = []
        for idx, name in enumerate(names):
            price_raw = prices[idx] if idx < len(prices) else None
            token_id = str(token_ids[idx]) if idx < len(token_ids) else ""
            outcomes.append(
                Outcome(
                    name=str(name),
                    token_id=token_id,
                    price=_to_float(price_raw),
                )
            )

        return cls(
            id=str(data.get("id", "")),
            slug=str(data.get("slug", "")),
            question=str(data.get("question", "")),
            condition_id=str(data.get("conditionId", "")),
            active=bool(data.get("active", False)),
            closed=bool(data.get("closed", False)),
            accepting_orders=bool(data.get("acceptingOrders", False)),
            end_date=_parse_datetime(data.get("endDate")),
            volume=_to_float(data.get("volumeNum")) or 0.0,
            volume_24hr=_to_float(data.get("volume24hr")) or 0.0,
            liquidity=_to_float(data.get("liquidityNum")) or 0.0,
            closed_time=_parse_datetime(data.get("closedTime")),
            uma_resolution_status=data.get("umaResolutionStatus"),
            outcomes=outcomes,
        )


@dataclass(slots=True)
class Quote:
    """A live quote update for a single outcome token, from the WS feed."""

    token_id: str
    best_bid: float | None = None
    best_ask: float | None = None
    last_trade_price: float | None = None
    timestamp: datetime | None = None

    @property
    def midpoint(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2


@dataclass(slots=True)
class Trade:
    """A single trade print from the WS `last_trade_price` event."""

    token_id: str
    price: float
    size: float
    side: str
    timestamp: datetime | None = None

    @property
    def notional_usd(self) -> float:
        return self.price * self.size


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            text = value.replace("Z", "+00:00")
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None
