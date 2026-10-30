"""CLOB market WebSocket manager.

No HA imports beyond type-only callback signatures. Owns one shared
connection, subscribes/unsubscribes token IDs dynamically, reconnects with
exponential backoff + jitter, and sends PING every 10s.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import ClientSession, ClientWSTimeout, WSMsgType

from .const import (
    CLOB_WS_URL,
    WS_PING_INTERVAL_SEC,
    WS_RECONNECT_MAX_SEC,
    WS_RECONNECT_MIN_SEC,
)

_LOGGER = logging.getLogger(__name__)

MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]


class PolymarketWsManager:
    """Manages a single shared WebSocket connection for all config entries."""

    def __init__(
        self,
        session: ClientSession,
        on_message: MessageHandler,
        on_connection_state_change: Callable[[bool], None] | None = None,
        url: str = CLOB_WS_URL,
    ) -> None:
        self._session = session
        self._on_message = on_message
        self._on_connection_state_change = on_connection_state_change
        self._url = url

        self._subscribed_tokens: set[str] = set()
        self._ws: Any = None
        self._run_task: asyncio.Task[None] | None = None
        self._stopped = False
        self._connected = False
        self._last_message_time: float | None = None
        self._reconnect_attempt = 0

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def last_message_age_sec(self) -> float | None:
        if self._last_message_time is None:
            return None
        return time.monotonic() - self._last_message_time

    @property
    def subscribed_token_count(self) -> int:
        return len(self._subscribed_tokens)

    async def start(self) -> None:
        self._stopped = False
        if self._run_task is None or self._run_task.done():
            self._run_task = asyncio.create_task(self._run_forever())

    async def stop(self) -> None:
        self._stopped = True
        if self._run_task is not None:
            self._run_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._run_task
            self._run_task = None
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        self._set_connected(False)

    async def subscribe(self, token_ids: list[str]) -> None:
        new_tokens = [t for t in token_ids if t not in self._subscribed_tokens]
        self._subscribed_tokens.update(token_ids)
        if new_tokens and self._ws is not None and self._connected:
            await self._send_json(
                {"operation": "subscribe", "assets_ids": new_tokens}
            )

    async def unsubscribe(self, token_ids: list[str]) -> None:
        tokens_to_remove = [t for t in token_ids if t in self._subscribed_tokens]
        self._subscribed_tokens.difference_update(token_ids)
        if tokens_to_remove and self._ws is not None and self._connected:
            await self._send_json(
                {"operation": "unsubscribe", "assets_ids": tokens_to_remove}
            )

    async def _send_json(self, payload: dict[str, Any]) -> None:
        if self._ws is None:
            return
        await self._ws.send_str(json.dumps(payload))

    def _set_connected(self, connected: bool) -> None:
        if connected != self._connected:
            self._connected = connected
            if self._on_connection_state_change is not None:
                self._on_connection_state_change(connected)

    async def _run_forever(self) -> None:
        while not self._stopped:
            try:
                await self._connect_and_listen()
                self._reconnect_attempt = 0
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Polymarket WS connection error: %s", err)
            finally:
                self._set_connected(False)
                self._ws = None

            if self._stopped:
                break

            delay = self._next_backoff_delay()
            _LOGGER.debug("Reconnecting to Polymarket WS in %.1fs", delay)
            await asyncio.sleep(delay)

    def _next_backoff_delay(self) -> float:
        self._reconnect_attempt += 1
        base = min(
            WS_RECONNECT_MIN_SEC * (2 ** (self._reconnect_attempt - 1)),
            WS_RECONNECT_MAX_SEC,
        )
        jitter = random.uniform(0, base * 0.25)
        return float(base + jitter)

    async def _connect_and_listen(self) -> None:
        timeout = ClientWSTimeout(ws_close=10)
        async with self._session.ws_connect(self._url, timeout=timeout) as ws:
            self._ws = ws
            if self._subscribed_tokens:
                await self._send_json(
                    {
                        "assets_ids": sorted(self._subscribed_tokens),
                        "type": "market",
                        "custom_feature_enabled": True,
                    }
                )
            self._set_connected(True)

            ping_task = asyncio.create_task(self._ping_loop(ws))
            try:
                async for msg in ws:
                    self._last_message_time = time.monotonic()
                    if msg.type == WSMsgType.TEXT:
                        await self._handle_text_message(msg.data)
                    elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR):
                        break
            finally:
                ping_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await ping_task

    async def _handle_text_message(self, data: str) -> None:
        if data == "PONG":
            return
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            _LOGGER.debug("Non-JSON WS message: %s", data)
            return

        messages = parsed if isinstance(parsed, list) else [parsed]
        for message in messages:
            if isinstance(message, dict):
                await self._on_message(message)

    async def _ping_loop(self, ws: Any) -> None:
        try:
            while True:
                await asyncio.sleep(WS_PING_INTERVAL_SEC)
                await ws.send_str("PING")
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Polymarket WS ping failed: %s", err)
