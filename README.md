# Polymarket Watch

A read-only Home Assistant integration that tracks [Polymarket](https://polymarket.com) prediction markets and lets your automations react to price moves, large trades, volume spikes, closing deadlines, and resolutions.

> **Unofficial, not affiliated with Polymarket.** This integration only reads public, no-auth Polymarket endpoints. It cannot trade, place orders, or touch a wallet. Polymarket's terms of service and your local gambling/prediction-market regulations apply to how you use this data.

## What it does

- Paste a Polymarket event or market URL (or just the slug) and the integration tracks it.
- Live probability, best bid/ask, spread, and last trade price for every outcome, pushed over Polymarket's WebSocket feed (falls back to REST polling if the socket drops).
- Volume, liquidity, end date, and resolution status, refreshed every 5 minutes.
- Fires HA events and UI-configurable device triggers when:
  - a probability crosses a threshold you set (e.g. "Yes" crosses 60%),
  - price moves fast within a time window,
  - a large trade prints,
  - 24h volume spikes,
  - the market is closing soon,
  - the market resolves.
- Services for price history lookups and market search, usable from scripts, automations, or the Assist API for LLM tooling.

![Screenshot: device page for a tracked market](docs/screenshots/device-page.png)
![Screenshot: config flow market confirmation](docs/screenshots/config-flow.png)

## Installation (HACS)

1. HACS > Integrations > search for "Polymarket Watch" (or add this repository as a custom repository).
2. Install, then restart Home Assistant.
3. Settings > Devices & services > Add integration > "Polymarket Watch".

## Setting up a tracked market

1. Paste a URL like `https://polymarket.com/event/will-x-happen` or `https://polymarket.com/market/will-y-happen`, or just the slug.
2. If it's a multi-market event, pick which sub-markets to track; each becomes its own device.
3. Confirm the question, and the integration starts tracking.
4. Open the entry's **Configure** page to tune thresholds, move/volume-spike sensitivity, large-trade size, closing-soon window, and the cooldown between repeated alerts.

## Example automations

**Notify when "Yes" crosses 60%:**

```yaml
automation:
  - alias: "Notify when Yes crosses 60%"
    trigger:
      - platform: event
        event_type: polymarket_watch_threshold_crossed
        event_data:
          outcome: "Yes"
          direction: up
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.threshold == 60 }}"
    action:
      - service: notify.mobile_app
        data:
          message: "{{ trigger.event.data.question }}: Yes just crossed 60%"
```

**Flash a light on resolution:**

```yaml
automation:
  - alias: "Flash light when a tracked market resolves"
    trigger:
      - platform: event
        event_type: polymarket_watch_resolved
    action:
      - service: light.turn_on
        target:
          entity_id: light.office
        data:
          flash: long
          color_name: green
```

**Daily TTS summary:**

```yaml
automation:
  - alias: "Daily Polymarket summary"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: tts.speak
        data:
          entity_id: tts.home_assistant_cloud
          media_player_entity_id: media_player.kitchen
          message: >
            {{ states('sensor.will_x_happen_yes_probability') }}% on:
            will X happen.
```

You can also build triggers in the UI: on a tracked market's device, use **Device triggers** to pick "Probability crossed a threshold", "Fast price move", "Large trade occurred", "24h volume spike", "Market resolved", or "Closing soon" without writing YAML.

## Services

- `polymarket_watch.get_price_history` — historical price points for one outcome (device, outcome, interval, fidelity). Returns response data.
- `polymarket_watch.refresh` — force an immediate metadata refresh for a tracked market.
- `polymarket_watch.search_markets` — search Polymarket by free text (query, limit). Returns response data; usable from Assist/LLM tooling.

## Diagnostics

Each config entry exposes a diagnostics download (Settings > Devices & services > Polymarket Watch > entry > Download diagnostics) with WebSocket connection state, subscribed token count, last message age, and per-outcome quote state. There is nothing sensitive to redact: every endpoint used is public and unauthenticated.

## Limitations

- Read-only by design. No trading, no wallet integration, no authenticated endpoints.
- Depends on Polymarket's public API and WebSocket feed staying stable; endpoint shapes were verified against the live API at the time of writing but may change.

## Development

```bash
pip install -r requirements_test.txt
ruff check custom_components/polymarket_watch
mypy custom_components/polymarket_watch
pytest tests
```
