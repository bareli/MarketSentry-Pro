"""hass-dependent fixtures, scoped to this subpackage only.

Requires pytest-homeassistant-custom-component, which pulls in
homeassistant.runner (POSIX-only `fcntl`) -- run these tests on Linux/macOS
or in CI, not natively on Windows.

No `pytest_plugins` declaration here: the package registers itself
automatically via its own `pytest11` entry point once installed (and
modern pytest rejects `pytest_plugins` in a non-top-level conftest
outright), so declaring it here would be both redundant and a CI error.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
