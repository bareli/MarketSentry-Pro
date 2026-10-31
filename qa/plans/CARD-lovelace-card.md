# CARD - marketsentry-card / marketsentry-instrument-card

Source: `card/src/`. Offline-testable: Vitest (pure logic) + Playwright (behavioral + visual
regression against `card/e2e/harness.html` and `harness-editor.html`, mocked `hass`). No live HA
needed for most of this plan; a live pass is only needed to confirm the bundle actually registers
as a Lovelace resource and renders inside a real HA frontend (see `qa/CLAUDE.md` §1 gating).

- **CARD-01** List card: one row per tracked instrument, grouped by `none`/`provider`/`kind`,
  filtered by `kinds`. Group label text is correct per kind including `crypto` ("Cryptocurrencies"
  in en) and per provider including `coingecko` ("CoinGecko").
- **CARD-02** Row rendering is kind-correct: outcome gets a green/red probability bar; stock/fx/
  crypto get a value+change+sparkline row. Status badge per kind: outcome resolved/closed/
  closing-soon/live, stock open/closed (from `marketState`), fx updated-today/stale, **crypto
  always "live"** (24/7, no session) - confirm this reads sensibly rather than just being a
  placeholder.
- **CARD-03** Link-out (`safeUrl`) only renders http(s) hrefs, drops any other scheme; outcome/
  stock/crypto rows link out where a URL exists, fx rows never do (no per-rate URL).
- **CARD-04** Single-instrument detail card: outcome view (probability bar + volume/liquidity
  stats + end date), generic view (stock/crypto/fx: big value + change + richer sparkline with
  area fill/marker dot/min-max range labels). Stock-only "Prev close" stat; fx-only "Published"
  footer. Crypto gets neither (shares the generic renderer but has no stock/fx-specific extras) -
  confirm that reads as "clean" rather than "missing a stat".
- **CARD-05** Both card editors (`marketsentry-card-editor`, `marketsentry-instrument-card-editor`)
  keep input focus and cursor position across every keystroke, even under HA's real
  setConfig-echo-back behavior (regression-covered by `card/e2e/editor-focus.spec.js` - this was a
  real, user-reported bug earlier in the project; don't let it regress silently in a future
  editor change).
- **CARD-06** i18n: every string in `card/src/i18n.js` has the exact same key set across all 8
  languages (enforced by `card/test/i18n.test.js`); `resolveLang()` falls back exact → base
  language → English for an unsupported region/language code; Hebrew renders correctly in RTL
  (`card/e2e/screenshots.spec.js`'s Hebrew test) - this only exercises the list card + one stock
  detail card in Hebrew, not every kind/every language combination.
- **CARD-07** Auto-dashboard view strategy (`custom:marketsentry` → `ll-strategy-view-marketsentry`):
  `buildStrategyView()` logic is unit-tested (`card/test/view-strategy.test.js`), but the actual
  custom-element wrapper/HA strategy-resolution wiring has never been smoke-tested against a real
  HA frontend this project's sessions - highest-priority CARD item for a live pass.
- **CARD-08** A card-only release doesn't require an HA restart (cache-busted via the integration
  version query string); a backend release does - confirm this still holds after any future change
  to how the static path is registered.
