"""Regression tests for ENH-016 - actionable mobile-app notification buttons
("Open dashboard" / "Snooze") on `notify_on_event.yaml` and
`resolved_announce.yaml`.

D-032 narrowed the snooze design: no new backend service or sensor. Snooze
state lives in a user-created `input_boolean` helper (an ordinary HA helper,
the same category as the already-optional `flash_light`/`tts_target`
inputs), and the suppression check lives entirely in this blueprint's own
`trigger:`/`condition:`/`variables:` - a second trigger on this automation
listens for the `mobile_app_notification_action` event matching the chosen
helper's entity id (used directly as the button's `action` id, so it is
unique per automation instance without any new backend state), and turns
that helper on for `snooze_hours` via `delay:` + `turn_off`. The "is this
currently snoozed" check elsewhere gates the pre-existing notify/light/TTS
actions.

These tests hand-trace (BUG-004/ENH-006 method, via the ENH-020 harness)
the three building blocks:

1. `notify_actions` - the `data.actions` list built from `mobile_notify_target`/
   `snooze_hours`/`snooze_helper`, including the "0 hours disables the
   Snooze button" case.
2. The gate condition that guards the pre-existing behaviour (default,
   untouched-by-ENH-016 case == True; snoozed == False).
3. The `trigger.id == 'marketsentry_snooze'` condition that distinguishes a
   real market event from the Snooze button being tapped.
"""

from __future__ import annotations

from typing import Any

from .blueprint_harness import (
    BLUEPRINTS_DIR,
    MockRegistry,
    MockState,
    load_blueprint,
    render_template,
    render_variables,
    substitute_inputs,
)

NOTIFY_PATH = BLUEPRINTS_DIR / "notify_on_event.yaml"
RESOLVED_PATH = BLUEPRINTS_DIR / "resolved_announce.yaml"

DASHBOARD_ACTION = {
    "action": "URI",
    "title": "Open dashboard",
    "uri": "/config/integrations/integration/marketsentry",
}


_DUMMY_TRIGGER = {"event": {"data": {"name": "", "winning_outcome": None}}}


def _notify_actions(path: Any, inputs: dict[str, Any]) -> list[dict[str, Any]]:
    """Render `notify_actions`. `resolved_announce.yaml`'s `variables:`
    block also contains `outcome_name`/`winning_outcome`, which read
    `trigger.event.data` regardless - a dummy trigger keeps those renderable
    so this helper can stay blueprint-agnostic."""
    blueprint = load_blueprint(path)
    registry = MockRegistry()
    variables = render_variables(blueprint, inputs, registry, extra_context={"trigger": _DUMMY_TRIGGER})
    return render_template("{{ notify_actions }}", registry, variables)


def _market_trigger_id(path: Any) -> str:
    """The default `trigger.id` HA assigns the first (unnamed) trigger in
    the list - its own position index as a string - to distinguish it from
    the blueprint's explicitly-`id`'d second (snooze) trigger."""
    blueprint = load_blueprint(path)
    assert blueprint["trigger"][1]["id"] == "marketsentry_snooze"
    return "0"


def _snooze_button_template(path: Any) -> str:
    """The condition on the top-level branch that reacts to the Snooze
    button being tapped (`trigger.id == 'marketsentry_snooze'`) - the same
    position (`action[0]`) in both blueprints."""
    blueprint = load_blueprint(path)
    substituted = substitute_inputs(blueprint["action"], blueprint, inputs={})
    return substituted[0]["if"][0]["value_template"]


def _not_snoozed_gate_template(path: Any) -> str:
    """The "is this automation currently silenced" condition that guards
    the pre-existing (pre-ENH-016) behaviour. The two blueprints structure
    their action sequence differently (`notify_on_event.yaml`'s existing
    action is an opaque `!input`, so its gate is a top-level sibling branch;
    `resolved_announce.yaml`'s existing branches are literal YAML, so its
    gate is nested inside the Snooze branch's `else:`), so the node's
    position differs even though the rendered template is the same shape."""
    blueprint = load_blueprint(path)
    substituted = substitute_inputs(blueprint["action"], blueprint, inputs={})
    if path == NOTIFY_PATH:
        return substituted[1]["if"][0]["value_template"]
    return substituted[0]["else"][0]["if"][0]["value_template"]


class TestNotifyActionsList:
    """`notify_actions` - shared shape across both blueprints. It is built
    independently of `mobile_notify_target` (that input only gates whether
    the notification carrying this list is ever sent at all - see
    `TestSnoozeGate`'s sibling, the `mobile_notify_target` condition each
    blueprint's own extra notify step uses) - always carries the Open
    dashboard button, and adds the Snooze button only when both
    `snooze_hours` > 0 and `snooze_helper` are configured."""

    def test_dashboard_button_always_present_by_default(self) -> None:
        for path in (NOTIFY_PATH, RESOLVED_PATH):
            assert _notify_actions(path, inputs={}) == [DASHBOARD_ACTION]

    def test_zero_snooze_hours_omits_snooze_button(self) -> None:
        """0 hours (the declared default) must not add a Snooze button even
        when a helper is configured - the brief's "0 disables the Snooze
        button" rule."""
        for path in (NOTIFY_PATH, RESOLVED_PATH):
            actions = _notify_actions(
                path,
                inputs={
                    "snooze_hours": 0,
                    "snooze_helper": "input_boolean.msft_snooze",
                },
            )
            assert actions == [DASHBOARD_ACTION]

    def test_both_buttons_when_fully_configured(self) -> None:
        for path in (NOTIFY_PATH, RESOLVED_PATH):
            actions = _notify_actions(
                path,
                inputs={
                    "snooze_hours": 2,
                    "snooze_helper": "input_boolean.msft_snooze",
                },
            )
            assert actions == [
                DASHBOARD_ACTION,
                {"action": "input_boolean.msft_snooze", "title": "Snooze 2h"},
            ]


class TestSnoozeGate:
    """The condition guarding the blueprint's pre-existing behaviour."""

    def test_default_unconfigured_automation_is_unaffected(self) -> None:
        """No snooze helper configured (the declared default, `""`) - the
        gate must stay open exactly like before ENH-016."""
        for path in (NOTIFY_PATH, RESOLVED_PATH):
            template = _not_snoozed_gate_template(path)
            registry = MockRegistry()
            trigger = {"id": _market_trigger_id(path)}
            fires = render_template(template, registry, context={"trigger": trigger, "snooze_helper": ""})
            assert fires is True

    def test_snoozed_helper_closes_the_gate(self) -> None:
        for path in (NOTIFY_PATH, RESOLVED_PATH):
            template = _not_snoozed_gate_template(path)
            registry = MockRegistry()
            registry.states["input_boolean.msft_snooze"] = MockState(
                "input_boolean.msft_snooze", "on"
            )
            trigger = {"id": _market_trigger_id(path)}
            context = {"trigger": trigger, "snooze_helper": "input_boolean.msft_snooze"}
            fires = render_template(template, registry, context)
            assert fires is False

    def test_helper_off_leaves_the_gate_open(self) -> None:
        for path in (NOTIFY_PATH, RESOLVED_PATH):
            template = _not_snoozed_gate_template(path)
            registry = MockRegistry()
            registry.states["input_boolean.msft_snooze"] = MockState(
                "input_boolean.msft_snooze", "off"
            )
            trigger = {"id": _market_trigger_id(path)}
            context = {"trigger": trigger, "snooze_helper": "input_boolean.msft_snooze"}
            fires = render_template(template, registry, context)
            assert fires is True


class TestSnoozeButtonTrigger:
    """The branch that reacts to the Snooze button itself (turn the helper
    on) is distinct from the branch that guards the pre-existing
    notify/light/TTS actions, and keyed only off `trigger.id`."""

    def test_snooze_button_tap_is_recognised(self) -> None:
        for path in (NOTIFY_PATH, RESOLVED_PATH):
            template = _snooze_button_template(path)
            registry = MockRegistry()
            fires = render_template(template, registry, context={"trigger": {"id": "marketsentry_snooze"}})
            assert fires is True

    def test_market_event_does_not_trigger_the_snooze_branch(self) -> None:
        for path in (NOTIFY_PATH, RESOLVED_PATH):
            template = _snooze_button_template(path)
            registry = MockRegistry()
            fires = render_template(template, registry, context={"trigger": {"id": "0"}})
            assert fires is False
