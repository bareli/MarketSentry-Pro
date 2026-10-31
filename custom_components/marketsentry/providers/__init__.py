"""Provider registry: maps a provider key to its Provider subclass, and
builds an instance from a config entry's data (credentials, if any).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .alpaca import AlpacaProvider
from .base import Provider
from .finnhub import FinnhubProvider
from .fx import FxProvider
from .polymarket import PolymarketProvider

if TYPE_CHECKING:
    from aiohttp import ClientSession

PROVIDERS: dict[str, type[Provider]] = {
    "polymarket": PolymarketProvider,
    "finnhub": FinnhubProvider,
    "alpaca": AlpacaProvider,
    "fx": FxProvider,
}


def build_provider(session: ClientSession, provider_key: str, data: dict[str, Any]) -> Provider:
    """Build a Provider instance for `provider_key` from a config entry's data."""
    if provider_key == "finnhub":
        return FinnhubProvider(session, api_key=data["api_key"])
    if provider_key == "alpaca":
        return AlpacaProvider(
            session,
            key_id=data["key_id"],
            secret_key=data["secret_key"],
            feed=data.get("feed", "iex"),
        )
    if provider_key == "fx":
        return FxProvider(session)
    return PolymarketProvider(session)


__all__ = ["PROVIDERS", "Provider", "build_provider"]
