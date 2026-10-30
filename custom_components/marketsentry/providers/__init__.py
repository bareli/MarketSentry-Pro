"""Provider registry: maps a provider key to its Provider subclass.

Instances are created on demand (they need an aiohttp session / credentials),
this module only maps keys to classes.
"""

from __future__ import annotations

from .alpaca import AlpacaProvider
from .base import Provider
from .finnhub import FinnhubProvider
from .fx import FxProvider
from .polymarket import PolymarketProvider

PROVIDERS: dict[str, type[Provider]] = {
    "polymarket": PolymarketProvider,
    "finnhub": FinnhubProvider,
    "alpaca": AlpacaProvider,
    "fx": FxProvider,
}

__all__ = ["PROVIDERS", "Provider"]
