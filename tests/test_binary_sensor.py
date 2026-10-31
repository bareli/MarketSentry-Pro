"""Tests for binary_sensor.py's StreamConnectedBinarySensor (ENH-007): the
sensor must surface the real connection phase each provider's `stream()`
loop reports, not just "the asyncio task hasn't died" - plain Python, no
hass fixture needed (see tests/test_sensor.py's module docstring: importing
homeassistant modules and instantiating its entity base classes at module
load time works fine on Windows, only the full `hass` test *fixture* used
by tests/config_flow/ needs the POSIX-only `homeassistant.runner`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from custom_components.marketsentry.binary_sensor import StreamConnectedBinarySensor
from custom_components.marketsentry.const import CONF_PROVIDER


@dataclass
class _FakeRuntimeData:
    """Just enough of `MarketSentryRuntimeData` for `StreamConnectedBinarySensor`."""

    provider_name: str = "Finnhub (stocks)"
    stream_connected: bool = False
    stream_phase: str = "connecting"
    stream_reconnect_count: int = 0


@dataclass
class _FakeConfigEntry:
    """Just enough of `ConfigEntry` for `provider_connection_device_info` plus
    `entry.runtime_data`."""

    entry_id: str = "entry1"
    data: dict[str, Any] = field(default_factory=lambda: {CONF_PROVIDER: "finnhub"})
    runtime_data: _FakeRuntimeData = field(default_factory=_FakeRuntimeData)


def test_is_on_false_while_connecting_even_though_stream_task_is_alive() -> None:
    """The core ENH-007 fix: before the fix, this sensor read "on" purely
    because the stream task hadn't died, even while still connecting for
    the first time. Now it must read off until a connection is actually
    established."""
    entry = _FakeConfigEntry(runtime_data=_FakeRuntimeData(stream_connected=False, stream_phase="connecting"))
    sensor = StreamConnectedBinarySensor(entry)

    assert sensor.is_on is False


def test_is_on_false_while_silently_reconnecting_in_a_tight_loop() -> None:
    """Matches the bug record's exact scenario: bad credentials that pass
    initial auth, or a flaky network, causing silent reconnects - the
    sensor must not read "connected" the whole time."""
    entry = _FakeConfigEntry(
        runtime_data=_FakeRuntimeData(stream_connected=False, stream_phase="reconnecting", stream_reconnect_count=5)
    )
    sensor = StreamConnectedBinarySensor(entry)

    assert sensor.is_on is False
    assert sensor.extra_state_attributes == {"reconnecting": True, "reconnect_count": 5}


def test_is_on_true_only_once_actually_connected() -> None:
    entry = _FakeConfigEntry(
        runtime_data=_FakeRuntimeData(stream_connected=True, stream_phase="connected", stream_reconnect_count=2)
    )
    sensor = StreamConnectedBinarySensor(entry)

    assert sensor.is_on is True
    assert sensor.extra_state_attributes == {"reconnecting": False, "reconnect_count": 2}


def test_extra_state_attributes_reports_reconnecting_during_backoff_too() -> None:
    """"backing_off" (waiting before the next reconnect attempt) counts as
    reconnecting from the user's point of view, same as the active retry."""
    entry = _FakeConfigEntry(
        runtime_data=_FakeRuntimeData(stream_connected=False, stream_phase="backing_off", stream_reconnect_count=1)
    )
    sensor = StreamConnectedBinarySensor(entry)

    assert sensor.extra_state_attributes == {"reconnecting": True, "reconnect_count": 1}


def test_reconnect_count_resets_to_zero_for_a_fresh_stream() -> None:
    entry = _FakeConfigEntry()
    sensor = StreamConnectedBinarySensor(entry)

    assert sensor.extra_state_attributes == {"reconnecting": False, "reconnect_count": 0}
