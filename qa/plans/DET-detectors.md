# DET - Detector logic

Source: `custom_components/marketsentry/detector.py`, wired per-kind in `__init__.py`'s
`_build_detectors`. Fully unit-testable offline, no HA fixture needed (`tests/test_detector.py`).

- **DET-01** `ThresholdDetector`: fires on crossing a configured threshold, respects hysteresis,
  doesn't re-fire on small oscillation inside the hysteresis band.
- **DET-02** `PriceMoveDetector`: relative (percent) mode for stock/fx/crypto vs absolute
  (percentage-point) mode for outcome; respects the move window.
- **DET-03** `DailyChangeDetector`: uses a supplied `previous_close` when given, else falls back
  to first-value-seen-today; fires at most once per UTC day; re-anchors at UTC midnight.
  - Crypto intentionally supplies no `previous_close` (CoinGecko's `usd_24h_change` isn't wired
    in) - confirm the first-seen-today fallback behaves sanely for a 24/7 market with no session
    boundary, since "first value seen today" is somewhat arbitrary for crypto vs stock/FX.
- **DET-04** `LargeTradeDetector`: fires on notional (price × size) over the threshold; only wired
  for outcome/stock kinds (confirm crypto/fx correctly have none, per `_build_detectors`).
- **DET-05** `VolumeSpikeDetector`, `ClosingSoonDetector`, `ResolvedDetector`: outcome-only;
  `ResolvedDetector` fires exactly once per instrument lifetime.
- **DET-06** `MarketOpenGapDetector`: stock-only, needs `market_state` transitions from
  `market_calendar.py`.
- **DET-07** `OfficialRatePublishedDetector`: fx-only (Bank of Israel source specifically, per
  README's automation example) - confirm it doesn't also fire for Frankfurter-sourced FX
  instruments where "official rate" doesn't apply.
- **DET-08** `CooldownGate`: per-event-type cooldown suppresses duplicate fires within the
  configured window without suppressing a *different* event type on the same instrument.
- **DET-09** Kind/option-key coupling: `_build_detectors` wires a detector purely off which
  `OPT_*` keys are present in options (not an explicit kind switch, except for
  outcome/stock/fx-specific ones) - if `default_options_for_kind` for a kind omits a key that
  detector silently never fires for that kind. Specifically verify crypto's options dict
  (`OPT_DAILY_CHANGE_PCT` present, `OPT_LARGE_TRADE_USD`/`OPT_MARKET_OPEN_GAP_PCT` intentionally
  absent) matches what `_build_detectors` actually wires for `kind == "crypto"`.
