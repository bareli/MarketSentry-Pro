"""Constants for the Polymarket Watch integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "polymarket_watch"

# --- API endpoints ---
GAMMA_BASE_URL: Final = "https://gamma-api.polymarket.com"
CLOB_BASE_URL: Final = "https://clob.polymarket.com"
DATA_API_BASE_URL: Final = "https://data-api.polymarket.com"
CLOB_WS_URL: Final = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# --- Config entry keys ---
CONF_SLUG: Final = "slug"
CONF_KIND: Final = "kind"  # "event" or "market"
CONF_OUTCOME_TOKEN_IDS: Final = "outcome_token_ids"  # list of selected sub-market slugs
CONF_URL_OR_SLUG: Final = "url_or_slug"

KIND_EVENT: Final = "event"
KIND_MARKET: Final = "market"

# --- Options keys & defaults ---
OPT_THRESHOLDS: Final = "thresholds"
OPT_HYSTERESIS_PP: Final = "hysteresis_pp"
OPT_MOVE_DELTA_PP: Final = "move_delta_pp"
OPT_MOVE_WINDOW_MIN: Final = "move_window_min"
OPT_LARGE_TRADE_USD: Final = "large_trade_usd"
OPT_VOLUME_SPIKE_PCT: Final = "volume_spike_pct"
OPT_CLOSING_SOON_HOURS: Final = "closing_soon_hours"
OPT_COOLDOWN_MIN: Final = "cooldown_min"

DEFAULT_THRESHOLDS: Final = [30.0, 50.0, 70.0]
DEFAULT_HYSTERESIS_PP: Final = 0.5
DEFAULT_MOVE_DELTA_PP: Final = 5.0
DEFAULT_MOVE_WINDOW_MIN: Final = 60
DEFAULT_LARGE_TRADE_USD: Final = 10_000.0
DEFAULT_VOLUME_SPIKE_PCT: Final = 50.0
DEFAULT_CLOSING_SOON_HOURS: Final = 24
DEFAULT_COOLDOWN_MIN: Final = 15

# --- Update intervals ---
METADATA_UPDATE_INTERVAL_SEC: Final = 300
REST_FALLBACK_POLL_INTERVAL_SEC: Final = 60
WS_DOWN_FALLBACK_THRESHOLD_SEC: Final = 60
WS_PING_INTERVAL_SEC: Final = 10
WS_RECONNECT_MIN_SEC: Final = 1
WS_RECONNECT_MAX_SEC: Final = 300

# --- Entity write throttling ---
STATE_WRITE_MIN_INTERVAL_SEC: Final = 5
STATE_WRITE_MIN_DELTA_PP: Final = 0.1

# --- Event types ---
EVENT_THRESHOLD_CROSSED: Final = "threshold_crossed"
EVENT_PRICE_MOVE: Final = "price_move"
EVENT_LARGE_TRADE: Final = "large_trade"
EVENT_VOLUME_SPIKE: Final = "volume_spike"
EVENT_RESOLVED: Final = "resolved"
EVENT_CLOSING_SOON: Final = "closing_soon"

EVENT_TYPES: Final = [
    EVENT_THRESHOLD_CROSSED,
    EVENT_PRICE_MOVE,
    EVENT_LARGE_TRADE,
    EVENT_VOLUME_SPIKE,
    EVENT_RESOLVED,
    EVENT_CLOSING_SOON,
]

BUS_EVENT_PREFIX: Final = "polymarket_watch_"

# --- Resolution status enum ---
STATUS_OPEN: Final = "open"
STATUS_PROPOSED: Final = "proposed"
STATUS_DISPUTED: Final = "disputed"
STATUS_RESOLVED: Final = "resolved"
STATUS_CLOSED: Final = "closed"

# --- Services ---
SERVICE_GET_PRICE_HISTORY: Final = "get_price_history"
SERVICE_REFRESH: Final = "refresh"
SERVICE_SEARCH_MARKETS: Final = "search_markets"

ATTR_OUTCOME: Final = "outcome"
ATTR_INTERVAL: Final = "interval"
ATTR_FIDELITY: Final = "fidelity"
ATTR_QUERY: Final = "query"
ATTR_LIMIT: Final = "limit"

MANUFACTURER: Final = "Polymarket (unofficial)"
