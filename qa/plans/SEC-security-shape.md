# SEC - Security shape

Dispatch `qa-security-expert` automatically whenever a diff touches credential handling, the
diagnostics redaction path, the static card-file route, or the `marketsentry/history` WS command
(see `PROJECT.md` → *Roles*). No multi-tenant isolation boundary exists to test - this is a
single-user integration.

- **SEC-01** `/marketsentry_static/marketsentry-card.js` (registered via
  `async_register_static_paths` in `async_setup`): confirm whether this is reachable without an
  authenticated HA session. It's a static JS bundle (not sensitive by itself), but confirm nothing
  else ever gets registered under the same unauthenticated path by a future change.
- **SEC-02** `marketsentry/history` WS command: confirm it requires an authenticated WS connection
  like the rest of HA's WS API (no custom bypass), and that it only returns history for the
  calling user's own instance data (not cross-entry, though there's only one HA instance so this
  is mostly a "did someone add a parameter that leaks another entry's device_id" check).
- **SEC-03** Diagnostics download redacts Finnhub `api_key` and both Alpaca `key_id` +
  `secret_key`. CODE-VERIFIED 2026-10-31 (no live HA needed): `diagnostics.py`'s
  `TO_REDACT = {CONF_API_KEY, CONF_KEY_ID, CONF_SECRET_KEY}` covers all three fields and is applied
  via `async_redact_data(dict(entry.data), TO_REDACT)` to the only place credentials appear in the
  diagnostics payload. Re-check this set whenever a provider adds a new credential field (e.g. a
  future provider needing an API secret beyond a single key).
- **SEC-04** No credential value (`api_key`/`key_id`/`secret_key`) ever reaches `_LOGGER` at any
  level, including debug - grep for any log call that interpolates `user_input`/`data`/`entry.data`
  wholesale rather than specific non-secret fields.
- **SEC-05** The card's `innerHTML` rendering (`marketsentry-card.js`,
  `marketsentry-instrument-card.js`) escapes every value sourced from entity state/attributes
  (`escapeHtml`/`escapeAttr`) before interpolating into the template string - a provider-supplied
  `name`/`symbol` containing HTML must not execute. `safeUrl()` already restricts `url` to
  http(s) - confirm every *other* interpolated field (not just `url`) is escaped, including fields
  added by the crypto provider this session (`name` built from CoinGecko's `coin['name']`, which
  is third-party data MarketSentry Pro doesn't control).
