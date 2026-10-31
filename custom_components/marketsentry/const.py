"""Constants for the MarketSentry Pro integration.

No HA imports here (matches detector.py's own rule) so this stays usable
from pure-Python provider/detector tests.
"""

from __future__ import annotations

from typing import Any, Final

DOMAIN: Final = "marketsentry"

# --- Polymarket API endpoints (used by api.py / ws.py / providers/polymarket.py) ---
GAMMA_BASE_URL: Final = "https://gamma-api.polymarket.com"
CLOB_BASE_URL: Final = "https://clob.polymarket.com"
DATA_API_BASE_URL: Final = "https://data-api.polymarket.com"
CLOB_WS_URL: Final = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# --- Config entry keys: one entry = one provider account ---
CONF_PROVIDER: Final = "provider"
CONF_API_KEY: Final = "api_key"
CONF_KEY_ID: Final = "key_id"
CONF_SECRET_KEY: Final = "secret_key"
CONF_FEED: Final = "feed"

PROVIDER_KEYS: Final = ("polymarket", "finnhub", "alpaca", "fx", "coingecko")

# --- Subentry keys: one subentry = one tracked instrument ---
SUBENTRY_TYPE_INSTRUMENT: Final = "instrument"

CONF_URL_OR_QUERY: Final = "url_or_query"
CONF_INSTRUMENT_ID: Final = "instrument_id"
CONF_SYMBOL: Final = "symbol"
CONF_INSTRUMENT_NAME: Final = "instrument_name"
CONF_INSTRUMENT_KIND: Final = "instrument_kind"
CONF_UNIT: Final = "unit"
CONF_URL: Final = "url"
CONF_EXTRA: Final = "extra"
CONF_OPTIONS: Final = "options"

# --- Per-instrument detection options (stored in subentry.data[CONF_OPTIONS]) ---
OPT_THRESHOLDS: Final = "thresholds"
OPT_HYSTERESIS: Final = "hysteresis"
OPT_MOVE_DELTA: Final = "move_delta"
OPT_MOVE_WINDOW_MIN: Final = "move_window_min"
OPT_DAILY_CHANGE_PCT: Final = "daily_change_pct"
OPT_LARGE_TRADE_USD: Final = "large_trade_usd"
OPT_VOLUME_SPIKE_PCT: Final = "volume_spike_pct"
OPT_CLOSING_SOON_HOURS: Final = "closing_soon_hours"
OPT_MARKET_OPEN_GAP_PCT: Final = "market_open_gap_pct"
OPT_EXTENDED_HOURS: Final = "extended_hours"
OPT_COOLDOWN_MIN: Final = "cooldown_min"

DEFAULT_COOLDOWN_MIN: Final = 15
DEFAULT_LARGE_TRADE_USD: Final = 10_000.0
DEFAULT_VOLUME_SPIKE_PCT: Final = 50.0
DEFAULT_CLOSING_SOON_HOURS: Final = 24
DEFAULT_MARKET_OPEN_GAP_PCT: Final = 3.0
DEFAULT_DAILY_CHANGE_PCT: Final = 3.0


def default_options_for_kind(kind: str) -> dict[str, Any]:
    """Kind-appropriate option defaults: pp for outcomes, percent for stocks/FX."""
    if kind == "outcome":
        return {
            OPT_THRESHOLDS: [30.0, 50.0, 70.0],
            OPT_HYSTERESIS: 0.5,
            OPT_MOVE_DELTA: 5.0,
            OPT_MOVE_WINDOW_MIN: 60,
            OPT_LARGE_TRADE_USD: DEFAULT_LARGE_TRADE_USD,
            OPT_VOLUME_SPIKE_PCT: DEFAULT_VOLUME_SPIKE_PCT,
            OPT_CLOSING_SOON_HOURS: DEFAULT_CLOSING_SOON_HOURS,
            OPT_COOLDOWN_MIN: DEFAULT_COOLDOWN_MIN,
        }
    if kind == "stock":
        return {
            OPT_THRESHOLDS: [],
            OPT_HYSTERESIS: 0.0,
            OPT_MOVE_DELTA: 2.0,
            OPT_MOVE_WINDOW_MIN: 60,
            OPT_DAILY_CHANGE_PCT: DEFAULT_DAILY_CHANGE_PCT,
            OPT_LARGE_TRADE_USD: DEFAULT_LARGE_TRADE_USD,
            OPT_MARKET_OPEN_GAP_PCT: DEFAULT_MARKET_OPEN_GAP_PCT,
            OPT_EXTENDED_HOURS: False,
            OPT_COOLDOWN_MIN: DEFAULT_COOLDOWN_MIN,
        }
    if kind == "crypto":
        return {
            OPT_THRESHOLDS: [],
            OPT_HYSTERESIS: 0.0,
            OPT_MOVE_DELTA: 3.0,
            OPT_MOVE_WINDOW_MIN: 60,
            OPT_DAILY_CHANGE_PCT: DEFAULT_DAILY_CHANGE_PCT,
            OPT_COOLDOWN_MIN: DEFAULT_COOLDOWN_MIN,
        }
    # fx
    return {
        OPT_THRESHOLDS: [],
        OPT_HYSTERESIS: 0.0,
        OPT_MOVE_DELTA: 0.5,
        OPT_MOVE_WINDOW_MIN: 24 * 60,
        OPT_DAILY_CHANGE_PCT: DEFAULT_DAILY_CHANGE_PCT,
        OPT_COOLDOWN_MIN: DEFAULT_COOLDOWN_MIN,
    }


# --- Update intervals ---
# The snapshot coordinator's REST poll (below) runs unconditionally every
# 5 minutes regardless of streaming state, which doubles as the streaming
# fallback; there's no separate WS-down-triggered fast-poll mode.
SNAPSHOT_POLL_INTERVAL_SEC: Final = 300
WS_PING_INTERVAL_SEC: Final = 10
WS_RECONNECT_MIN_SEC: Final = 1
WS_RECONNECT_MAX_SEC: Final = 300

# --- Entity write throttling ---
STATE_WRITE_MIN_INTERVAL_SEC: Final = 5
STATE_WRITE_MIN_DELTA: Final = 0.1

# --- Event types ---
EVENT_THRESHOLD_CROSSED: Final = "threshold_crossed"
EVENT_PRICE_MOVE: Final = "price_move"
EVENT_DAILY_CHANGE: Final = "daily_change"
EVENT_LARGE_TRADE: Final = "large_trade"
EVENT_VOLUME_SPIKE: Final = "volume_spike"
EVENT_RESOLVED: Final = "resolved"
EVENT_CLOSING_SOON: Final = "closing_soon"
EVENT_MARKET_OPEN_GAP: Final = "market_open_gap"
EVENT_OFFICIAL_RATE_PUBLISHED: Final = "official_rate_published"

EVENT_TYPES_BY_KIND: Final[dict[str, list[str]]] = {
    "outcome": [
        EVENT_THRESHOLD_CROSSED,
        EVENT_PRICE_MOVE,
        EVENT_LARGE_TRADE,
        EVENT_VOLUME_SPIKE,
        EVENT_RESOLVED,
        EVENT_CLOSING_SOON,
    ],
    "stock": [
        EVENT_THRESHOLD_CROSSED,
        EVENT_PRICE_MOVE,
        EVENT_DAILY_CHANGE,
        EVENT_LARGE_TRADE,
        EVENT_MARKET_OPEN_GAP,
    ],
    "fx": [
        EVENT_THRESHOLD_CROSSED,
        EVENT_PRICE_MOVE,
        EVENT_DAILY_CHANGE,
        EVENT_OFFICIAL_RATE_PUBLISHED,
    ],
    "crypto": [
        EVENT_THRESHOLD_CROSSED,
        EVENT_PRICE_MOVE,
        EVENT_DAILY_CHANGE,
    ],
}

ALL_EVENT_TYPES: Final = sorted({e for types in EVENT_TYPES_BY_KIND.values() for e in types})

BUS_EVENT_PREFIX: Final = "marketsentry_"

# --- Resolution status enum (outcome kind only) ---
STATUS_OPEN: Final = "open"
STATUS_PROPOSED: Final = "proposed"
STATUS_DISPUTED: Final = "disputed"
STATUS_RESOLVED: Final = "resolved"
STATUS_CLOSED: Final = "closed"

# --- Market state enum (stock kind only) ---
MARKET_STATE_PRE: Final = "pre"
MARKET_STATE_REGULAR: Final = "regular"
MARKET_STATE_POST: Final = "post"
MARKET_STATE_CLOSED: Final = "closed"

# --- Services ---
SERVICE_GET_PRICE_HISTORY: Final = "get_price_history"
SERVICE_REFRESH: Final = "refresh"
SERVICE_SEARCH_INSTRUMENTS: Final = "search_instruments"

ATTR_HOURS: Final = "hours"
ATTR_QUERY: Final = "query"
ATTR_LIMIT: Final = "limit"

PROVIDER_MANUFACTURER: Final[dict[str, str]] = {
    "polymarket": "Polymarket (unofficial)",
    "finnhub": "Finnhub (unofficial)",
    "alpaca": "Alpaca (unofficial)",
    "fx": "Frankfurter / Bank of Israel (unofficial)",
    "coingecko": "CoinGecko (unofficial)",
}
