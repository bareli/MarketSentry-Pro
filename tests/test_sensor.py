"""Tests for sensor.py's ENH-011 position-value logic: pure Python, no hass
fixture needed (see tests/test_init_detectors.py's module docstring - only
the full `hass` test *fixture* used by tests/config_flow/ needs the
POSIX-only `homeassistant.runner`; importing `homeassistant` modules at
module load time works fine on Windows once its dependencies are
installed)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from custom_components.marketsentry import InstrumentDetectors, InstrumentTracker
from custom_components.marketsentry.const import CONF_PROVIDER, OPT_QUANTITY
from custom_components.marketsentry.detector import (
    CooldownGate,
    PriceMoveDetector,
    ThresholdDetector,
)
from custom_components.marketsentry.providers.base import InstrumentRef, Quote
from custom_components.marketsentry.sensor import (
    PositionValueTotalSensor,
    _position_value,
    _unrealized_pnl,
)


@dataclass
class _FakeConfigEntry:
    """Just enough of `ConfigEntry` for `provider_connection_device_info`:
    `entry_id` and `data[CONF_PROVIDER]`."""

    entry_id: str = "entry1"
    data: dict[str, Any] = field(default_factory=lambda: {CONF_PROVIDER: "finnhub"})


def _ref(kind: str, instrument_id: str = "X", unit: str = "USD") -> InstrumentRef:
    return InstrumentRef(provider="test", id=instrument_id, symbol="X", name="X", kind=kind, unit=unit)


def _tracker(
    kind: str, quantity: float | None, price: float | None, unit: str = "USD", instrument_id: str = "X"
) -> InstrumentTracker:
    return InstrumentTracker(
        subentry_id=instrument_id,
        ref=_ref(kind, instrument_id, unit),
        options={OPT_QUANTITY: quantity},
        detectors=InstrumentDetectors(
            threshold=ThresholdDetector([], 0.0),
            move=PriceMoveDetector(5.0, 60, relative=kind != "outcome"),
        ),
        cooldown=CooldownGate(15),
        last_quote=Quote(price=price),
    )


def test_position_value_is_quantity_times_price_for_stock() -> None:
    assert _position_value(_ref("stock"), 10.0, 150.0) == 1500.0


def test_position_value_is_quantity_times_percent_scaled_price_for_outcome() -> None:
    """Matches `ProbabilitySensor.native_value`, which reports price*100
    (e.g. 0.65 -> 65.0), not the raw 0-1 probability."""
    assert _position_value(_ref("outcome"), 10.0, 0.65) == 650.0


def test_position_value_is_none_when_quantity_unset() -> None:
    """The opt-in default: a pure-watchlist instrument has no quantity set,
    and must get None, not 0 - this is what keeps it invisible by default."""
    assert _position_value(_ref("stock"), None, 150.0) is None


def test_position_value_is_none_when_no_live_price_yet() -> None:
    assert _position_value(_ref("stock"), 10.0, None) is None


def test_position_value_total_sums_only_trackers_with_quantity_set() -> None:
    """One instrument has a quantity, one does not - the total must only
    include the one that does, not treat the unset one as 0."""
    trackers = [
        _tracker("stock", quantity=10.0, price=150.0, instrument_id="AAPL"),
        _tracker("stock", quantity=None, price=300.0, instrument_id="MSFT"),
    ]
    sensor = PositionValueTotalSensor(entry=_FakeConfigEntry(), provider_name="Finnhub", kind="stock", unit="USD", trackers=trackers)
    assert sensor.native_value == 1500.0


def test_position_value_total_is_none_when_no_tracker_has_quantity_set() -> None:
    """Per-kind total reads unknown, not a misleading 0, until at least one
    instrument in the group has a quantity set."""
    trackers = [_tracker("crypto", quantity=None, price=65000.0, instrument_id="bitcoin")]
    sensor = PositionValueTotalSensor(entry=_FakeConfigEntry(), provider_name="CoinGecko", kind="crypto", unit="USD", trackers=trackers)
    assert sensor.native_value is None


def test_position_value_total_rounds_to_two_decimals() -> None:
    trackers = [
        _tracker("crypto", quantity=0.1, price=65000.111, instrument_id="bitcoin"),
        _tracker("crypto", quantity=1.0, price=3000.004, instrument_id="ethereum"),
    ]
    sensor = PositionValueTotalSensor(entry=_FakeConfigEntry(), provider_name="CoinGecko", kind="crypto", unit="USD", trackers=trackers)
    assert sensor.native_value == round(0.1 * 65000.111 + 1.0 * 3000.004, 2)


def test_unrealized_pnl_is_quantity_times_price_minus_cost_basis_for_stock() -> None:
    pnl, pnl_pct = _unrealized_pnl(10.0, 100.0, 150.0, is_outcome=False)
    assert pnl == 500.0
    assert pnl_pct == 50.0


def test_unrealized_pnl_is_percent_scaled_for_outcome() -> None:
    """Matches `_position_value`'s outcome convention: `price` (0-1) is
    scaled to the same 0-100 percent terms `cost_basis` is entered in
    (e.g. bought at 50, now worth 65 -> +15 absolute, +30%)."""
    pnl, pnl_pct = _unrealized_pnl(10.0, 50.0, 0.65, is_outcome=True)
    assert pnl == 150.0
    assert pnl_pct == 30.0


def test_unrealized_pnl_is_none_when_quantity_unset() -> None:
    assert _unrealized_pnl(None, 100.0, 150.0, is_outcome=False) == (None, None)


def test_unrealized_pnl_is_none_when_cost_basis_unset() -> None:
    """Unlike `_position_value` (which only needs quantity), P&L also needs
    cost_basis - that's the thing that makes P&L computable at all."""
    assert _unrealized_pnl(10.0, None, 150.0, is_outcome=False) == (None, None)


def test_unrealized_pnl_is_none_when_no_live_price_yet() -> None:
    assert _unrealized_pnl(10.0, 100.0, None, is_outcome=False) == (None, None)


def test_unrealized_pnl_pct_is_none_when_cost_basis_is_zero() -> None:
    """Division-by-zero guard: a 0 cost basis can't produce a percent, but
    the absolute P&L is still well-defined."""
    pnl, pnl_pct = _unrealized_pnl(10.0, 0.0, 150.0, is_outcome=False)
    assert pnl == 1500.0
    assert pnl_pct is None
