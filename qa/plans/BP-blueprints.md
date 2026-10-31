# BP - Automation blueprints

Source: `blueprints/automation/marketsentry/*.yaml`. YAML-syntax-valid and `!input`-tag-parseable
(checked this session with a custom PyYAML loader), but **never imported into a real HA instance
and run** - that needs a live pass (`qa/CLAUDE.md` §1 gating: importing/running a blueprint on the
owner's real instance can flash a real light or send a real notification).

- **BP-01** `notify_on_event.yaml`: importable via the `my.home-assistant.io` blueprint-import
  link in README; the `trigger` input correctly offers every MarketSentry Pro device trigger type;
  the default `notify_action` template (`{{ trigger.event.data.name }}: ... -> ...`) renders
  without a Jinja error for at least one real fired event.
- **BP-02** `resolved_announce.yaml`: fires only on a `resolved` event; light-flash and TTS
  branches are both optional and independently skippable; the `winning_outcome` template handles
  `None` (market resolved with no clear winner, if that's possible) without erroring.
- **BP-03** `daily_digest.yaml`: `integration_entities('marketsentry')` + `expand()` +
  `selectattr('attributes.kind', 'defined')` actually enumerates every tracked primary sensor on a
  real instance (this exact combination of Jinja helpers was never run against live HA templating
  this session - highest-priority BP item to verify); the "no instruments tracked yet" branch
  renders when the list is empty; the digest's per-line format stays readable with a mix of
  outcome/stock/crypto/fx instruments.
