"""Tests for `notify_on_event.yaml`'s default notification action template.

This blueprint has no `variables:` block of its own - its only template is
the default `notify_action`'s message, which reads straight from
`trigger.event.data` (the device trigger's event payload: name/old/new/
delta/url/...). No HA template globals are involved at all, just attribute
access on the trigger event data, so this module exercises
`substitute_inputs`/`render_template` without needing `MockRegistry` to
hold any entities.
"""

from __future__ import annotations

from typing import Any

from .blueprint_harness import (
    BLUEPRINTS_DIR,
    MockRegistry,
    load_blueprint,
    render_template,
    substitute_inputs,
)

BLUEPRINT_PATH = BLUEPRINTS_DIR / "notify_on_event.yaml"


def _default_message(trigger: dict[str, Any]) -> str:
    blueprint = load_blueprint(BLUEPRINT_PATH)
    substituted = substitute_inputs(blueprint, blueprint, inputs={})
    # ENH-016 wrapped the original `action: !input notify_action` in a new
    # "is this automation currently snoozed" if-block (see
    # test_enh016_actionable_notifications.py) - `notify_action`'s own
    # default content, and this test's assertion about it, are unchanged.
    message_template = substituted["action"][1]["then"][0]["data"]["message"]
    return render_template(message_template, MockRegistry(), context={"trigger": trigger})


def test_default_message_renders_name_old_and_new() -> None:
    trigger = {
        "event": {
            "data": {
                "name": "MSFT",
                "old": "409.1",
                "new": "412.6",
                "delta": "3.5",
                "url": "https://example.com/msft",
            }
        }
    }

    message = _default_message(trigger)

    assert message == "MSFT: 409.1 -> 412.6"
