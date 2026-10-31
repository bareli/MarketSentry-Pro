"""Tests for providers/alpaca.py: REST shapes, auth errors, WS auth+quote dispatch."""

from __future__ import annotations

import json

import pytest
from aiohttp import web

import custom_components.marketsentry.providers.alpaca as alpaca_module
from custom_components.marketsentry.providers.alpaca import AlpacaProvider
from custom_components.marketsentry.providers.base import CannotConnect, InstrumentRef, InvalidAuth


async def _provider_for(aiohttp_client, app: web.Application) -> AlpacaProvider:
    client = await aiohttp_client(app)
    alpaca_module.ALPACA_DATA_REST_BASE_URL = str(client.make_url("")).rstrip("/")
    return AlpacaProvider(client.session, key_id="key", secret_key="secret")


async def test_resolve_builds_ref_from_latest_trade(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.headers["APCA-API-KEY-ID"] == "key"
        assert request.headers["APCA-API-SECRET-KEY"] == "secret"
        return web.json_response({"trade": {"p": 150.0, "s": 10, "t": "2026-01-01T15:00:00Z"}})

    app = web.Application()
    app.router.add_get("/stocks/AAPL/trades/latest", handler)
    provider = await _provider_for(aiohttp_client, app)

    refs = await provider.resolve("aapl")

    assert refs[0].id == "AAPL"
    assert refs[0].kind == "stock"


async def test_resolve_raises_cannot_connect_for_unknown_symbol(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"trade": None})

    app = web.Application()
    app.router.add_get("/stocks/ZZZZ/trades/latest", handler)
    provider = await _provider_for(aiohttp_client, app)

    with pytest.raises(CannotConnect):
        await provider.resolve("zzzz")


async def test_validate_raises_invalid_auth_on_403(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=403)

    app = web.Application()
    app.router.add_get("/stocks/AAPL/trades/latest", handler)
    provider = await _provider_for(aiohttp_client, app)

    with pytest.raises(InvalidAuth):
        await provider.validate({"key_id": "bad", "secret_key": "bad"})


async def test_validate_raises_invalid_auth_with_missing_credentials() -> None:
    provider = AlpacaProvider(session=None, key_id="", secret_key="")  # type: ignore[arg-type]
    with pytest.raises(InvalidAuth):
        await provider.validate({})


async def test_fetch_snapshot_computes_mid_from_bid_ask(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"quote": {"bp": 149.5, "ap": 150.5, "t": "2026-01-01T15:00:00Z"}})

    app = web.Application()
    app.router.add_get("/stocks/AAPL/quotes/latest", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="alpaca", id="AAPL", symbol="AAPL", name="AAPL", kind="stock", unit="USD")
    quotes = await provider.fetch_snapshot([ref])

    assert quotes["AAPL"].price == 150.0
    assert quotes["AAPL"].bid == 149.5
    assert quotes["AAPL"].ask == 150.5


async def test_fetch_snapshot_one_bad_ref_should_not_drop_the_others(aiohttp_client) -> None:
    """PROV-06 regression: a single ref's failure must not abort the whole
    snapshot, matching the per-ref degradation FxProvider/CryptoProvider/
    PolymarketProvider already implement. Alpaca's fetch_snapshot has no
    per-ref try/except, so today this raises instead of returning a partial
    dict - see qa/plans/PROV-providers.md PROV-06."""

    async def handler(request: web.Request) -> web.Response:
        if request.path.endswith("/BAD/quotes/latest"):
            return web.Response(status=500)
        return web.json_response({"quote": {"bp": 149.5, "ap": 150.5, "t": "2026-01-01T15:00:00Z"}})

    app = web.Application()
    app.router.add_get("/stocks/{symbol}/quotes/latest", handler)
    provider = await _provider_for(aiohttp_client, app)

    good_ref = InstrumentRef(provider="alpaca", id="AAPL", symbol="AAPL", name="AAPL", kind="stock", unit="USD")
    bad_ref = InstrumentRef(provider="alpaca", id="BAD", symbol="BAD", name="BAD", kind="stock", unit="USD")

    quotes = await provider.fetch_snapshot([good_ref, bad_ref])

    assert "AAPL" in quotes, "a healthy ref's quote was dropped because another ref in the same batch failed"


async def test_fetch_history_parses_bars(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response(
            {"bars": [{"t": "2026-01-01T15:00:00Z", "c": 150.0}, {"t": "2026-01-01T16:00:00Z", "c": 151.0}]}
        )

    app = web.Application()
    app.router.add_get("/stocks/AAPL/bars", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="alpaca", id="AAPL", symbol="AAPL", name="AAPL", kind="stock", unit="USD")
    points = await provider.fetch_history(ref, hours=24)

    assert len(points) == 2
    assert points[1].price == 151.0


async def test_connect_and_listen_auths_then_dispatches_quote(aiohttp_client) -> None:
    received: list[dict] = []

    async def ws_handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                payload = json.loads(msg.data)
                received.append(payload)
                if payload.get("action") == "auth":
                    await ws.send_str(json.dumps([{"T": "success", "msg": "authenticated"}]))
                elif payload.get("action") == "subscribe":
                    await ws.send_str(
                        json.dumps(
                            [{"T": "q", "S": "AAPL", "bp": 149.5, "ap": 150.5, "t": "2026-01-01T15:00:00Z"}]
                        )
                    )
                    await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/v2/iex", ws_handler)
    client = await aiohttp_client(app)
    base = str(client.make_url("/v2/_")).replace("http://", "ws://")[:-1]
    alpaca_module.ALPACA_STREAM_URL_TEMPLATE = base + "{feed}"

    provider = AlpacaProvider(client.session, key_id="key", secret_key="secret", feed="iex")

    quotes: list[tuple[str, object]] = []

    async def on_quote(symbol: str, quote: object) -> None:
        quotes.append((symbol, quote))

    async def on_trade(symbol: str, trade: object) -> None:
        pass

    await provider._connect_and_listen(["AAPL"], on_quote, on_trade)

    assert any(r.get("action") == "auth" for r in received)
    assert quotes[0][0] == "AAPL"
    assert quotes[0][1].price == 150.0
