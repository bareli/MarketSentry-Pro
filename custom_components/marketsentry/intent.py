"""Assist/LLM-tool exposure for ad-hoc instrument search (ENH-015).

`search_instruments` (services.py) is a plain Home Assistant service: a
script or automation can call it explicitly, but neither Assist voice nor an
LLM-tool-calling conversation agent can reach it by natural language on its
own (see ENH-015 / D-021 / D-036).

Current Home Assistant (`homeassistant/helpers/llm.py`, `AssistAPI`) does not
expose a public hook to register one ad-hoc `llm.Tool` directly - the only
API-level entry point, `llm.async_register_api`, registers a whole competing
`llm.API` (a full tool/prompt bundle an agent must be configured to use
*instead of* the built-in "Assist" API), which is a much bigger surface than
one extra tool and not how any core integration adds a single action.

What `AssistAPI` actually does (see its `_async_get_tools`) is wrap every
registered `homeassistant.helpers.intent.IntentHandler` whose `platforms`
matches the user's exposed entity domains in an `llm.IntentTool`. Registering
a custom `intent.IntentHandler` via `intent.async_register` is the supported,
documented extension point third-party integrations use to add one
Assist/LLM-callable action (the same mechanism behind every "Hass*" built-in
intent) - so that is what this module does, instead of a custom `llm.API`.

This reuses `async_search_instruments` from `services.py` rather than
duplicating the provider-search/credential logic; the `search_instruments`
service's own behavior for direct (script/automation) callers is unchanged.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import intent

from .const import ATTR_LIMIT, ATTR_QUERY, CONF_PROVIDER, PROVIDER_KEYS
from .services import async_search_instruments

INTENT_SEARCH_INSTRUMENTS = "MarketSentrySearchInstruments"

_DEFAULT_LIMIT = 5


class SearchInstrumentsIntentHandler(intent.IntentHandler):
    """Find a tradable instrument by name/symbol and speak back the matches."""

    intent_type = INTENT_SEARCH_INSTRUMENTS
    description = (
        "Search MarketSentry Pro for a stock, cryptocurrency, FX pair, or "
        "Polymarket prediction market by name or symbol, e.g. 'search for AAPL' "
        "or 'find Bitcoin'. Returns the matching instruments; it does not by "
        "itself start tracking them."
    )

    @property
    def slot_schema(self) -> dict[Any, Any]:
        """Slots an LLM/Assist tool call fills in."""
        return {
            vol.Required(CONF_PROVIDER): vol.In(PROVIDER_KEYS),
            vol.Required(ATTR_QUERY): cv.string,
            vol.Optional(ATTR_LIMIT): vol.Coerce(int),
        }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Run the search and set a concise speech response."""
        hass: HomeAssistant = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        provider_key: str = slots[CONF_PROVIDER]["value"]
        query: str = slots[ATTR_QUERY]["value"]
        limit: int = slots.get(ATTR_LIMIT, {}).get("value", _DEFAULT_LIMIT)

        response = intent_obj.create_response()
        try:
            refs = await async_search_instruments(hass, provider_key, query, limit)
        except ValueError as err:
            response.async_set_error(intent.IntentResponseErrorCode.FAILED_TO_HANDLE, str(err))
            return response

        if not refs:
            response.async_set_speech(f"I couldn't find any instrument matching '{query}'.")
            return response

        names = [f"{ref.name} ({ref.symbol})" for ref in refs]
        if len(names) == 1:
            speech = f"Found {names[0]}."
        else:
            speech = f"Found {len(names)} matches: {', '.join(names)}."
        response.async_set_speech(speech)
        return response


async def async_setup_intents(hass: HomeAssistant) -> None:
    """Register the search_instruments Assist/LLM intent. Safe to call more than once.

    This is HA's own `intent` component's documented integration-platform
    protocol (`homeassistant.components.intent.IntentPlatformProtocol`,
    `async def async_setup_intents(self, hass) -> None`): a module named
    `intent.py` exposing a top-level function of this exact name/signature
    is auto-discovered and awaited by `async_process_integration_platforms`
    during HA's own bootstrap - it must be a real coroutine function (even
    though this body has nothing to await) or HA's `await
    platform.async_setup_intents(hass)` raises `TypeError: 'NoneType'
    object can't be awaited`. HA calls this automatically; nothing in this
    integration needs to call it itself (see `__init__.py`)."""
    if any(handler.intent_type == INTENT_SEARCH_INSTRUMENTS for handler in intent.async_get(hass)):
        return
    intent.async_register(hass, SearchInstrumentsIntentHandler())
