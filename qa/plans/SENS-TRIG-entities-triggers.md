# SENS / TRIG - Entities, devices, diagnostics, device triggers

Source: `custom_components/marketsentry/{entity,sensor,binary_sensor,device_trigger,diagnostics}.py`.
Entity/device-shape tests need the full `hass` fixture (CI-only, Linux); diagnostics redaction and
device-trigger-type-list logic can be read/reasoned about statically if a live/CI instance isn't
available.

- **SENS-01** One HA device per tracked instrument (subentry), named/manufacturer/model correct
  per kind (`_MODEL_BY_KIND`); a 4th+ kind added to the provider layer without a matching
  `_MODEL_BY_KIND` entry falls back to the raw kind string as the model - confirm this is still
  true for `crypto` (it has an entry: "Cryptocurrency").
  - **CODE-VERIFIED, 2026-10-31, qa-engineer.** `entity.py`'s `_MODEL_BY_KIND` has
    `"crypto": "Cryptocurrency"`. Read directly, no hass fixture needed for this static dict check.
    Full device-registry shape (actual device rows created) is CI-only (needs `hass` fixture).
- **SENS-02** Per-kind sensor set: outcome gets probability/last-trade-price/spread (+ Polymarket
  metadata sensors when a market slug is known); stock gets price/previous-close/market-state;
  crypto gets price only; fx gets rate only. A kind with a sensor set that never got added here
  silently has zero entities and zero data, not an error.
  - **CODE-VERIFIED, 2026-10-31, qa-engineer.** `sensor.py`'s `async_setup_entry` kind-branch
    matches exactly: outcome → Probability/LastTradePrice/Spread (+ conditional metadata sensors);
    stock → Price/PreviousClose/MarketState; crypto → Price only; else (fx) → Rate only. Read
    directly; entity-registration-actually-happens is CI-only.
- **SENS-03** `card_attributes()` (kind/provider/url) appears as `extra_state_attributes` on every
  kind's *primary* sensor (the one the card's `rows.js` picks up via
  `PRIMARY_TRANSLATION_KEYS = {"probability", "price", "rate"}`). Crypto deliberately reuses the
  `price` translation key (shared with stock) - confirm this doesn't collide/confuse anything
  when both a stock and a crypto instrument exist in the same HA instance (e.g. entity_id
  disambiguation, unique_id collision - unique_id is `{subentry_id}_price` so should be fine, but
  worth one concrete check).
  - **CODE-VERIFIED, 2026-10-31, qa-engineer.** `PriceSensor` (shared by stock and crypto) sets
    `_attr_unique_id = f"{tracker.subentry_id}_price"`; `subentry_id` is per-instrument-unique (one
    subentry per tracked instrument), so a stock `PriceSensor` and a crypto `PriceSensor` in the
    same HA instance get different `subentry_id`s and therefore different `unique_id`s - no
    collision. No defect found.
- **SENS-04** Diagnostics download redacts Finnhub `api_key` AND both Alpaca `key_id` +
  `secret_key` - confirm both Alpaca fields are actually covered, not just one left raw.
  - **CODE-VERIFIED** (cross-reference: already resolved this session as SEC-03,
    `qa/security/findings/` - `diagnostics.py`'s `TO_REDACT = {CONF_API_KEY, CONF_KEY_ID,
    CONF_SECRET_KEY}` covers Finnhub's key and both Alpaca fields). Not re-filed; see SEC-03.
- **SENS-05** State-write throttling (`STATE_WRITE_MIN_INTERVAL_SEC`/`STATE_WRITE_MIN_DELTA`)
  doesn't drop a *meaningful* first-ever write (the "no prior value" case always writes).
  - **CODE-VERIFIED, 2026-10-31, qa-engineer.** `entity.py`'s `_should_write_throttled`: `if
    self._last_written_value is None or new_value is None: ... return True` - the first-ever write
    (no prior value) always proceeds, before any interval/delta check. No defect found.
- **SENS-06** `binary_sensor`: outcome-only `closed`/`accepting_orders` (needs Polymarket
  metadata); `stream_connected` only appears when `supports_streaming` is true - confirm it's
  correctly absent for fx and crypto (both poll-only).
  - **CODE-VERIFIED, 2026-10-31, qa-engineer.** `binary_sensor.py`'s `async_setup_entry`: the
    outcome-only sensors are gated on `tracker.ref.kind != "outcome": continue`;
    `StreamConnectedBinarySensor` is added only `if runtime.provider.supports_streaming:` - and
    both `FxProvider`/`CryptoProvider` have `supports_streaming = False` (confirmed PROV-07), so
    both are correctly excluded. No defect found.
- **TRIG-01** Device trigger list shown in the UI for a given device matches
  `EVENT_TYPES_BY_KIND[kind]` exactly - no extra, no missing, for all four kinds including crypto.
  - **CODE-VERIFIED (logic only, not run against a device registry), 2026-10-31, qa-engineer.**
    `device_trigger.py`'s `async_get_triggers` returns exactly
    `[{..., CONF_TYPE: event_type} for event_type in EVENT_TYPES_BY_KIND[kind]]` - a direct,
    unfiltered pass-through of the const dict, so correctness reduces entirely to
    `EVENT_TYPES_BY_KIND` itself, which was already cross-checked against `_build_detectors`
    (DET-09) and found consistent for crypto. The actual "what the UI shows for a real device" is
    CI-only (needs the `hass` device registry fixture).
- **TRIG-02** Firing a device trigger's underlying bus event (`marketsentry_<type>`) carries the
  full payload (name/symbol/old/new/delta/url/...) regardless of whether the automation was built
  via the device-trigger UI or raw YAML event trigger - `{{ trigger.event.data.* }}` works either
  way (this is what the shipped blueprints rely on).
  - **CODE-VERIFIED, 2026-10-31, qa-engineer.** `__init__.py`'s `_fire_detected_event` builds one
    flat payload dict (entry_id/subentry_id/provider/kind/symbol/instrument_id/unit/name/old/new/
    delta/direction/window_min/url/+extra) and fires it via `hass.bus.async_fire(f"marketsentry_
    {event.event_type}", payload)` - a single HA bus event, independent of how any listener
    attaches. `device_trigger.py`'s `async_attach_trigger` itself just builds a standard `event`
    trigger config (`CONF_PLATFORM: "event"`, same event type) and delegates to
    `event_trigger.async_attach_trigger` - the exact same mechanism a raw YAML `trigger: event`
    would use. No divergence between the two attachment paths; both observe the identical event
    bus payload. No defect found.
