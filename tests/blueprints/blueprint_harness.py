"""Reusable harness for rendering MarketSentry Pro's automation blueprints'
Jinja templates without a running Home Assistant instance.

This replaces the one-off hand-trace scripts used for BUG-004, UX-002, UX-003
and ENH-006 (see `qa/bugs/ENH-006.md`'s verification section for the most
recent example) with something that runs under `pytest`.

Two things a blueprint YAML needs that a plain `yaml.safe_load` /
`jinja2.Environment` do not provide out of the box:

1. The `!input <name>` tag. Home Assistant's real blueprint engine
   (`annotatedyaml.input.substitute`) only replaces a YAML node that *is* an
   `Input` placeholder - not any plain string that happens to match an
   input's name elsewhere in the document. `BlueprintInputRef`/
   `substitute_inputs` below reproduce exactly that: a literal `!input foo`
   node becomes a `BlueprintInputRef("foo")` on load, and only a node that
   *is* one of those gets replaced by `substitute_inputs`, falling back to
   the input's own declared `default` when the caller didn't configure it.
   This distinction is what BUG-004 turned on: `resolved_announce.yaml`
   referenced `flash_light`/`tts_entity`/`tts_target` directly in template
   condition *strings* without ever binding them through `variables:`, so at
   render time they were unbound Jinja names (`Undefined`), not the
   substituted value - this harness reproduces that unbound-name behaviour
   faithfully instead of accidentally "fixing" it by auto-binding every
   input name into the template context.

2. The Home Assistant template globals these three blueprints actually call.
   Grepped from all three blueprint YAMLs, that is exactly: `expand`,
   `integration_entities`, and `device_name` (plus the built-in Jinja
   filters/tests they use - `selectattr`, `truncate`, `count`, `list`,
   `default` - which come for free from a plain `jinja2.Environment` and
   need no mocking). `is_state`/`state_attr`/`device_attr` are mentioned in
   ENH-020's brief as *examples* of HA template globals in general, but none
   of the three blueprints call them, so they are not mocked here - see
   ENH-020's handback for why.

   Real contracts (confirmed by reading `homeassistant/helpers/template.py`
   in the `homeassistant` PyPI package - see ENH-020's handback for the
   version note: PyPI's newest available build at the time of this work was
   2025.4.4, which still has these as plain functions in one module rather
   than the `helpers/template/extensions/` package layout newer HA versions
   use; the contracts below match that source, and `device_name`'s contract
   additionally matches what ENH-006 already confirmed and relied on when
   it implemented `daily_digest.yaml`'s device-name preference):

   - `expand(*entities)` -> resolves each entity id (or iterable of entity
     ids) to its `State` object, skipping anything with no registered
     state. Real HA also expands groups/zones recursively; none of these
     blueprints ever pass one, so that part is not reproduced.
   - `integration_entities(domain)` -> entity ids belonging to that
     integration domain. Real HA tries a config-entry-title match first,
     then falls back to a plain domain match via `entity_sources()`. The
     blueprints always call this with the domain name itself
     (`integration_entities('marketsentry')`), so only the domain-match
     fallback path is reproduced.
   - `device_name(entity_id)` -> the entity's device's `name_by_user or
     name`, or `None` if the entity has no device, or isn't registered at
     all.

   ENH-016 added a fourth: `is_state(entity_id, state)` -> `True` if the
   entity is currently in exactly that state, `False` otherwise (including
   when the entity doesn't exist at all - real HA returns `False` rather
   than raising for an unknown/malformed entity id, which is what the
   snooze-helper condition in both `notify_on_event.yaml` and
   `resolved_announce.yaml` relies on for the "no helper configured" case).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jinja2
import yaml

BLUEPRINTS_DIR = (
    Path(__file__).resolve().parents[2] / "blueprints" / "automation" / "marketsentry"
)

_BARE_EXPR = re.compile(r"^\{\{(?P<expr>.*)\}\}$", re.DOTALL)


class BlueprintInputRef(str):
    """A YAML node that was `!input <name>`; its own string value is the
    input's name, exactly what HA's blueprint loader produces for that node
    before substitution replaces it with the configured/default value."""


class _BlueprintLoader(yaml.SafeLoader):
    pass


def _construct_input(loader: yaml.SafeLoader, node: yaml.Node) -> BlueprintInputRef:
    return BlueprintInputRef(loader.construct_scalar(node))


_BlueprintLoader.add_constructor("!input", _construct_input)


def load_blueprint(path: Path) -> dict[str, Any]:
    """Parse a blueprint YAML file, tolerating its `!input` tags."""
    with path.open(encoding="utf-8") as f:
        return yaml.load(f, Loader=_BlueprintLoader)


def _declared_default(blueprint: dict[str, Any], name: str) -> Any:
    declared_inputs = blueprint["blueprint"]["input"]
    return declared_inputs[name].get("default")


def substitute_inputs(node: Any, blueprint: dict[str, Any], inputs: dict[str, Any]) -> Any:
    """Replace every literal `!input <name>` node with its configured value
    (or the blueprint's own declared default when `inputs` doesn't set it).

    Only a node that *is* a `BlueprintInputRef` is replaced - a plain string
    elsewhere in the tree that happens to equal an input's name is left
    alone. See the module docstring / BUG-004.
    """
    if isinstance(node, BlueprintInputRef):
        name = str(node)
        if name in inputs:
            return inputs[name]
        return _declared_default(blueprint, name)
    if isinstance(node, dict):
        return {k: substitute_inputs(v, blueprint, inputs) for k, v in node.items()}
    if isinstance(node, list):
        return [substitute_inputs(v, blueprint, inputs) for v in node]
    return node


@dataclass
class MockState:
    """Stand-in for HA's `homeassistant.core.State`."""

    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class MockDevice:
    """Stand-in for HA's device registry entry, just the two name fields
    `device_name()` reads."""

    id: str
    name: str | None = None
    name_by_user: str | None = None


@dataclass
class MockRegistry:
    """Simple python stand-in for HA's state machine + entity/device
    registries, holding just enough to back `expand`, `integration_entities`
    and `device_name`."""

    states: dict[str, MockState] = field(default_factory=dict)
    entity_domain: dict[str, str] = field(default_factory=dict)
    entity_device: dict[str, str] = field(default_factory=dict)
    devices: dict[str, MockDevice] = field(default_factory=dict)

    def add_entity(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
        domain: str = "marketsentry",
        device: MockDevice | None = None,
    ) -> None:
        """Register one tracked entity, optionally attached to a device."""
        self.states[entity_id] = MockState(entity_id, state, attributes or {})
        self.entity_domain[entity_id] = domain
        if device is not None:
            self.devices[device.id] = device
            self.entity_device[entity_id] = device.id

    def expand(self, *args: Any) -> list[MockState]:
        found: dict[str, MockState] = {}
        search: list[Any] = list(args)
        while search:
            item = search.pop()
            if isinstance(item, str):
                state = self.states.get(item)
                if state is not None:
                    found[state.entity_id] = state
            elif isinstance(item, Iterable):
                search.extend(item)
        return list(found.values())

    def integration_entities(self, domain: str) -> list[str]:
        if not domain:
            return []
        return [eid for eid, d in self.entity_domain.items() if d == domain]

    def device_name(self, entity_id: str) -> str | None:
        device_id = self.entity_device.get(entity_id)
        if device_id is None:
            return None
        device = self.devices.get(device_id)
        if device is None:
            return None
        return device.name_by_user or device.name

    def is_state(self, entity_id: Any, state: str) -> bool:
        if not isinstance(entity_id, str):
            return False
        found = self.states.get(entity_id)
        if found is None:
            return False
        return found.state == state


def build_environment(registry: MockRegistry) -> jinja2.Environment:
    """A `jinja2.Environment` with the HA template globals these blueprints
    call, backed by `registry`.

    `undefined=jinja2.Undefined` matches BUG-004's own reproduction: HA's
    real `LoggingUndefined` subclasses `jinja2.Undefined` without touching
    `__eq__`/`__ne__`/`__bool__`, so a bare `jinja2.Undefined` reproduces the
    same "an unbound name compares truthy" behaviour that bug turned on.
    """
    env = jinja2.Environment(undefined=jinja2.Undefined, autoescape=False)
    env.globals["expand"] = registry.expand
    env.globals["integration_entities"] = registry.integration_entities
    env.globals["device_name"] = registry.device_name
    env.globals["is_state"] = registry.is_state
    return env


def _render_value(env: jinja2.Environment, value: Any, context: dict[str, Any]) -> Any:
    """Render one substituted value.

    A plain (non-template) value passes through unchanged. A template string
    that is *only* a single `{{ expression }}` renders to the expression's
    native Python type (via `Environment.compile_expression`), matching real
    HA's "a template with exactly one output node keeps its native type"
    behaviour - needed here because `daily_digest.yaml`'s `tracked` variable
    must stay a real list for the `digest` variable's `for s in tracked` to
    work. Anything else (literal text mixed with one or more expressions, or
    control-flow tags) renders to a string via the normal template render.
    """
    if not isinstance(value, str) or ("{{" not in value and "{%" not in value):
        return value
    stripped = value.strip()
    match = _BARE_EXPR.match(stripped)
    if match and stripped.count("{{") == 1 and "{%" not in stripped:
        compiled_expression = env.compile_expression(match.group("expr"))
        return compiled_expression(**context)
    return env.from_string(value).render(**context)


def render_variables(
    blueprint: dict[str, Any],
    inputs: dict[str, Any],
    registry: MockRegistry,
    extra_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render a blueprint's `variables:` block, in declaration order.

    Each entry is substituted (`!input` -> configured/default value) and
    then rendered (see `_render_value`). Earlier variables, plus
    `extra_context` (e.g. a mock `trigger`), are visible to later ones -
    matching how HA evaluates a blueprint's `variables:` block top to
    bottom.
    """
    env = build_environment(registry)
    raw_variables = blueprint.get("variables") or {}
    context: dict[str, Any] = dict(extra_context or {})
    rendered: dict[str, Any] = {}
    for name, raw_value in raw_variables.items():
        value = substitute_inputs(raw_value, blueprint, inputs)
        value = _render_value(env, value, context)
        context[name] = value
        rendered[name] = value
    return rendered


def render_template(
    template_str: str,
    registry: MockRegistry,
    context: dict[str, Any] | None = None,
) -> Any:
    """Render one ad hoc template string (an action's `value_template`,
    `message`, etc.) against `registry` and `context` (typically rendered
    `variables:` plus a mock `trigger`)."""
    env = build_environment(registry)
    return _render_value(env, template_str, context or {})
