# PROV - Provider modules

Source: `custom_components/marketsentry/providers/{base,polymarket,finnhub,alpaca,fx,crypto}.py`.
Unit-testable offline (`tests/providers/`); most API facts are explicitly flagged in code/README
as **not** verified against live provider docs this project's sessions - a mismatch with the real
API on first live use is a "needs verification", check README's unverified-facts list before
filing as a fresh bug.

- **PROV-01** Polymarket: `resolve()` on a URL/slug, `search()` on free text, `fetch_snapshot()`
  WS + REST fallback shape, `fetch_history()`.
- **PROV-02** Finnhub: `validate()` against a real/fake key, WS subscribe/trade shape, REST
  `/quote` + `/search`, free-tier WS symbol limit behavior (~30, unverified).
- **PROV-03** Alpaca: `validate()`, IEX vs SIP feed selection, WS quote/trade shape (quote
  confirmed live previously; trade shape unverified), REST market-data paths.
- **PROV-04** FX: `resolve()` routes `EUR/ILS` → Frankfurter, `EUR/ILS/boi` → Bank of Israel;
  malformed input raises `CannotConnect`; BOI `fetch_history` is a known no-op (not a bug).
- **PROV-05** Crypto (CoinGecko): `resolve()` on an exact coin id vs free text (expect
  `CannotConnect` → caller falls back to `search()`); `search()` returns up to `limit` matches;
  `fetch_snapshot()` batches every ref id into one `/simple/price` call (verify this actually
  happens against the live API, not just the mocked test); `fetch_history()` days = ceil(hours/24).
  - Shipped this session with zero live verification - highest-priority PROV item to actually hit
    the real CoinGecko API against once, for: exact endpoint paths/params, rate-limit behavior
    on the free tier with several tracked coins, and whether `/coins/{id}` 404s as assumed for an
    unknown id vs some other status/shape.
- **PROV-06** Every provider's `fetch_snapshot()` degrades gracefully per-ref on a single failure
  (one bad instrument doesn't drop the whole snapshot) - confirmed pattern in FX/crypto, verify
  Polymarket/Finnhub/Alpaca too.
- **PROV-07** `requires_api_key`/`supports_streaming` flags are correct per provider (drives
  config-flow credential step and whether `_async_start_streaming` runs at all).
