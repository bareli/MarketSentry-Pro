"""Shared, plain-data fixtures for MarketSentry Pro tests.

No Home Assistant test-harness plugin here on purpose: test_models.py,
test_detector.py, test_api.py, and test_ws.py exercise pure-Python /
aiohttp-only modules and must be runnable without the full `hass` fixture
(which pytest-homeassistant-custom-component cannot provide on Windows,
since homeassistant.runner imports the POSIX-only `fcntl` module). The
`hass`-dependent config flow tests register that plugin themselves in
tests/config_flow/conftest.py.

pytest-homeassistant-custom-component registers itself via its own
pytest11 entry point (see tests/config_flow/conftest.py's docstring) and
brings in pytest-socket, which blocks real socket creation session-wide
once loaded -- including the loopback sockets our aiohttp_client-based
fake-server tests (test_api.py, test_ws.py, providers/test_*.py) need for
their local test servers. Requesting the `socket_enabled` fixture
re-enables sockets for the duration of a test; doing it autouse here
covers every test module without touching each test's signature.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _allow_sockets_for_local_test_servers(socket_enabled: None) -> None:
    """No-op body: requesting `socket_enabled` is what re-enables sockets."""


GAMMA_MARKET_FIXTURE = {
    "id": "1",
    "slug": "will-x-happen",
    "question": "Will X happen?",
    "conditionId": "0xabc",
    "active": True,
    "closed": False,
    "acceptingOrders": True,
    "endDate": "2027-01-01T00:00:00Z",
    "volumeNum": "1000.0",
    "volume24hr": "100.0",
    "liquidityNum": "500.0",
    "closedTime": None,
    "umaResolutionStatus": None,
    "outcomes": '["Yes", "No"]',
    "outcomePrices": '["0.6", "0.4"]',
    "clobTokenIds": '["111", "222"]',
}

GAMMA_EVENT_SINGLE_MARKET_FIXTURE = {
    "id": "10",
    "slug": "some-event",
    "title": "Some event",
    "active": True,
    "closed": False,
    "ended": False,
    "endDate": "2027-01-01T00:00:00Z",
    "volume": 1000,
    "volume24hr": 100,
    "liquidity": 500,
    "negRisk": False,
    "markets": [GAMMA_MARKET_FIXTURE],
}

GAMMA_EVENT_MULTI_MARKET_FIXTURE = {
    "id": "11",
    "slug": "multi-event",
    "title": "Multi event",
    "active": True,
    "closed": False,
    "ended": False,
    "endDate": "2027-01-01T00:00:00Z",
    "volume": 1000,
    "volume24hr": 100,
    "liquidity": 500,
    "negRisk": True,
    "markets": [
        {**GAMMA_MARKET_FIXTURE, "slug": "sub-a", "question": "Sub A?"},
        {**GAMMA_MARKET_FIXTURE, "slug": "sub-b", "question": "Sub B?"},
    ],
}
