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
  - **CODE-VERIFIED (live), 2026-10-31, qa-engineer.** Made direct read-only `curl` calls against
    the real `https://api.coingecko.com/api/v3` (no HA instance involved) for every endpoint the
    module docstring assumes: `/coins/bitcoin?...` → 200 with `{"id","symbol","name",...}` as
    assumed; `/coins/not-a-real-coin-xyz123?...` → **404** with `{"error":"coin not found"}`,
    confirming the code's `resp.status == 404 → CannotConnect` branch matches the live API, not
    just the mocked test; `/search?query=bit` → 200 `{"coins":[{"id","symbol","name",...}]}` as
    assumed; `/simple/price?ids=bitcoin,ethereum&...` → 200, confirming the batched-call-for-every-
    ref shape in one real request, and `ids=bitcoin,not-a-real-coin-xyz123` → 200 with only
    `bitcoin` present (the unknown id is silently dropped, not an error) - confirms
    `fetch_snapshot`'s per-ref "missing from response → skip" handling matches live behavior;
    `/coins/bitcoin/market_chart?vs_currency=usd&days=2` → 200 `{"prices":[[ms,price],...]}` as
    assumed. All endpoint paths, params and response shapes the code/docstring assumed are
    confirmed accurate against the live API today. Not verified: sustained free-tier rate-limit
    behavior with many tracked coins over time (only ~6 calls made in one short session, no
    429 encountered - too small a sample to confirm the limit itself, only that it wasn't hit).
- **PROV-06** Every provider's `fetch_snapshot()` degrades gracefully per-ref on a single failure
  (one bad instrument doesn't drop the whole snapshot) - confirmed pattern in FX/crypto, verify
  Polymarket/Finnhub/Alpaca too.
  - **CONFIRMED BUG for Finnhub/Alpaca, 2026-10-31, qa-engineer → BUG-003 (issue filed, see
    record).** Polymarket (`fetch_snapshot`'s `try/except PolymarketApiError: continue` per ref)
    and FX (`try/except CannotConnect` per ref) both degrade correctly - CODE-VERIFIED by reading
    `polymarket.py`/`fx.py`. Crypto's single batched call degrades per-coin too (confirmed live
    above: an unrecognized id is just missing from the response, not an exception). Finnhub and
    Alpaca have **no** per-ref try/except around their REST call inside `fetch_snapshot()`'s loop -
    one ref's `CannotConnect`/`InvalidAuth` aborts the whole call, which `coordinator.py` turns
    into `UpdateFailed` for the entire config entry. Reproduced with a new failing-first regression
    test in each provider's test file (currently RED, proving the defect - see BUG-003):
    `tests/providers/test_finnhub.py::test_fetch_snapshot_one_bad_ref_should_not_drop_the_others`,
    `tests/providers/test_alpaca.py::test_fetch_snapshot_one_bad_ref_should_not_drop_the_others`.
- **PROV-07** `requires_api_key`/`supports_streaming` flags are correct per provider (drives
  config-flow credential step and whether `_async_start_streaming` runs at all).
  - **CODE-VERIFIED, 2026-10-31, qa-engineer.** Read every provider class's two attributes plus
    `__init__.py`'s `_async_start_streaming` gate (`if not runtime.provider.supports_streaming or
    not runtime.trackers: return`): polymarket (`False`/`True`, has `stream()`), finnhub
    (`True`/`True`, has `stream()`), alpaca (`True`/`True`, has `stream()`), fx (`False`/`False`,
    no `stream()`), crypto (`False`/`False`, no `stream()`) - all consistent with whether the class
    actually implements `stream()` and with the gate.
