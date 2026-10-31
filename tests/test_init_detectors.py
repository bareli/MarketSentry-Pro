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


def test_build_detectors_crypto_matches_its_default_options() -> None:
    """DET-09: crypto gets exactly threshold/move/daily_change, nothing else -
    matching default_options_for_kind("crypto") and EVENT_TYPES_BY_KIND["crypto"]."""
    detectors = msp._build_detectors("crypto", default_options_for_kind("crypto"))

    assert detectors.threshold is not None
    assert detectors.move is not None
    assert detectors.daily_change is not None
    assert detectors.large_trade is None
    assert detectors.volume_spike is None
    assert detectors.closing_soon is None
    assert detectors.resolved is None
    assert detectors.market_open_gap is None
    assert detectors.official_rate_published is None


def test_build_detectors_fx_wires_official_rate_published_for_every_fx_instrument() -> None:
    """DET-07 regression: `_build_detectors` takes only `kind` (never the ref/id), so it
    cannot distinguish a Frankfurter-sourced fx instrument (id "frankfurter:EUR:ILS") from a
    Bank-of-Israel-sourced one (id "boi:EUR:ILS") - every fx instrument gets an
    OfficialRatePublishedDetector wired, even though "official rate published" is documented
    (README, qa/plans/DET-detectors.md DET-07) as a Bank-of-Israel-only concept. See BUG-005:
    `__init__.py`'s `_async_process_quote` also calls this detector unconditionally for every fx
    tracker regardless of `tracker.ref.id`'s source prefix, so a Frankfurter instrument's quote
    (whose `Quote.ts` changes date once a day, same as BOI's) will fire the
    `marketsentry_official_rate_published` bus event too."""
    fx_opts = default_options_for_kind("fx")

    detectors = msp._build_detectors("fx", fx_opts)

    assert detectors.official_rate_published is not None, (
        "fx gets this detector unconditionally - _build_detectors has no way to wire it "
        "only for boi-sourced refs, since it never receives the InstrumentRef/id at all"
    )
