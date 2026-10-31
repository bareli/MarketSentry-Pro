# Historical risk areas

Where this project has actually broken, mapped from changed files to the test plans that would
catch it. Updated by the manager after each run; read it before scoping a risk-based `/qa` pass.

## New instrument kind / new provider (highest-risk change shape in this codebase)

Every real bug found in the 2026-10-31 full cycle traced back to adding a new instrument kind
(`crypto`) or a new provider (`coingecko`) touching code that was written generically enough to
*look* kind-agnostic but had one or two spots that weren't:

- `providers/crypto.py`'s `InstrumentRef.name` baked the symbol in (`"Bitcoin (BTC)"`), which
  every *other* provider's `name` doesn't do - broke `config_flow.py`'s confirm-step template
  (`"Tracking **{name}** ({symbol})."`), producing a duplicated symbol. → BUG-001.
- The two REST-only, no-streaming providers that predate the generic-loop pattern (Finnhub,
  Alpaca) never got the per-ref `try/except` that FX/crypto/Polymarket all have in
  `fetch_snapshot()` - not caught by adding crypto, but caught *while* auditing crypto's own
  degrade-per-ref behavior against every other provider side by side. → BUG-003.
- `__init__.py`'s `_build_detectors`/`_async_process_quote` key `OfficialRatePublishedDetector`
  off instrument *kind* (`"fx"`) only, never the ref's *source* (`boi:` vs `frankfurter:`) -
  pre-existing gap, surfaced while checking whether the new kind's wiring followed the same
  pattern correctly. → BUG-005.

**Risk-area rule for next time:** when a diff adds a new `kind` or a new provider, the highest-
value review isn't just "does the new one work" - it's "read every *other* provider/kind's
equivalent code path side by side with the new one, looking for places they silently differ."
That's where BUG-003 and BUG-005 came from; neither was in the diff that added crypto.

## Config-flow confirm/options forms

`_options_schema`/`default_options_for_kind`/`EVENT_TYPES_BY_KIND` must all three stay in sync
per kind (`const.py`, `config_flow.py`, `__init__.py`'s `_build_detectors`) - a kind missing from
one of the three silently drops a detector or a form field rather than erroring. Verified in sync
for all four kinds as of 2026-10-31 (DET-09); re-check this triangle whenever a 5th kind is added.

Options form fields (`qa/bugs` UX-004) have no units and no `data_description` - the same field
name (`move_delta`, `hysteresis`) means percentage points for outcomes and absolute currency for
stocks/crypto, with nothing in the UI saying so. Worth checking again if a new kind's unit
convention differs further.

## The card's "generic" renderer absorbs new kinds almost for free

`marketsentry-card.js`/`marketsentry-instrument-card.js`'s `row.kind !== "outcome"` branch (the
"generic" stock/fx view) picked up `crypto` automatically with zero card-side changes beyond a
group label and an always-"live" badge - because crypto's primary sensor deliberately reused the
`"price"` translation key already in `PRIMARY_TRANSLATION_KEYS`. This is a strong pattern: a new
non-outcome kind that reuses an existing primary translation key gets list/detail card support
for free. The flip side (BUG-002): `getStubConfig()` on the instrument card assumes at least one
instrument already exists - a zero-instrument HA install crashes `setConfig()` instead of reaching
the existing graceful empty state. Check this specifically whenever a new card or editor's
`getStubConfig()` is added.

## Automation blueprints are effectively untested until someone runs them live

All 3 shipped blueprints (`blueprints/automation/marketsentry/*.yaml`) passed YAML-syntax
validation and looked correct on read-through, but `resolved_announce.yaml` had a real functional
bug (BUG-004: unbound blueprint-input variables silently evaluate as Jinja `Undefined`, which is
always-truthy in the `is not none` checks used, so "optional" light/TTS steps always run) that
only direct Jinja-semantics tracing caught - not YAML validation, not a code read that stopped at
"looks like a reasonable template." Next time a blueprint ships: trace every `variables:` block's
actual binding, don't just read the `action:` steps.

## What's still genuinely unverified (not a defect - a gap)

- The `custom:marketsentry` dashboard view strategy (`ll-strategy-view-marketsentry`) has never
  been run against a real HA frontend's actual strategy-resolution code - both the engineer and
  UX passes this run were explicitly blocked from live HA access (gated, single real instance).
  One open question from UX review: does `config.title` reach the view/tab's own title, or only
  the embedded card's title? Needs a live check.
- CoinGecko's free-tier rate limit behavior under sustained load (many tracked coins, repeated
  polls) - only ~6 one-off calls were made this run, not enough to observe a 429.
- `tests/config_flow/` (the full `hass`-fixture suite) only runs in CI on Linux; this project's
  active dev machine is Windows and cannot run it locally at all (`fcntl` import failure). Every
  CFG-series finding this run that needed that fixture was either inferred from a green CI run or
  left as a documented gap, never guessed.
