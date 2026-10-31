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

Both pytest-aiohttp and pytest-homeassistant-custom-component provide a
fixture named `aiohttp_client`, and once both plugins are active (as in
CI, where sockets aren't blocked so pytest-homeassistant-custom-component
fully loads) the one that wins shadows ours unpredictably - and HA's
version raised "Timeout context manager should be used inside a task"
for every request, since it isn't meant for standalone aiohttp testing
outside of a `hass` instance. Defining our own `aiohttp_client` fixture
here (a root conftest fixture always takes precedence over a
plugin-provided one of the same name) removes the ambiguity for every
test in the tree without changing any test file.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


@pytest.fixture(autouse=True)
def _allow_sockets_for_local_test_servers(socket_enabled: None) -> None:
    """No-op body: requesting `socket_enabled` is what re-enables sockets."""


@pytest.fixture
async def aiohttp_client() -> AsyncIterator[Callable[[web.Application], Awaitable[TestClient]]]:
    clients: list[TestClient] = []

    async def _make_client(app: web.Application) -> TestClient:
        client = TestClient(TestServer(app))
        await client.start_server()
        clients.append(client)
        return client

    yield _make_client

    for client in clients:
        await client.close()


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
