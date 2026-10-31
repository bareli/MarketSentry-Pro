"""Coordinators: a generic per-entry price-snapshot poll, plus a
Polymarket-specific metadata poll (volume/liquidity/end date/resolution)
that only applies to kind="outcome" instruments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PolymarketApiClient, PolymarketApiError, PolymarketNotFoundError
from .const import SNAPSHOT_POLL_INTERVAL_SEC
from .models import Market
from .providers.base import InstrumentRef, Provider, Quote

_LOGGER = logging.getLogger(__name__)


class ProviderSnapshotCoordinator(DataUpdateCoordinator[dict[str, Quote]]):
    """Polls `Provider.fetch_snapshot` for every instrument tracked by one entry.

    `refs` is mutated in place by __init__.py as subentries are added/removed,
    so the next poll always covers the current set.
    """

    def __init__(self, hass: HomeAssistant, provider: Provider, entry_title: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"marketsentry_snapshot_{entry_title}",
            update_interval=timedelta(seconds=SNAPSHOT_POLL_INTERVAL_SEC),
        )
        self._provider = provider
        self.refs: list[InstrumentRef] = []

    async def _async_update_data(self) -> dict[str, Quote]:
        if not self.refs:
            return {}
        try:
            return await self._provider.fetch_snapshot(list(self.refs))
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Snapshot poll failed: {type(err).__name__}") from err


@dataclass(slots=True)
class MarketMetadata:
    """Snapshot of one Polymarket market's metadata."""

    market: Market


class PolymarketMetadataCoordinator(DataUpdateCoordinator[MarketMetadata]):
    """Polls Gamma metadata for one Polymarket market (shared by every outcome
    subentry tracking that market) every 5 minutes."""

    def __init__(self, hass: HomeAssistant, api: PolymarketApiClient, market_slug: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"marketsentry_polymarket_metadata_{market_slug}",
            update_interval=timedelta(seconds=SNAPSHOT_POLL_INTERVAL_SEC),
        )
        self._api = api
        self._market_slug = market_slug

    async def _async_update_data(self) -> MarketMetadata:
        try:
            market = await self._api.get_market_by_slug(self._market_slug)
        except PolymarketNotFoundError as err:
            raise UpdateFailed(f"Market '{self._market_slug}' not found (404)") from err
        except PolymarketApiError as err:
            raise UpdateFailed(f"Error fetching market '{self._market_slug}': {err}") from err
        return MarketMetadata(market=market)
