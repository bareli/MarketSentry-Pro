"""Tests for providers/alpaca.py: REST shapes, auth errors, WS auth+quote dispatch."""

from __future__ import annotations

import asyncio
import json

import pytest
from aiohttp import web

import custom_components.marketsentry.providers.alpaca as alpaca_module
from custom_components.marketsentry.providers.alpaca import AlpacaProvider
from custom_components.marketsentry.providers.base import (
    CannotConnect,
    InstrumentRef,
    InvalidAuth,
    StreamStatus,
)


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
    """ENH-008 regression: Alpaca's real historical-bars endpoint is the multi-symbol
    /v2/stocks/bars (symbols= query param), and nests bars under {"bars": {"<symbol>": [...]}} -
    not /v2/stocks/{symbol}/bars with a flat list, which this test used to assert. Confirmed
    against docs.alpaca.markets live, 2026-10-31 - see providers/alpaca.py's module docstring."""

    async def handler(request: web.Request) -> web.Response:
        assert request.query["symbols"] == "AAPL"
        return web.json_response(
            {
                "bars": {
                    "AAPL": [
                        {"t": "2026-01-01T15:00:00Z", "c": 150.0},
                        {"t": "2026-01-01T16:00:00Z", "c": 151.0},
                    ]
                },
                "next_page_token": None,
            }
        )

    app = web.Application()
    app.router.add_get("/stocks/bars", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="alpaca", id="AAPL", symbol="AAPL", name="AAPL", kind="stock", unit="USD")
    points = await provider.fetch_history(ref, hours=24)

    assert len(points) == 2
    assert points[1].price == 151.0


async def test_fetch_history_ignores_other_symbols_in_a_shared_response(aiohttp_client) -> None:
    """The multi-symbol endpoint's response could in principle carry other symbols' bars
    (not requested here, since fetch_history only ever asks for one at a time) - confirm only
    the requested ref's bars are read, by key, not by position or a flattened merge."""

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "bars": {
                    "AAPL": [{"t": "2026-01-01T15:00:00Z", "c": 150.0}],
                    "MSFT": [{"t": "2026-01-01T15:00:00Z", "c": 999.0}],
                }
            }
        )

    app = web.Application()
    app.router.add_get("/stocks/bars", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="alpaca", id="AAPL", symbol="AAPL", name="AAPL", kind="stock", unit="USD")
    points = await provider.fetch_history(ref, hours=24)

    assert len(points) == 1
    assert points[0].price == 150.0


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


async def test_connect_and_listen_reports_connected_status_after_auth(aiohttp_client) -> None:
    """ENH-007: "connected" must only be reported once the WS auth handshake
    actually succeeds (not merely once the socket opens), with the
    reconnect_count it was given passed through unchanged."""

    async def ws_handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                payload = json.loads(msg.data)
                if payload.get("action") == "auth":
                    await ws.send_str(json.dumps([{"T": "success", "msg": "authenticated"}]))
                elif payload.get("action") == "subscribe":
                    await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/v2/iex", ws_handler)
    client = await aiohttp_client(app)
    base = str(client.make_url("/v2/_")).replace("http://", "ws://")[:-1]
    alpaca_module.ALPACA_STREAM_URL_TEMPLATE = base + "{feed}"

    provider = AlpacaProvider(client.session, key_id="key", secret_key="secret", feed="iex")
    statuses: list[StreamStatus] = []

    async def on_quote(symbol: str, quote: object) -> None:
        pass

    async def on_trade(symbol: str, trade: object) -> None:
        pass

    await provider._connect_and_listen(["AAPL"], on_quote, on_trade, statuses.append, reconnect_count=2)

    assert statuses == [StreamStatus(phase="connected", reconnect_count=2)]


async def test_connect_and_listen_reports_no_status_when_auth_fails(aiohttp_client) -> None:
    """ENH-007: a failed WS auth must raise InvalidAuth (existing behavior,
    unchanged) and must NOT report "connected" - the finnhub/alpaca
    stream() loop treats an exception from `_connect_and_listen` as a
    failed attempt and moves straight to backing_off/reconnecting."""

    async def ws_handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_str(json.dumps([{"T": "error", "msg": "auth failed"}]))
        await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/v2/iex", ws_handler)
    client = await aiohttp_client(app)
    base = str(client.make_url("/v2/_")).replace("http://", "ws://")[:-1]
    alpaca_module.ALPACA_STREAM_URL_TEMPLATE = base + "{feed}"

    provider = AlpacaProvider(client.session, key_id="key", secret_key="secret", feed="iex")
    statuses: list[StreamStatus] = []

    async def on_quote(symbol: str, quote: object) -> None:
        pass

    async def on_trade(symbol: str, trade: object) -> None:
        pass

    with pytest.raises(InvalidAuth):
        await provider._connect_and_listen(["AAPL"], on_quote, on_trade, statuses.append)

    assert statuses == []


async def test_stream_reports_reconnect_phases_and_increments_reconnect_count(monkeypatch) -> None:
    """ENH-007 regression: same phase/reconnect_count contract as Finnhub's
    stream() loop - "connecting" first, then "backing_off" right after a
    failed attempt (before sleeping), then "reconnecting" on retry, with
    reconnect_count rising across the cycle."""

    provider = AlpacaProvider(session=None, key_id="key", secret_key="secret")  # type: ignore[arg-type]
    calls = 0

    async def fake_connect_and_listen(symbols, on_quote, on_trade, on_status=None, reconnect_count=0):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise CannotConnect("boom")
        raise asyncio.CancelledError

    real_sleep = asyncio.sleep
    monkeypatch.setattr(provider, "_connect_and_listen", fake_connect_and_listen)
    monkeypatch.setattr(alpaca_module.asyncio, "sleep", lambda *_a, **_k: real_sleep(0))

    ref = InstrumentRef(provider="alpaca", id="AAPL", symbol="AAPL", name="AAPL", kind="stock", unit="USD")
    statuses: list[StreamStatus] = []

    async def on_quote(symbol: str, quote: object) -> None:
        pass

    async def on_trade(symbol: str, trade: object) -> None:
        pass

    async def on_event(symbol: str, event: object) -> None:
        pass

    with pytest.raises(asyncio.CancelledError):
        await provider.stream([ref], on_quote, on_trade, on_event, statuses.append)

    assert statuses == [
        StreamStatus(phase="connecting", reconnect_count=0),
        StreamStatus(phase="backing_off", reconnect_count=1),
        StreamStatus(phase="reconnecting", reconnect_count=1),
    ]
