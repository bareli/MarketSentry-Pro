# Claude Code update prompt: rename to MarketSentry Pro + multi-provider

Paste everything below this line into the running Claude Code session.

---

Spec update for the project you are building (currently "Polymarket-Manager-Pro", originally specified as "Polymarket Watch" / domain `polymarket_watch`). Two changes: (A) rename the project, (B) generalize it from Polymarket-only to a multi-provider market monitor. Everything in the original spec still applies unless overridden here.

## Step 0: checkpoint first

1. Stop at a clean point in your current task. Make sure tests that passed still pass.
2. If not a git repo yet, `git init`. Commit everything: `chore: checkpoint before rename to MarketSentry Pro`.
3. Give me a 5-line status: what is done, what is in progress, what is untested.

## A. Rename

Use these names everywhere (code, manifest, translations, tests, README, CI, card, comments):

| Item | Old (any variant you used) | New |
|---|---|---|
| Display name | Polymarket Manager Pro / Polymarket Watch | MarketSentry Pro |
| Repo / root folder | Polymarket-Manager-Pro | MarketSentry-Pro |
| HA domain + package folder | `polymarket_watch` (or whatever you used) | `marketsentry` |
| Path | `custom_components/<old>/` | `custom_components/marketsentry/` |
| Bus events | `polymarket_watch_<type>` | `marketsentry_<type>` |
| Services | `polymarket_watch.*` | `marketsentry.*` |
| WS command | `polymarket_watch/history` | `marketsentry/history` |
| Card element / file | `polymarket-watch-card` | `marketsentry-card` / `marketsentry-card.js` |
| Card type in YAML | `custom:polymarket-watch-card` | `custom:marketsentry-card` |
| Python logger / constants | `polymarket_watch` | `marketsentry` |

Rules:
- Use `git mv` for files/folders so history is kept.
- After renaming, run `grep -rniE "polymarket[_-]?(watch|manager)|Polymarket Manager|Polymarket Watch" .` (excluding `.git` and `node_modules`) and fix every hit. The word "Polymarket" must remain only where it refers to the Polymarket provider/API.
- `manifest.json`: domain `marketsentry`, name `MarketSentry Pro`, keep version but bump minor.
- `hacs.json`: name `MarketSentry Pro`.
- README title and all docs: "MarketSentry Pro: monitor prediction markets, stocks and exchange rates in Home Assistant and automate on price changes". State: unofficial, not affiliated with Polymarket, Finnhub, Alpaca, the Bank of Israel or any other provider.
- No config-entry migration needed (nothing released yet). Start config entry `VERSION = 1`, `MINOR_VERSION = 1`.
- Run the full test suite, ruff, mypy, hassfest, card build. Commit: `refactor: rename project to MarketSentry Pro`.
- Do NOT rename the root folder yourself while this session runs inside it. I will do it at the end (see Step F).

## B. Multi-provider architecture

Generalize from "market" to **instrument**: a Polymarket outcome, a stock ticker, or a currency pair.

```
custom_components/marketsentry/
  providers/
    __init__.py        registry: PROVIDERS = {"polymarket": ..., "finnhub": ..., "alpaca": ..., "fx": ...}
    base.py            Provider ABC + dataclasses
    polymarket.py      move existing api.py/ws.py logic here (behavior unchanged)
    finnhub.py         US stocks, WebSocket trades + REST quote/candles
    alpaca.py          US stocks, WebSocket IEX trades/quotes (optional provider)
    fx.py              exchange rates: Frankfurter (market mid) + Bank of Israel (official representative rate)
  detector.py          generic over Instrument (no provider-specific code)
  history.py, websocket_api.py, coordinator.py, entity.py, sensor.py, binary_sensor.py, event.py, ...
```

`providers/base.py`:

```python
class Provider(ABC):
    key: str                      # "polymarket", "finnhub", ...
    name: str
    requires_api_key: bool
    supports_streaming: bool
    async def validate(self, credentials) -> None: ...          # raise InvalidAuth / CannotConnect
    async def search(self, query: str, limit: int) -> list[InstrumentRef]: ...
    async def resolve(self, user_input: str) -> list[InstrumentRef]: ...  # URL, slug, ticker, pair
    async def fetch_snapshot(self, refs) -> dict[str, Quote]: ...
    async def fetch_history(self, ref, hours: int) -> list[PricePoint]: ...
    async def stream(self, refs, on_quote, on_trade, on_event) -> None: ...  # only if supports_streaming
```

Dataclasses: `InstrumentRef(provider, id, symbol, name, kind: Literal["outcome","stock","fx"], unit, url)`, `Quote(price, bid, ask, ts, market_state)`, `Trade(price, size, notional, side, ts)`, `ProviderEvent(type, data)`.

Shared rules: one streaming connection per provider (singleton), dynamic subscribe/unsubscribe, exponential backoff with jitter, REST polling fallback, per-provider rate limiting, the same 5 s / minimum-change state-write throttle as before.

### B1. Polymarket provider
Move the existing implementation behind the interface. No behavior change. Its `kind` is `outcome`, unit `%`. Provider-specific events: `resolved`, `closing_soon`.

### B2. Finnhub provider (US stocks, NASDAQ/NYSE)
- Requires the user's own free API key (config flow field, stored in entry data, redacted in diagnostics).
- WebSocket `wss://ws.finnhub.io?token=<key>`; subscribe `{"type":"subscribe","symbol":"AAPL"}`; trade messages `{"type":"trade","data":[{"p":price,"s":symbol,"t":ms,"v":volume}]}`. REST `/api/v1/quote` (c, d, dp, h, l, o, pc, t), `/api/v1/search`, `/api/v1/stock/candle` if available on free tier.
- These are from my knowledge, not freshly verified: **read the current official docs at finnhub.io/docs/api before coding** and adjust. Respect the free tier: about 60 REST calls/min and a WebSocket symbol limit (reported as 30, verify). Enforce the symbol limit in the config flow with a clear error.
- Free tier is personal, non-commercial use. Put that in the config flow description and README.
- Unit: the instrument's currency (USD), device_class monetary.

### B3. Alpaca provider (optional, US stocks)
- Requires user's API key ID + secret.
- WebSocket `wss://stream.data.alpaca.markets/v2/iex` (free Basic plan, IEX only, 30 symbols); auth `{"action":"auth","key":..., "secret":...}`, subscribe `{"action":"subscribe","trades":[...],"quotes":[...]}`. Paid SIP feed via option `feed: sip`.
- Verify against docs.alpaca.markets before coding. Clearly label IEX prices as "IEX feed, not consolidated" in the UI.

### B4. FX provider (exchange rates)
Two sources under one provider, user picks per pair:
- **Frankfurter** (`frankfurter.dev`, no key, daily mid-market rates, ILS supported). Verify the current base URL and endpoints from frankfurter.dev before coding. Poll every 60 min (rates change once a day; don't hammer it).
- **Bank of Israel official representative rate** (שער יציג), rates vs ILS. Research and use the official Bank of Israel public API (boi.org.il / its SDMX service); verify the endpoint, publication schedule and format before coding. Poll every 60 min on business days. Expose the publication date as an attribute.
- No API key. `kind` = `fx`, unit = quote currency (e.g. ILS per 1 EUR), 4 decimals.
- FX-specific event: `official_rate_published` (Bank of Israel publishes a new daily rate).

### B5. Do NOT add Yahoo Finance
It is an unofficial API with terms and stability issues. Leave it out.

## C. Detector changes (generic)

Same triggers as before, now for any instrument, configured per instrument in the options flow:
- `threshold_crossed` (absolute levels, hysteresis): for outcomes in %, for stocks/FX in price units.
- `price_move`: |change| ≥ X within N minutes. Express X in **percent** for stocks/FX (default 2 % in 60 min for stocks, 0.5 % in 24 h for FX) and in **percentage points** for Polymarket outcomes (default 5 pp in 60 min).
- `daily_change`: change vs previous close (stocks) / previous official rate (FX) ≥ X %.
- `large_trade`: notional ≥ USD X (Polymarket and stocks only).
- `volume_spike`: (Polymarket and stocks only).
- Stocks only: `market_open_gap` (open vs previous close ≥ X %), and suppress `price_move` outside regular hours unless the user enables extended hours. Expose `market_state` (pre, regular, post, closed) as a sensor; use the NYSE/NASDAQ calendar, including US holidays, from a maintained source or a bundled table you can update, with tests for DST changes.
- Cooldowns as before.
- Event payload adds `provider`, `kind`, `symbol`, `unit`, `change_pct` alongside existing fields.

## D. Config flow changes

1. First step: choose provider (Polymarket, Stocks via Finnhub, Stocks via Alpaca, Exchange rates).
2. Credentials step only for providers that need a key; validate with a live call; one config entry per provider account. Instruments are added as **subentries** (HA config subentries) so the user adds/removes tickers, pairs and markets without re-entering keys. If subentries are not workable for some reason, explain why and propose an alternative before implementing it.
3. Instrument step: search box (provider `search`) or paste URL/ticker/pair; show a confirmation list.
4. Options per instrument: thresholds, move %, window, cooldown, extended hours (stocks).
5. `he` and `en` translations for all new strings.

## E. Card changes (`marketsentry-card`)

- Rows for all instruments across providers. Group or filter by provider/kind (`group_by: provider|kind|none`, `kinds: [outcome, stock, fx]`).
- Formatting per kind: outcomes in %, stocks with currency symbol and 2 decimals, FX with 4 decimals ("EUR/ILS 3.9123"), change in pp for outcomes and % for stocks/FX.
- Stocks show a market-state chip (Pre, Open, After, Closed). FX shows source chip (Market / Bank of Israel official) and publication date.
- Status badge per kind: outcomes Live/Closing soon/Closed/Resolved; stocks Open/Closed; FX Updated today / Stale.
- Sparkline works for all kinds (from the ring buffer via `marketsentry/history`).
- Link out: Polymarket market page, stock page on the provider site, nothing for FX.
- Update visual editor, Vitest helpers and the Playwright screenshots (light, dark, RTL) with mixed instruments.

## F. Finish

1. All tests, ruff, mypy, hassfest, HACS validation, card build green.
2. README: providers table (what's free, what needs a key, limits, terms), example automations for each kind, for example:
   - Notify when EUR/ILS official rate goes above 4.10.
   - TTS when NASDAQ:NVDA moves 3 % in 60 min during market hours.
   - Flash a light when a Polymarket outcome crosses 60 %.
3. Commit: `feat: multi-provider MarketSentry Pro (Polymarket, Finnhub, Alpaca, FX)`.
4. Update any absolute paths in configs/scripts/CI that contain `Polymarket-Manager-Pro` to be relative so the folder rename can't break them.
5. Print a final summary: what changed, any API facts you could not verify, and the exact commands for me to rename the root folder after I exit this session:
   - from the parent directory: `mv Polymarket-Manager-Pro MarketSentry-Pro`
   - if a GitHub remote exists: rename the repo on GitHub and run `git remote set-url origin <new-url>`.

Ask me before adding any dependency, any provider beyond these four, or any feature beyond this spec.
