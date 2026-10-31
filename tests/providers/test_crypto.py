"""Tests for providers/crypto.py: CoinGecko's free public API."""

from __future__ import annotations

import pytest
from aiohttp import web

import custom_components.marketsentry.providers.crypto as crypto_module
from custom_components.marketsentry.providers.base import CannotConnect, InstrumentRef
from custom_components.marketsentry.providers.crypto import CryptoProvider


async def _provider_for(aiohttp_client, app: web.Application) -> CryptoProvider:
    client = await aiohttp_client(app)
    crypto_module.COINGECKO_BASE_URL = str(client.make_url("/cg")).rstrip("/")
    return CryptoProvider(client.session)


async def test_resolve_exact_coin_id(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"})

    app = web.Application()
    app.router.add_get("/cg/coins/bitcoin", handler)
    provider = await _provider_for(aiohttp_client, app)

    refs = await provider.resolve("bitcoin")

    assert refs[0].id == "bitcoin"
    assert refs[0].symbol == "BTC"
    assert refs[0].kind == "crypto"
    assert refs[0].unit == "USD"
    assert refs[0].name == "Bitcoin (BTC)"
    assert refs[0].url == "https://www.coingecko.com/en/coins/bitcoin"


async def test_resolve_normalizes_input(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"id": "usd-coin", "symbol": "usdc", "name": "USD Coin"})

    app = web.Application()
    app.router.add_get("/cg/coins/usd-coin", handler)
    provider = await _provider_for(aiohttp_client, app)

    refs = await provider.resolve("USD Coin")  # spaces -> hyphens, lowercased

    assert refs[0].id == "usd-coin"


async def test_resolve_raises_on_unknown_id(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=404)

    app = web.Application()
    app.router.add_get("/cg/coins/not-a-real-coin", handler)
    provider = await _provider_for(aiohttp_client, app)

    with pytest.raises(CannotConnect):
        await provider.resolve("not-a-real-coin")


async def test_search_returns_matches_up_to_limit(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.query["query"] == "bit"
        return web.json_response(
            {
                "coins": [
                    {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
                    {"id": "bitcoin-cash", "symbol": "bch", "name": "Bitcoin Cash"},
                    {"id": "bitconnect", "symbol": "bcc", "name": "Bitconnect"},
                ]
            }
        )

    app = web.Application()
    app.router.add_get("/cg/search", handler)
    provider = await _provider_for(aiohttp_client, app)

    refs = await provider.search("bit", limit=2)

    assert len(refs) == 2
    assert refs[0].id == "bitcoin"
    assert refs[1].id == "bitcoin-cash"


async def test_search_returns_empty_when_no_coins_key(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({})

    app = web.Application()
    app.router.add_get("/cg/search", handler)
    provider = await _provider_for(aiohttp_client, app)

    assert await provider.search("xyz", limit=10) == []


async def test_fetch_snapshot_batches_all_refs_in_one_call(aiohttp_client) -> None:
    seen_ids = {}

    async def handler(request: web.Request) -> web.Response:
        seen_ids["ids"] = request.query["ids"]
        return web.json_response(
            {
                "bitcoin": {"usd": 67000.5, "last_updated_at": 1730000000},
                "ethereum": {"usd": 3500.25, "last_updated_at": 1730000001},
            }
        )

    app = web.Application()
    app.router.add_get("/cg/simple/price", handler)
    provider = await _provider_for(aiohttp_client, app)

    refs = [
        InstrumentRef(provider="coingecko", id="bitcoin", symbol="BTC", name="Bitcoin (BTC)", kind="crypto", unit="USD"),
        InstrumentRef(provider="coingecko", id="ethereum", symbol="ETH", name="Ethereum (ETH)", kind="crypto", unit="USD"),
    ]
    quotes = await provider.fetch_snapshot(refs)

    assert seen_ids["ids"] == "bitcoin,ethereum"
    assert quotes["bitcoin"].price == 67000.5
    assert quotes["ethereum"].price == 3500.25


async def test_fetch_snapshot_skips_refs_missing_from_response(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"bitcoin": {"usd": 67000.5}})

    app = web.Application()
    app.router.add_get("/cg/simple/price", handler)
    provider = await _provider_for(aiohttp_client, app)

    refs = [
        InstrumentRef(provider="coingecko", id="bitcoin", symbol="BTC", name="Bitcoin (BTC)", kind="crypto", unit="USD"),
        InstrumentRef(provider="coingecko", id="dogecoin", symbol="DOGE", name="Dogecoin (DOGE)", kind="crypto", unit="USD"),
    ]
    quotes = await provider.fetch_snapshot(refs)

    assert "bitcoin" in quotes
    assert "dogecoin" not in quotes


async def test_fetch_snapshot_returns_empty_dict_on_request_failure(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=500)

    app = web.Application()
    app.router.add_get("/cg/simple/price", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="coingecko", id="bitcoin", symbol="BTC", name="Bitcoin (BTC)", kind="crypto", unit="USD")
    quotes = await provider.fetch_snapshot([ref])

    assert quotes == {}


async def test_fetch_snapshot_with_no_refs_skips_the_request(aiohttp_client) -> None:
    app = web.Application()
    provider = await _provider_for(aiohttp_client, app)

    assert await provider.fetch_snapshot([]) == {}


async def test_fetch_history_parses_price_series(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.query["days"] == "2"
        return web.json_response({"prices": [[1730000000000, 66000.0], [1730003600000, 67000.5]]})

    app = web.Application()
    app.router.add_get("/cg/coins/bitcoin/market_chart", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="coingecko", id="bitcoin", symbol="BTC", name="Bitcoin (BTC)", kind="crypto", unit="USD")
    points = await provider.fetch_history(ref, hours=36)  # ceil(36/24) = 2 days

    assert len(points) == 2
    assert points[0].price == 66000.0
    assert points[1].price == 67000.5


async def test_fetch_history_returns_empty_on_malformed_response(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"prices": "not-a-list"})

    app = web.Application()
    app.router.add_get("/cg/coins/bitcoin/market_chart", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="coingecko", id="bitcoin", symbol="BTC", name="Bitcoin (BTC)", kind="crypto", unit="USD")
    points = await provider.fetch_history(ref, hours=24)

    assert points == []


async def test_validate_is_a_no_op() -> None:
    provider = CryptoProvider(session=None)  # type: ignore[arg-type]
    await provider.validate({})  # must not raise
