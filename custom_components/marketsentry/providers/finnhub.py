"""Finnhub provider: US stocks (NASDAQ/NYSE), free tier.

Requires the user's own free API key (finnhub.io). Free tier is personal,
non-commercial use only; respect that in the UI/README.

API facts below were NOT confirmed via a live authenticated call (ENH-008, 2026-10-31): no
Finnhub API key was available this session, Finnhub's own published "demo" token no longer works
(401 on /quote and /search), and creating a Finnhub account is out of scope for this agent to do
on the owner's behalf. finnhub.io/docs/api is a JS-rendered SPA that fetch tooling cannot read
either. They ARE corroborated against independent, actively-maintained third-party sources (a real
consumer project's Avro schema for the WS trade message, the `finnhub_api` Elixir client's REST
quote model) that match this file's assumptions exactly - a secondary-source match, not a live
Finnhub response. Get a free API key and verify directly before relying on exact field names/
limits in production:
- WebSocket: wss://ws.finnhub.io?token=<key>; subscribe
  {"type":"subscribe","symbol":"AAPL"}; trade messages
  {"type":"trade","data":[{"p":price,"s":symbol,"t":ms,"v":volume,"c":[...]}]}.
- REST quote: GET /quote?symbol= (token via X-Finnhub-Token header) ->
  {"c":current,"d":change,"dp":percent_change,"h":high,"l":low,"o":open,
  "pc":previous_close,"t":ts}.
- REST search: GET /search?q= (token via X-Finnhub-Token header) ->
  {"count":N,"result":[{"symbol","displaySymbol","description","type"}]}.
- Free tier: ~60 REST calls/min; WebSocket symbol-subscription limit
  reported as 30 (unverified, enforce conservatively upstream).

REST calls authenticate via the X-Finnhub-Token header, not a query
param, so the key never ends up in a logged URL. The WebSocket handshake
has no header-auth option, so the token must be in its connect URL; WS
errors are logged/reported by exception type only, never str(err), to
avoid leaking that URL.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
from datetime import UTC, datetime
from typing import Any

from aiohttp import ClientResponseError, ClientSession, ClientTimeout, WSMsgType

from .base import (
    CannotConnect,
    InstrumentRef,
    InvalidAuth,
    OnProviderEvent,
    OnQuote,
    OnStreamStatus,
    OnTrade,
    PricePoint,
    Provider,
    Quote,
    StreamStatus,
    Trade,
)

_LOGGER = logging.getLogger(__name__)

FINNHUB_REST_BASE_URL = "https://finnhub.io/api/v1"
FINNHUB_WS_URL = "wss://ws.finnhub.io"

FREE_TIER_WS_SYMBOL_LIMIT = 30

_REQUEST_TIMEOUT = ClientTimeout(total=15)
_RECONNECT_MIN_SEC = 1
_RECONNECT_MAX_SEC = 300


def _candle_resolution_for(hours: int) -> str:
    if hours <= 1:
        return "1"
    if hours <= 24:
        return "15"
    if hours <= 24 * 7:
        return "60"
    return "D"


class FinnhubProvider(Provider):
    """US stocks via Finnhub's free REST + WebSocket API."""

    key = "finnhub"
    name = "Finnhub (stocks)"
    requires_api_key = True
    supports_streaming = True

    def __init__(self, session: ClientSession, api_key: str) -> None:
        self._session = session
        self._api_key = api_key

    async def _get(
        self, path: str, params: dict[str, Any] | None = None, api_key: str | None = None
    ) -> Any:
        # Token goes in a header, never the URL/query string, so it can't
        # leak into logs, exception messages, or request_info on an error.
        headers = {"X-Finnhub-Token": api_key or self._api_key}
        url = f"{FINNHUB_REST_BASE_URL}{path}"
        try:
            async with self._session.get(
                url, params=params, headers=headers, timeout=_REQUEST_TIMEOUT
            ) as resp:
                if resp.status == 401:
                    raise InvalidAuth("Invalid Finnhub API key")
                resp.raise_for_status()
                return await resp.json()
        except InvalidAuth:
            raise
        except ClientResponseError as err:
            raise CannotConnect(f"Finnhub request to {path} failed: HTTP {err.status}") from err
        except Exception as err:  # noqa: BLE001
            raise CannotConnect(f"Finnhub request to {path} failed: {type(err).__name__}") from err

    async def validate(self, credentials: dict[str, Any]) -> None:
        key = credentials.get("api_key", "")
        if not key:
            raise InvalidAuth("Finnhub requires an API key")
        await self._get("/search", {"q": "AAPL"}, api_key=key)

    async def search(self, query: str, limit: int) -> list[InstrumentRef]:
        data = await self._get("/search", {"q": query})
        results = data.get("result", []) if isinstance(data, dict) else []
        refs: list[InstrumentRef] = []
        for item in results[:limit]:
            symbol = item.get("symbol")
            if not symbol:
                continue
            refs.append(
                InstrumentRef(
                    provider="finnhub",
                    id=symbol,
                    symbol=item.get("displaySymbol", symbol),
                    name=item.get("description", symbol),
                    kind="stock",
                    unit="USD",
                    url=f"https://finnhub.io/quote/{symbol}",
                )
            )
        return refs

    async def resolve(self, user_input: str) -> list[InstrumentRef]:
        symbol = user_input.strip().upper()
        quote = await self._get("/quote", {"symbol": symbol})
        if not isinstance(quote, dict):
            raise CannotConnect(f"Unknown Finnhub symbol: {symbol}")
        no_data = quote.get("c") in (None, 0) and quote.get("h") in (None, 0)
        if no_data:
            raise CannotConnect(f"Unknown Finnhub symbol: {symbol}")

        name = symbol
        with contextlib.suppress(CannotConnect, InvalidAuth):
            matches = await self.search(symbol, limit=5)
            for match in matches:
                if match.id == symbol:
                    name = match.name
                    break

        return [
            InstrumentRef(
                provider="finnhub",
                id=symbol,
                symbol=symbol,
                name=name,
                kind="stock",
                unit="USD",
                url=f"https://finnhub.io/quote/{symbol}",
            )
        ]

    async def fetch_snapshot(self, refs: list[InstrumentRef]) -> dict[str, Quote]:
        quotes: dict[str, Quote] = {}
        for ref in refs:
            try:
                data = await self._get("/quote", {"symbol": ref.id})
            except CannotConnect as err:
                _LOGGER.debug("Finnhub snapshot failed for %s: %s", ref.id, err)
                continue
            if not isinstance(data, dict):
                continue
            price = data.get("c")
            ts_raw = data.get("t")
            quotes[ref.id] = Quote(
                price=float(price) if price is not None else None,
                previous_close=float(data["pc"]) if data.get("pc") is not None else None,
                ts=datetime.fromtimestamp(float(ts_raw), tz=UTC) if ts_raw else datetime.now(UTC),
            )
        return quotes

    async def fetch_history(self, ref: InstrumentRef, hours: int) -> list[PricePoint]:
        now = datetime.now(UTC)
        resolution = _candle_resolution_for(hours)
        data = await self._get(
            "/stock/candle",
            {
                "symbol": ref.id,
                "resolution": resolution,
                "from": int(now.timestamp()) - hours * 3600,
                "to": int(now.timestamp()),
            },
        )
        if not isinstance(data, dict) or data.get("s") != "ok":
            return []
        timestamps = data.get("t", [])
        closes = data.get("c", [])
        return [
            PricePoint(ts=datetime.fromtimestamp(float(t), tz=UTC), price=float(c))
            for t, c in zip(timestamps, closes, strict=False)
        ]

    async def stream(
        self,
        refs: list[InstrumentRef],
        on_quote: OnQuote,
        on_trade: OnTrade,
        on_event: OnProviderEvent,
        on_status: OnStreamStatus | None = None,
    ) -> None:
        if len(refs) > FREE_TIER_WS_SYMBOL_LIMIT:
            _LOGGER.warning(
                "Subscribing to %d Finnhub symbols, above the free-tier limit of %d",
                len(refs),
                FREE_TIER_WS_SYMBOL_LIMIT,
            )

        symbols = [ref.id for ref in refs]
        attempt = 0
        reconnect_count = 0
        while True:
            if on_status is not None:
                on_status(
                    StreamStatus(
                        phase="connecting" if reconnect_count == 0 else "reconnecting",
                        reconnect_count=reconnect_count,
                    )
                )
            try:
                await self._connect_and_listen(symbols, on_quote, on_trade, on_status, reconnect_count)
                attempt = 0
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                # Never log str(err) here: aiohttp WS errors can embed the
                # full request URL, which carries the API token as a query
                # param (the WS handshake has no header-auth option).
                _LOGGER.debug("Finnhub WS error: %s", type(err).__name__)

            attempt += 1
            reconnect_count += 1
            delay = min(_RECONNECT_MIN_SEC * (2 ** (attempt - 1)), _RECONNECT_MAX_SEC)
            if on_status is not None:
                on_status(StreamStatus(phase="backing_off", reconnect_count=reconnect_count))
            await asyncio.sleep(delay + random.uniform(0, delay * 0.25))

    async def _connect_and_listen(
        self,
        symbols: list[str],
        on_quote: OnQuote,
        on_trade: OnTrade,
        on_status: OnStreamStatus | None = None,
        reconnect_count: int = 0,
    ) -> None:
        url = f"{FINNHUB_WS_URL}?token={self._api_key}"
        async with self._session.ws_connect(url) as ws:
            if on_status is not None:
                on_status(StreamStatus(phase="connected", reconnect_count=reconnect_count))
            for symbol in symbols:
                await ws.send_str(json.dumps({"type": "subscribe", "symbol": symbol}))

            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR):
                        break
                    continue
                try:
                    parsed = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue
                if parsed.get("type") != "trade":
                    continue
                now = datetime.now(UTC)
                for item in parsed.get("data", []):
                    symbol = item.get("s")
                    price = item.get("p")
                    if not symbol or price is None:
                        continue
                    size = float(item.get("v", 0) or 0)
                    ts = datetime.fromtimestamp(item["t"] / 1000, tz=UTC) if item.get("t") else now
                    await on_trade(symbol, Trade(price=float(price), size=size, ts=ts))
                    await on_quote(symbol, Quote(price=float(price), ts=ts))
