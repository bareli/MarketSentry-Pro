"""Provider abstraction: one interface for Polymarket, Finnhub, Alpaca, FX.

An "instrument" is anything trackable: a Polymarket outcome, a stock ticker,
or an FX pair. No HA imports here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

InstrumentKind = Literal["outcome", "stock", "fx"]

MarketState = Literal["pre", "regular", "post", "closed"]


@dataclass(slots=True, frozen=True)
class InstrumentRef:
    """A stable reference to one trackable instrument under a provider."""

    provider: str
    id: str
    symbol: str
    name: str
    kind: InstrumentKind
    unit: str
    url: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Quote:
    """A point-in-time price snapshot for one instrument."""

    price: float | None = None
    bid: float | None = None
    ask: float | None = None
    ts: datetime | None = None
    market_state: MarketState | None = None
    previous_close: float | None = None


@dataclass(slots=True)
class Trade:
    """A single executed trade/print for one instrument."""

    price: float
    size: float
    side: str | None = None
    ts: datetime | None = None

    @property
    def notional(self) -> float:
        return self.price * self.size


@dataclass(slots=True)
class PricePoint:
    """One point of historical price data."""

    ts: datetime
    price: float


@dataclass(slots=True)
class ProviderEvent:
    """A provider-specific event not covered by Quote/Trade (e.g. resolution)."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)


OnQuote = Callable[[str, Quote], Awaitable[None]]
OnTrade = Callable[[str, Trade], Awaitable[None]]
OnProviderEvent = Callable[[str, ProviderEvent], Awaitable[None]]


class CannotConnect(Exception):
    """Raised when a provider cannot be reached."""


class InvalidAuth(Exception):
    """Raised when provider credentials are missing or rejected."""


class Provider(ABC):
    """Common interface every market data provider implements."""

    key: str
    name: str
    requires_api_key: bool
    supports_streaming: bool

    @abstractmethod
    async def validate(self, credentials: dict[str, Any]) -> None:
        """Raise InvalidAuth / CannotConnect if credentials don't work."""

    @abstractmethod
    async def search(self, query: str, limit: int) -> list[InstrumentRef]:
        """Free-text search for instruments (ticker/company/market name)."""

    @abstractmethod
    async def resolve(self, user_input: str) -> list[InstrumentRef]:
        """Resolve a URL, slug, ticker, or pair the user typed/pasted directly."""

    @abstractmethod
    async def fetch_snapshot(self, refs: list[InstrumentRef]) -> dict[str, Quote]:
        """Fetch a current quote for each ref, keyed by InstrumentRef.id."""

    @abstractmethod
    async def fetch_history(self, ref: InstrumentRef, hours: int) -> list[PricePoint]:
        """Fetch historical price points for one instrument."""

    async def stream(
        self,
        refs: list[InstrumentRef],
        on_quote: OnQuote,
        on_trade: OnTrade,
        on_event: OnProviderEvent,
    ) -> None:
        """Run a streaming connection for the given refs until cancelled.

        Only implemented by providers with supports_streaming = True.
        """
        raise NotImplementedError(f"{self.key} does not support streaming")
