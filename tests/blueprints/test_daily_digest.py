"""Regression tests for `daily_digest.yaml` - ENH-006 and the BP-03
"no instruments tracked yet" empty branch.

ENH-006: the digest line for an entity should prefer its device's plain
name (`device_name(entity_id)`, which internally reads
`device.name_by_user or device.name`) over the sensor's own, possibly
longer `friendly_name`, falling back to `friendly_name` when there is no
device match. UX-003's remainder (60-char truncation) is copy-only, not a
template-execution concern, and is not covered here (see ENH-020's
handback).
"""

from __future__ import annotations

from .blueprint_harness import (
    BLUEPRINTS_DIR,
    MockDevice,
    MockRegistry,
    load_blueprint,
    render_variables,
)

BLUEPRINT_PATH = BLUEPRINTS_DIR / "daily_digest.yaml"


def _digest(registry: MockRegistry) -> str:
    blueprint = load_blueprint(BLUEPRINT_PATH)
    variables = render_variables(blueprint, inputs={}, registry=registry)
    return variables["digest"]


def test_empty_digest_when_no_instruments_tracked() -> None:
    registry = MockRegistry()

    assert _digest(registry) == "No MarketSentry Pro instruments are tracked yet."


def test_digest_prefers_device_name_over_friendly_name() -> None:
    registry = MockRegistry()
    registry.add_entity(
        "sensor.will_x_happen_probability",
        state="0.62",
        attributes={"kind": "outcome", "friendly_name": "Will X happen? Probability"},
        device=MockDevice(id="dev-1", name="Will X happen?"),
    )

    digest = _digest(registry)

    assert "Will X happen?: 0.62" in digest
    assert "Probability" not in digest


def test_digest_falls_back_to_friendly_name_when_no_device_match() -> None:
    registry = MockRegistry()
    registry.add_entity(
        "sensor.msft_price",
        state="410.2",
        attributes={"kind": "stock", "friendly_name": "MSFT Price", "unit_of_measurement": "USD"},
    )

    digest = _digest(registry)

    assert "MSFT Price: 410.2 USD" in digest


def test_digest_excludes_entities_outside_the_marketsentry_domain() -> None:
    """`integration_entities('marketsentry')` must not pick up an entity
    from an unrelated integration living in the same mock registry."""
    registry = MockRegistry()
    registry.add_entity(
        "sensor.msft_price",
        state="410.2",
        attributes={"kind": "stock", "friendly_name": "MSFT Price"},
    )
    registry.add_entity(
        "sensor.outdoor_temperature",
        state="18.0",
        attributes={"kind": "temperature"},
        domain="other_integration",
    )

    digest = _digest(registry)

    assert "MSFT Price: 410.2" in digest
    assert "18.0" not in digest
    assert "outdoor_temperature" not in digest
