"""Crypto provider: CoinGecko's free, no-key public API.

NOT confirmed live this session (no research-fetch tooling available for
this provider either, matching the existing caveat on fx.py/finnhub.py's
unverified facts below). Built against CoinGecko's long-documented public
v3 contract; verify before relying on it in production:

- Base URL `https://api.coingecko.com/api/v3`.
- `GET /search?query=<text>` -> `{"coins": [{"id": "bitcoin", "symbol":
  "btc", "name": "Bitcoin", ...}, ...]}` for free-text search.
- `GET /coins/{id}?localization=false&tickers=false&market_data=false&
  community_data=false&developer_data=false&sparkline=false` -> `{"id":
  "bitcoin", "symbol": "btc", "name": "Bitcoin", ...}` to resolve an
  exact CoinGecko coin id pasted directly.
- `GET /simple/price?ids=bitcoin,ethereum&vs_currencies=usd&
  include_24hr_change=true&include_24hr_vol=true&include_market_cap=true&
  include_last_updated_at=true` -> `{"bitcoin": {"usd": 67000.5,
  "usd_24h_change": 1.23, "usd_24h_vol": 3.2e10, "usd_market_cap": 1.3e12,
  "last_updated_at": 1730000000}, ...}` for batched snapshots (all
  tracked coins in one call, to stay inside CoinGecko's free-tier rate
  limit).
- `GET /coins/{id}/market_chart?vs_currency=usd&days=<n>` -> `{"prices":
  [[ms_timestamp, price], ...], ...}` for history.

Instrument id convention: the CoinGecko coin id itself (e.g. "bitcoin"),
always priced in USD. No API key, no streaming (CoinGecko's free tier has
no WebSocket feed) - REST poll only, same shape as the FX provider.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from aiohttp import ClientSession, ClientTimeout

from .base import CannotConnect, InstrumentRef, PricePoint, Provider, Quote

_LOGGER = logging.getLogger(__name__)

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

_REQUEST_TIMEOUT = ClientTimeout(total=15)

_COIN_LOOKUP_PARAMS = {
    "localization": "false",
    "tickers": "false",
    "market_data": "false",
    "community_data": "false",
    "developer_data": "false",
    "sparkline": "false",
}


def _ref_from_coin(coin: dict[str, Any]) -> InstrumentRef:
    coin_id = coin["id"]
    symbol = str(coin["symbol"]).upper()
    return InstrumentRef(
        provider="coingecko",
        id=coin_id,
        symbol=symbol,
        name=f"{coin['name']} ({symbol})",
        kind="crypto",
        unit="USD",
        url=f"https://www.coingecko.com/en/coins/{coin_id}",
    )


class CryptoProvider(Provider):
    """Cryptocurrencies via CoinGecko's free public API."""

    key = "coingecko"
    name = "CoinGecko (crypto)"
    requires_api_key = False
    supports_streaming = False

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def validate(self, credentials: dict[str, Any]) -> None:
        return  # no API key

    async def search(self, query: str, limit: int) -> list[InstrumentRef]:
        data = await self._get("/search", {"query": query})
        coins = data.get("coins", []) if isinstance(data, dict) else []
        return [_ref_from_coin(coin) for coin in coins[:limit]]

    async def resolve(self, user_input: str) -> list[InstrumentRef]:
        coin_id = user_input.strip().lower().replace(" ", "-")
        data = await self._get(f"/coins/{coin_id}", _COIN_LOOKUP_PARAMS)
        if not isinstance(data, dict) or "id" not in data:
            raise CannotConnect(f"No CoinGecko coin for id: {user_input}")
        return [_ref_from_coin(data)]

    async def fetch_snapshot(self, refs: list[InstrumentRef]) -> dict[str, Quote]:
        if not refs:
            return {}
        ids = ",".join(ref.id for ref in refs)
        try:
            data = await self._get(
                "/simple/price",
                {
                    "ids": ids,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_last_updated_at": "true",
                },
            )
        except CannotConnect as err:
            _LOGGER.debug("CoinGecko snapshot failed for %s: %s", ids, err)
            return {}

        quotes: dict[str, Quote] = {}
        if not isinstance(data, dict):
            return quotes
        for ref in refs:
            coin_data = data.get(ref.id)
            if not isinstance(coin_data, dict) or coin_data.get("usd") is None:
                continue
            last_updated_at = coin_data.get("last_updated_at")
            ts = datetime.fromtimestamp(last_updated_at, UTC) if last_updated_at else datetime.now(UTC)
            quotes[ref.id] = Quote(price=float(coin_data["usd"]), ts=ts)
        return quotes

    async def fetch_history(self, ref: InstrumentRef, hours: int) -> list[PricePoint]:
        days = max(1, -(-hours // 24))  # ceil(hours / 24)
        data = await self._get(f"/coins/{ref.id}/market_chart", {"vs_currency": "usd", "days": str(days)})
        prices = data.get("prices", []) if isinstance(data, dict) else []
        points: list[PricePoint] = []
        for entry in prices:
            if not isinstance(entry, list) or len(entry) != 2:
                continue
            ms, price = entry
            points.append(PricePoint(ts=datetime.fromtimestamp(ms / 1000, UTC), price=float(price)))
        return points

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{COINGECKO_BASE_URL}{path}"
        try:
            async with self._session.get(url, params=params, timeout=_REQUEST_TIMEOUT) as resp:
                if resp.status == 404:
                    raise CannotConnect(f"CoinGecko {path} returned 404")
                resp.raise_for_status()
                return await resp.json()
        except CannotConnect:
            raise
        except Exception as err:  # noqa: BLE001
            raise CannotConnect(f"CoinGecko request to {path} failed: {err}") from err
