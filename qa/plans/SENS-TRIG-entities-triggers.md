# SENS / TRIG - Entities, devices, diagnostics, device triggers

Source: `custom_components/marketsentry/{entity,sensor,binary_sensor,device_trigger,diagnostics}.py`.
Entity/device-shape tests need the full `hass` fixture (CI-only, Linux); diagnostics redaction and
device-trigger-type-list logic can be read/reasoned about statically if a live/CI instance isn't
available.

- **SENS-01** One HA device per tracked instrument (subentry), named/manufacturer/model correct
  per kind (`_MODEL_BY_KIND`); a 4th+ kind added to the provider layer without a matching
  `_MODEL_BY_KIND` entry falls back to the raw kind string as the model - confirm this is still
  true for `crypto` (it has an entry: "Cryptocurrency").
- **SENS-02** Per-kind sensor set: outcome gets probability/last-trade-price/spread (+ Polymarket
  metadata sensors when a market slug is known); stock gets price/previous-close/market-state;
  crypto gets price only; fx gets rate only. A kind with a sensor set that never got added here
  silently has zero entities and zero data, not an error.
- **SENS-03** `card_attributes()` (kind/provider/url) appears as `extra_state_attributes` on every
  kind's *primary* sensor (the one the card's `rows.js` picks up via
  `PRIMARY_TRANSLATION_KEYS = {"probability", "price", "rate"}`). Crypto deliberately reuses the
  `price` translation key (shared with stock) - confirm this doesn't collide/confuse anything
  when both a stock and a crypto instrument exist in the same HA instance (e.g. entity_id
  disambiguation, unique_id collision - unique_id is `{subentry_id}_price` so should be fine, but
  worth one concrete check).
- **SENS-04** Diagnostics download redacts Finnhub `api_key` AND both Alpaca `key_id` +
  `secret_key` - confirm both Alpaca fields are actually covered, not just one left raw.
- **SENS-05** State-write throttling (`STATE_WRITE_MIN_INTERVAL_SEC`/`STATE_WRITE_MIN_DELTA`)
  doesn't drop a *meaningful* first-ever write (the "no prior value" case always writes).
- **SENS-06** `binary_sensor`: outcome-only `closed`/`accepting_orders` (needs Polymarket
  metadata); `stream_connected` only appears when `supports_streaming` is true - confirm it's
  correctly absent for fx and crypto (both poll-only).
- **TRIG-01** Device trigger list shown in the UI for a given device matches
  `EVENT_TYPES_BY_KIND[kind]` exactly - no extra, no missing, for all four kinds including crypto.
- **TRIG-02** Firing a device trigger's underlying bus event (`marketsentry_<type>`) carries the
  full payload (name/symbol/old/new/delta/url/...) regardless of whether the automation was built
  via the device-trigger UI or raw YAML event trigger - `{{ trigger.event.data.* }}` works either
  way (this is what the shipped blueprints rely on).
