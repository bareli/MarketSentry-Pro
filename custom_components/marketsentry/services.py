"""Services for MarketSentry Pro: get_price_history, refresh, search_instruments."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    ATTR_HOURS,
    ATTR_LIMIT,
    ATTR_QUERY,
    CONF_PROVIDER,
    DOMAIN,
    PROVIDER_KEYS,
    SERVICE_GET_PRICE_HISTORY,
    SERVICE_REFRESH,
    SERVICE_SEARCH_INSTRUMENTS,
)
from .providers import PROVIDERS, build_provider
from .providers.base import CannotConnect, InvalidAuth

if TYPE_CHECKING:
    from . import InstrumentTracker, MarketSentryConfigEntry

GET_PRICE_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Optional(ATTR_HOURS, default=24): vol.Coerce(int),
    }
)

REFRESH_SCHEMA = vol.Schema({vol.Required("device_id"): cv.string})

SEARCH_INSTRUMENTS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PROVIDER): vol.In(PROVIDER_KEYS),
        vol.Required(ATTR_QUERY): cv.string,
        vol.Optional(ATTR_LIMIT, default=10): vol.Coerce(int),
    }
)


def _find_tracker_for_device(
    hass: HomeAssistant, device_id: str
) -> tuple[MarketSentryConfigEntry, InstrumentTracker]:
    device_registry = dr.async_get(hass)
    device = device_registry.devices.get(device_id)
    if device is None:
        raise ValueError(f"Unknown device_id: {device_id}")

    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            continue
        for subentry_id in device.config_entries_subentries.get(entry_id, set()):
            if subentry_id and subentry_id in entry.runtime_data.trackers:
                return entry, entry.runtime_data.trackers[subentry_id]

    raise ValueError(f"No tracked instrument found for device_id: {device_id}")


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register domain services. Safe to call multiple times (no-op after first)."""
    if hass.services.has_service(DOMAIN, SERVICE_GET_PRICE_HISTORY):
        return

    async def handle_get_price_history(call: ServiceCall) -> ServiceResponse:
        entry, tracker = _find_tracker_for_device(hass, call.data["device_id"])
        try:
            points = await entry.runtime_data.provider.fetch_history(
                tracker.ref, hours=call.data.get(ATTR_HOURS, 24)
            )
        except CannotConnect as err:
            raise ValueError(str(err)) from err
        history = [{"t": point.ts.isoformat(), "p": point.price} for point in points]
        return cast(ServiceResponse, {"history": history})

    async def handle_refresh(call: ServiceCall) -> ServiceResponse:
        entry, _tracker = _find_tracker_for_device(hass, call.data["device_id"])
        await entry.runtime_data.snapshot_coordinator.async_request_refresh()
        return None

    async def handle_search_instruments(call: ServiceCall) -> ServiceResponse:
        provider_key = call.data[CONF_PROVIDER]
        session = async_get_clientsession(hass)

        credentials: dict[str, object] = {}
        if PROVIDERS[provider_key].requires_api_key:
            entry = next(
                (
                    e
                    for e in hass.config_entries.async_entries(DOMAIN)
                    if e.data.get(CONF_PROVIDER) == provider_key
                ),
                None,
            )
            if entry is None:
                raise ValueError(f"No configured {provider_key} account found")
            credentials = dict(entry.data)

        provider = build_provider(session, provider_key, credentials)
        try:
            refs = await provider.search(call.data[ATTR_QUERY], call.data.get(ATTR_LIMIT, 10))
        except (CannotConnect, InvalidAuth) as err:
            raise ValueError(str(err)) from err

        instruments = [
            {
                "id": ref.id,
                "symbol": ref.symbol,
                "name": ref.name,
                "kind": ref.kind,
                "unit": ref.unit,
                "url": ref.url,
            }
            for ref in refs
        ]
        return cast(ServiceResponse, {"instruments": instruments})

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PRICE_HISTORY,
        handle_get_price_history,
        schema=GET_PRICE_HISTORY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        handle_refresh,
        schema=REFRESH_SCHEMA,
        supports_response=SupportsResponse.NONE,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH_INSTRUMENTS,
        handle_search_instruments,
        schema=SEARCH_INSTRUMENTS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
