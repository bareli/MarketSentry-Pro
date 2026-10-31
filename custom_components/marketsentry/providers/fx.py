"""FX provider: exchange rates from two sources, no API key for either.

- Frankfurter (ECB-based market mid rate, frankfurter.dev): daily rates,
  wide currency coverage, no key. **Confirmed live (ENH-008, 2026-10-31)**:
  base URL `https://api.frankfurter.dev/v1` is correct and canonical (the
  older `.app` domain 301-redirects to it); `/latest`, `/{start}..{end}`
  and `/currencies` all respond exactly as documented, with `base`/`symbols`
  params and the `{"amount":1.0,"base":"EUR","date":"...",
  "rates":{"ILS":3.91,...}}` response shape confirmed verbatim.
- Bank of Israel official representative rate (שער יציג): published once
  per foreign-currency business day, vs ILS, "an indicator... no
  obligatory status under law" per BOI. **Confirmed live (ENH-008,
  2026-10-31)**: `https://edge.boi.org.il/FusionEdgeServer/sdmx/v2/data/
  dataflow/BOI.STATISTICS/EXR/1.0/<series_key>` with the guessed series-key
  convention `RER_<CCY>_ILS` (e.g. `RER_USD_ILS`) returns real, current
  representative-rate rows with `format=csv` alone - every row already
  carries `DATA_TYPE=OF00` without needing a filter. The `c[DATA_TYPE]=OF00`
  filter this module's code used to send is otherwise-harmless (aiohttp
  percent-encodes the brackets and the server still returns 200), but
  unnecessary - dropped it since the plain query already confirms. History
  queries use the standard SDMX `startPeriod`/`endPeriod` params, also
  confirmed live - `fetch_history()` for BOI is now implemented (previously
  returned `[]` unconditionally, pending this verification).

Instrument id convention: "<source>:<base_ccy>:<quote_ccy>", source is
"frankfurter" or "boi", e.g. "frankfurter:EUR:ILS" or "boi:USD:ILS" (BOI
rates are always vs ILS). resolve() accepts "EUR/ILS" (-> frankfurter,
market mid) or "EUR/ILS/boi" (-> Bank of Israel official rate).
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, date, datetime
from typing import Any

from aiohttp import ClientSession, ClientTimeout

from .base import CannotConnect, InstrumentRef, PricePoint, Provider, Quote

_LOGGER = logging.getLogger(__name__)

FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"
BOI_SDMX_BASE_URL = "https://edge.boi.org.il/FusionEdgeServer/sdmx/v2/data/dataflow/BOI.STATISTICS/EXR/1.0"

_REQUEST_TIMEOUT = ClientTimeout(total=15)


def _parse_pair(ref_id: str) -> tuple[str, str, str]:
    source, base_ccy, quote_ccy = ref_id.split(":")
    return source, base_ccy, quote_ccy


class FxProvider(Provider):
    """Exchange rates: Frankfurter (market mid) or Bank of Israel (official)."""

    key = "fx"
    name = "Exchange rates"
    requires_api_key = False
    supports_streaming = False

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def validate(self, credentials: dict[str, Any]) -> None:
        return  # no API key for either source

    async def search(self, query: str, limit: int) -> list[InstrumentRef]:
        try:
            return await self.resolve(query)
        except CannotConnect:
            return []

    async def resolve(self, user_input: str) -> list[InstrumentRef]:
        parts = user_input.strip().upper().replace("-", "/").split("/")
        if len(parts) < 2:
            raise CannotConnect(f"Expected a pair like EUR/ILS, got: {user_input}")
        base_ccy, quote_ccy = parts[0], parts[1]
        source = "boi" if len(parts) >= 3 and parts[2].lower() == "boi" else "frankfurter"

        if source == "frankfurter":
            await self._frankfurter_get("/latest", {"base": base_ccy, "symbols": quote_ccy})
        else:
            await self._boi_fetch_latest(base_ccy)

        label = "Bank of Israel official rate" if source == "boi" else "market rate"
        return [
            InstrumentRef(
                provider="fx",
                id=f"{source}:{base_ccy}:{quote_ccy}",
                symbol=f"{base_ccy}/{quote_ccy}",
                name=f"{base_ccy}/{quote_ccy} ({label})",
                kind="fx",
                unit=quote_ccy,
            )
        ]

    async def fetch_snapshot(self, refs: list[InstrumentRef]) -> dict[str, Quote]:
        quotes: dict[str, Quote] = {}
        for ref in refs:
            source, base_ccy, quote_ccy = _parse_pair(ref.id)
            try:
                if source == "frankfurter":
                    quotes[ref.id] = await self._frankfurter_quote(base_ccy, quote_ccy)
                else:
                    quotes[ref.id] = await self._boi_quote(base_ccy)
            except CannotConnect as err:
                _LOGGER.debug("FX snapshot failed for %s: %s", ref.id, err)
        return quotes

    async def fetch_history(self, ref: InstrumentRef, hours: int) -> list[PricePoint]:
        source, base_ccy, quote_ccy = _parse_pair(ref.id)
        days = max(1, hours // 24) + 1
        end = datetime.now(UTC).date()
        start = end.fromordinal(end.toordinal() - days)

        if source != "frankfurter":
            return await self._boi_fetch_history(base_ccy, start, end)

        data = await self._frankfurter_get(
            f"/{start.isoformat()}..{end.isoformat()}", {"base": base_ccy, "symbols": quote_ccy}
        )
        rates = data.get("rates", {}) if isinstance(data, dict) else {}
        points: list[PricePoint] = []
        for date_str, day_rates in sorted(rates.items()):
            rate = day_rates.get(quote_ccy)
            if rate is None:
                continue
            points.append(
                PricePoint(ts=datetime.fromisoformat(date_str).replace(tzinfo=UTC), price=float(rate))
            )
        return points

    # --- Frankfurter ---

    async def _frankfurter_get(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{FRANKFURTER_BASE_URL}{path}"
        try:
            async with self._session.get(url, params=params, timeout=_REQUEST_TIMEOUT) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as err:  # noqa: BLE001
            raise CannotConnect(f"Frankfurter request to {path} failed: {err}") from err

    async def _frankfurter_quote(self, base_ccy: str, quote_ccy: str) -> Quote:
        data = await self._frankfurter_get("/latest", {"base": base_ccy, "symbols": quote_ccy})
        rate = data.get("rates", {}).get(quote_ccy) if isinstance(data, dict) else None
        if rate is None:
            raise CannotConnect(f"No Frankfurter rate for {base_ccy}/{quote_ccy}")
        date_str = data.get("date")
        ts = datetime.fromisoformat(date_str).replace(tzinfo=UTC) if date_str else datetime.now(UTC)
        return Quote(price=float(rate), ts=ts)

    # --- Bank of Israel ---

    async def _boi_fetch_latest(self, base_ccy: str) -> dict[str, Any]:
        series_key = f"RER_{base_ccy}_ILS"
        url = f"{BOI_SDMX_BASE_URL}/{series_key}"
        params = {"format": "csv"}
        try:
            async with self._session.get(url, params=params, timeout=_REQUEST_TIMEOUT) as resp:
                resp.raise_for_status()
                text = await resp.text()
        except Exception as err:  # noqa: BLE001
            raise CannotConnect(f"Bank of Israel request for {base_ccy}/ILS failed: {err}") from err

        rows = list(csv.DictReader(io.StringIO(text)))
        if not rows:
            raise CannotConnect(f"No Bank of Israel rate for {base_ccy}/ILS")
        return rows[-1]

    async def _boi_quote(self, base_ccy: str) -> Quote:
        row = await self._boi_fetch_latest(base_ccy)
        rate = row.get("OBS_VALUE")
        date_str = row.get("TIME_PERIOD")
        if rate is None:
            raise CannotConnect(f"Bank of Israel response missing OBS_VALUE for {base_ccy}/ILS")
        ts = datetime.fromisoformat(date_str).replace(tzinfo=UTC) if date_str else datetime.now(UTC)
        return Quote(price=float(rate), ts=ts)

    async def _boi_fetch_history(self, base_ccy: str, start: date, end: date) -> list[PricePoint]:
        series_key = f"RER_{base_ccy}_ILS"
        url = f"{BOI_SDMX_BASE_URL}/{series_key}"
        params = {
            "format": "csv",
            "startPeriod": start.isoformat(),
            "endPeriod": end.isoformat(),
        }
        try:
            async with self._session.get(url, params=params, timeout=_REQUEST_TIMEOUT) as resp:
                resp.raise_for_status()
                text = await resp.text()
        except Exception as err:  # noqa: BLE001
            raise CannotConnect(f"Bank of Israel history request for {base_ccy}/ILS failed: {err}") from err

        points: list[PricePoint] = []
        for row in csv.DictReader(io.StringIO(text)):
            rate = row.get("OBS_VALUE")
            date_str = row.get("TIME_PERIOD")
            if rate is None or date_str is None:
                continue
            points.append(
                PricePoint(ts=datetime.fromisoformat(date_str).replace(tzinfo=UTC), price=float(rate))
            )
        return points
