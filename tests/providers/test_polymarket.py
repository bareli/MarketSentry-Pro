"""Tests for providers/polymarket.py: Provider-interface adapter over the
existing Gamma/CLOB client, and the WS message -> on_quote/on_trade/on_event
dispatch table.
"""

from __future__ import annotations

import asyncio

import pytest
from aiohttp import web

import custom_components.marketsentry.api as api_module
import custom_components.marketsentry.providers.polymarket as polymarket_module
from custom_components.marketsentry.models import Market
from custom_components.marketsentry.providers.base import InstrumentRef, ProviderEvent, Quote, Trade
from custom_components.marketsentry.providers.polymarket import (
    PolymarketProvider,
    _dispatch_ws_message,
    _market_to_refs,
)
from tests.conftest import GAMMA_MARKET_FIXTURE


async def _noop_on_quote(ref_id: str, quote: Quote) -> None:
    pass


async def _noop_on_trade(ref_id: str, trade) -> None:  # noqa: ANN001
    pass


async def _noop_on_event(ref_id: str, event: ProviderEvent) -> None:
    pass


class _FakeWsManager:
    """Stands in for PolymarketWsManager: captures the connection-state
    callback so a test can drive it directly instead of a real WebSocket.
    Records the most recently constructed instance on the class itself so
    the test can reach it without threading extra plumbing through stream()."""

    last_instance: _FakeWsManager | None = None

    def __init__(self, session, on_message, on_connection_state_change=None, url=None) -> None:  # noqa: ANN001
        self.on_connection_state_change = on_connection_state_change
        self.subscribed: list[str] = []
        _FakeWsManager.last_instance = self

    async def subscribe(self, token_ids: list[str]) -> None:
        self.subscribed.extend(token_ids)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


def test_market_to_refs_yields_one_ref_per_outcome() -> None:
    market = Market.from_gamma(GAMMA_MARKET_FIXTURE)
    refs = _market_to_refs(market)

    assert len(refs) == 2
    assert refs[0] == InstrumentRef(
        provider="polymarket",
        id="111",
        symbol="Yes",
        name="Will X happen?: Yes",
        kind="outcome",
        unit="%",
        url="https://polymarket.com/market/will-x-happen",
        extra={"market_slug": "will-x-happen", "question": "Will X happen?"},
    )


async def test_resolve_market_slug(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response(GAMMA_MARKET_FIXTURE)

    app = web.Application()
    app.router.add_get("/markets/slug/will-x-happen", handler)
    client = await aiohttp_client(app)
    api_module.GAMMA_BASE_URL = str(client.make_url("")).rstrip("/")

    provider = PolymarketProvider(client.session)
    refs = await provider.resolve("https://polymarket.com/market/will-x-happen")

    assert len(refs) == 2
    assert {r.symbol for r in refs} == {"Yes", "No"}


async def test_fetch_snapshot_uses_order_book(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response(
            {"bids": [{"price": "0.58", "size": "100"}], "asks": [{"price": "0.60", "size": "50"}]}
        )

    app = web.Application()
    app.router.add_get("/book", handler)
    client = await aiohttp_client(app)
    api_module.CLOB_BASE_URL = str(client.make_url("")).rstrip("/")

    provider = PolymarketProvider(client.session)
    ref = InstrumentRef(provider="polymarket", id="111", symbol="Yes", name="Yes", kind="outcome", unit="%")
    quotes = await provider.fetch_snapshot([ref])

    assert quotes["111"].bid == 0.58
    assert quotes["111"].ask == 0.60
    assert quotes["111"].price == pytest.approx(0.59)


async def test_stream_reports_connect_and_reconnect_via_on_status(aiohttp_client, monkeypatch) -> None:
    """ENH-007 regression: PolymarketProvider.stream() must keep reporting
    real connect/reconnect phases through on_status, not regress to a
    permanently-"connecting"/never-connected binary sensor for a provider
    that does stream over a real WS connection."""
    monkeypatch.setattr(polymarket_module, "PolymarketWsManager", _FakeWsManager)

    app = web.Application()
    client = await aiohttp_client(app)
    provider = PolymarketProvider(client.session)
    ref = InstrumentRef(provider="polymarket", id="111", symbol="Yes", name="Yes", kind="outcome", unit="%")

    statuses = []
    task = asyncio.ensure_future(
        provider.stream([ref], _noop_on_quote, _noop_on_trade, _noop_on_event, statuses.append)
    )
    for _ in range(5):
        await asyncio.sleep(0)

    assert [s.phase for s in statuses] == ["connecting"]

    manager = _FakeWsManager.last_instance
    assert manager is not None
    manager.on_connection_state_change(True)
    manager.on_connection_state_change(False)
    manager.on_connection_state_change(True)

    assert [s.phase for s in statuses] == ["connecting", "connected", "reconnecting", "connected"]
    assert statuses[-1].reconnect_count == 1

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


class TestDispatchWsMessage:
    async def test_price_change_dispatches_quote(self) -> None:
        received: list[tuple[str, Quote]] = []

        async def on_quote(token_id: str, quote: Quote) -> None:
            received.append((token_id, quote))

        async def on_trade(token_id: str, trade: Trade) -> None:
            pass

        async def on_event(token_id: str, event: ProviderEvent) -> None:
            pass

        message = {
            "event_type": "price_change",
            "price_changes": [{"asset_id": "111", "best_bid": "0.55", "best_ask": "0.57"}],
        }
        await _dispatch_ws_message(message, on_quote, on_trade, on_event)

        assert received[0][0] == "111"
        assert received[0][1].bid == 0.55
        assert received[0][1].price == pytest.approx(0.56)

    async def test_last_trade_price_dispatches_trade(self) -> None:
        received: list[tuple[str, Trade]] = []

        async def on_quote(token_id: str, quote: Quote) -> None:
            pass

        async def on_trade(token_id: str, trade: Trade) -> None:
            received.append((token_id, trade))

        async def on_event(token_id: str, event: ProviderEvent) -> None:
            pass

        message = {"event_type": "last_trade_price", "asset_id": "111", "price": "0.6", "size": "10", "side": "BUY"}
        await _dispatch_ws_message(message, on_quote, on_trade, on_event)

        assert received[0][0] == "111"
        assert received[0][1].price == 0.6
        assert received[0][1].size == 10.0

    async def test_market_resolved_dispatches_event_per_asset(self) -> None:
        received: list[tuple[str, ProviderEvent]] = []

        async def on_quote(token_id: str, quote: Quote) -> None:
            pass

        async def on_trade(token_id: str, trade: Trade) -> None:
            pass

        async def on_event(token_id: str, event: ProviderEvent) -> None:
            received.append((token_id, event))

        message = {
            "event_type": "market_resolved",
            "assets_ids": ["111", "222"],
            "winning_asset_id": "111",
        }
        await _dispatch_ws_message(message, on_quote, on_trade, on_event)

        assert len(received) == 2
        winning = {token_id: event.data["winning"] for token_id, event in received}
        assert winning == {"111": True, "222": False}
