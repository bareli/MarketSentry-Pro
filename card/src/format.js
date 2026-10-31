/**
 * Pure formatting helpers for marketsentry-card. No DOM, no hass — unit
 * testable in isolation (see test/format.test.js).
 */

/** @param {"outcome"|"stock"|"fx"} kind @param {number|null} value @param {string} [unit] */
export function formatValue(kind, value, unit) {
  if (value == null || Number.isNaN(value)) return "—";
  if (kind === "outcome") return `${value.toFixed(1)}%`;
  if (kind === "fx") return `${value.toFixed(4)}${unit ? ` ${unit}` : ""}`;
  const symbol = unit === "USD" ? "$" : unit ? `${unit} ` : "";
  return `${symbol}${value.toFixed(2)}`;
}

/**
 * Change indicator: percentage points for outcomes, percent for stocks/FX.
 * @param {"outcome"|"stock"|"fx"} kind
 * @param {number|null} changePct
 * @param {number|null} deltaPp
 */
export function formatChange(kind, changePct, deltaPp) {
  if (kind === "outcome") {
    if (deltaPp == null || Number.isNaN(deltaPp)) return null;
    return `${deltaPp > 0 ? "+" : ""}${deltaPp.toFixed(1)}pp`;
  }
  if (changePct == null || Number.isNaN(changePct)) return null;
  return `${changePct > 0 ? "+" : ""}${changePct.toFixed(2)}%`;
}

const MARKET_STATE_LABELS = { pre: "Pre", regular: "Open", post: "After", closed: "Closed" };

/** @param {string|null|undefined} state */
export function marketStateLabel(state) {
  return (state && MARKET_STATE_LABELS[state]) || "Closed";
}

/**
 * Status badge text per kind.
 * @param {{kind: string, resolutionStatus?: string|null, closed?: boolean|null,
 *   endDate?: string|null, marketState?: string|null, publishedDate?: string|null}} row
 * @param {Date} [now]
 */
export function statusBadge(row, now = new Date()) {
  if (row.kind === "outcome") {
    if (row.resolutionStatus === "resolved") return "Resolved";
    if (row.closed) return "Closed";
    if (row.endDate) {
      const hoursLeft = (new Date(row.endDate).getTime() - now.getTime()) / 3_600_000;
      if (hoursLeft >= 0 && hoursLeft <= 24) return "Closing soon";
    }
    return "Live";
  }
  if (row.kind === "stock") {
    return row.marketState && row.marketState !== "closed" ? "Open" : "Closed";
  }
  if (row.kind === "fx") {
    if (!row.publishedDate) return "Stale";
    const published = new Date(row.publishedDate);
    return published.toDateString() === now.toDateString() ? "Updated today" : "Stale";
  }
  return "";
}
