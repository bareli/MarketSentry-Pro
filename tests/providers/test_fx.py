"""Tests for providers/fx.py: Frankfurter + Bank of Israel source routing."""

from __future__ import annotations

import pytest
from aiohttp import web

import custom_components.marketsentry.providers.fx as fx_module
from custom_components.marketsentry.providers.base import CannotConnect, InstrumentRef
from custom_components.marketsentry.providers.fx import FxProvider


async def _provider_for(aiohttp_client, app: web.Application) -> FxProvider:
    client = await aiohttp_client(app)
    fx_module.FRANKFURTER_BASE_URL = str(client.make_url("/frankfurter")).rstrip("/")
    fx_module.BOI_SDMX_BASE_URL = str(client.make_url("/boi")).rstrip("/")
    return FxProvider(client.session)


async def test_resolve_defaults_to_frankfurter(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.query["base"] == "EUR"
        assert request.query["symbols"] == "ILS"
        return web.json_response({"amount": 1.0, "base": "EUR", "date": "2026-10-30", "rates": {"ILS": 3.91}})

    app = web.Application()
    app.router.add_get("/frankfurter/latest", handler)
    provider = await _provider_for(aiohttp_client, app)

    refs = await provider.resolve("EUR/ILS")

    assert refs[0].id == "frankfurter:EUR:ILS"
    assert refs[0].kind == "fx"
    assert refs[0].unit == "ILS"


async def test_resolve_boi_suffix_selects_official_source(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        # ENH-008 (2026-10-31): confirmed live that the series key alone already
        # scopes to representative rates - no DATA_TYPE filter needed or sent.
        assert "c[DATA_TYPE]" not in request.query
        return web.Response(
            text="TIME_PERIOD,OBS_VALUE\n2026-10-29,3.90\n",
            content_type="text/csv",
        )

    app = web.Application()
    app.router.add_get("/boi/RER_EUR_ILS", handler)
    provider = await _provider_for(aiohttp_client, app)

    refs = await provider.resolve("EUR/ILS/boi")

    assert refs[0].id == "boi:EUR:ILS"
    assert "Bank of Israel" in refs[0].name


async def test_resolve_rejects_malformed_input() -> None:
    provider = FxProvider(session=None)  # type: ignore[arg-type]
    with pytest.raises(CannotConnect):
        await provider.resolve("not-a-pair")


async def test_fetch_snapshot_frankfurter(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"amount": 1.0, "base": "EUR", "date": "2026-10-30", "rates": {"ILS": 3.91}})

    app = web.Application()
    app.router.add_get("/frankfurter/latest", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="fx", id="frankfurter:EUR:ILS", symbol="EUR/ILS", name="EUR/ILS", kind="fx", unit="ILS")
    quotes = await provider.fetch_snapshot([ref])

    assert quotes[ref.id].price == 3.91


async def test_fetch_snapshot_boi_parses_csv(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(
            text="TIME_PERIOD,OBS_VALUE\n2026-10-28,3.88\n2026-10-29,3.90\n",
            content_type="text/csv",
        )

    app = web.Application()
    app.router.add_get("/boi/RER_USD_ILS", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="fx", id="boi:USD:ILS", symbol="USD/ILS", name="USD/ILS", kind="fx", unit="ILS")
    quotes = await provider.fetch_snapshot([ref])

    # Takes the LAST row (most recent observation), not the first.
    assert quotes[ref.id].price == 3.90


async def test_fetch_snapshot_skips_failed_sources(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=500)

    app = web.Application()
    app.router.add_get("/frankfurter/latest", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="fx", id="frankfurter:EUR:ILS", symbol="EUR/ILS", name="EUR/ILS", kind="fx", unit="ILS")
    quotes = await provider.fetch_snapshot([ref])

    assert quotes == {}


async def test_fetch_history_boi_parses_csv_with_date_range(aiohttp_client) -> None:
    """ENH-008 regression: BOI's history fetch used to unconditionally return [] pending a
    confirmed date-range filter syntax. Confirmed live, 2026-10-31: standard SDMX
    startPeriod/endPeriod query params, same series-key endpoint as the latest-rate fetch."""

    async def handler(request: web.Request) -> web.Response:
        assert "startPeriod" in request.query
        assert "endPeriod" in request.query
        assert "c[DATA_TYPE]" not in request.query
        return web.Response(
            text=(
                "TIME_PERIOD,OBS_VALUE\n"
                "2026-10-28,3.88\n"
                "2026-10-29,3.90\n"
            ),
            content_type="text/csv",
        )

    app = web.Application()
    app.router.add_get("/boi/RER_USD_ILS", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="fx", id="boi:USD:ILS", symbol="USD/ILS", name="USD/ILS", kind="fx", unit="ILS")
    points = await provider.fetch_history(ref, hours=48)

    assert len(points) == 2
    assert points[1].price == 3.90


async def test_fetch_history_boi_raises_cannot_connect_on_request_failure(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=500)

    app = web.Application()
    app.router.add_get("/boi/RER_USD_ILS", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="fx", id="boi:USD:ILS", symbol="USD/ILS", name="USD/ILS", kind="fx", unit="ILS")
    with pytest.raises(CannotConnect):
        await provider.fetch_history(ref, hours=24)


async def test_fetch_history_frankfurter_parses_time_series(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "base": "EUR",
                "rates": {
                    "2026-10-28": {"ILS": 3.88},
                    "2026-10-29": {"ILS": 3.90},
                },
            }
        )

    app = web.Application()
    app.router.add_get("/frankfurter/{date_range}", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="fx", id="frankfurter:EUR:ILS", symbol="EUR/ILS", name="EUR/ILS", kind="fx", unit="ILS")
    points = await provider.fetch_history(ref, hours=48)

    assert len(points) == 2
    assert points[1].price == 3.90


async def test_search_delegates_to_resolve(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"amount": 1.0, "base": "EUR", "date": "2026-10-30", "rates": {"ILS": 3.91}})

    app = web.Application()
    app.router.add_get("/frankfurter/latest", handler)
    provider = await _provider_for(aiohttp_client, app)

    refs = await provider.search("EUR/ILS", limit=10)
    assert refs[0].id == "frankfurter:EUR:ILS"


async def test_search_returns_empty_on_cannot_connect(aiohttp_client) -> None:
    app = web.Application()
    provider = await _provider_for(aiohttp_client, app)

    assert await provider.search("not-a-pair", limit=10) == []


async def test_frankfurter_quote_raises_when_rate_missing(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"amount": 1.0, "base": "EUR", "date": "2026-10-30", "rates": {}})

    app = web.Application()
    app.router.add_get("/frankfurter/latest", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="fx", id="frankfurter:EUR:ILS", symbol="EUR/ILS", name="EUR/ILS", kind="fx", unit="ILS")
    quotes = await provider.fetch_snapshot([ref])
    assert quotes == {}


async def test_boi_quote_raises_when_obs_value_missing(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(text="TIME_PERIOD\n2026-10-29\n", content_type="text/csv")

    app = web.Application()
    app.router.add_get("/boi/RER_USD_ILS", handler)
    provider = await _provider_for(aiohttp_client, app)

    ref = InstrumentRef(provider="fx", id="boi:USD:ILS", symbol="USD/ILS", name="USD/ILS", kind="fx", unit="ILS")
    quotes = await provider.fetch_snapshot([ref])
    assert quotes == {}


async def test_boi_fetch_latest_raises_when_no_rows(aiohttp_client) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(text="TIME_PERIOD,OBS_VALUE\n", content_type="text/csv")

    app = web.Application()
    app.router.add_get("/boi/RER_USD_ILS", handler)
    provider = await _provider_for(aiohttp_client, app)

    with pytest.raises(CannotConnect):
        await provider.resolve("USD/ILS/boi")
