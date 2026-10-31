# marketsentry-card

Lovelace card for MarketSentry Pro. Shows one row per tracked instrument
(Polymarket outcome, stock, FX pair) across every configured provider
account, grouped/filtered by provider or kind.

No framework dependency: a vanilla Web Component (`HTMLElement` +
`attachShadow`), bundled with [esbuild](https://esbuild.github.io/) to a
single ES module. The build output is committed to
`../custom_components/marketsentry/www/marketsentry-card.js` — that's
what ships to users; `custom_components/marketsentry/__init__.py`
registers it automatically as a Lovelace resource (`add_extra_js_url` +
`async_register_static_paths`) on startup, so there's nothing for the
end user to add manually.

## How it gets its data

- **The row list** comes straight from `hass.entities` / `hass.devices` /
  `hass.states` (the standard way a card reads entity data), filtered to
  `platform === "marketsentry"` and keyed off each kind's primary sensor
  (`translation_key` of `probability`/`price`/`rate`). Each primary
  sensor exposes `kind`/`provider`/`url` as `extra_state_attributes`
  specifically so the card can group/filter/link without a custom round
  trip (see `entity.py`'s `card_attributes` on the Python side).
- **Sparklines** come from a custom WS command, `marketsentry/history`,
  backed by an in-memory ring buffer (`history.py` /
  `websocket_api.py`) — independent of the recorder and of any
  provider's rate-limited history API.

## Layout

```
src/
  format.js, grouping.js, sparkline.js, rows.js   pure logic, unit-tested
  marketsentry-card.js                             the card custom element
  marketsentry-card-editor.js                      the visual editor
  index.js                                         bundle entry point
test/            Vitest unit tests for the pure logic
e2e/              Playwright: a static harness page (mocked hass, mixed
                  instruments) + screenshots (light/dark/RTL) and a few
                  behavioral assertions (row count, link-out)
build.mjs         esbuild bundler -> ../custom_components/.../www/
```

## Development

```bash
npm install
npm run build        # rebuild the shipped dist file after any src/ change
npm test              # Vitest: format/grouping/sparkline/rows (36 tests)
npx playwright install chromium   # once
npx playwright test               # light/dark/RTL screenshots + behavior
```

Always run `npm run build` after changing anything under `src/` — the
committed `www/marketsentry-card.js` is what ships, not the source.

Playwright isn't wired into the Python CI workflow (it needs a browser
download); run it locally when touching the card's rendering/layout.
`e2e/screenshots.spec.js-snapshots/*.png` are the committed baselines —
re-run with `--update-snapshots` after an intentional visual change and
review the diff before committing.

## Known gaps

- No automated check that the committed `www/marketsentry-card.js`
  matches a fresh `npm run build` of `src/` (CI doesn't rebuild and
  diff it). Rebuild and commit manually after any source change.
- The card's reliance on `hass.entities`/`hass.devices` having
  `platform`/`device_id`/`translation_key` fields matches the
  documented/standard HA frontend shape used throughout the HACS card
  ecosystem, but wasn't verified against a live running Home Assistant
  frontend session (none was available in this project's sessions).
