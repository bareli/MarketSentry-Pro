"""Services for Polymarket Watch: get_price_history, refresh, search_markets."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PolymarketApiClient, PolymarketApiError
from .const import (
    ATTR_FIDELITY,
    ATTR_INTERVAL,
    ATTR_LIMIT,
    ATTR_OUTCOME,
    ATTR_QUERY,
    DOMAIN,
    SERVICE_GET_PRICE_HISTORY,
    SERVICE_REFRESH,
    SERVICE_SEARCH_MARKETS,
)

if TYPE_CHECKING:
    from . import PolymarketWatchConfigEntry

GET_PRICE_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required(ATTR_OUTCOME): cv.string,
        vol.Optional(ATTR_INTERVAL, default="1d"): vol.In(
            ["1h", "6h", "1d", "1w", "1m", "all", "max"]
        ),
        vol.Optional(ATTR_FIDELITY): vol.Coerce(int),
    }
)

REFRESH_SCHEMA = vol.Schema({vol.Required("device_id"): cv.string})

SEARCH_MARKETS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_QUERY): cv.string,
        vol.Optional(ATTR_LIMIT, default=10): vol.Coerce(int),
    }
)


def _find_entry_for_device(hass: HomeAssistant, device_id: str) -> PolymarketWatchConfigEntry:
    device_registry = dr.async_get(hass)
    device = device_registry.devices.get(device_id)
    if device is None:
        raise ValueError(f"Unknown device_id: {device_id}")
    for config_entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(config_entry_id)
        if entry is not None and entry.domain == DOMAIN:
            return entry
    raise ValueError(f"No Polymarket Watch config entry found for device_id: {device_id}")


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register domain services. Safe to call multiple times (no-op after first)."""
    if hass.services.has_service(DOMAIN, SERVICE_GET_PRICE_HISTORY):
        return

    async def handle_get_price_history(call: ServiceCall) -> ServiceResponse:
        entry = _find_entry_for_device(hass, call.data["device_id"])
        tracker = entry.runtime_data.tracker
        outcome_name = call.data[ATTR_OUTCOME]
        token_id = next(
            (o.token_id for o in tracker.outcomes.values() if o.outcome_name == outcome_name),
            None,
        )
        if token_id is None:
            raise ValueError(f"Unknown outcome '{outcome_name}' for this device")

        session = async_get_clientsession(hass)
        api = PolymarketApiClient(session)
        try:
            history = await api.get_price_history(
                token_id,
                interval=call.data.get(ATTR_INTERVAL, "1d"),
                fidelity=call.data.get(ATTR_FIDELITY),
            )
        except PolymarketApiError as err:
            raise ValueError(str(err)) from err
        return cast(ServiceResponse, {"history": history})

    async def handle_refresh(call: ServiceCall) -> ServiceResponse:
        entry = _find_entry_for_device(hass, call.data["device_id"])
        await entry.runtime_data.tracker.coordinator.async_request_refresh()
        return None

    async def handle_search_markets(call: ServiceCall) -> ServiceResponse:
        session = async_get_clientsession(hass)
        api = PolymarketApiClient(session)
        try:
            results = await api.search_markets(call.data[ATTR_QUERY], call.data.get(ATTR_LIMIT, 10))
        except PolymarketApiError as err:
            raise ValueError(str(err)) from err
        return cast(ServiceResponse, {"markets": results})

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
        SERVICE_SEARCH_MARKETS,
        handle_search_markets,
        schema=SEARCH_MARKETS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
