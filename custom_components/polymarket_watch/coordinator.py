"""DataUpdateCoordinator for Gamma metadata, with REST fallback pricing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PolymarketApiClient, PolymarketApiError, PolymarketNotFoundError
from .const import METADATA_UPDATE_INTERVAL_SEC
from .models import Market

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class MarketData:
    """Snapshot of one tracked market, refreshed each coordinator cycle."""

    market: Market


class PolymarketMetadataCoordinator(DataUpdateCoordinator[MarketData]):
    """Polls Gamma metadata for a single tracked market every 5 minutes."""

    def __init__(self, hass: HomeAssistant, api: PolymarketApiClient, market_slug: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"polymarket_watch_metadata_{market_slug}",
            update_interval=timedelta(seconds=METADATA_UPDATE_INTERVAL_SEC),
        )
        self._api = api
        self._market_slug = market_slug

    async def _async_update_data(self) -> MarketData:
        try:
            market = await self._api.get_market_by_slug(self._market_slug)
        except PolymarketNotFoundError as err:
            raise UpdateFailed(f"Market '{self._market_slug}' not found (404)") from err
        except PolymarketApiError as err:
            raise UpdateFailed(f"Error fetching market '{self._market_slug}': {err}") from err
        return MarketData(market=market)
