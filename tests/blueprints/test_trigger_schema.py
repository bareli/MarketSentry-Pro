"""Regression test for a real bug caught during ENH-016's review: a blueprint's
`trigger:` list is not Jinja-templated, so `blueprint_harness.py`'s template-focused
tooling never exercises it - it needs HA's own trigger config schema instead.

`market_trigger`'s selector is `selector: trigger: {}`, whose resolved value is
always a *list* of trigger dicts (HA's `cv.TRIGGER_SCHEMA` normalizes a single
trigger to a one-item list too). Naively adding a second, blueprint-internal
trigger via:

    trigger:
      - !input market_trigger
      - id: marketsentry_snooze
        ...

substitutes that list as a single list *item*, producing a list-within-a-list
(`[[trig], {id: snooze}]`), which fails `cv.TRIGGER_SCHEMA` outright
(`expected a dictionary @ data[0]`) - breaking every automation built from
either blueprint, since `market_trigger` is a required input. The fix wraps the
substituted list in HA's own documented nested-trigger-group syntax,
`{"triggers": [...]}`, which `cv.TRIGGER_SCHEMA`'s `_base_trigger_list_flatten`
step is specifically built to unwrap.
"""

from __future__ import annotations

import homeassistant.helpers.config_validation as cv

from .blueprint_harness import BLUEPRINTS_DIR, load_blueprint, substitute_inputs

_REALISTIC_MARKET_TRIGGER = [
    {
        "platform": "device",
        "device_id": "some-device-id",
        "domain": "marketsentry",
        "type": "resolved",
    }
]


def _validated_trigger_list(blueprint_filename: str, *, snooze_helper: str) -> list[dict]:
    blueprint = load_blueprint(BLUEPRINTS_DIR / blueprint_filename)
    raw_trigger = blueprint["trigger"]
    substituted = substitute_inputs(
        raw_trigger,
        blueprint,
        {"market_trigger": _REALISTIC_MARKET_TRIGGER, "snooze_helper": snooze_helper},
    )
    return cv.TRIGGER_SCHEMA(substituted)


def test_notify_on_event_trigger_list_is_valid_with_snooze_configured() -> None:
    result = _validated_trigger_list("notify_on_event.yaml", snooze_helper="input_boolean.test")
    assert result[0]["platform"] == "device"
    assert result[1]["id"] == "marketsentry_snooze"
    assert result[1]["platform"] == "event"


def test_notify_on_event_trigger_list_is_valid_with_snooze_unconfigured() -> None:
    # snooze_helper left at its declared default ("") - the blueprint input
    # isn't passed at all, so it falls back to the default the same way a
    # real user who never touched that field would get.
    blueprint = load_blueprint(BLUEPRINTS_DIR / "notify_on_event.yaml")
    substituted = substitute_inputs(
        blueprint["trigger"], blueprint, {"market_trigger": _REALISTIC_MARKET_TRIGGER}
    )
    result = cv.TRIGGER_SCHEMA(substituted)
    assert result[0]["platform"] == "device"
    assert result[1]["id"] == "marketsentry_snooze"


def test_resolved_announce_trigger_list_is_valid_with_snooze_configured() -> None:
    result = _validated_trigger_list("resolved_announce.yaml", snooze_helper="input_boolean.test")
    assert result[0]["platform"] == "device"
    assert result[1]["id"] == "marketsentry_snooze"
    assert result[1]["platform"] == "event"
