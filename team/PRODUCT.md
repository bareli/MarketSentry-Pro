# Product profile

Owned by the product manager. Keep it short and current. Mark anything unsourced `TO CONFIRM`.

## What it is

MarketSentry Pro: a Home Assistant custom integration (HACS) that tracks Polymarket prediction
markets, stocks (Finnhub or Alpaca/IEX), cryptocurrencies (CoinGecko) and FX rates (Frankfurter /
Bank of Israel), fires HA events and device triggers on price moves and thresholds, and ships a
Lovelace card (list view, single-instrument detail view, an auto-dashboard view strategy) plus
three importable automation blueprints. Read-only by design: no trading, no wallet/brokerage
access. Source: root `README.md`.

## Users

One confirmed real user: the owner (Victor/bareli), running their own HA instance, bilingual
Hebrew/English (Hebrew is the daily language - see `qa/PROJECT.md` Locale). Published on HACS as a
public custom repository (MIT license), so other HA users can and do install it, but no other
install base has been directly observed. Source: `qa/PROJECT.md`.

## The job

Let a home user watch prediction markets, stocks, crypto and FX alongside the rest of their smart
home, and automate on price moves without writing provider-API integration code themselves.
"Done well" = tracked instruments stay current, the dashboard is readable at a glance, and
automations fire on real events, not false ones. TO CONFIRM (inferred from feature set and
README's framing, not stated directly by the owner).

## Goals (this quarter)

1. Ship v0.5.0's feature set cleanly: 8-language i18n, 3 ready-made blueprints, a richer
   instrument chart, the auto-dashboard view strategy, and the new CoinGecko crypto provider.
   Source: this session's work, already shipped and live-verified.
2. TO CONFIRM - anything beyond stabilizing v0.5.0 (more providers, more blueprint coverage, HACS
   default-store submission) is not stated by the owner yet.

## Non-goals

- No trading, no order placement, no wallet/brokerage integration - stated explicitly and
  repeatedly in the README and the top-of-file disclaimer. This is a hard non-goal, not a
  TO CONFIRM.
- No multi-tenant / multi-user account model - single HA instance, single owner. Source:
  `qa/PROJECT.md` Security shape.

## Priorities

TO CONFIRM - the owner has not ranked open work. As of this profile's creation, the open QA
backlog (6 confirmed defects, 4 UX findings, 5 enhancement ideas from the 2026-10-31 full-cycle
run) is the nearest thing to a priority list, and severity in `qa/bugs/`, `qa/security/findings/`,
`qa/ux/findings/` is the product manager's own best-effort ranking signal, not an owner ranking.

## Constraints

- MIT license, unofficial/no-affiliation disclaimer toward every provider (Polymarket, Finnhub,
  Alpaca, CoinGecko, the Bank of Israel) - any product decision that reads as implying
  affiliation, endorsement, or trading capability is out of bounds. Source: README.
- Each provider's own terms apply (e.g. Finnhub's free tier is personal/non-commercial use only).
  Source: README.
- No legal/accessibility frame has been confirmed beyond the above - see `qa/PROJECT.md` Legal
  frame / Accessibility (`TODO(ask owner)` there too).
- Dev machine is Windows; the `tests/config_flow` suite (full HA fixture) only runs in CI on
  Linux. Not a product constraint, but shapes what "verified before shipping" can mean locally.

## Definition of done for a release

TO CONFIRM - no stated bar. Working precedent from this project's own git history: `ruff`/`mypy
--strict`/`pytest` clean, card `Vitest`/`Playwright` clean, version bumped per the owner's stated
git convention (patch for small fixes direct to master, minor for feature branches), CI green
before tagging.

## Decision rights

Default: team-kit RULEBOOK §2. No project-specific override stated.

## Locale

English and Hebrew (RTL) are the two languages known to matter directly to the owner; the product
also ships German, French, Spanish, Portuguese (Brazil), Italian and Dutch as of v0.5.0. Source:
`qa/PROJECT.md` Locale, `card/src/i18n.js`, `custom_components/marketsentry/translations/`.
