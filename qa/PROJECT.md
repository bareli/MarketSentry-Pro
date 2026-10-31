# QA project profile: MarketSentry Pro

The global QA kit (`~/.claude/qa-kit/`) holds process only. Everything that is true of THIS product
lives here and in `qa/CLAUDE.md` (environments, instances, traps) and `qa/knowledge/` (what QA learned).

Fill only what the code or the owner proves. A `TODO(ask owner)` is honest; a guess is a defect.

## Product

- Name: MarketSentry Pro (domain/code identifier: `marketsentry`)
- What it does: a Home Assistant custom integration (HACS) that tracks Polymarket prediction
  markets, stocks (Finnhub or Alpaca/IEX), cryptocurrencies (CoinGecko), and FX rates
  (Frankfurter / Bank of Israel), fires HA events/device triggers on price moves and thresholds,
  and ships a Lovelace card (list + single-instrument detail + an auto-dashboard view strategy)
  to display them. Read-only: no trading, no wallet/brokerage access.
- Owner (rules on UX/ENH decisions): Victor (bareli)
- Production URL: N/A - not a hosted service. The only live runtime is a Home Assistant instance
  that installs this integration via HACS. This project's one known live instance is the owner's
  own home automation system at `http://homeassistant.local:8123` - see *Security shape* and
  `qa/CLAUDE.md` §1 for why that instance is gated like production even though it is not a SaaS prod.
- Deploy: the owner installs/updates via HACS (custom repository) on their HA instance, then
  restarts HA if Python changed. Never "live" just because `master` was pushed or a tag was cut -
  it is live only after HACS redownload + restart on that specific instance.

## Users

One real user confirmed: the owner (Victor), running their own HA instance, bilingual
Hebrew/English. Card and backend now also ship de/fr/es/pt-BR/it/nl translations for any other
HACS user who installs it, but no other user has been directly observed. TODO(ask owner): any
known install base beyond the owner's own instance (HACS download counts, issues from strangers)?

## Locale

UI languages: en, he, de, fr, es, pt-BR, it, nl (backend config flow/entities/triggers/services,
and the `marketsentry-card`/`marketsentry-instrument-card` frontend - see `card/src/i18n.js` and
`custom_components/marketsentry/translations/*.json`). Hebrew is RTL and is the owner's own daily
language; realistic test content should include Hebrew device/market names and RTL layout, not
just English LTR. Dates/currencies are not deeply localized (`formatValue`/`formatCompactUsd` are
mostly USD/ILS-shaped); flag anything that reads as an English-only assumption.

## Stack

- Backend: Python 3.13, Home Assistant custom_components architecture (config entries +
  subentries), aiohttp for all provider HTTP/WS calls, no database (HA's own entity/recorder
  stores state). `ruff` + `mypy --strict` enforced in CI.
- Tests (backend): pytest + `pytest-homeassistant-custom-component`. Config-flow/subentry-flow
  tests need the full `hass` fixture, which imports `homeassistant.runner` -> POSIX-only `fcntl` -
  **these do not run on this Windows dev machine**, only in CI (Linux). Everything else
  (`detector`, `models`, `api`, `ws`, `market_calendar`, `providers/*`) runs anywhere via
  `pytest tests --ignore=tests/config_flow -p no:homeassistant`.
- Frontend: vanilla Web Components (no framework), bundled with esbuild into
  `custom_components/marketsentry/www/marketsentry-card.js`, auto-registered as a Lovelace
  resource by the backend on startup. Tests: Vitest (unit, pure logic) + Playwright (behavioral +
  visual-regression screenshots, `card/e2e/`).
- No background job queue beyond the integration's own `ProviderSnapshotCoordinator` (5-minute
  REST poll floor) and each provider's own WS `stream()` loop with its own reconnect/backoff.

## Paths

- Application code (read-only for everyone except qa-developer): `custom_components/marketsentry/`
  (backend), `card/src/` (frontend source; built output is
  `custom_components/marketsentry/www/marketsentry-card.js`, do not hand-edit).
- Test project (finders may add a failing regression test only):
  `tests/` (pytest, mirrors `custom_components/marketsentry/` structure: `tests/providers/`,
  `tests/config_flow/`, etc.) and `card/test/` (Vitest) + `card/e2e/` (Playwright).
- Build / test commands (see root `README.md` → *Development*):
  - Backend: `pip install -r requirements_test.txt`, `ruff check custom_components/marketsentry`,
    `mypy custom_components/marketsentry`, `pytest tests` (Linux) or
    `pytest tests --ignore=tests/config_flow -p no:homeassistant` (Windows-safe subset).
  - Card: `cd card && npm run build && npm test` (Vitest) and `npx playwright test` (e2e; needs a
    browser download, not in the main CI workflow - see `card/README.md`).

## Roles

- qa-engineer: **on**. Functional correctness of providers/detectors/config-flow/entities/card.
- qa-ux-expert: **on**. The card is real end-user UI (dashboard, config-flow forms, blueprints).
- qa-performance-engineer: **on request**. No database/N-tenant surface; relevant lenses are poll
  interval correctness (5-min floor), WS reconnect/backoff behavior, and card render cost at
  realistic instrument counts (tens, not thousands).
- qa-security-expert: **on request**, but dispatch automatically (per RULEBOOK/skill standing
  rule) whenever a diff touches credential handling (Finnhub `api_key`, Alpaca `key_id`/
  `secret_key`), the diagnostics redaction path, the unauthenticated static card file route, or
  the `marketsentry/history` WS command.
- qa-accessibility-expert: **on request**. No legal accessibility obligation is known for a
  personal HACS integration (TODO(ask owner) to confirm), but RTL/Hebrew correctness matters to
  the owner directly - fold that into qa-ux-expert's brief rather than a full standing audit.
- qa-developer: **on**. Fixes `qa:awaiting-fix` issues under the same CI gates (ruff, mypy
  --strict, pytest, Vitest, Playwright) the project already enforces.

## Always in scope

Whenever a provider module, `config_flow.py`, `__init__.py`'s detector/snapshot wiring, or
`entity.py`/`sensor.py`/`binary_sensor.py` changes:

- Credential storage and redaction (diagnostics download must not leak `api_key`/`secret_key`).
- Config-flow validation (`validate()` raising `InvalidAuth`/`CannotConnect` correctly, the
  provider-selection → credentials → instrument-subentry flow not skipping steps).
- `default_options_for_kind` / `_options_schema` / `EVENT_TYPES_BY_KIND` staying in sync for every
  instrument kind (outcome, stock, fx, crypto) - a kind missing from one of these silently drops
  detectors or device triggers rather than erroring.
- The card's primary-entity detection (`PRIMARY_TRANSLATION_KEYS` in `card/src/rows.js`) and
  kind-based rendering branches (`statusBadge`, `marketStateLabel`) - a new kind that falls through
  every branch renders an empty/wrong badge instead of failing loudly.

## Business outcomes

- Adding a provider account (config flow `user` step) creates one config entry with
  `CONF_PROVIDER` set and (if the provider needs credentials) validated credentials stored.
- Adding an instrument (subentry flow) creates one subentry, one HA device, and the kind-
  appropriate sensor/binary_sensor entities, and registers device triggers matching
  `EVENT_TYPES_BY_KIND[kind]`.
- A price update (poll or stream) writes the entity's state (throttled per
  `STATE_WRITE_MIN_INTERVAL_SEC`/`STATE_WRITE_MIN_DELTA`), appends to the history ring buffer, and
  evaluates every configured detector; a detector firing both fires an HA bus event
  `marketsentry_<type>` with the full payload (name/old/new/delta/url/...) and dispatches an
  internal signal the card/diagnostics can consume.
- The `marketsentry-card` bundle is auto-registered as a Lovelace resource on HA startup with no
  manual step; a card-only release does not require an HA restart (cache-busted via
  `?v=<integration.version>`), a backend release does.

## Security shape

- No multi-tenant isolation model - this is a single-user, single-HA-instance integration; there
  is no cross-customer boundary to test.
- Public/anonymous routes: the bundled `marketsentry-card.js` is served from
  `/marketsentry_static/marketsentry-card.js` via `async_register_static_paths` - confirm whether
  this requires an authenticated HA session or is reachable unauthenticated (TODO: verify; worth a
  security-expert pass). The one custom WS command, `marketsentry/history`, rides HA's own
  WebSocket auth (TODO: confirm no instrument data leaks pre-auth).
- Credentials held: Finnhub `api_key`; Alpaca `key_id` + `secret_key`. Stored in the config entry's
  `data` (HA's own storage, not this integration's). README claims diagnostics redact them -
  verify the redaction actually covers both Alpaca fields, not just one.
- No other PII is collected; tracked instruments and their prices are the only user data, and they
  reflect the owner's own choices, not third-party personal data.
- Third-party credentials: user-supplied Finnhub/Alpaca keys only, entered once per config entry,
  never logged (TODO: grep for accidental `_LOGGER` of raw credentials as a quick security check).

## Deliberate behaviour

- FX's Bank of Israel source has no `fetch_history` implementation (returns `[]`) - documented in
  README as pending SDMX date-range-filter verification, not a bug.
- (Resolved by ENH-009, issue #19) The list card's "change" column used to be a rough first-point-
  vs-last-point figure from the sparkline ring buffer; it now reads the backend's real `change_pp`/
  `change_pct` sensor attribute directly. The single-instrument detail card
  (`marketsentry-instrument-card.js`) still has the old sparkline-approximation pattern - out of
  ENH-009's stated scope, flagged as a possible follow-up, not yet filed.
- `stream_connected` binary sensor is an approximation ("the stream task is running"), not a
  live per-reconnect up/down signal - documented, not a bug.
- Several provider API facts (Finnhub WS shapes, Alpaca feed paths, Frankfurter base URL, BOI's
  SDMX series-key format, CoinGecko's endpoints) are explicitly flagged in code/README as
  unverified against live docs this project's sessions - treat a mismatch with the real API as a
  "needs verification" finding, not automatically a regression, and check `qa/knowledge/` /
  README before filing.

## Legal frame

TODO(ask owner). No regulatory frame has been confirmed. This is an MIT-licensed personal HACS
integration, not a product processing third-party customer data; the README's own disclaimer
("Unofficial, not affiliated with Polymarket, Finnhub, Alpaca, CoinGecko, the Bank of Israel or
any other provider... cannot trade, place orders, or touch a wallet or brokerage account") is the
closest thing to a stated legal posture. No standing legal-checklist plan exists yet.

## Accessibility

Standard: not formally adopted (TODO: ask owner whether WCAG 2.1 AA should be the bar even
without a legal mandate, given the card is real UI). No accessibility statement published. RTL
(Hebrew) correctness is the one accessibility-adjacent property known to matter to the owner
directly - see *Locale*.

## Scale target

Single HA instance; realistic instrument counts are tens (the owner's own live dashboard this
session had ~4-7 tracked instruments), not thousands. Performance findings should be judged
against "a home user adds 20-50 instruments across providers," not SaaS multi-tenant scale.

## Fix constraints

- `qa-developer` must keep `ruff check custom_components/marketsentry` and
  `mypy custom_components/marketsentry` (strict) clean, and the full `pytest tests` suite passing
  (config-flow subset only verifiable in CI on Linux, not locally on Windows - say so in the fix
  PR/commit if that subset wasn't run locally).
- Card fixes must keep `card` Vitest (`npm test`) and Playwright (`npx playwright test`) green;
  any visual change requires regenerating screenshot baselines with `--update-snapshots` AND a
  human/agent visually confirming the new baseline before committing it (never blind-accept a
  snapshot diff).
- No `console.log` in committed card code (owner's global preference, `~/.claude/CLAUDE.md`).
- Git convention (owner's global preference): small/bug-fix changes go directly on `master` with a
  new patch tag; anything larger goes on a feature branch merged to `master` with a new minor tag.
  Always run tests before committing; never skip hooks.
- Translation files (`custom_components/marketsentry/translations/*.json`) must keep identical key
  sets across all 8 languages - a key present in `en.json` but missing elsewhere fails HA's own
  translation loader silently for that language. Same invariant for `card/src/i18n.js`'s `STRINGS`
  object (enforced today by `card/test/i18n.test.js`'s parity test).

## Test ID series

- `CFG` - config flow / subentry flow (provider setup, instrument add/reconfigure).
- `PROV` - provider modules (Polymarket, Finnhub, Alpaca, CoinGecko, FX).
- `DET` - detector logic (threshold, move, daily-change, large-trade, volume-spike, resolved,
  closing-soon, market-open-gap, official-rate-published).
- `SENS` - sensor/binary_sensor entities, device/entity registry shape, diagnostics redaction.
- `TRIG` - device triggers / HA bus events.
- `CARD` - `marketsentry-card` / `marketsentry-instrument-card` (list + detail cards, editors).
- `STRAT` - the `custom:marketsentry` dashboard view strategy.
- `I18N` - translation parity and RTL rendering, backend and card.
- `BP` - the three shipped automation blueprints.
- `SEC` - security-shape checks (credential redaction, static-file auth, WS auth).
- `PERF` - poll interval, WS reconnect/backoff, card render cost.
- `UX` - config-flow usability, card editor usability, dashboard readability.

## Leak terms

- MarketSentry Pro
- marketsentry
- bareli/MarketSentry-Pro
- homeassistant.local
- Polymarket
- Finnhub
- Alpaca
- CoinGecko
- HACS
