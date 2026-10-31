# CFG - Config flow / subentry flow

Source: `custom_components/marketsentry/config_flow.py`. Needs the full `hass` fixture - only
runs in CI (Linux), not on this Windows dev machine. A QA pass through these either runs in a
Linux environment or is inferred from CI's `Lint and test` workflow being green; say which.

- **CFG-01** Adding a Polymarket account (no credentials) creates a config entry with
  `CONF_PROVIDER=polymarket`, no credential keys stored.
- **CFG-02** Adding an Exchange rates (fx) account: same as CFG-01, no credentials step shown.
- **CFG-03** Adding a CoinGecko account: same as CFG-01, no credentials step shown.
- **CFG-04** Adding a Finnhub account with a valid key succeeds; with an invalid key shows
  `invalid_auth`; unreachable shows `cannot_connect`.
- **CFG-05** Adding an Alpaca account: key_id + secret_key + feed (default `iex`), same
  valid/invalid/unreachable matrix as CFG-04.
- **CFG-06** Re-adding an already-configured provider account aborts `already_configured`
  (unique_id = provider key).
- **CFG-07** Add-instrument: pasting a Polymarket URL/slug with exactly one match goes straight to
  confirm; a query with multiple matches shows the select step; zero matches shows `not_found`.
- **CFG-08** Add-instrument: a stock ticker (Finnhub/Alpaca) resolves directly; free text search
  works on Finnhub, is unsupported on Alpaca (paste exact ticker only).
- **CFG-09** Add-instrument: `EUR/ILS` resolves to the Frankfurter market-rate instrument;
  `EUR/ILS/boi` resolves to the Bank-of-Israel official-rate instrument.
- **CFG-10** Add-instrument: a CoinGecko coin id (e.g. `bitcoin`) resolves directly; free text
  (ticker or name) falls through to search and offers a pick list.
- **CFG-11** Confirm step shows kind-appropriate option fields only (see `_options_schema`):
  outcome gets volume-spike/closing-soon, stock/crypto/fx get daily-change, outcome/stock get
  large-trade, stock gets market-open-gap + extended-hours. Crypto gets none of the stock/outcome
  -only fields.
  - CAUGHT THIS SESSION: `OPT_DAILY_CHANGE_PCT` field visibility requires `kind in ("stock", "fx",
    "crypto")` - verify a 4th kind added in the future doesn't get silently skipped here too.
- **CFG-12** Reconfigure an existing instrument's options updates `CONF_OPTIONS` only, keeps
  identity/kind/unit unchanged, and the entry reloads with the new detector settings live.
- **CFG-13** Adding the same instrument id twice under one account aborts `already_configured`.
- **CFG-14** Thresholds field parses a comma-separated list (`"30,50,70"` → `[30.0, 50.0, 70.0]`),
  tolerates stray whitespace, empty string → `[]`.
- **CFG-15** The confirm step's description (`"Tracking **{name}** ({symbol})."`) never duplicates
  the symbol - regression test for BUG-001 (crypto's `InstrumentRef.name` baked the symbol in
  twice: "Tracking Bitcoin (BTC) (BTC)."). Live-reproduced with two different coins (bitcoin,
  ethereum) 2026-10-31; not yet covered by an automated test.
