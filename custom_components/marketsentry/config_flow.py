"""Config flow for MarketSentry Pro.

One config entry = one provider account (credentials step only for
providers that need a key). Each tracked instrument is added afterward as
a config *subentry* under that entry, so adding/removing/reconfiguring
instruments never re-asks for credentials.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

import voluptuous as vol
from homeassistant.components.persistent_notification import (
    async_create as async_create_notification,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_EXTRA,
    CONF_FEED,
    CONF_INSTRUMENT_ID,
    CONF_INSTRUMENT_KIND,
    CONF_INSTRUMENT_NAME,
    CONF_KEY_ID,
    CONF_OPTIONS,
    CONF_PROVIDER,
    CONF_SECRET_KEY,
    CONF_SYMBOL,
    CONF_UNIT,
    CONF_URL,
    CONF_URL_OR_QUERY,
    DOMAIN,
    OPT_CLOSING_SOON_HOURS,
    OPT_COOLDOWN_MIN,
    OPT_COST_BASIS,
    OPT_DAILY_CHANGE_PCT,
    OPT_EXTENDED_HOURS,
    OPT_HYSTERESIS,
    OPT_LARGE_TRADE_USD,
    OPT_MARKET_OPEN_GAP_PCT,
    OPT_MOVE_DELTA,
    OPT_MOVE_WINDOW_MIN,
    OPT_QUANTITY,
    OPT_THRESHOLDS,
    OPT_VOLUME_SPIKE_PCT,
    PROVIDER_KEYS,
    SUBENTRY_TYPE_INSTRUMENT,
    default_options_for_kind,
)
from .providers import PROVIDERS, build_provider
from .providers.base import CannotConnect, InstrumentRef, InvalidAuth, PricePoint, Provider

_LOGGER = logging.getLogger(__name__)

# ENH-017: a rough volatility hint next to the confirm step's threshold
# fields. A week is enough points for a day-over-day average without
# asking a rate-limited provider for much; kept short and timed out so a
# slow/dead provider degrades to no hint rather than blocking setup.
VOLATILITY_HINT_HOURS = 24 * 7
VOLATILITY_HINT_TIMEOUT_SEC = 5.0

STEP_PROVIDER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PROVIDER): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=key, label=PROVIDERS[key].name)
                    for key in PROVIDER_KEYS
                ]
            )
        )
    }
)

STEP_INSTRUMENT_SCHEMA = vol.Schema({vol.Required(CONF_URL_OR_QUERY): str})


def _thresholds_to_str(thresholds: list[float]) -> str:
    return ",".join(str(t) for t in thresholds)


def _parse_thresholds(raw: str) -> list[float]:
    return [float(t.strip()) for t in raw.split(",") if t.strip()]


def _quantity_to_str(quantity: float | None) -> str:
    return "" if quantity is None else str(quantity)


def _parse_quantity(raw: str) -> float | None:
    raw = raw.strip()
    return float(raw) if raw else None


# Cost basis per unit (ENH-012) is string-encoded/blank-means-unset the same
# way quantity is (D-031: shares the field's shape) - reuse rather than
# duplicate the float-or-blank logic.
_cost_basis_to_str = _quantity_to_str
_parse_cost_basis = _parse_quantity


def _volatility_hint_pct(points: list[PricePoint], kind: str) -> float | None:
    """Rough average day-over-day absolute change from a short history
    sample - one number per day (its last price in the sample), then the
    average absolute change between consecutive days. Deliberately simple:
    this is a sizing hint for the confirm step's threshold fields, not a
    statistical model. `None` when there isn't enough data (fewer than two
    distinct days) to say anything.

    For `outcome`, `PricePoint.price` is the same raw 0-1 probability
    `Quote.price` carries (see sensor.py's `_position_value`/
    `_unrealized_pnl` `is_outcome` scaling convention), so the change is
    expressed in percentage points (the probability delta, times 100) -
    not a percent-of-percent relative change - matching how this project
    already treats probability as already being in 0-100 terms. Every
    other kind is a plain relative percent change.
    """
    if len(points) < 2:
        return None
    daily_last: dict[date, float] = {}
    for point in sorted(points, key=lambda p: p.ts):
        daily_last[point.ts.date()] = point.price
    prices = list(daily_last.values())
    if len(prices) < 2:
        return None

    deltas: list[float] = []
    for prev, curr in zip(prices, prices[1:], strict=False):
        if kind == "outcome":
            deltas.append(abs(curr - prev) * 100)
        elif prev:
            deltas.append(abs(curr - prev) / abs(prev) * 100)
    return sum(deltas) / len(deltas) if deltas else None


async def _async_volatility_hint(provider: Provider, ref: InstrumentRef) -> str:
    """A one-line threshold-sizing hint for the confirm step's
    `description_placeholders`, or "" if none could be computed.

    ENH-017: a provider outage, timeout, or a sample too thin to compute
    anything meaningful must degrade to today's plain confirm step, never
    block or error the confirmation - so every failure here, caught
    broadly on purpose, just means an empty hint rather than a broken flow.
    """
    try:
        points = await asyncio.wait_for(
            provider.fetch_history(ref, hours=VOLATILITY_HINT_HOURS),
            timeout=VOLATILITY_HINT_TIMEOUT_SEC,
        )
    except Exception as err:  # noqa: BLE001 - any provider failure degrades to no hint
        _LOGGER.debug("Volatility hint unavailable for %s: %s", ref.symbol, err)
        return ""

    avg = _volatility_hint_pct(points, ref.kind)
    if avg is None:
        return ""
    unit = "percentage points" if ref.kind == "outcome" else "%"
    return (
        f" {ref.symbol} moved ~{avg:.1f}{unit} on an average day over the last week."
    )


def _options_schema(kind: str, defaults: dict[str, Any]) -> vol.Schema:
    fields: dict[Any, Any] = {
        vol.Optional(OPT_THRESHOLDS, default=_thresholds_to_str(defaults.get(OPT_THRESHOLDS, []))): str,
        vol.Optional(OPT_HYSTERESIS, default=defaults.get(OPT_HYSTERESIS, 0.0)): vol.Coerce(float),
        vol.Optional(OPT_MOVE_DELTA, default=defaults.get(OPT_MOVE_DELTA, 5.0)): vol.Coerce(float),
        vol.Optional(OPT_MOVE_WINDOW_MIN, default=defaults.get(OPT_MOVE_WINDOW_MIN, 60)): vol.Coerce(int),
        vol.Optional(OPT_COOLDOWN_MIN, default=defaults.get(OPT_COOLDOWN_MIN, 15)): vol.Coerce(int),
        vol.Optional(OPT_QUANTITY, default=_quantity_to_str(defaults.get(OPT_QUANTITY))): str,
        vol.Optional(OPT_COST_BASIS, default=_cost_basis_to_str(defaults.get(OPT_COST_BASIS))): str,
    }
    if kind in ("stock", "fx", "crypto"):
        fields[
            vol.Optional(OPT_DAILY_CHANGE_PCT, default=defaults.get(OPT_DAILY_CHANGE_PCT, 3.0))
        ] = vol.Coerce(float)
    if kind in ("outcome", "stock"):
        fields[
            vol.Optional(OPT_LARGE_TRADE_USD, default=defaults.get(OPT_LARGE_TRADE_USD, 10000.0))
        ] = vol.Coerce(float)
    if kind == "outcome":
        fields[
            vol.Optional(OPT_VOLUME_SPIKE_PCT, default=defaults.get(OPT_VOLUME_SPIKE_PCT, 50.0))
        ] = vol.Coerce(float)
        fields[
            vol.Optional(OPT_CLOSING_SOON_HOURS, default=defaults.get(OPT_CLOSING_SOON_HOURS, 24))
        ] = vol.Coerce(int)
    if kind == "stock":
        fields[
            vol.Optional(OPT_MARKET_OPEN_GAP_PCT, default=defaults.get(OPT_MARKET_OPEN_GAP_PCT, 3.0))
        ] = vol.Coerce(float)
        fields[vol.Optional(OPT_EXTENDED_HOURS, default=defaults.get(OPT_EXTENDED_HOURS, False))] = bool
    return vol.Schema(fields)


DASHBOARD_STRATEGY_NOTIFICATION_ID = "marketsentry_dashboard_strategy"


def _any_instrument_exists(hass: HomeAssistant, exclude_entry_id: str) -> bool:
    """True if any MarketSentry Pro entry other than `exclude_entry_id` already has an instrument."""
    return any(
        entry.subentries
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.entry_id != exclude_entry_id
    )


def _notify_dashboard_strategy(hass: HomeAssistant) -> None:
    """One-time nudge toward the auto-dashboard strategy, shown after the very first instrument."""
    async_create_notification(
        hass,
        title="MarketSentry Pro: build a dashboard automatically",
        message=(
            "Your first tracked instrument is set up. Add a view to any dashboard, "
            "switch it to YAML mode (pencil icon > Add view > 3-dot menu), and paste:\n\n"
            "```yaml\n"
            "strategy:\n"
            "  type: custom:marketsentry\n"
            "```\n\n"
            "It fills itself with every instrument you track, no manual card placement."
        ),
        notification_id=DASHBOARD_STRATEGY_NOTIFICATION_ID,
    )


def _parse_options_form(kind: str, user_input: dict[str, Any]) -> dict[str, Any]:
    opts = dict(default_options_for_kind(kind))
    opts[OPT_THRESHOLDS] = _parse_thresholds(user_input.get(OPT_THRESHOLDS, ""))
    opts[OPT_QUANTITY] = _parse_quantity(user_input.get(OPT_QUANTITY, ""))
    opts[OPT_COST_BASIS] = _parse_cost_basis(user_input.get(OPT_COST_BASIS, ""))
    for key in (
        OPT_HYSTERESIS,
        OPT_MOVE_DELTA,
        OPT_MOVE_WINDOW_MIN,
        OPT_DAILY_CHANGE_PCT,
        OPT_LARGE_TRADE_USD,
        OPT_VOLUME_SPIKE_PCT,
        OPT_CLOSING_SOON_HOURS,
        OPT_MARKET_OPEN_GAP_PCT,
        OPT_EXTENDED_HOURS,
        OPT_COOLDOWN_MIN,
    ):
        if key in user_input:
            opts[key] = user_input[key]
    return opts


class MarketSentryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up one provider account. Instruments are added afterward as subentries."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        self._provider_key: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._provider_key = user_input[CONF_PROVIDER]
            await self.async_set_unique_id(self._provider_key)
            self._abort_if_unique_id_configured()

            if not PROVIDERS[self._provider_key].requires_api_key:
                return await self._async_finish_no_credentials()
            if self._provider_key == "finnhub":
                return await self.async_step_finnhub_credentials()
            return await self.async_step_alpaca_credentials()

        return self.async_show_form(step_id="user", data_schema=STEP_PROVIDER_SCHEMA)

    async def _async_finish_no_credentials(self) -> ConfigFlowResult:
        assert self._provider_key is not None
        session = async_get_clientsession(self.hass)
        provider = build_provider(session, self._provider_key, {})
        await provider.validate({})
        return self.async_create_entry(
            title=PROVIDERS[self._provider_key].name,
            data={CONF_PROVIDER: self._provider_key},
        )

    async def async_step_finnhub_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            provider = build_provider(session, "finnhub", user_input)
            try:
                await provider.validate(user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth_finnhub"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=PROVIDERS["finnhub"].name,
                    data={CONF_PROVIDER: "finnhub", CONF_API_KEY: user_input[CONF_API_KEY]},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                )
            }
        )
        return self.async_show_form(
            step_id="finnhub_credentials", data_schema=schema, errors=errors
        )

    async def async_step_alpaca_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            provider = build_provider(session, "alpaca", user_input)
            try:
                await provider.validate(user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth_alpaca"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=PROVIDERS["alpaca"].name,
                    data={
                        CONF_PROVIDER: "alpaca",
                        CONF_KEY_ID: user_input[CONF_KEY_ID],
                        CONF_SECRET_KEY: user_input[CONF_SECRET_KEY],
                        CONF_FEED: user_input.get(CONF_FEED, "iex"),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_KEY_ID): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Required(CONF_SECRET_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_FEED, default="iex"): vol.In(["iex", "sip"]),
            }
        )
        return self.async_show_form(
            step_id="alpaca_credentials", data_schema=schema, errors=errors
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_TYPE_INSTRUMENT: InstrumentSubentryFlow}


class InstrumentSubentryFlow(ConfigSubentryFlow):
    """Add or reconfigure one tracked instrument under a provider entry."""

    def __init__(self) -> None:
        self._pending_ref: InstrumentRef | None = None
        self._pending_choices: dict[str, InstrumentRef] = {}

    def _build_provider(self) -> Provider:
        entry = self._get_entry()
        session = async_get_clientsession(self.hass)
        return build_provider(session, entry.data[CONF_PROVIDER], dict(entry.data))

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            provider = self._build_provider()
            query = user_input[CONF_URL_OR_QUERY]
            refs: list[InstrumentRef] = []
            try:
                refs = await provider.resolve(query)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                try:
                    refs = await provider.search(query, limit=10)
                except (CannotConnect, InvalidAuth):
                    refs = []

            if not refs and not errors:
                errors["base"] = "not_found"

            if refs and not errors:
                if len(refs) == 1:
                    self._pending_ref = refs[0]
                    return await self.async_step_confirm()
                self._pending_choices = {ref.id: ref for ref in refs}
                return await self.async_step_select()

        return self.async_show_form(
            step_id="user", data_schema=STEP_INSTRUMENT_SCHEMA, errors=errors
        )

    async def async_step_select(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if user_input is not None:
            self._pending_ref = self._pending_choices[user_input["instrument"]]
            return await self.async_step_confirm()

        options = [
            selector.SelectOptionDict(value=ref.id, label=f"{ref.symbol} - {ref.name}")
            for ref in self._pending_choices.values()
        ]
        schema = vol.Schema(
            {
                vol.Required("instrument"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options)
                )
            }
        )
        return self.async_show_form(step_id="select", data_schema=schema)

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        ref = self._pending_ref
        assert ref is not None

        entry = self._get_entry()
        existing_ids = {
            subentry.data.get(CONF_INSTRUMENT_ID) for subentry in entry.subentries.values()
        }
        if ref.id in existing_ids:
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            is_first_instrument_ever = not existing_ids and not _any_instrument_exists(
                self.hass, entry.entry_id
            )
            data = {
                CONF_INSTRUMENT_ID: ref.id,
                CONF_SYMBOL: ref.symbol,
                CONF_INSTRUMENT_NAME: ref.name,
                CONF_INSTRUMENT_KIND: ref.kind,
                CONF_UNIT: ref.unit,
                CONF_URL: ref.url,
                CONF_EXTRA: ref.extra,
                CONF_OPTIONS: _parse_options_form(ref.kind, user_input),
            }
            if is_first_instrument_ever:
                _notify_dashboard_strategy(self.hass)
            return self.async_create_entry(title=ref.name, data=data, unique_id=ref.id)

        schema = _options_schema(ref.kind, default_options_for_kind(ref.kind))
        volatility_hint = await _async_volatility_hint(self._build_provider(), ref)
        return self.async_show_form(
            step_id="confirm",
            data_schema=schema,
            description_placeholders={
                "name": ref.name,
                "symbol": ref.symbol,
                "volatility_hint": volatility_hint,
            },
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()
        kind = subentry.data[CONF_INSTRUMENT_KIND]

        if user_input is not None:
            return self.async_update_and_abort(
                entry,
                subentry,
                data_updates={CONF_OPTIONS: _parse_options_form(kind, user_input)},
            )

        schema = _options_schema(kind, subentry.data.get(CONF_OPTIONS, {}))
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            description_placeholders={"name": subentry.title},
        )
