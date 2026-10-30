"""Base entity for Polymarket Watch: one HA device per tracked market."""

from __future__ import annotations

import time

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, STATE_WRITE_MIN_DELTA_PP, STATE_WRITE_MIN_INTERVAL_SEC
from .coordinator import PolymarketMetadataCoordinator


def market_device_info(market_slug: str, question: str) -> DeviceInfo:
    """Build the HA device representing one tracked market."""
    return DeviceInfo(
        identifiers={(DOMAIN, market_slug)},
        name=question,
        manufacturer=MANUFACTURER,
        model="Prediction market",
        configuration_url=f"https://polymarket.com/market/{market_slug}",
    )


class PolymarketEntity(CoordinatorEntity[PolymarketMetadataCoordinator]):
    """Common base: device grouping + recorder-friendly state throttling."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PolymarketMetadataCoordinator, market_slug: str, question: str) -> None:
        super().__init__(coordinator)
        self._market_slug = market_slug
        self._attr_device_info = market_device_info(market_slug, question)
        self._last_write_time: float = 0.0
        self._last_written_value: float | None = None

    def _should_write_throttled(self, new_value: float | None) -> bool:
        """Throttle writes to protect the recorder: max once per 5s, min 0.1pp delta."""
        now = time.monotonic()
        if self._last_written_value is None or new_value is None:
            self._last_write_time = now
            self._last_written_value = new_value
            return True

        elapsed = now - self._last_write_time
        delta = abs(new_value - self._last_written_value)

        if elapsed < STATE_WRITE_MIN_INTERVAL_SEC and delta < STATE_WRITE_MIN_DELTA_PP:
            return False

        self._last_write_time = now
        self._last_written_value = new_value
        return True
