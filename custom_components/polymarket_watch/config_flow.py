"""Config flow for Polymarket Watch: UI-only, config + options + reconfigure."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_IMPORT,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    PolymarketApiClient,
    PolymarketApiError,
    PolymarketNotFoundError,
    parse_polymarket_url_or_slug,
)
from .const import (
    CONF_KIND,
    CONF_OUTCOME_TOKEN_IDS,
    CONF_SLUG,
    CONF_URL_OR_SLUG,
    DEFAULT_CLOSING_SOON_HOURS,
    DEFAULT_COOLDOWN_MIN,
    DEFAULT_HYSTERESIS_PP,
    DEFAULT_LARGE_TRADE_USD,
    DEFAULT_MOVE_DELTA_PP,
    DEFAULT_MOVE_WINDOW_MIN,
    DEFAULT_THRESHOLDS,
    DEFAULT_VOLUME_SPIKE_PCT,
    DOMAIN,
    KIND_MARKET,
    OPT_CLOSING_SOON_HOURS,
    OPT_COOLDOWN_MIN,
    OPT_HYSTERESIS_PP,
    OPT_LARGE_TRADE_USD,
    OPT_MOVE_DELTA_PP,
    OPT_MOVE_WINDOW_MIN,
    OPT_THRESHOLDS,
    OPT_VOLUME_SPIKE_PCT,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema({vol.Required(CONF_URL_OR_SLUG): str})


class PolymarketWatchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow: parse URL/slug -> confirm -> (pick sub-markets)."""

    VERSION = 1

    def __init__(self) -> None:
        self._event_data: dict[str, Any] | None = None
        self._market_slug: str | None = None
        self._market_question: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                parsed = parse_polymarket_url_or_slug(user_input[CONF_URL_OR_SLUG])
            except ValueError:
                errors["base"] = "invalid_url"
            else:
                session = async_get_clientsession(self.hass)
                api = PolymarketApiClient(session)
                try:
                    if parsed.kind == KIND_MARKET:
                        market = await api.get_market_by_slug(parsed.slug)
                        self._market_slug = market.slug
                        self._market_question = market.question
                        return await self.async_step_confirm_market()

                    event = await api.get_event_by_slug(parsed.slug)
                    markets = event.get("markets", [])
                    if len(markets) == 1:
                        self._market_slug = markets[0]["slug"]
                        self._market_question = markets[0].get("question", event.get("title", ""))
                        return await self.async_step_confirm_market()

                    self._event_data = event
                    return await self.async_step_select_markets()
                except PolymarketNotFoundError:
                    errors["base"] = "not_found"
                except PolymarketApiError:
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_confirm_market(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._market_slug is not None

        if user_input is not None:
            return await self._async_create_market_entry(self._market_slug, self._market_question or self._market_slug)

        return self.async_show_form(
            step_id="confirm_market",
            data_schema=vol.Schema({}),
            description_placeholders={"question": self._market_question or self._market_slug},
        )

    async def async_step_select_markets(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._event_data is not None
        markets = self._event_data.get("markets", [])
        options = [
            selector.SelectOptionDict(value=m["slug"], label=m.get("question", m["slug"]))
            for m in markets
        ]

        if user_input is not None:
            selected_slugs: list[str] = user_input["markets"]
            if not selected_slugs:
                return self.async_show_form(
                    step_id="select_markets",
                    data_schema=self._select_markets_schema(options),
                    errors={"base": "no_markets_selected"},
                )

            slug_to_question = {m["slug"]: m.get("question", m["slug"]) for m in markets}

            for slug in selected_slugs[1:]:
                await self.hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_IMPORT},
                    data={CONF_SLUG: slug, "question": slug_to_question[slug]},
                )

            first_slug = selected_slugs[0]
            return await self._async_create_market_entry(first_slug, slug_to_question[first_slug])

        return self.async_show_form(
            step_id="select_markets", data_schema=self._select_markets_schema(options)
        )

    @staticmethod
    def _select_markets_schema(options: list[selector.SelectOptionDict]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("markets"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, multiple=True)
                )
            }
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Create an additional entry for a sub-market picked in async_step_select_markets."""
        return await self._async_create_market_entry(import_data[CONF_SLUG], import_data["question"])

    async def _async_create_market_entry(self, slug: str, question: str) -> ConfigFlowResult:
        await self.async_set_unique_id(slug)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=question,
            data={
                CONF_KIND: KIND_MARKET,
                CONF_SLUG: slug,
                CONF_OUTCOME_TOKEN_IDS: [],
            },
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Allow re-pointing an existing entry at a different URL/slug."""
        return await self.async_step_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PolymarketWatchOptionsFlow()


class PolymarketWatchOptionsFlow(OptionsFlow):
    """Options flow: change detection thresholds for an existing entry."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            thresholds_raw = user_input[OPT_THRESHOLDS]
            thresholds = [float(t.strip()) for t in thresholds_raw.split(",") if t.strip()]
            return self.async_create_entry(
                data={
                    OPT_THRESHOLDS: thresholds,
                    OPT_HYSTERESIS_PP: user_input[OPT_HYSTERESIS_PP],
                    OPT_MOVE_DELTA_PP: user_input[OPT_MOVE_DELTA_PP],
                    OPT_MOVE_WINDOW_MIN: user_input[OPT_MOVE_WINDOW_MIN],
                    OPT_LARGE_TRADE_USD: user_input[OPT_LARGE_TRADE_USD],
                    OPT_VOLUME_SPIKE_PCT: user_input[OPT_VOLUME_SPIKE_PCT],
                    OPT_CLOSING_SOON_HOURS: user_input[OPT_CLOSING_SOON_HOURS],
                    OPT_COOLDOWN_MIN: user_input[OPT_COOLDOWN_MIN],
                }
            )

        opts = self.config_entry.options
        thresholds_default = ",".join(str(t) for t in opts.get(OPT_THRESHOLDS, DEFAULT_THRESHOLDS))

        schema = vol.Schema(
            {
                vol.Required(OPT_THRESHOLDS, default=thresholds_default): str,
                vol.Required(
                    OPT_HYSTERESIS_PP, default=opts.get(OPT_HYSTERESIS_PP, DEFAULT_HYSTERESIS_PP)
                ): vol.Coerce(float),
                vol.Required(
                    OPT_MOVE_DELTA_PP, default=opts.get(OPT_MOVE_DELTA_PP, DEFAULT_MOVE_DELTA_PP)
                ): vol.Coerce(float),
                vol.Required(
                    OPT_MOVE_WINDOW_MIN,
                    default=opts.get(OPT_MOVE_WINDOW_MIN, DEFAULT_MOVE_WINDOW_MIN),
                ): vol.Coerce(int),
                vol.Required(
                    OPT_LARGE_TRADE_USD,
                    default=opts.get(OPT_LARGE_TRADE_USD, DEFAULT_LARGE_TRADE_USD),
                ): vol.Coerce(float),
                vol.Required(
                    OPT_VOLUME_SPIKE_PCT,
                    default=opts.get(OPT_VOLUME_SPIKE_PCT, DEFAULT_VOLUME_SPIKE_PCT),
                ): vol.Coerce(float),
                vol.Required(
                    OPT_CLOSING_SOON_HOURS,
                    default=opts.get(OPT_CLOSING_SOON_HOURS, DEFAULT_CLOSING_SOON_HOURS),
                ): vol.Coerce(int),
                vol.Required(
                    OPT_COOLDOWN_MIN, default=opts.get(OPT_COOLDOWN_MIN, DEFAULT_COOLDOWN_MIN)
                ): vol.Coerce(int),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
