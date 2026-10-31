# CFG - Config flow / subentry flow

Source: `custom_components/marketsentry/config_flow.py`. Needs the full `hass` fixture - only
runs in CI (Linux), not on this Windows dev machine. A QA pass through these either runs in a
Linux environment or is inferred from CI's `Lint and test` workflow being green; say which.

- **CFG-01** Adding a Polymarket account (no credentials) creates a config entry with
  `CONF_PROVIDER=polymarket`, no credential keys stored.
  - **CI-only verified.** `tests/config_flow/test_config_flow.py::test_polymarket_entry_needs_no_credentials`
    exists and exercises exactly this (asserts `result["data"] == {CONF_PROVIDER: "polymarket"}`).
    Needs the `hass` fixture (Linux-only); not run locally this session (Windows). Inferred from
    the latest `Lint and test` CI run on `master` being green (`gh run list`, run 41188574880,
    success, 2026-10-31).
- **CFG-02** Adding an Exchange rates (fx) account: same as CFG-01, no credentials step shown.
  - **CI-only verified (same code path, not a dedicated test by name).** The generic
    "no-credentials" path (`_async_finish_no_credentials`) is kind-agnostic - it only branches on
    `PROVIDERS[key].requires_api_key`, which is `False` for both fx and polymarket identically.
    `test_duplicate_provider_entry_aborts` actually creates an fx entry via this exact path first
    (to then duplicate it), so it is exercised, just not asserted on by a test named for CFG-02
    specifically. No dedicated fx-only "creates entry" test exists.
- **CFG-03** Adding a CoinGecko account: same as CFG-01, no credentials step shown.
  - **Not exercised by name; same generic code path as CFG-01/02.** No test in
    `test_config_flow.py` creates a `coingecko` entry. Low risk (identical kind-agnostic branch,
    `requires_api_key=False` confirmed for `CryptoProvider` under PROV-07), but it is a genuine gap
    - nothing currently proves the "coingecko" string specifically round-trips through
    `PROVIDERS["coingecko"]`/`build_provider` without typo-class errors. Flagging as a test
    coverage gap, not a bug (no evidence of an actual defect).
- **CFG-04** Adding a Finnhub account with a valid key succeeds; with an invalid key shows
  `invalid_auth`; unreachable shows `cannot_connect`.
  - **CI-only verified, partial.** `test_finnhub_credentials_invalid_auth` and
    `test_finnhub_credentials_success_creates_entry` both exist. No `cannot_connect` case test for
    Finnhub specifically (Alpaca has one, Finnhub doesn't) - test coverage gap, not a bug; the
    `except CannotConnect: errors["base"] = "cannot_connect"` branch in `config_flow.py` is
    identical code to the tested Alpaca path.
- **CFG-05** Adding an Alpaca account: key_id + secret_key + feed (default `iex`), same
  valid/invalid/unreachable matrix as CFG-04.
  - **CI-only verified, partial.** `test_alpaca_credentials_cannot_connect` exists. No
    `invalid_auth`/success-creates-entry test for Alpaca specifically (Finnhub has both) - mirror
    gap of CFG-04's, same reasoning (shared code path already proven for Finnhub).
- **CFG-06** Re-adding an already-configured provider account aborts `already_configured`
  (unique_id = provider key).
  - **CI-only verified.** `test_duplicate_provider_entry_aborts` exists and covers exactly this.
- **CFG-07** Add-instrument: pasting a Polymarket URL/slug with exactly one match goes straight to
  confirm; a query with multiple matches shows the select step; zero matches shows `not_found`.
  - **CI-only verified, partial** (per BUG-001's note, already in this file before this session).
    `test_instrument_subentry_single_match_flow` and `test_instrument_subentry_multiple_matches_shows_select`
    both exist; no dedicated "zero matches → not_found" test found in `test_config_flow.py` this
    session either - still a gap, not a bug (the `if not refs and not errors: errors["base"] =
    "not_found"` line in `config_flow.py` is simple and directly adjacent to the tested code).
- **CFG-08** Add-instrument: a stock ticker (Finnhub/Alpaca) resolves directly; free text search
  works on Finnhub, is unsupported on Alpaca (paste exact ticker only).
  - **CODE-VERIFIED at the provider level (ran, Windows-safe).** `test_finnhub.py`'s
    `test_search_maps_results_to_instrument_refs` confirms free-text search works for Finnhub.
    `alpaca.py`'s `search()` is `try: return await self.resolve(query); except CannotConnect:
    return []` - free text that isn't an exact ticker raises `CannotConnect` from `resolve()`
    (confirmed by `test_alpaca.py::test_resolve_raises_cannot_connect_for_unknown_symbol`) which
    `search()` swallows into `[]`, and the generic subentry flow then shows `not_found` - matches
    "unsupported on Alpaca (paste exact ticker only)" exactly. The subentry flow's generic
    resolve→search→not_found orchestration itself is CI-only verified (see CFG-07).
- **CFG-09** Add-instrument: `EUR/ILS` resolves to the Frankfurter market-rate instrument;
  `EUR/ILS/boi` resolves to the Bank-of-Israel official-rate instrument.
  - **CODE-VERIFIED (ran, Windows-safe).** `tests/providers/test_fx.py::test_resolve_defaults_to_frankfurter`
    and `test_resolve_boi_suffix_selects_official_source` both exist and pass locally (pure
    provider-level logic, no hass fixture).
- **CFG-10** Add-instrument: a CoinGecko coin id (e.g. `bitcoin`) resolves directly; free text
  (ticker or name) falls through to search and offers a pick list.
  - **CODE-VERIFIED (ran, Windows-safe + live, see PROV-05).** `test_crypto.py::test_resolve_exact_coin_id`
    and `test_resolve_raises_on_unknown_id` cover the resolve-vs-fall-through-to-search split; the
    live CoinGecko `/coins/{id}` 404 behavior behind `test_resolve_raises_on_unknown_id`'s mock was
    independently confirmed against the real API this session (PROV-05).
- **CFG-11** Confirm step shows kind-appropriate option fields only (see `_options_schema`):
  outcome gets volume-spike/closing-soon, stock/crypto/fx get daily-change, outcome/stock get
  large-trade, stock gets market-open-gap + extended-hours. Crypto gets none of the stock/outcome
  -only fields.
  - CAUGHT THIS SESSION: `OPT_DAILY_CHANGE_PCT` field visibility requires `kind in ("stock", "fx",
    "crypto")` - verify a 4th kind added in the future doesn't get silently skipped here too.
  - **CODE-VERIFIED (ran directly, Windows-safe, no hass fixture).** `_options_schema` is a plain
    function; called directly with `kind="crypto"`: fields present are exactly `thresholds`,
    `hysteresis`, `move_delta`, `move_window_min`, `cooldown_min`, `daily_change_pct` - no
    `large_trade_usd`, `market_open_gap_pct`, `volume_spike_pct`, `closing_soon_hours`,
    `extended_hours`. Matches the plan's description exactly for crypto. No automated test exists
    for `_options_schema` directly (flagged as a coverage gap, no defect found - not added as a
    new test this session per budget, since nothing is broken).
- **CFG-12** Reconfigure an existing instrument's options updates `CONF_OPTIONS` only, keeps
  identity/kind/unit unchanged, and the entry reloads with the new detector settings live.
  - **CI-only verified.** `test_instrument_subentry_reconfigure_updates_options` and
    `test_adding_instrument_subentry_reloads_entry_and_creates_entities` both exist.
- **CFG-13** Adding the same instrument id twice under one account aborts `already_configured`.
  - **CI-only verified.** `test_instrument_subentry_duplicate_aborts` exists.
- **CFG-14** Thresholds field parses a comma-separated list (`"30,50,70"` → `[30.0, 50.0, 70.0]`),
  tolerates stray whitespace, empty string → `[]`.
  - **CODE-VERIFIED (ran directly, Windows-safe, no hass fixture).** `_parse_thresholds` is a plain
    function; ran it directly: `"30,50,70"` → `[30.0, 50.0, 70.0]`, `" 30 , 50 ,70 "` → same
    (whitespace tolerated), `""` → `[]`. Matches exactly. No automated test exists for this
    function specifically (coverage gap, no defect - not added, nothing broken).
- **CFG-15** The confirm step's description (`"Tracking **{name}** ({symbol})."`) never duplicates
  the symbol - regression test for BUG-001 (crypto's `InstrumentRef.name` baked the symbol in
  twice: "Tracking Bitcoin (BTC) (BTC)."). Live-reproduced with two different coins (bitcoin,
  ethereum) 2026-10-31; not yet covered by an automated test.
- **CFG-16** Creating the very first instrument subentry across the whole integration (no other
  config entry has one yet) raises a one-time `persistent_notification` pointing at the
  `custom:marketsentry` dashboard strategy; a second instrument on the same entry does not
  re-notify. ENH-003 (issue #10), implemented per decision D-009/D-011.
  - **AUTOMATED** `tests/config_flow/test_config_flow.py::test_first_instrument_ever_notifies_dashboard_strategy`
    and `::test_second_instrument_does_not_renotify` (CI-only, Linux `hass` fixture - see
    `qa/CLAUDE.md` §1). **Coverage gap** (flagged by qa-ux-expert verifying ENH-003, 2026-10-31):
    neither test exercises the cross-entry case (a second config entry's first instrument, while
    another entry already has one, must not re-notify) - that branch of `_any_instrument_exists()`
    is verified by code reading only, not automated. No defect found; add the missing test case if
    this code is touched again.
