"""Tests for api.py: URL/slug parsing and client error normalization."""

from __future__ import annotations

import pytest
from aiohttp import web

from custom_components.marketsentry.api import (
    PolymarketApiClient,
    PolymarketApiError,
    PolymarketNotFoundError,
    parse_polymarket_url_or_slug,
)


@pytest.mark.parametrize(
    ("value", "expected_kind", "expected_slug"),
    [
        ("https://polymarket.com/event/will-x-happen", "event", "will-x-happen"),
        ("https://polymarket.com/market/will-y-happen", "market", "will-y-happen"),
        ("polymarket.com/event/will-x-happen", "event", "will-x-happen"),
        ("polymarket.com/event/will-x-happen?tid=123", "event", "will-x-happen"),
        ("event/will-x-happen", "event", "will-x-happen"),
        ("market/will-y-happen", "market", "will-y-happen"),
        ("will-x-happen", "event", "will-x-happen"),
    ],
)
def test_parse_polymarket_url_or_slug(value: str, expected_kind: str, expected_slug: str) -> None:
    result = parse_polymarket_url_or_slug(value)
    assert result.kind == expected_kind
    assert result.slug == expected_slug


def test_parse_polymarket_url_or_slug_rejects_garbage_url() -> None:
    with pytest.raises(ValueError):
        parse_polymarket_url_or_slug("https://polymarket.com/")


def test_parse_polymarket_url_or_slug_rejects_bad_path_prefix() -> None:
    with pytest.raises(ValueError):
        parse_polymarket_url_or_slug("foo/bar")


async def _client_for(aiohttp_client, path: str, handler) -> PolymarketApiClient:
    app = web.Application()
    app.router.add_get(path, handler)
    client = await aiohttp_client(app)
    import custom_components.marketsentry.api as api_module

    base_url = str(client.make_url("")).rstrip("/")
    api_module.GAMMA_BASE_URL = base_url
    api_module.CLOB_BASE_URL = base_url
    api_module.DATA_API_BASE_URL = base_url
    return PolymarketApiClient(client.session)


async def test_get_event_by_slug(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"id": "1", "slug": "some-event", "markets": []})

    api = await _client_for(aiohttp_client, "/events/slug/some-event", handler)
    event = await api.get_event_by_slug("some-event")
    assert event["slug"] == "some-event"


async def test_search_markets_returns_markets_key_from_dict_response(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.query["q"] == "election"
        assert request.query["limit"] == "5"
        return web.json_response({"markets": [{"slug": "a"}, {"slug": "b"}]})

    api = await _client_for(aiohttp_client, "/public-search", handler)
    results = await api.search_markets("election", limit=5)
    assert [r["slug"] for r in results] == ["a", "b"]


async def test_search_markets_flattens_nested_events_response(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "events": [
                    {"slug": "event-1", "markets": [{"slug": "a"}, {"slug": "b"}]},
                    {"slug": "event-2", "markets": [{"slug": "c"}]},
                ],
                "tags": [],
            }
        )

    api = await _client_for(aiohttp_client, "/public-search", handler)
    results = await api.search_markets("election", limit=5)
    assert [r["slug"] for r in results] == ["a", "b", "c"]


async def test_search_markets_handles_bare_list_response(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response([{"slug": "a"}])

    api = await _client_for(aiohttp_client, "/public-search", handler)
    results = await api.search_markets("election")
    assert results == [{"slug": "a"}]


async def test_get_price_parses_float_response(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.query["side"] == "BUY"
        return web.json_response({"price": 0.42})

    api = await _client_for(aiohttp_client, "/price", handler)
    price = await api.get_price("tok1", "BUY")
    assert price == 0.42


async def test_get_book_returns_raw_dict(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"bids": [], "asks": [], "tick_size": "0.01"})

    api = await _client_for(aiohttp_client, "/book", handler)
    book = await api.get_book("tok1")
    assert book["tick_size"] == "0.01"


async def test_get_price_history_with_fidelity(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.query["market"] == "tok1"
        assert request.query["fidelity"] == "60"
        return web.json_response({"history": [{"t": 1, "p": 0.5}]})

    api = await _client_for(aiohttp_client, "/prices-history", handler)
    history = await api.get_price_history("tok1", interval="1d", fidelity=60)
    assert history == [{"t": 1, "p": 0.5}]


async def test_get_resolution_returns_raw_dict(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.query["condition"] == "0xabc"
        return web.json_response({"status": "resolved"})

    api = await _client_for(aiohttp_client, "/v2/resolutions", handler)
    resolution = await api.get_resolution("0xabc")
    assert resolution["status"] == "resolved"


async def test_get_midpoint_parses_string_price(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.query["token_id"] == "abc"
        return web.json_response({"mid_price": "0.45"})

    app = web.Application()
    app.router.add_get("/midpoint", handler)
    client = await aiohttp_client(app)

    api = PolymarketApiClient(client.session)
    import custom_components.marketsentry.api as api_module

    api_module.CLOB_BASE_URL = str(client.make_url("")).rstrip("/")
    mid = await api.get_midpoint("abc")
    assert mid == 0.45


async def test_get_market_by_slug_raises_not_found_on_404(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=404)

    app = web.Application()
    app.router.add_get("/markets/slug/{slug}", handler)
    client = await aiohttp_client(app)

    api = PolymarketApiClient(client.session)
    with pytest.raises(PolymarketNotFoundError):
        await api._get_json(str(client.make_url("/markets/slug/nope")))


async def test_get_json_wraps_transport_errors(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=500)

    app = web.Application()
    app.router.add_get("/boom", handler)
    client = await aiohttp_client(app)

    api = PolymarketApiClient(client.session)
    with pytest.raises(PolymarketApiError):
        await api._get_json(str(client.make_url("/boom")))
