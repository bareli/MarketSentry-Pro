# Claude Code prompt: Polymarket Watch, a Home Assistant custom integration

Paste everything below this line into Claude Code.

---

Build a production-quality Home Assistant custom integration called **Polymarket Watch** (domain: `polymarket_watch`). It monitors Polymarket prediction markets read-only and lets HA automations trigger on market changes. It will be distributed through HACS (which becomes the built-in HA "Marketplace" from HA 2026.11), so follow current HA integration quality-scale rules (aim for Silver, design for Gold).

## Hard constraints

- READ-ONLY. No trading, no wallet, no private keys, no order placement, no authenticated endpoints. Only public, no-auth Polymarket endpoints.
- Fully async. Use `async_get_clientsession(hass)` for REST and `session.ws_connect()` (aiohttp) for WebSocket. No `requests`, no blocking I/O, no extra dependencies unless strictly needed.
- Python 3.13, target HA 2026.10+. Type hints everywhere, `ruff` clean, `mypy --strict` clean on the integration package.
- UI-only configuration (config flow + options flow). No YAML config.
- Translations: `en` and `he` (Hebrew).
- Units: probabilities in `%` (0-100, 1 decimal), money in `USD` (device_class monetary).

## Polymarket API facts (from docs.polymarket.com, verify against live responses)

Gamma API (metadata), base `https://gamma-api.polymarket.com`:
- `GET /events/slug/{slug}` returns an Event with `id, slug, title, active, closed, ended, endDate, volume, volume24hr, liquidity, negRisk, markets[]`.
- `GET /markets/slug/{slug}` returns a Market with `id, question, conditionId, slug, outcomes, outcomePrices, clobTokenIds, volumeNum, volume24hr, liquidityNum, endDate, active, closed, closedTime, umaResolutionStatus, acceptingOrders, bestBid, bestAsk, lastTradePrice`.
- `outcomes`, `outcomePrices`, `clobTokenIds` are typed as strings in the schema and are most likely JSON-encoded arrays. Parse defensively: if value is `str`, `json.loads` it; if already a list, use as is. Write a unit test for both shapes.
- Rate limits: `/markets` 300 req/10s, `/events` 500 req/10s (per IP, throttled not rejected).

CLOB REST, base `https://clob.polymarket.com` (no auth for reads):
- `GET /midpoint?token_id=` returns `{"mid_price": "0.45"}` (string).
- `GET /price?token_id=&side=BUY|SELL` returns `{"price": 0.45}`.
- `GET /book?token_id=` returns `bids/asks [{price,size}]`, `last_trade_price`, `tick_size`.
- `GET /prices-history?market=<token_id>&interval=1h|6h|1d|1w|1m|all|max&fidelity=<minutes>` returns `{"history":[{"t":unix,"p":float}]}`. Note the param is `market`, not `token_id`.

CLOB market WebSocket, `wss://ws-subscriptions-clob.polymarket.com/ws/market`:
- After connect send: `{"assets_ids": ["<token_id>", ...], "type": "market", "custom_feature_enabled": true}`.
- Add/remove tokens without reconnecting: `{"operation": "subscribe"|"unsubscribe", "assets_ids": [...]}`.
- Send text `PING` every 10 s; server replies `PONG`.
- Event types (field `event_type`): `book`, `price_change` (`price_changes[]` with `asset_id, price, size, side, best_bid, best_ask`), `last_trade_price` (`asset_id, price, size, side, timestamp`), `tick_size_change`, `best_bid_ask` (`asset_id, best_bid, best_ask, spread`), `market_resolved` (`market, assets_ids, winning_asset_id, winning_outcome`), `new_market`. The last three require `custom_feature_enabled: true`.

Resolution: Gamma `closed`, `umaResolutionStatus`, `closedTime`; WS `market_resolved`; optional `GET https://data-api.polymarket.com/v2/resolutions?condition=<conditionId>` (`status`, `resolved_at`, `payouts`).

## Architecture

```
custom_components/polymarket_watch/
  __init__.py          setup/unload, runtime_data
  manifest.json        iot_class: cloud_push, integration_type: service
  config_flow.py       config + options + reconfigure
  const.py
  api.py               typed REST client (Gamma + CLOB), no HA imports
  ws.py                WebSocket manager, no HA imports beyond callbacks
  models.py            dataclasses: Market, Outcome, Quote, Trade
  coordinator.py       DataUpdateCoordinator for Gamma metadata + REST fallback
  detector.py          pure-Python change detection (thresholds, moves, spikes), unit-testable
  entity.py            base entity, one HA device per tracked market
  sensor.py
  binary_sensor.py
  event.py             HA `event` platform entities
  device_trigger.py    UI device triggers
  services.yaml / services.py
  diagnostics.py       redact nothing sensitive (there is none), include WS status
  strings.json, translations/en.json, translations/he.json
  icons.json
hacs.json
tests/ (pytest-homeassistant-custom-component, recorded JSON fixtures)
```

- **Config entry = one tracked market or event.** User pastes a Polymarket URL (`polymarket.com/event/<slug>` or `/market/<slug>`) or a slug. Parse it, fetch from Gamma, show the question(s) for confirmation. For a multi-market event, let the user pick which sub-markets to track (multi-select).
- **One shared WebSocket** for all config entries (singleton in `hass.data`), subscribing/unsubscribing token IDs dynamically. Reconnect with exponential backoff (1 s up to 5 min, with jitter). If WS is down more than 60 s, fall back to REST polling `/midpoint` every 60 s until WS recovers. Expose WS health as a diagnostic binary sensor.
- **Gamma metadata coordinator** per entry, every 5 min (volume, liquidity, closed, endDate, resolution status).
- **Price source of truth:** midpoint from `best_bid_ask` / `price_change` best_bid+best_ask; `last_trade_price` stored separately.
- **Recorder protection:** throttle entity state writes to at most once per 5 s per entity, and only when the value changes by at least 0.1 percentage points. Put high-churn attributes (bid, ask, spread) in attributes excluded from recorder via `_unrecorded_attributes`.

## Entities (per tracked market, grouped under one device named after the question)

Sensors:
- `<outcome> probability` (%), one per outcome, attributes: token_id, best_bid, best_ask, spread, last_update.
- Last trade price (%), 24h volume (USD), total volume (USD), liquidity (USD), spread (pp, diagnostic).
- End date (device_class timestamp).
- Resolution status (enum: open, proposed, disputed, resolved, closed).
- Winning outcome (string, unknown until resolved).

Binary sensors: closed, accepting orders, WebSocket connected (diagnostic, integration-level).

Event entities (HA `event` platform) with event_types: `threshold_crossed`, `price_move`, `large_trade`, `volume_spike`, `resolved`, `closing_soon`.

## Change detection (detector.py, pure functions, 100% unit-tested)

Options flow per entry (with sane defaults):
- Thresholds list per outcome, e.g. `[30, 50, 70]` %. Fire `threshold_crossed` with direction up/down. Hysteresis 0.5 pp to avoid flapping.
- Price move: fire `price_move` when |change| ≥ X pp (default 5) within a rolling window of N minutes (default 60).
- Large trade: fire `large_trade` when price × size ≥ USD X (default 10,000).
- Volume spike: 24h volume grows by ≥ X % (default 50) between metadata polls.
- Closing soon: fire once when time to endDate ≤ H hours (default 24).
- Resolved: fire once on `market_resolved` or Gamma closed+resolved, with winning outcome.
- Cooldown per event type per outcome (default 15 min) so automations aren't spammed.

Every detection does three things: triggers the event entity, fires a bus event `polymarket_watch_<type>` with payload `{entry_id, market_slug, question, outcome, token_id, old, new, delta_pp, direction, window_min, url}`, and is available as a device trigger in the automation UI.

## Services (with response data where useful)

- `polymarket_watch.get_price_history` (target device, outcome, interval, fidelity) returns `{history: [{t, p}]}` via `SupportsResponse.ONLY`, for scripts and LLM/Assist use.
- `polymarket_watch.refresh` forces metadata refresh.
- `polymarket_watch.search_markets` (query, limit) returns matching markets from Gamma `/public-search`, response only.

## Quality and delivery

- Tests: config flow (URL, slug, invalid, multi-market event), parser for string vs list fields, detector (thresholds with hysteresis, windowed moves, cooldown), WS manager (subscribe, resubscribe after reconnect, PING loop, fallback to REST), entity state throttling. Target ≥ 90% coverage on detector/api/ws.
- Repairs issue if a tracked market 404s or is archived.
- `diagnostics.py` with WS state, subscribed token count, last message age.
- README with: what it does, screenshots placeholders, example automations (notify when "Yes" crosses 60%; flash a light on resolution; daily TTS summary), the read-only disclaimer, and a note that Polymarket's terms and local regulations apply to the user.
- `hacs.json`, GitHub Actions for `hassfest`, HACS validation, ruff, pytest.
- Do NOT use Polymarket's logo. Use a neutral icon (`mdi:chart-line`) and state "unofficial, not affiliated with Polymarket" in README and manifest-adjacent docs.

## Work plan

1. Scaffold the structure, `manifest.json`, `hacs.json`, CI.
2. `api.py` + `models.py` + parser tests with fixtures.
3. `detector.py` + full tests (do this before any HA wiring).
4. `ws.py` + tests with a fake WS server.
5. Config/options flow + tests.
6. Coordinator, entities, event platform, device triggers, services.
7. Diagnostics, repairs, translations (en, he), README with example automations.
8. Run ruff, mypy, pytest, hassfest locally; fix everything; then summarize what was built and any API assumptions that need live verification.

Ask me before adding any dependency or any feature beyond this spec.
