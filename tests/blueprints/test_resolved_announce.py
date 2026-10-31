"""Regression tests for `resolved_announce.yaml` - BUG-004.

BUG-004: the light-flash and TTS branches referenced the raw `flash_light`/
`tts_entity`/`tts_target` input names directly inside condition
`value_template` strings without ever binding them through the blueprint's
`variables:` block. Since Home Assistant's blueprint substitution only
replaces a literal `!input <name>` node (not a plain string that happens to
match an input's name), those names were unbound Jinja `Undefined` objects
at render time - and `Undefined.__eq__`/`__ne__` only compare equal to
another `Undefined`, so both "is this optional branch configured?" checks
evaluated `True` unconditionally, regardless of what the user configured.
The fix adds `flash_light`/`tts_target`/`tts_entity` to `variables:` via
`!input`, so the conditions see the real substituted values.
"""

from __future__ import annotations

from typing import Any

from .blueprint_harness import (
    BLUEPRINTS_DIR,
    MockRegistry,
    load_blueprint,
    render_template,
    render_variables,
    substitute_inputs,
)

BLUEPRINT_PATH = BLUEPRINTS_DIR / "resolved_announce.yaml"


def _trigger(name: str, winning_outcome: str | None) -> dict[str, Any]:
    return {"event": {"data": {"name": name, "winning_outcome": winning_outcome}}}


def _render(inputs: dict[str, Any], winning_outcome: str | None = "Yes") -> dict[str, Any]:
    """Load the blueprint, substitute `inputs`, and render the two optional
    branches' condition templates plus the TTS message."""
    blueprint = load_blueprint(BLUEPRINT_PATH)
    registry = MockRegistry()
    trigger = _trigger("Will X happen?", winning_outcome)

    variables = render_variables(blueprint, inputs, registry, extra_context={"trigger": trigger})
    context = {**variables, "trigger": trigger}

    # ENH-016 wrapped the original two branches inside a new outer "is this
    # automation currently snoozed" if/else (see test_enh016_actionable_
    # notifications.py) - the branches themselves, and this test's
    # assertions about them, are otherwise unchanged.
    substituted_action = substitute_inputs(blueprint["action"], blueprint, inputs)
    not_snoozed_branches = substituted_action[0]["else"][0]["then"]
    light_condition = not_snoozed_branches[0]["if"][0]["value_template"]
    tts_condition = not_snoozed_branches[1]["if"][0]["value_template"]
    tts_message_template = not_snoozed_branches[1]["then"][0]["data"]["message"]

    return {
        "light_fires": render_template(light_condition, registry, context),
        "tts_fires": render_template(tts_condition, registry, context),
        "tts_message": render_template(tts_message_template, registry, context),
    }


def test_defaults_skip_both_optional_branches() -> None:
    """BUG-004: with no light/TTS configured (the blueprint's own declared
    defaults - `flash_light: []`, `tts_target: []`, `tts_entity: ""`), both
    optional branches must stay off."""
    result = _render(inputs={})

    assert result["light_fires"] is False
    assert result["tts_fires"] is False


def test_configured_light_and_tts_both_fire() -> None:
    """When the user actually configures a light and a TTS target/engine,
    both branches must turn on."""
    result = _render(
        inputs={
            "flash_light": {"entity_id": ["light.living_room"]},
            "tts_target": {"entity_id": ["media_player.kitchen"]},
            "tts_entity": "tts.google_translate_say",
        }
    )

    assert result["light_fires"] is True
    assert result["tts_fires"] is True


def test_light_only_leaves_tts_off() -> None:
    """The two optional branches are independent: configuring only the
    light must not also turn on the (still unconfigured) TTS branch."""
    result = _render(
        inputs={"flash_light": {"entity_id": ["light.living_room"]}},
    )

    assert result["light_fires"] is True
    assert result["tts_fires"] is False


def test_tts_message_includes_winning_outcome_when_present() -> None:
    result = _render(
        inputs={
            "tts_target": {"entity_id": ["media_player.kitchen"]},
            "tts_entity": "tts.google_translate_say",
        },
        winning_outcome="Yes",
    )

    assert result["tts_message"] == "Will X happen? resolved as Yes."


def test_tts_message_omits_winning_outcome_when_none() -> None:
    result = _render(
        inputs={
            "tts_target": {"entity_id": ["media_player.kitchen"]},
            "tts_entity": "tts.google_translate_say",
        },
        winning_outcome=None,
    )

    assert result["tts_message"] == "Will X happen? resolved."
