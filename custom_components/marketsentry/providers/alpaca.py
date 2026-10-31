"""Alpaca provider (optional): US stocks via the free IEX feed.

Requires an Alpaca API key ID + secret. IEX-only data on the free Basic
plan is NOT the consolidated tape; label it as such in the UI.

Facts confirmed live (ENH-008, 2026-10-31) by fetching docs.alpaca.markets directly and, where
docs alone were ambiguous, cross-checking against actively-maintained third-party client
libraries (py-alpaca-api, the Elixir alpa_ex client) that call the same endpoints today:
- Auth: {"action":"auth","key":KEY_ID,"secret":SECRET_KEY} -> reply
  [{"T":"success","msg":"authenticated"}]. Must auth within 10s of connecting.
- Subscribe (additive): {"action":"subscribe","trades":[...],"quotes":[...],
  "bars":[...]}; unsubscribe removes only the listed symbols.
- Quote message shape: {"T":"q","S":symbol,"bp":bid_price,"bs":bid_size,
  "ap":ask_price,"as":ask_size,"t":iso_timestamp,...}.
- Error codes: 405 symbol limit exceeded, 406 connection limit exceeded
  (most accounts: 1 connection), 409 insufficient subscription.
- WS feed path segment: literal "iex" or "sip" (`wss://stream.data.alpaca.markets/v2/iex` or
  `/v2/sip`); sandbox variant is `wss://stream.data.sandbox.alpaca.markets/v2/{feed}`. Matches
  `ALPACA_STREAM_URL_TEMPLATE` below exactly.
- REST latest-quote/latest-trade: the single-symbol paths this code uses
  (/v2/stocks/{symbol}/quotes/latest, /v2/stocks/{symbol}/trades/latest) are still actively called
  by maintained third-party clients today - kept as-is.
- REST historical bars: **was wrong, fixed this session.** The real endpoint is the multi-symbol
  `/v2/stocks/bars` with a `symbols` query param (not `/v2/stocks/{symbol}/bars`), and the response
  nests bars under `{"bars": {"<symbol>": [...]}}`, not a flat list - `fetch_history()` would have
  thrown `AttributeError` iterating dict keys as bar objects. `fetch_history()` below now builds
  the correct URL/params and extracts `bars_by_symbol[ref.id]`.

NOT independently confirmed (no Alpaca account available to this session to call live; corroborated
only by the sources above, not Alpaca's own response):
- The exact trade message field names (assumed "T":"t" with p/s/t/S, by analogy with the
  confirmed quote shape - docs.alpaca.markets/docs/streaming-market-data shows quote and bar
  message examples but not a trade one).
- The free-tier WS symbol limit (commonly cited as 30; only the error code for exceeding it, 405,
  is confirmed).
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import UTC, datetime
from typing import Any

from aiohttp import ClientSession, ClientTimeout, WSMsgType

from .base import (
    CannotConnect,
    InstrumentRef,
    InvalidAuth,
    OnProviderEvent,
    OnQuote,
    OnTrade,
    PricePoint,
    Provider,
    Quote,
    Trade,
)

_LOGGER = logging.getLogger(__name__)

ALPACA_DATA_REST_BASE_URL = "https://data.alpaca.markets/v2"
ALPACA_STREAM_URL_TEMPLATE = "wss://stream.data.alpaca.markets/v2/{feed}"

FREE_TIER_WS_SYMBOL_LIMIT = 30  # unverified this session, see module docstring

_REQUEST_TIMEOUT = ClientTimeout(total=15)
_AUTH_TIMEOUT_SEC = 10
_RECONNECT_MIN_SEC = 1
_RECONNECT_MAX_SEC = 300


def _bar_timeframe_for(hours: int) -> str:
    if hours <= 1:
        return "1Min"
    if hours <= 24:
        return "15Min"
    if hours <= 24 * 7:
        return "1Hour"
    return "1Day"


class AlpacaProvider(Provider):
    """US stocks via Alpaca's free IEX feed (optional provider)."""

    key = "alpaca"
    name = "Alpaca (stocks, IEX feed)"
    requires_api_key = True
    supports_streaming = True

    def __init__(self, session: ClientSession, key_id: str, secret_key: str, feed: str = "iex") -> None:
        self._session = session
        self._key_id = key_id
        self._secret_key = secret_key
        self._feed = feed

    def _auth_headers(self, key_id: str | None = None, secret_key: str | None = None) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": key_id or self._key_id,
            "APCA-API-SECRET-KEY": secret_key or self._secret_key,
        }

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{ALPACA_DATA_REST_BASE_URL}{path}"
        try:
            async with self._session.get(
                url, params=params, headers=self._auth_headers(), timeout=_REQUEST_TIMEOUT
            ) as resp:
                if resp.status in (401, 403):
                    raise InvalidAuth("Invalid Alpaca API key/secret")
                resp.raise_for_status()
                return await resp.json()
        except InvalidAuth:
            raise
        except Exception as err:  # noqa: BLE001
            raise CannotConnect(f"Alpaca request to {path} failed: {err}") from err

    async def validate(self, credentials: dict[str, Any]) -> None:
        key_id = credentials.get("key_id", "")
        secret_key = credentials.get("secret_key", "")
        if not key_id or not secret_key:
            raise InvalidAuth("Alpaca requires a key ID and secret key")

        url = f"{ALPACA_DATA_REST_BASE_URL}/stocks/AAPL/trades/latest"
        try:
            async with self._session.get(
                url,
                headers=self._auth_headers(key_id, secret_key),
                timeout=_REQUEST_TIMEOUT,
            ) as resp:
                if resp.status in (401, 403):
                    raise InvalidAuth("Invalid Alpaca API key/secret")
                resp.raise_for_status()
        except InvalidAuth:
            raise
        except Exception as err:  # noqa: BLE001
            raise CannotConnect(f"Could not reach Alpaca: {err}") from err

    async def search(self, query: str, limit: int) -> list[InstrumentRef]:
        # Alpaca's market-data API has no free-text symbol search; a direct
        # ticker lookup via resolve() is the supported path.
        try:
            return await self.resolve(query)
        except CannotConnect:
            return []

    async def resolve(self, user_input: str) -> list[InstrumentRef]:
        symbol = user_input.strip().upper()
        data = await self._get(f"/stocks/{symbol}/trades/latest")
        if not isinstance(data, dict) or not data.get("trade"):
            raise CannotConnect(f"Unknown Alpaca symbol: {symbol}")

        return [
            InstrumentRef(
                provider="alpaca",
                id=symbol,
                symbol=symbol,
                name=symbol,
                kind="stock",
                unit="USD",
                url=f"https://app.alpaca.markets/research/stocks/{symbol}",
            )
        ]

    async def fetch_snapshot(self, refs: list[InstrumentRef]) -> dict[str, Quote]:
        quotes: dict[str, Quote] = {}
        for ref in refs:
            try:
                data = await self._get(f"/stocks/{ref.id}/quotes/latest")
            except CannotConnect as err:
                _LOGGER.debug("Alpaca snapshot failed for %s: %s", ref.id, err)
                continue
            quote_data = data.get("quote") if isinstance(data, dict) else None
            if not quote_data:
                continue
            bid = quote_data.get("bp")
            ask = quote_data.get("ap")
            price = (bid + ask) / 2 if bid is not None and ask is not None else None
            ts_raw = quote_data.get("t")
            quotes[ref.id] = Quote(
                price=price,
                bid=float(bid) if bid is not None else None,
                ask=float(ask) if ask is not None else None,
                ts=_parse_iso(ts_raw) or datetime.now(UTC),
            )
        return quotes

    async def fetch_history(self, ref: InstrumentRef, hours: int) -> list[PricePoint]:
        now = datetime.now(UTC)
        start = now.timestamp() - hours * 3600
        data = await self._get(
            "/stocks/bars",
            {
                "symbols": ref.id,
                "timeframe": _bar_timeframe_for(hours),
                "start": datetime.fromtimestamp(start, tz=UTC).isoformat(),
                "end": now.isoformat(),
            },
        )
        bars_by_symbol = data.get("bars", {}) if isinstance(data, dict) else {}
        bars = bars_by_symbol.get(ref.id, []) if isinstance(bars_by_symbol, dict) else []
        points: list[PricePoint] = []
        for bar in bars:
            ts = _parse_iso(bar.get("t"))
            close = bar.get("c")
            if ts is None or close is None:
                continue
            points.append(PricePoint(ts=ts, price=float(close)))
        return points

    async def stream(
        self,
        refs: list[InstrumentRef],
        on_quote: OnQuote,
        on_trade: OnTrade,
        on_event: OnProviderEvent,
    ) -> None:
        if len(refs) > FREE_TIER_WS_SYMBOL_LIMIT:
            _LOGGER.warning(
                "Subscribing to %d Alpaca symbols, above the assumed free-tier limit of %d",
                len(refs),
                FREE_TIER_WS_SYMBOL_LIMIT,
            )

        symbols = [ref.id for ref in refs]
        attempt = 0
        while True:
            try:
                await self._connect_and_listen(symbols, on_quote, on_trade)
                attempt = 0
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Alpaca WS error: %s", err)

            attempt += 1
            delay = min(_RECONNECT_MIN_SEC * (2 ** (attempt - 1)), _RECONNECT_MAX_SEC)
            await asyncio.sleep(delay + random.uniform(0, delay * 0.25))

    async def _connect_and_listen(self, symbols: list[str], on_quote: OnQuote, on_trade: OnTrade) -> None:
        url = ALPACA_STREAM_URL_TEMPLATE.format(feed=self._feed)
        async with self._session.ws_connect(url) as ws:
            await ws.send_str(
                json.dumps({"action": "auth", "key": self._key_id, "secret": self._secret_key})
            )
            authenticated = False
            try:
                async with asyncio.timeout(_AUTH_TIMEOUT_SEC):
                    async for msg in ws:
                        if msg.type != WSMsgType.TEXT:
                            continue
                        for item in json.loads(msg.data):
                            if item.get("T") == "success" and item.get("msg") == "authenticated":
                                authenticated = True
                        if authenticated:
                            break
            except TimeoutError as err:
                raise CannotConnect("Alpaca WS auth timed out") from err

            if not authenticated:
                raise InvalidAuth("Alpaca WS authentication failed")

            await ws.send_str(
                json.dumps({"action": "subscribe", "trades": symbols, "quotes": symbols})
            )

            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR):
                        break
                    continue
                try:
                    items = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue
                for item in items:
                    await _handle_stream_item(item, on_quote, on_trade)


async def _handle_stream_item(item: dict[str, Any], on_quote: OnQuote, on_trade: OnTrade) -> None:
    msg_type = item.get("T")
    symbol = item.get("S")
    if not symbol:
        return
    ts = _parse_iso(item.get("t")) or datetime.now(UTC)

    if msg_type == "t":
        price = item.get("p")
        if price is None:
            return
        size = float(item.get("s", 0) or 0)
        await on_trade(symbol, Trade(price=float(price), size=size, ts=ts))
        await on_quote(symbol, Quote(price=float(price), ts=ts))
    elif msg_type == "q":
        bid, ask = item.get("bp"), item.get("ap")
        price = (bid + ask) / 2 if bid is not None and ask is not None else None
        await on_quote(
            symbol,
            Quote(
                price=price,
                bid=float(bid) if bid is not None else None,
                ask=float(ask) if ask is not None else None,
                ts=ts,
            ),
        )


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
