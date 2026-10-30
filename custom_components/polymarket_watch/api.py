"""Typed async REST client for Polymarket Gamma + CLOB public endpoints.

No HA imports. Caller supplies an aiohttp ClientSession (e.g. from
homeassistant.helpers.aiohttp_client.async_get_clientsession).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import urlparse

from aiohttp import ClientSession, ClientTimeout

from .const import CLOB_BASE_URL, DATA_API_BASE_URL, GAMMA_BASE_URL
from .models import Market

_LOGGER = logging.getLogger(__name__)

_REQUEST_TIMEOUT = ClientTimeout(total=15)


class PolymarketApiError(Exception):
    """Raised when a Polymarket API call fails."""


class PolymarketNotFoundError(PolymarketApiError):
    """Raised when a market/event slug does not exist (HTTP 404)."""


@dataclass(slots=True)
class ParsedPolymarketUrl:
    """Result of parsing a user-supplied Polymarket URL or bare slug."""

    kind: str  # "event" or "market"
    slug: str


def parse_polymarket_url_or_slug(value: str) -> ParsedPolymarketUrl:
    """Parse `polymarket.com/event/<slug>`, `/market/<slug>`, or a bare slug.

    A bare slug (no scheme, no slashes) is assumed to be an event slug, since
    that is the more common share pattern.
    """
    value = value.strip()
    if "://" in value or value.startswith("polymarket.com"):
        url = value if "://" in value else f"https://{value}"
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] in ("event", "market"):
            return ParsedPolymarketUrl(kind=parts[0], slug=parts[1])
        raise ValueError(f"Could not parse a Polymarket event/market slug from: {value}")

    if "/" in value:
        parts = [p for p in value.split("/") if p]
        if len(parts) >= 2 and parts[0] in ("event", "market"):
            return ParsedPolymarketUrl(kind=parts[0], slug=parts[1])
        raise ValueError(f"Could not parse a Polymarket event/market slug from: {value}")

    return ParsedPolymarketUrl(kind="event", slug=value)


class PolymarketApiClient:
    """Thin async wrapper around Gamma, CLOB, and data-api public endpoints."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def _get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        try:
            async with self._session.get(url, params=params, timeout=_REQUEST_TIMEOUT) as resp:
                if resp.status == 404:
                    raise PolymarketNotFoundError(f"Not found: {url}")
                resp.raise_for_status()
                return await resp.json()
        except PolymarketNotFoundError:
            raise
        except Exception as err:  # noqa: BLE001 - normalize all transport errors
            raise PolymarketApiError(f"Request to {url} failed: {err}") from err

    # --- Gamma API ---

    async def get_event_by_slug(self, slug: str) -> dict[str, Any]:
        return cast(dict[str, Any], await self._get_json(f"{GAMMA_BASE_URL}/events/slug/{slug}"))

    async def get_market_by_slug(self, slug: str) -> Market:
        data = await self._get_json(f"{GAMMA_BASE_URL}/markets/slug/{slug}")
        return Market.from_gamma(data)

    async def search_markets(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        data = await self._get_json(
            f"{GAMMA_BASE_URL}/public-search",
            params={"q": query, "limit": limit},
        )
        if isinstance(data, dict):
            return list(data.get("markets", []))
        return list(data) if isinstance(data, list) else []

    # --- CLOB REST ---

    async def get_midpoint(self, token_id: str) -> float | None:
        data = await self._get_json(f"{CLOB_BASE_URL}/midpoint", params={"token_id": token_id})
        raw = data.get("mid_price") if isinstance(data, dict) else None
        return float(raw) if raw is not None else None

    async def get_price(self, token_id: str, side: str) -> float | None:
        data = await self._get_json(
            f"{CLOB_BASE_URL}/price", params={"token_id": token_id, "side": side}
        )
        raw = data.get("price") if isinstance(data, dict) else None
        return float(raw) if raw is not None else None

    async def get_book(self, token_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._get_json(f"{CLOB_BASE_URL}/book", params={"token_id": token_id}),
        )

    async def get_price_history(
        self, token_id: str, interval: str = "1d", fidelity: int | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"market": token_id, "interval": interval}
        if fidelity is not None:
            params["fidelity"] = fidelity
        data = await self._get_json(f"{CLOB_BASE_URL}/prices-history", params=params)
        return list(data.get("history", [])) if isinstance(data, dict) else []

    # --- Resolution (data-api) ---

    async def get_resolution(self, condition_id: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._get_json(
                f"{DATA_API_BASE_URL}/v2/resolutions", params={"condition": condition_id}
            ),
        )
