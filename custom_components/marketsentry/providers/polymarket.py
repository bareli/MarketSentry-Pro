"""Polymarket provider: wraps the existing Gamma/CLOB client and WS manager
behind the generic Provider interface. No behavior change to the underlying
REST/WS logic in api.py / ws.py.

Deviation from the architecture sketch: api.py and ws.py stay at the package
root (not physically moved under providers/) because __init__.py and the
entity platforms still import them directly for the single-provider wiring
that ships today; wiring the rest of the integration onto the Provider
interface is a follow-up. This module adapts the existing client/WS manager
rather than duplicating their logic.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any

from aiohttp import ClientSession

from ..api import (
    PolymarketApiClient,
    PolymarketApiError,
    PolymarketNotFoundError,
    parse_polymarket_url_or_slug,
)
from ..models import Market
from ..ws import PolymarketWsManager
from .base import (
    CannotConnect,
    InstrumentRef,
    OnProviderEvent,
    OnQuote,
    OnTrade,
    PricePoint,
    Provider,
    ProviderEvent,
    Quote,
    Trade,
)

_HISTORY_INTERVAL_BY_HOURS = (
    (1, "1h"),
    (6, "6h"),
    (24, "1d"),
    (24 * 7, "1w"),
    (24 * 31, "1m"),
)


def _market_to_refs(market: Market) -> list[InstrumentRef]:
    url = f"https://polymarket.com/market/{market.slug}"
    return [
        InstrumentRef(
            provider="polymarket",
            id=outcome.token_id,
            symbol=outcome.name,
            name=f"{market.question}: {outcome.name}",
            kind="outcome",
            unit="%",
            url=url,
        )
        for outcome in market.outcomes
        if outcome.token_id
    ]


def _history_interval_for(hours: int) -> str:
    for max_hours, interval in _HISTORY_INTERVAL_BY_HOURS:
        if hours <= max_hours:
            return interval
    return "max"


class PolymarketProvider(Provider):
    """Read-only Polymarket outcomes. No API key required."""

    key = "polymarket"
    name = "Polymarket"
    requires_api_key = False
    supports_streaming = True

    def __init__(self, session: ClientSession) -> None:
        self._api = PolymarketApiClient(session)
        self._session = session

    async def validate(self, credentials: dict[str, Any]) -> None:
        return  # public, no-auth API: nothing to validate

    async def search(self, query: str, limit: int) -> list[InstrumentRef]:
        try:
            raw_markets = await self._api.search_markets(query, limit)
        except PolymarketApiError as err:
            raise CannotConnect(str(err)) from err

        refs: list[InstrumentRef] = []
        for raw in raw_markets:
            try:
                refs.extend(_market_to_refs(Market.from_gamma(raw)))
            except (KeyError, TypeError, ValueError):
                continue
        return refs

    async def resolve(self, user_input: str) -> list[InstrumentRef]:
        try:
            parsed = parse_polymarket_url_or_slug(user_input)
        except ValueError as err:
            raise CannotConnect(str(err)) from err

        try:
            if parsed.kind == "market":
                market = await self._api.get_market_by_slug(parsed.slug)
                return _market_to_refs(market)

            event = await self._api.get_event_by_slug(parsed.slug)
        except PolymarketNotFoundError as err:
            raise CannotConnect(f"Not found: {user_input}") from err
        except PolymarketApiError as err:
            raise CannotConnect(str(err)) from err

        refs: list[InstrumentRef] = []
        for market_data in event.get("markets", []):
            refs.extend(_market_to_refs(Market.from_gamma(market_data)))
        return refs

    async def fetch_snapshot(self, refs: list[InstrumentRef]) -> dict[str, Quote]:
        quotes: dict[str, Quote] = {}
        for ref in refs:
            try:
                book = await self._api.get_book(ref.id)
            except PolymarketApiError:
                continue
            best_bid = _best_price(book.get("bids", []))
            best_ask = _best_price(book.get("asks", []))
            last_trade = _to_float(book.get("last_trade_price"))
            price = None
            if best_bid is not None and best_ask is not None:
                price = (best_bid + best_ask) / 2
            quotes[ref.id] = Quote(
                price=price,
                bid=best_bid,
                ask=best_ask,
                ts=datetime.now(UTC),
            )
            if last_trade is not None:
                quotes[ref.id].price = quotes[ref.id].price or last_trade
        return quotes

    async def fetch_history(self, ref: InstrumentRef, hours: int) -> list[PricePoint]:
        interval = _history_interval_for(hours)
        try:
            history = await self._api.get_price_history(ref.id, interval=interval)
        except PolymarketApiError as err:
            raise CannotConnect(str(err)) from err

        points: list[PricePoint] = []
        for point in history:
            ts_raw = point.get("t")
            price_raw = point.get("p")
            if ts_raw is None or price_raw is None:
                continue
            points.append(
                PricePoint(ts=datetime.fromtimestamp(float(ts_raw), tz=UTC), price=float(price_raw))
            )
        return points

    async def stream(
        self,
        refs: list[InstrumentRef],
        on_quote: OnQuote,
        on_trade: OnTrade,
        on_event: OnProviderEvent,
    ) -> None:
        async def handle_message(message: dict[str, Any]) -> None:
            await _dispatch_ws_message(message, on_quote, on_trade, on_event)

        ws_manager = PolymarketWsManager(self._session, handle_message)
        await ws_manager.subscribe([ref.id for ref in refs])
        await ws_manager.start()
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            with contextlib.suppress(Exception):
                await ws_manager.stop()
            raise


def _best_price(levels: list[dict[str, Any]]) -> float | None:
    if not levels:
        return None
    prices = [_to_float(level.get("price")) for level in levels]
    valid = [p for p in prices if p is not None]
    return max(valid) if valid else None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def _dispatch_ws_message(
    message: dict[str, Any], on_quote: OnQuote, on_trade: OnTrade, on_event: OnProviderEvent
) -> None:
    event_type = message.get("event_type")
    now = datetime.now(UTC)

    if event_type in ("price_change", "best_bid_ask"):
        changes = message.get("price_changes") if event_type == "price_change" else [message]
        for change in changes or []:
            token_id = change.get("asset_id")
            if not token_id:
                continue
            best_bid = _to_float(change.get("best_bid"))
            best_ask = _to_float(change.get("best_ask"))
            price = None
            if best_bid is not None and best_ask is not None:
                price = (best_bid + best_ask) / 2
            await on_quote(token_id, Quote(price=price, bid=best_bid, ask=best_ask, ts=now))

    elif event_type == "last_trade_price":
        token_id = message.get("asset_id")
        if token_id:
            price = _to_float(message.get("price")) or 0.0
            size = _to_float(message.get("size")) or 0.0
            await on_trade(token_id, Trade(price=price, size=size, side=message.get("side"), ts=now))

    elif event_type == "market_resolved":
        winning_asset_id = message.get("winning_asset_id")
        for token_id in message.get("assets_ids", []):
            await on_event(
                token_id,
                ProviderEvent(
                    type="resolved",
                    data={"winning": token_id == winning_asset_id},
                ),
            )
