"""Tests for providers/polymarket.py: Provider-interface adapter over the
existing Gamma/CLOB client, and the WS message -> on_quote/on_trade/on_event
dispatch table.
"""

from __future__ import annotations

import pytest
from aiohttp import web

import custom_components.marketsentry.api as api_module
from custom_components.marketsentry.models import Market
from custom_components.marketsentry.providers.base import InstrumentRef, ProviderEvent, Quote, Trade
from custom_components.marketsentry.providers.polymarket import (
    PolymarketProvider,
    _dispatch_ws_message,
    _market_to_refs,
)
from tests.conftest import GAMMA_MARKET_FIXTURE


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
