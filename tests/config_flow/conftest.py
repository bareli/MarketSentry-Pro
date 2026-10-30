"""hass-dependent fixtures, scoped to this subpackage only.

Requires pytest-homeassistant-custom-component, which pulls in
homeassistant.runner (POSIX-only `fcntl`) -- run these tests on Linux/macOS
or in CI, not natively on Windows.
"""

from __future__ import annotations

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
