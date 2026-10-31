# DET - Detector logic

Source: `custom_components/marketsentry/detector.py`, wired per-kind in `__init__.py`'s
`_build_detectors`. Fully unit-testable offline, no HA fixture needed (`tests/test_detector.py`).

- **DET-01** `ThresholdDetector`: fires on crossing a configured threshold, respects hysteresis,
  doesn't re-fire on small oscillation inside the hysteresis band.
  - **CODE-VERIFIED (ran), 2026-10-31, qa-engineer.** `tests/test_detector.py::TestThresholdDetector`
    covers upward/downward crossing, hysteresis flap suppression, re-arming, multi-threshold
    independence. Ran green locally (Windows, no hass fixture needed - pure Python).
- **DET-02** `PriceMoveDetector`: relative (percent) mode for stock/fx/crypto vs absolute
  (percentage-point) mode for outcome; respects the move window.
  - **CODE-VERIFIED (ran), 2026-10-31, qa-engineer.** `TestPriceMoveDetector` +
    `TestPriceMoveDetectorRelativeMode` cover both modes, window expiry, reset-after-fire. Ran green.
- **DET-03** `DailyChangeDetector`: uses a supplied `previous_close` when given, else falls back
  to first-value-seen-today; fires at most once per UTC day; re-anchors at UTC midnight.
  - Crypto intentionally supplies no `previous_close` (CoinGecko's `usd_24h_change` isn't wired
    in) - confirm the first-seen-today fallback behaves sanely for a 24/7 market with no session
    boundary, since "first value seen today" is somewhat arbitrary for crypto vs stock/FX.
  - **CODE-VERIFIED (ran), 2026-10-31, qa-engineer.** `TestDailyChangeDetector` covers the supplied-
    previous_close path, the once-per-day limit, the midnight re-anchor, and
    `test_falls_back_to_first_value_seen_without_previous_close` (using an FX ref, but the detector
    is kind-agnostic - same code path crypto uses). The fallback is "sane" in the sense that it's
    deterministic and matches the documented behavior (first observed value each UTC day becomes
    the reference); whether a UTC-midnight boundary is the *right* choice for a 24/7 market is a
    product question, not a code defect - no bug found, this is as-designed per the module
    docstring ("callers simply don't use [session-specific detectors] for other kinds").
- **DET-04** `LargeTradeDetector`: fires on notional (price × size) over the threshold; only wired
  for outcome/stock kinds (confirm crypto/fx correctly have none, per `_build_detectors`).
  - **CODE-VERIFIED (ran), 2026-10-31, qa-engineer.** Detector unit-tested in isolation
    (`TestLargeTradeDetector`). Wiring confirmed by direct execution of `_build_detectors("crypto",
    default_options_for_kind("crypto"))` (importable and runnable without the hass fixture -
    `__init__.py` only *imports* homeassistant modules, which works fine on Windows; only the
    `hass` test *fixture* needs Linux): `large_trade` is `None` for crypto, confirming it is not
    wired, matching `EVENT_TYPES_BY_KIND["crypto"]` (no `large_trade`). Same check for fx (not
    shown in plan, but `kind in ("outcome","stock")` excludes both crypto and fx identically).
- **DET-05** `VolumeSpikeDetector`, `ClosingSoonDetector`, `ResolvedDetector`: outcome-only;
  `ResolvedDetector` fires exactly once per instrument lifetime.
  - **CODE-VERIFIED (ran), 2026-10-31, qa-engineer.** `TestVolumeSpikeDetector`,
    `TestClosingSoonDetector`, `TestResolvedDetector` all ran green. Outcome-only wiring confirmed
    via the same direct `_build_detectors` execution as DET-04/09 (all three are `None` for crypto).
- **DET-06** `MarketOpenGapDetector`: stock-only, needs `market_state` transitions from
  `market_calendar.py`.
  - **CODE-VERIFIED (ran), 2026-10-31, qa-engineer.** `TestMarketOpenGapDetector` ran green
    (regular-hours-only firing, once-per-session). Stock-only wiring confirmed directly:
    `_build_detectors` only builds it `if kind == "stock" and OPT_MARKET_OPEN_GAP_PCT in opts`.
- **DET-07** `OfficialRatePublishedDetector`: fx-only (Bank of Israel source specifically, per
  README's automation example) - confirm it doesn't also fire for Frankfurter-sourced FX
  instruments where "official rate" doesn't apply.
  - **CONFIRMED BUG, 2026-10-31, qa-engineer → BUG-005 (issue filed, see record).**
    `TestOfficialRatePublishedDetector` ran green in isolation (no fire on first observation,
    fires on new publication date, no refire same date) - the detector class itself is correct.
    The wiring is not: `_build_detectors(kind, opts)` only ever sees the instrument *kind* ("fx"),
    never the ref/id, so it cannot distinguish a `"boi:EUR:ILS"` ref from a
    `"frankfurter:EUR:ILS"` ref - both get `OfficialRatePublishedDetector` constructed. Confirmed
    unconditional by direct execution: `_build_detectors("fx", default_options_for_kind("fx"))` →
    `official_rate_published is not None`. The call site, `__init__.py`'s `_async_process_quote`
    (~line 359), is equally unconditional - no check on `tracker.ref.id`'s source prefix - and
    `fx.py`'s `_frankfurter_quote()` sets `Quote.ts` from Frankfurter's own daily-changing `date`
    field, the same shape of signal the detector fires on for BOI's `TIME_PERIOD`. So a
    Frankfurter-sourced instrument's quote date rolling over to a new day **will** fire
    `marketsentry_official_rate_published`, exactly the risk this test case named.
- **DET-08** `CooldownGate`: per-event-type cooldown suppresses duplicate fires within the
  configured window without suppressing a *different* event type on the same instrument.
  - **CODE-VERIFIED (ran), 2026-10-31, qa-engineer.** `TestCooldownGate` ran green (suppression
    within window, allowed after expiry, independent per-outcome/event-type key).
- **DET-09** Kind/option-key coupling: `_build_detectors` wires a detector purely off which
  `OPT_*` keys are present in options (not an explicit kind switch, except for
  outcome/stock/fx-specific ones) - if `default_options_for_kind` for a kind omits a key that
  detector silently never fires for that kind. Specifically verify crypto's options dict
  (`OPT_DAILY_CHANGE_PCT` present, `OPT_LARGE_TRADE_USD`/`OPT_MARKET_OPEN_GAP_PCT` intentionally
  absent) matches what `_build_detectors` actually wires for `kind == "crypto"`.
  - **CODE-VERIFIED (ran), 2026-10-31, qa-engineer.** No automated test exercises `_build_detectors`
    directly (not in `tests/test_detector.py` or anywhere else), so this was ad-hoc verified by
    direct execution: `_build_detectors("crypto", default_options_for_kind("crypto"))` →
    `threshold`/`move`/`daily_change` built, `large_trade`/`volume_spike`/`closing_soon`/`resolved`/
    `market_open_gap`/`official_rate_published` all `None`. This matches `default_options_for_kind
    ("crypto")`'s keys exactly (`OPT_THRESHOLDS`, `OPT_HYSTERESIS`, `OPT_MOVE_DELTA`,
    `OPT_MOVE_WINDOW_MIN`, `OPT_DAILY_CHANGE_PCT`, `OPT_COOLDOWN_MIN` - no `OPT_LARGE_TRADE_USD`/
    `OPT_MARKET_OPEN_GAP_PCT`) and matches `EVENT_TYPES_BY_KIND["crypto"]` (`threshold_crossed`,
    `price_move`, `daily_change` only). No defect found; no regression test added since nothing is
    broken (this would be a good candidate for a `tests/test_init_detectors.py` locking in the
    mapping for all four kinds, left as a suggestion rather than added, to keep this run's test
    changes scoped to reproduced defects only).
