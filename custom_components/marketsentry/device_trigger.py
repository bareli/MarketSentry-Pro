"""Device triggers for MarketSentry Pro: one per detection event type that
applies to the device's instrument kind.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_EVENT_DATA,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import BUS_EVENT_PREFIX, DOMAIN, EVENT_TYPES_BY_KIND

if TYPE_CHECKING:
    from . import MarketSentryConfigEntry

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): vol.In(sorted({e for types in EVENT_TYPES_BY_KIND.values() for e in types}))}
)


def _tracker_kind_for_device(hass: HomeAssistant, device_id: str) -> str | None:
    device_registry = dr.async_get(hass)
    device = device_registry.devices.get(device_id)
    if device is None:
        return None

    for entry_id in device.config_entries:
        raw_entry = hass.config_entries.async_get_entry(entry_id)
        if raw_entry is None or raw_entry.domain != DOMAIN:
            continue
        entry = cast("MarketSentryConfigEntry", raw_entry)
        for subentry_id in device.config_entries_subentries.get(entry_id, set()):
            tracker = entry.runtime_data.trackers.get(subentry_id) if subentry_id else None
            if tracker is not None:
                return str(tracker.ref.kind)
    return None


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict[str, Any]]:
    kind = _tracker_kind_for_device(hass, device_id)
    if kind is None:
        return []
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: event_type,
        }
        for event_type in EVENT_TYPES_BY_KIND[kind]
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    device_registry = dr.async_get(hass)
    device = device_registry.devices.get(config[CONF_DEVICE_ID])
    entry_id = next(iter(device.config_entries), None) if device else None

    event_data: dict[str, Any] = {"entry_id": entry_id} if entry_id else {}

    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: f"{BUS_EVENT_PREFIX}{config[CONF_TYPE]}",
            CONF_EVENT_DATA: event_data,
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
