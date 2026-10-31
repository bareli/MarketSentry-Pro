"""Base entity for MarketSentry Pro: one HA device per tracked instrument
(subentry), plus a per-entry diagnostics device for provider connection health.
"""

from __future__ import annotations

import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PROVIDER,
    DOMAIN,
    PROVIDER_MANUFACTURER,
    STATE_WRITE_MIN_DELTA,
    STATE_WRITE_MIN_INTERVAL_SEC,
)
from .coordinator import ProviderSnapshotCoordinator
from .providers.base import InstrumentRef

_MODEL_BY_KIND = {
    "outcome": "Prediction market outcome",
    "stock": "Stock",
    "fx": "Exchange rate",
}


def card_attributes(ref: InstrumentRef) -> dict[str, str | None]:
    """kind/provider/url on each kind's primary sensor, for marketsentry-card
    to group, filter, and link out without a custom WS round trip."""
    return {"kind": ref.kind, "provider": ref.provider, "url": ref.url}


def instrument_device_info(entry_id: str, ref: InstrumentRef) -> DeviceInfo:
    """Build the HA device representing one tracked instrument (subentry)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}:{ref.id}")},
        name=ref.name,
        manufacturer=PROVIDER_MANUFACTURER.get(ref.provider, ref.provider),
        model=_MODEL_BY_KIND.get(ref.kind, ref.kind),
        configuration_url=ref.url,
    )


def provider_connection_device_info(entry: ConfigEntry, provider_name: str) -> DeviceInfo:
    """Entry-level device for connection diagnostics, not tied to an instrument."""
    provider_key = entry.data.get(CONF_PROVIDER, "")
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}:_connection")},
        name=f"{provider_name} connection",
        manufacturer=PROVIDER_MANUFACTURER.get(provider_key, provider_key),
        model="Provider connection",
        entry_type=DeviceEntryType.SERVICE,
    )


class InstrumentEntity(CoordinatorEntity[ProviderSnapshotCoordinator]):
    """Common base: device grouping + recorder-friendly state throttling."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ProviderSnapshotCoordinator, entry_id: str, ref: InstrumentRef) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._ref = ref
        self._attr_device_info = instrument_device_info(entry_id, ref)
        self._last_write_time: float = 0.0
        self._last_written_value: float | None = None

    def _should_write_throttled(self, new_value: float | None) -> bool:
        """Throttle writes to protect the recorder: max once per 5s, min delta."""
        now = time.monotonic()
        if self._last_written_value is None or new_value is None:
            self._last_write_time = now
            self._last_written_value = new_value
            return True

        elapsed = now - self._last_write_time
        delta = abs(new_value - self._last_written_value)

        if elapsed < STATE_WRITE_MIN_INTERVAL_SEC and delta < STATE_WRITE_MIN_DELTA:
            return False

        self._last_write_time = now
        self._last_written_value = new_value
        return True
