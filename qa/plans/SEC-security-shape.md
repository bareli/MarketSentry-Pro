# SEC - Security shape

Dispatch `qa-security-expert` automatically whenever a diff touches credential handling, the
diagnostics redaction path, the static card-file route, or the `marketsentry/history` WS command
(see `PROJECT.md` → *Roles*). No multi-tenant isolation boundary exists to test - this is a
single-user integration.

- **SEC-01** `/marketsentry_static/marketsentry-card.js` (registered via
  `async_register_static_paths` in `async_setup`): confirm whether this is reachable without an
  authenticated HA session. CODE+LIVE-VERIFIED 2026-10-31: `curl -I` against the live instance's
  static path returned `HTTP 200` unauthenticated - by design, matching how HA serves its own
  frontend JS pre-login, and the file is just the card's bundled JS (identical to what's public on
  GitHub), not a security issue. Re-check if this path is ever reused to serve anything
  non-public.
- **SEC-02** `marketsentry/history` WS command: confirm it requires an authenticated WS connection
  like the rest of HA's WS API (no custom bypass), and that it only returns history for the
  calling user's own instance data. CODE-VERIFIED 2026-10-31: `websocket_api.py`'s
  `websocket_history` carries no `@require_admin` or other decorator that would relax auth, and
  registers via the standard `async_register_command` - HA enforces connection-level auth before
  any registered command (including this one) is dispatched, so there's no custom bypass. Not
  independently live-tested against an actual unauthenticated WS connection attempt this session.
- **SEC-03** Diagnostics download redacts Finnhub `api_key` and both Alpaca `key_id` +
  `secret_key`. CODE-VERIFIED 2026-10-31 (no live HA needed): `diagnostics.py`'s
  `TO_REDACT = {CONF_API_KEY, CONF_KEY_ID, CONF_SECRET_KEY}` covers all three fields and is applied
  via `async_redact_data(dict(entry.data), TO_REDACT)` to the only place credentials appear in the
  diagnostics payload. Re-check this set whenever a provider adds a new credential field (e.g. a
  future provider needing an API secret beyond a single key).
- **SEC-04** No credential value (`api_key`/`key_id`/`secret_key`) ever reaches `_LOGGER` at any
  level, including debug. CODE-VERIFIED 2026-10-31: `grep -rn "_LOGGER\." custom_components/marketsentry
  --include="*.py" | grep -iE "api_key|key_id|secret|credential|user_input|entry\.data|data\["`
  returned zero matches - no log call interpolates a credential-shaped variable or the raw
  data/user_input dicts that would contain one.
- **SEC-05** The card's `innerHTML` rendering (`marketsentry-card.js`,
  `marketsentry-instrument-card.js`) escapes every value sourced from entity state/attributes
  (`escapeHtml`/`escapeAttr`) before interpolating into the template string - a provider-supplied
  `name`/`symbol` containing HTML must not execute. CODE-VERIFIED 2026-10-31 (read both files
  again this session): every interpolated `row.name`, badge/chip text, and the crypto provider's
  CoinGecko-sourced `name` all pass through `escapeHtml`/`escapeAttr`; `safeUrl()` separately
  restricts `url` to http(s). No un-escaped interpolation found.
- **SEC-06** Finnhub/Alpaca credential fields in the config flow are plain visible text, not
  password-masked. **CONFIRMED BUG, filed as [SEC-001](../security/findings/SEC-001.md).**
