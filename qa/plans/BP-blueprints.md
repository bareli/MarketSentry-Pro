# BP - Automation blueprints

Source: `blueprints/automation/marketsentry/*.yaml`. YAML-syntax-valid and `!input`-tag-parseable
(checked this session with a custom PyYAML loader), but **never imported into a real HA instance
and run** - that needs a live pass (`qa/CLAUDE.md` §1 gating: importing/running a blueprint on the
owner's real instance can flash a real light or send a real notification).

- **BP-01** `notify_on_event.yaml`: importable via the `my.home-assistant.io` blueprint-import
  link in README; the `trigger` input correctly offers every MarketSentry Pro device trigger type;
  the default `notify_action` template (`{{ trigger.event.data.name }}: ... -> ...`) renders
  without a Jinja error for at least one real fired event.
  - **CODE-VERIFIED (hand review), 2026-10-31, qa-engineer.** `trigger: !input market_trigger` and
    `action: !input notify_action` are both whole-node `!input` substitutions (the entire YAML
    value is the `!input` tag), which HA's blueprint substitution does handle correctly (confirmed
    by reading `annotatedyaml/input.py::substitute`, which replaces any node that *is* an `Input`
    placeholder). The default action's template only references `trigger`, which HA's automation
    engine always injects into action-template context for a fired trigger - not a bare
    blueprint-input name (unlike BP-02, below). No Jinja-undefined risk found. Device-trigger list
    content itself is TRIG-01 (already verified: directly derived from `EVENT_TYPES_BY_KIND`).
    Not run against a live HA instance this session (out of scope - see brief).
  - **Reviewed 2026-10-31 (qa-ux-expert), usability angle, code review only - never imported into
    live HA this session:** input descriptions are clear for a non-developer (names the exact
    template variables available in the default action). No usability issue found.
- **BP-02** `resolved_announce.yaml`: fires only on a `resolved` event; light-flash and TTS
  branches are both optional and independently skippable; the `winning_outcome` template handles
  `None` (market resolved with no clear winner, if that's possible) without erroring.
  - **CONFIRMED BUG, 2026-10-31, qa-engineer → BUG-004 (issue filed, see record).** The
    `winning_outcome`-handles-`None` half is fine (`{{ ... if winning_outcome is not none else ''
    }}`, and `winning_outcome` IS correctly bound via the blueprint's own `variables:` block as
    `"{{ trigger.event.data.winning_outcome }}"`, a real `trigger`-context reference, not a bare
    input name). The "optional and independently skippable" half is **not true**: the two
    `if`/`condition: template` gates reference `flash_light`, `tts_entity`, `tts_target` as bare
    Jinja names, but those three are never bound to anything - they're not in the `variables:`
    block, and blueprint `!input` substitution only replaces a YAML node that literally *is* the
    `!input` tag (confirmed from HA's own substitution source), not a name mentioned inside a
    string. At render time they are Jinja `Undefined`, and `Undefined.__eq__`/`__ne__` only
    compare equal to another `Undefined` (confirmed from `jinja2/runtime.py`) - so `is not none`,
    `!= []` and `not in [none, '']` all evaluate `True` unconditionally. Reproduced with a
    standalone Jinja2 render matching HA's exact `Undefined` semantics: both gate conditions render
    `"True"` with the inputs undefined. With the blueprint's own defaults (nothing configured
    beyond the trigger), this means `tts.speak` is still invoked with `entity_id: ""` on every
    resolution event - the documented "leave empty to skip" default is broken, not merely an edge
    case. No live HA instance was touched to produce this evidence (out of scope this session);
    the proof is the exact Jinja/HA source + a matching standalone render, not a guess.
- **BP-03** `daily_digest.yaml`: `integration_entities('marketsentry')` + `expand()` +
  `selectattr('attributes.kind', 'defined')` actually enumerates every tracked primary sensor on a
  real instance (this exact combination of Jinja helpers was never run against live HA templating
  this session - highest-priority BP item to verify); the "no instruments tracked yet" branch
  renders when the list is empty; the digest's per-line format stays readable with a mix of
  outcome/stock/crypto/fx instruments.
  - **CODE-VERIFIED (hand review), 2026-10-31, qa-engineer, still CI/live-unverified for actual
    execution.** `integration_entities(domain_or_title)` is documented to accept either an
    integration's domain (`"marketsentry"`, matching `DOMAIN`) or a config-entry title, and return
    every entity across every config entry of that domain - correct usage for "every instrument
    across every provider account". `expand()` transparently resolves a list of plain entity IDs
    to their `State` objects (its group-expansion behavior is a superset that includes this).
    `selectattr('attributes.kind', 'defined')` uses Jinja2's documented dotted-attribute-path
    support in `make_attrgetter` (chains `getattr`-then-`getitem` per path segment, the same
    mechanism that lets `state.attributes.foo` work at all in HA templates) - this correctly
    filters down to entities carrying a `kind` attribute, i.e. exactly the primary sensors
    (`card_attributes()` is only applied to Probability/Price/Rate sensors, confirmed under
    SENS-03). No Jinja-undefined-variable risk found here (unlike BP-02): `tracked` is a real
    `variables:`-bound name, and `s` is for-loop-bound. The "no instruments tracked yet" branch and
    the per-line format read correctly on paper. This combination of helpers genuinely was not
    executed against a live/CI `hass` templating engine this session (no browser/live-instance
    access per the brief) - the above is a documented-behavior-based code review, not an execution
    result; flag for an actual live render if the owner wants certainty beyond this.
