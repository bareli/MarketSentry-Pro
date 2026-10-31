"""Tests for __init__.py's `_build_detectors`: kind/option-key wiring.

Pure Python - no hass fixture needed. `custom_components.marketsentry` only
*imports* homeassistant modules at module load time (which works fine on
Windows); only the `hass` test *fixture* used by `tests/config_flow/` needs
the POSIX-only `homeassistant.runner` (`fcntl`). `_build_detectors` and
`default_options_for_kind` are both plain functions this file calls directly.
"""

from __future__ import annotations

import custom_components.marketsentry as msp
from custom_components.marketsentry.const import default_options_for_kind
from custom_components.marketsentry.providers.base import InstrumentRef


def _ref(kind: str, instrument_id: str) -> InstrumentRef:
    return InstrumentRef(
        provider="test", id=instrument_id, symbol="X", name="X", kind=kind, unit="USD"
    )


def test_build_detectors_crypto_matches_its_default_options() -> None:
    """DET-09: crypto gets exactly threshold/move/daily_change, nothing else -
    matching default_options_for_kind("crypto") and EVENT_TYPES_BY_KIND["crypto"]."""
    detectors = msp._build_detectors(_ref("crypto", "bitcoin"), default_options_for_kind("crypto"))

    assert detectors.threshold is not None
    assert detectors.move is not None
    assert detectors.daily_change is not None
    assert detectors.large_trade is None
    assert detectors.volume_spike is None
    assert detectors.closing_soon is None
    assert detectors.resolved is None
    assert detectors.market_open_gap is None
    assert detectors.official_rate_published is None


def test_build_detectors_fx_wires_official_rate_published_only_for_boi_refs() -> None:
    """BUG-005 regression: "official rate published" is a Bank-of-Israel-only concept
    (README, qa/plans/DET-detectors.md DET-07). `_build_detectors` now takes the full
    `InstrumentRef` (not just the kind) so it can tell a Frankfurter-sourced fx instrument
    (id "frankfurter:EUR:ILS") apart from a Bank-of-Israel-sourced one (id "boi:EUR:ILS") -
    only the latter should get an OfficialRatePublishedDetector wired. Before the fix, every
    fx ref got one unconditionally regardless of source."""
    fx_opts = default_options_for_kind("fx")

    boi_detectors = msp._build_detectors(_ref("fx", "boi:EUR:ILS"), fx_opts)
    frankfurter_detectors = msp._build_detectors(_ref("fx", "frankfurter:EUR:ILS"), fx_opts)

    assert boi_detectors.official_rate_published is not None, (
        "a boi:-sourced fx ref must get the official_rate_published detector wired"
    )
    assert frankfurter_detectors.official_rate_published is None, (
        "a frankfurter:-sourced fx ref must NOT get the official_rate_published detector wired - "
        "it is a Bank-of-Israel-only concept"
    )
