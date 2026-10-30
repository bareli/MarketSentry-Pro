"""FX provider: exchange rates from two sources, no API key for either.

- Frankfurter (ECB-based market mid rate, frankfurter.dev): daily rates,
  wide currency coverage, no key. Facts below are NOT confirmed this
  session (the research fetch tooling failed on frankfurter.dev); they
  match Frankfurter's long-documented stable contract. Verify before
  relying on them: base URL `https://api.frankfurter.dev/v1`, endpoints
  `/latest`, `/{date}`, `/{start}..{end}`, `/currencies`, params
  `base`/`symbols`, response `{"amount":1.0,"base":"EUR","date":"...",
  "rates":{"ILS":3.91,...}}`.
- Bank of Israel official representative rate (שער יציג): published once
  per foreign-currency business day, vs ILS, "an indicator... no
  obligatory status under law" per BOI. NOT confirmed this session either
  (same tooling failure). Per BOI's own published guide
  (boi.org.il, "extracting representative exchange rates from the new
  series database"), the SDMX endpoint is under
  `https://edge.boi.org.il/FusionEdgeServer/sdmx/v2/data/dataflow/
  BOI.STATISTICS/EXR/1.0/<series_key>` filtered to `DATA_TYPE=OF00`
  (representative rates only - not every rate in the database is
  representative), with `format=csv` for a simple CSV response. The
  series-key naming convention (assumed `RER_<CCY>_ILS`, e.g.
  `RER_USD_ILS`) is inferred from the guide's example `RER_GBP_ILS` and
  is NOT independently verified. Confirm the exact key format and
  dimension-filter syntax (`c[DATA_TYPE]=OF00`) against a live query
  before relying on this in production.

Instrument id convention: "<source>:<base_ccy>:<quote_ccy>", source is
"frankfurter" or "boi", e.g. "frankfurter:EUR:ILS" or "boi:USD:ILS" (BOI
rates are always vs ILS). resolve() accepts "EUR/ILS" (-> frankfurter,
market mid) or "EUR/ILS/boi" (-> Bank of Israel official rate).
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, datetime
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
        if source != "frankfurter":
            # BOI's SDMX history query needs a confirmed date-range filter
            # syntax this session could not verify; not implemented yet.
            return []

        days = max(1, hours // 24) + 1
        end = datetime.now(UTC).date()
        start = end.fromordinal(end.toordinal() - days)
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
        params = {"c[DATA_TYPE]": "OF00", "format": "csv"}
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
