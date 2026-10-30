"""Tests for providers/finnhub.py: REST shapes, auth errors, WS trade dispatch."""

from __future__ import annotations

import json

import pytest
from aiohttp import web

import custom_components.marketsentry.providers.finnhub as finnhub_module
from custom_components.marketsentry.providers.base import InstrumentRef, InvalidAuth
from custom_components.marketsentry.providers.finnhub import FinnhubProvider


async def _provider_for(aiohttp_client, app: web.Application) -> FinnhubProvider:
    client = await aiohttp_client(app)
    finnhub_module.FINNHUB_REST_BASE_URL = str(client.make_url("")).rstrip("/")
    return FinnhubProvider(client.session, api_key="test-key")


async def test_search_maps_results_to_instrument_refs(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.query["q"] == "apple"
        assert request.headers["X-Finnhub-Token"] == "test-key"
        assert "token" not in request.query
        return web.json_response(
            {
                "count": 1,
                "result": [
                    {"symbol": "AAPL", "displaySymbol": "AAPL", "description": "Apple Inc", "type": "Common Stock"}
                ],
            }
        )

    app = web.Application()
    app.router.add_get("/search", handler)
    provider = await _provider_for(aiohttp_client, app)

    refs = await provider.search("apple", limit=10)

    assert len(refs) == 1
    assert refs[0].id == "AAPL"
    assert refs[0].kind == "stock"
    assert refs[0].unit == "USD"


async def test_validate_raises_invalid_auth_on_401(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=401)

    app = web.Application()
    app.router.add_get("/search", handler)
    provider = await _provider_for(aiohttp_client, app)

    with pytest.raises(InvalidAuth):
        await provider.validate({"api_key": "bad-key"})


async def test_validate_raises_invalid_auth_with_no_key() -> None:
    provider = FinnhubProvider(session=None, api_key="")  # type: ignore[arg-type]
    with pytest.raises(InvalidAuth):
        await provider.validate({})


async def test_fetch_snapshot_parses_quote_fields(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"c": 150.5, "d": 1.2, "dp": 0.8, "h": 151, "l": 149, "o": 150, "pc": 149.3, "t": 1700000000})

    app = web.Application()
    app.router.add_get("/quote", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="finnhub", id="AAPL", symbol="AAPL", name="Apple", kind="stock", unit="USD")
    quotes = await provider.fetch_snapshot([ref])

    assert quotes["AAPL"].price == 150.5
    assert quotes["AAPL"].previous_close == 149.3


async def test_fetch_history_returns_empty_when_no_data(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"s": "no_data"})

    app = web.Application()
    app.router.add_get("/stock/candle", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="finnhub", id="AAPL", symbol="AAPL", name="Apple", kind="stock", unit="USD")
    points = await provider.fetch_history(ref, hours=24)

    assert points == []


async def test_fetch_history_parses_candles(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"s": "ok", "t": [1700000000, 1700003600], "c": [150.0, 151.5]})

    app = web.Application()
    app.router.add_get("/stock/candle", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="finnhub", id="AAPL", symbol="AAPL", name="Apple", kind="stock", unit="USD")
    points = await provider.fetch_history(ref, hours=24)

    assert len(points) == 2
    assert points[1].price == 151.5


async def test_connect_and_listen_dispatches_trade_messages(aiohttp_client) -> None:
    async def ws_handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_str(
            json.dumps({"type": "trade", "data": [{"s": "AAPL", "p": 150.25, "v": 10, "t": 1700000000000}]})
        )
        await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/", ws_handler)
    client = await aiohttp_client(app)
    finnhub_module.FINNHUB_WS_URL = str(client.make_url("/")).replace("http://", "ws://").rstrip("/")

    provider = FinnhubProvider(client.session, api_key="test-key")

    trades: list[tuple[str, object]] = []
    quotes: list[tuple[str, object]] = []

    async def on_quote(symbol: str, quote: object) -> None:
        quotes.append((symbol, quote))

    async def on_trade(symbol: str, trade: object) -> None:
        trades.append((symbol, trade))

    await provider._connect_and_listen(["AAPL"], on_quote, on_trade)

    assert trades[0][0] == "AAPL"
    assert quotes[0][0] == "AAPL"
