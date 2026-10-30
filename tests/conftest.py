"""Shared, plain-data fixtures for Polymarket Watch tests.

No Home Assistant test-harness plugin here on purpose: test_models.py,
test_detector.py, test_api.py, and test_ws.py exercise pure-Python /
aiohttp-only modules and must be runnable without the full `hass` fixture
(which pytest-homeassistant-custom-component cannot provide on Windows,
since homeassistant.runner imports the POSIX-only `fcntl` module). The
`hass`-dependent config flow tests register that plugin themselves in
tests/config_flow/conftest.py.
"""

from __future__ import annotations

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
