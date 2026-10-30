"""Tests for ws.py: subscribe/resubscribe, PING loop, message parsing via a fake WS server."""

from __future__ import annotations

import asyncio
import json

import pytest
from aiohttp import web

from custom_components.marketsentry.ws import PolymarketWsManager


async def _fake_ws_app(received: list[dict], pings: list[str]):
    async def handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                if msg.data == "PING":
                    pings.append(msg.data)
                    await ws.send_str("PONG")
                else:
                    received.append(json.loads(msg.data))
        return ws

    app = web.Application()
    app.router.add_get("/ws", handler)
    return app


async def test_subscribe_sends_initial_payload(aiohttp_client) -> None:
    received: list[dict] = []
    pings: list[str] = []
    app = await _fake_ws_app(received, pings)
    client = await aiohttp_client(app)

    messages: list[dict] = []

    async def on_message(msg: dict) -> None:
        messages.append(msg)

    manager = PolymarketWsManager(
        client.session, on_message, url=str(client.make_url("/ws")).replace("http://", "ws://")
    )
    await manager.subscribe(["tok1", "tok2"])
    await manager.start()
    await asyncio.sleep(0.2)

    assert manager.connected
    assert any(m.get("type") == "market" for m in received)

    await manager.stop()


async def test_subscribe_after_connect_sends_operation_message(aiohttp_client) -> None:
    received: list[dict] = []
    pings: list[str] = []
    app = await _fake_ws_app(received, pings)
    client = await aiohttp_client(app)

    async def on_message(msg: dict) -> None:
        pass

    manager = PolymarketWsManager(
        client.session, on_message, url=str(client.make_url("/ws")).replace("http://", "ws://")
    )
    await manager.start()
    await asyncio.sleep(0.1)

    await manager.subscribe(["tok3"])
    await asyncio.sleep(0.1)

    assert any(m.get("operation") == "subscribe" and "tok3" in m.get("assets_ids", []) for m in received)

    await manager.stop()


async def test_incoming_market_message_dispatched_to_handler(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_str(json.dumps({"event_type": "price_change", "price_changes": []}))
        async for _ in ws:
            pass
        return ws

    app = web.Application()
    app.router.add_get("/ws", handler)
    client = await aiohttp_client(app)

    messages: list[dict] = []

    async def on_message(msg: dict) -> None:
        messages.append(msg)

    manager = PolymarketWsManager(
        client.session, on_message, url=str(client.make_url("/ws")).replace("http://", "ws://")
    )
    await manager.start()
    await asyncio.sleep(0.2)

    assert any(m.get("event_type") == "price_change" for m in messages)

    await manager.stop()


async def test_pong_text_is_ignored_not_parsed_as_json() -> None:
    async def on_message(_msg: dict) -> None:
        pytest.fail("PONG should not be dispatched as a market message")

    manager = PolymarketWsManager(session=None, on_message=on_message)
    await manager._handle_text_message("PONG")
