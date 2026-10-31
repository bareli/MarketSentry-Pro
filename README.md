# MarketSentry Pro

MarketSentry Pro: monitor prediction markets, stocks and exchange rates in Home Assistant and automate on price changes.

> **Unofficial, not affiliated with Polymarket, Finnhub, Alpaca, the Bank of Israel or any other provider.** This integration only reads public endpoints with each provider's own no-auth or free-tier access. It cannot trade, place orders, or touch a wallet or brokerage account. Each provider's terms of service (Finnhub's free tier is personal/non-commercial use only) and your local regulations apply to how you use this data.

A read-only Home Assistant integration that tracks instruments across four providers and lets your automations react to price moves, thresholds, large trades, and more.

## What it does

- **Polymarket** — prediction market outcomes. Live probability, best bid/ask, spread, last trade price, volume, liquidity, end date, and resolution status, pushed over Polymarket's WebSocket feed.
- **Finnhub** — US stocks (free tier, personal/non-commercial use, your own API key). Live trades over WebSocket.
- **Alpaca** — US stocks via the free IEX feed (optional, your own API key pair). IEX prices only, not the consolidated tape.
- **FX** — exchange rates from Frankfurter (market mid-rate, no key) or the Bank of Israel's official daily representative rate (שער יציג, no key).
- Every REST-polling provider's prices refresh at least every 5 minutes regardless of streaming state, so sensors stay current even if a WebSocket connection drops.
- Fires HA events and UI-configurable device triggers per instrument kind: `threshold_crossed`, `price_move`, `daily_change` (stocks/FX), `large_trade` (Polymarket/stocks), `volume_spike`/`closing_soon`/`resolved` (Polymarket), `market_open_gap` (stocks), `official_rate_published` (FX, Bank of Israel source).
- Services for price history lookups and instrument search, usable from scripts, automations, or the Assist API for LLM tooling.

## Installation (HACS)

1. HACS > Integrations > search for "MarketSentry Pro" (or add this repository as a custom repository).
2. Install, then restart Home Assistant.
3. Settings > Devices & services > Add integration > "MarketSentry Pro".

## Setting up a provider account and tracked instruments

One config entry = one provider account. Credentials (if the provider needs any) are entered once; instruments are added afterward as **subentries** under that entry, so adding/removing an instrument never re-asks for a key.

1. **Add integration > MarketSentry Pro**, pick a provider: Polymarket, Finnhub, Alpaca, or Exchange rates.
2. Polymarket and Exchange rates need no credentials. Finnhub needs an API key; Alpaca needs a key ID + secret (and a feed choice, default `iex`). Credentials are validated live.
3. On the new entry's page, use **Add instrument** (a subentry) and paste:
   - a Polymarket URL/slug (`polymarket.com/event/...` or `/market/...`), or free text to search,
   - a stock ticker (Finnhub/Alpaca), or free text to search (Finnhub only — Alpaca has no search, paste an exact ticker),
   - an FX pair like `EUR/ILS` (Frankfurter market rate) or `EUR/ILS/boi` (Bank of Israel official rate).
4. If a Polymarket market has multiple outcomes or a search returns several matches, pick one; run **Add instrument** again for any others.
5. Confirm and set per-instrument thresholds, move/daily-change sensitivity, large-trade size, cooldown, etc. (defaults are sensible per kind). Edit them later via the subentry's **Reconfigure**.

Each instrument becomes its own device with its own entities and its own device triggers (the trigger list shown in the UI matches what that instrument's kind can actually fire).

## Example automations

**Notify when a Polymarket outcome crosses 60%:**

```yaml
automation:
  - alias: "Notify when Yes crosses 60%"
    trigger:
      - platform: event
        event_type: marketsentry_threshold_crossed
        event_data:
          symbol: "Yes"
          direction: up
    action:
      - service: notify.mobile_app
        data:
          message: "{{ trigger.event.data.name }} just crossed a threshold"
```

**TTS when a stock moves fast during market hours:**

```yaml
automation:
  - alias: "NVDA fast move"
    trigger:
      - platform: event
        event_type: marketsentry_price_move
        event_data:
          symbol: "NVDA"
    action:
      - service: tts.speak
        data:
          entity_id: tts.home_assistant_cloud
          media_player_entity_id: media_player.kitchen
          message: "NVDA moved {{ trigger.event.data.change_pct | round(1) }} percent"
```

**Notify when the Bank of Israel publishes a new EUR/ILS rate above a level:**

```yaml
automation:
  - alias: "EUR/ILS official rate published"
    trigger:
      - platform: event
        event_type: marketsentry_official_rate_published
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.new > 4.10 }}"
    action:
      - service: notify.mobile_app
        data:
          message: "EUR/ILS official rate: {{ trigger.event.data.new }}"
```

**Flash a light when a Polymarket market resolves:**

```yaml
automation:
  - alias: "Flash light when a tracked market resolves"
    trigger:
      - platform: event
        event_type: marketsentry_resolved
    action:
      - service: light.turn_on
        target:
          entity_id: light.office
        data:
          flash: long
          color_name: green
```

You can also build these as device triggers in the UI without writing YAML — each instrument's device lists only the trigger types that apply to its kind.

## Services

- `marketsentry.get_price_history` — historical price points for one tracked instrument (device, hours). Returns response data.
- `marketsentry.refresh` — force an immediate price refresh for a tracked instrument's provider account.
- `marketsentry.search_instruments` — search a provider by free text (provider, query, limit). Returns response data; usable from Assist/LLM tooling.

## Diagnostics

Each config entry exposes a diagnostics download (Settings > Devices & services > MarketSentry Pro > entry > Download diagnostics) with provider/stream connection state and per-instrument quote state. Finnhub/Alpaca credentials in the entry's stored data are redacted; every price endpoint itself is public.

## Limitations

- Read-only by design. No trading, no wallet/brokerage integration, no order placement.
- Streaming connection health is tracked per provider account, not finely per-reconnect (each provider's own `stream()` loop handles its own reconnect/backoff internally without reporting intermediate transitions); the "stream connected" binary sensor is an approximation of "the stream task is running," not a live up/down signal.
- No frontend card yet (`marketsentry-card` from the original spec isn't built).
- Some external API facts (noted per-provider below) weren't independently verified against live docs in this project's sessions; verify before relying on them in production.

## Development

```bash
pip install -r requirements_test.txt
ruff check custom_components/marketsentry
mypy custom_components/marketsentry
pytest tests
```

Config-flow and subentry-flow tests need the full `hass` test fixture
(`pytest-homeassistant-custom-component`), which imports `homeassistant.runner`
→ the POSIX-only `fcntl` module — they run in CI (Linux) but not natively on
Windows. Everything else (`detector`, `models`, `api`, `ws`, `market_calendar`,
all four `providers/*`) is plain Python/aiohttp and runs anywhere:

```bash
pytest tests --ignore=tests/config_flow -p no:homeassistant
```

## Build status / what to verify before production use

**Landed and wired into HA:** the `Provider` interface and all four
providers (`providers/base.py`, `polymarket.py`, `finnhub.py`, `alpaca.py`,
`fx.py`); a generalized `detector.py` (percent vs. percentage-point
`price_move`, `DailyChangeDetector`, `MarketOpenGapDetector`,
`OfficialRatePublishedDetector`); `market_calendar.py` (NYSE/NASDAQ session
state, bundled 2025-2027 holiday table); the config flow (provider +
credentials) and instrument config *subentries* (add/search/confirm/
reconfigure); the generic `ProviderSnapshotCoordinator` + streaming glue in
`__init__.py`; kind-conditional `sensor`/`binary_sensor`/`event` platforms;
`device_trigger.py`; `services.py`; en/he translations. 98 unit tests pass;
ruff and mypy --strict are clean. The subentry-based config flow itself
(the part needing the full `hass` fixture) is written against this
session's installed Home Assistant 2026.2.3 and verified by directly
inspecting that package's real APIs (`ConfigSubentryFlow`,
`AddConfigEntryEntitiesCallback`, `DeviceEntry.config_entries_subentries`)
rather than guessed, but hasn't been smoke-tested against a running HA
instance.

**Not built:** the `marketsentry-card` frontend (Lit/JS, Vitest, Playwright
screenshots, visual editor) — a separate toolchain this project hasn't
started.

**API facts flagged as unverified in each provider's module docstring**
(a research-fetch tool failed this session on most sources; one, Alpaca's
streaming-market-data page, was confirmed live). Verify before relying on
these in production:
- Finnhub: WS subscribe/trade message shapes, REST `/quote` and `/search`
  field names, free-tier WS symbol limit (~30).
- Alpaca: the exact stream feed path/value (`iex` vs `sip`), trade message
  field names (the quote message shape WAS confirmed live), REST
  market-data endpoint paths, free-tier WS symbol limit.
- Frankfurter: base URL (`api.frankfurter.dev/v1` vs the older `.app`
  domain), `base`/`symbols` vs `from`/`to` parameter names.
- Bank of Israel: the SDMX series-key format (assumed `RER_<CCY>_ILS`) and
  the `c[DATA_TYPE]=OF00` filter syntax — taken from BOI's own published
  guide, not a live test call. `fetch_history` for this source isn't
  implemented yet, pending that verification.
