"""Tests for api.py: URL/slug parsing and client error normalization."""

from __future__ import annotations

import pytest
from aiohttp import web

from custom_components.polymarket_watch.api import (
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


async def test_get_midpoint_parses_string_price(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.query["token_id"] == "abc"
        return web.json_response({"mid_price": "0.45"})

    app = web.Application()
    app.router.add_get("/midpoint", handler)
    client = await aiohttp_client(app)

    api = PolymarketApiClient(client.session)
    import custom_components.polymarket_watch.api as api_module

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
