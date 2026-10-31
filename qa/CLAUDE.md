# QA overlay: MarketSentry Pro

Read `~/.claude/qa-kit/RULEBOOK.md` first, then `qa/PROJECT.md`. This file adds this project's
specifics under the same § numbers. Where it contradicts the rulebook, it wins here, and says so.

## §1 Environments

| Env | Base URL | "Database" | Writes |
|---|---|---|---|
| `unit` | none (offline tests) | none | Always allowed |
| `live` | `http://homeassistant.local:8123` | HA's own `.storage/` on the owner's machine | **Gated - see below** |

This project has no disposable dev/staging server. `unit` (pytest/Vitest/Playwright against mocked
`hass` fixtures) is the only always-safe environment. `live` is the owner's real home - it is the
functional equivalent of production even though it isn't a SaaS "prod": a write there can flash a
real light, send a real phone notification, spend a tracked provider's API quota, or change a
dashboard the owner actually uses. Apply RULEBOOK §1's production gating to `live` in full: never
touch it without the owner's explicit go-ahead for that specific action in the current
conversation, and prefer reading over writing even then.

How to run the `unit` suite (Windows-safe subset; this dev machine cannot run the HA test fixture
at all - `homeassistant.runner` imports POSIX-only `fcntl`):

```bash
# Backend
pip install -r requirements_test.txt
ruff check custom_components/marketsentry
mypy custom_components/marketsentry
pytest tests --ignore=tests/config_flow -p no:homeassistant

# Card
cd card
npm run build
npm test            # Vitest
npx playwright test # behavioral + screenshot regression (needs a browser download once)
```

The `tests/config_flow/` suite (full `hass` fixture) only runs in CI (Linux, `Lint and test`
workflow on GitHub Actions). A QA pass that touches `config_flow.py` must say explicitly whether
that subset was verified locally (it wasn't, on Windows) or only inferred from a green CI run.

### "Database" access

There is no database. HA's own entity registry/recorder holds state on whatever instance is
running; for `live`, that's the owner's `homeassistant.local` instance, inspectable only via its
own UI/API (Settings > Devices & services, the diagnostics download, or `hass.states`/`hass.data`
if you have a WS/REST session) - never a direct file read of someone's `.storage/`.

## §2 Boundaries

See `PROJECT.md` → *Paths*. `qa-developer` is the only role that edits
`custom_components/marketsentry/` or `card/src/`; everyone else is read-only there and may add a
regression test under `tests/` or `card/test/`/`card/e2e/` for a reproduced defect.

## §3 Builds

No shared warm build to reuse between agents - each pytest/Vitest/Playwright invocation is cheap
and fast (whole suite is seconds, not minutes). Run the full `unit` command block above per batch
rather than trying to share a build artifact. Card changes rebuild via `npm run build`
(`esbuild`, sub-second) before `npm test`/`playwright test` - stale `www/marketsentry-card.js`
after a `card/src/` edit is the single most common self-inflicted false negative here; always
rebuild before testing.

## §4 Instances

| Port | "Database" | Notes |
|---|---|---|
| n/a | n/a | No local server this project starts for QA. `live` instance below is the owner's, not QA's to start/stop/reset. |

| Live instance | Notes |
|---|---|
| `http://homeassistant.local:8123` | Owner's real HA instance. Gated per §1. Browser automation in prior sessions used tab id references that do not survive across sessions - get a fresh `tabs_context_mcp` before assuming any tab exists. |

## §8 Specs

No legacy spec documents. The closest thing to a spec is the root `README.md` (feature behavior,
explicit "unverified API facts", explicit "deliberate behaviour, not a bug" list) and the module
docstrings in `custom_components/marketsentry/providers/*.py`, which flag which provider-API
details were never confirmed against live docs. Treat README's "Build status / what to verify
before production use" section as the closest thing this project has to a known-issues list -
read it before filing something it already flags as unverified rather than unknown-broken.
