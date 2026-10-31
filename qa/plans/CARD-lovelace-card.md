# CARD - marketsentry-card / marketsentry-instrument-card

Source: `card/src/`. Offline-testable: Vitest (pure logic) + Playwright (behavioral + visual
regression against `card/e2e/harness.html` and `harness-editor.html`, mocked `hass`). No live HA
needed for most of this plan; a live pass is only needed to confirm the bundle actually registers
as a Lovelace resource and renders inside a real HA frontend (see `qa/CLAUDE.md` §1 gating).

- **CARD-01** List card: one row per tracked instrument, grouped by `none`/`provider`/`kind`,
  filtered by `kinds`. Group label text is correct per kind including `crypto` ("Cryptocurrencies"
  in en) and per provider including `coingecko` ("CoinGecko"). **Reviewed 2026-10-31
  (qa-ux-expert):** verified independently green (`npx playwright test`, 12/12). Light/dark/RTL
  baselines (`card-light-win32.png`/`card-dark-win32.png`/`card-rtl-win32.png`) look correct -
  group labels, badges, chips and the probability bar all mirror correctly in RTL. **ENH-001
  filed** (issue #8, `qa:awaiting-decision`): the zero-instrument empty state
  ("No tracked instruments match this card's filters") reads as a filter problem rather than a
  first-run cue; the view-strategy's own empty state already has better wording to reuse.
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
  confirm that reads as "clean" rather than "missing a stat". **Reviewed 2026-10-31
  (qa-ux-expert):** crypto's leaner layout reads as intentionally clean, no issue there.
  **UX-001 filed** (issue #4, MEDIUM, `qa:awaiting-decision`): the richer chart's min-range label
  overlaps the sparkline's own line/area-fill at both 320px and desktop widths, LTR and RTL alike
  - reproduced with the project's own realistic mock history, not an edge case (see
  `qa/evidence/UX-001-*.png`). **BUG-002 filed** (issue #3, LOW): `getStubConfig()` can hand
  `setConfig()` a config its own author rejects (empty-string `entity` when zero instruments are
  tracked yet), throwing instead of reaching the existing graceful `empty_instrument` placeholder
  - reproduced directly against the built bundle in the Playwright harness.
- **CARD-05** Both card editors (`marketsentry-card-editor`, `marketsentry-instrument-card-editor`)
  keep input focus and cursor position across every keystroke, even under HA's real
  setConfig-echo-back behavior (regression-covered by `card/e2e/editor-focus.spec.js` - this was a
  real, user-reported bug earlier in the project; don't let it regress silently in a future
  editor change).
- **CARD-06** i18n: every string in `card/src/i18n.js` has the exact same key set across all 8
  languages (enforced by `card/test/i18n.test.js`); `resolveLang()` falls back exact → base
  language → English for an unsupported region/language code; Hebrew renders correctly in RTL
  (`card/e2e/screenshots.spec.js`'s Hebrew test) - this only exercises the list card + one stock
  detail card in Hebrew, not every kind/every language combination. **Reviewed 2026-10-31
  (qa-ux-expert):** captured fresh screenshots of *real* Hebrew content in RTL (not just the
  mirrored-English `card-rtl` baseline, which exercises direction but not actual Hebrew text) at
  both desktop and 320px widths (`qa/evidence/UX-001-hebrew-rtl-full-*.png` - named for the UX-001
  session, not a separate finding). Layout holds up: group labels right-align correctly, chips/
  badges wrap sensibly, Western numerals stay LTR within the RTL flow as expected, no overflow or
  clipping with the real (long) Hebrew strings in `i18n.js`. No defect found in the Hebrew/RTL
  render itself; the only chart legibility issue found (UX-001) reproduces identically in English
  and Hebrew, so it isn't an RTL-specific defect. Note: the project's own visual-regression suite
  still only has a mirrored-English RTL baseline (`card-rtl-win32.png`), not a real-Hebrew-content
  one - worth a baseline addition at some point so a future Hebrew string change (e.g. a long
  translated instrument name) gets caught by `playwright test` instead of only by manual review.
- **CARD-07** Auto-dashboard view strategy (`custom:marketsentry` → `ll-strategy-view-marketsentry`):
  `buildStrategyView()` logic is unit-tested (`card/test/view-strategy.test.js`), but the actual
  custom-element wrapper/HA strategy-resolution wiring has never been smoke-tested against a real
  HA frontend this project's sessions - highest-priority CARD item for a live pass. **Reviewed
  2026-10-31 (qa-ux-expert), code review only - UNVERIFIED against a live HA frontend, no live
  access this session:** `marketsentry-view-strategy.js`/`strategy-view-logic.js` match the
  documented contract as far as can be told from source - `static async generate(config, hass)` on
  a `customElements.define("ll-strategy-view-marketsentry", ...)`-registered element, returning a
  view config (`{cards: [...]}`), safe-navigated `config` access, and a defensive `buildRows()`
  that returns `[]` rather than throwing when `hass` is null/entities aren't populated yet (so the
  empty-state markdown card should render even if the strategy runs before `hass` has settled).
  One thing flagged but **not filed** (can't confirm HA's exact view-strategy field contract
  without a live frontend to test against): `config?.title` is only ever applied to the embedded
  `marketsentry-card`'s own title, never to the returned view config's own `title` - if HA's view
  strategies honor a top-level `title` for the view/tab name (the way a normal view config does),
  a user who sets `strategy: {type: custom:marketsentry, title: "My Markets"}` expecting the
  dashboard tab itself to read "My Markets" would see the card titled that but the tab left at its
  default. Needs a live check before treating as a real gap; noted here so it isn't lost.
- **CARD-08** A card-only release doesn't require an HA restart (cache-busted via the integration
  version query string); a backend release does - confirm this still holds after any future change
  to how the static path is registered. **Not reviewed this session** (no change to the static
  path registration in this diff; out of this pass's budget to re-verify from scratch).
