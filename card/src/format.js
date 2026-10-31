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

/** Compact USD, e.g. $1.2M, $340K, $980. @param {number|null} value */
export function formatCompactUsd(value) {
  if (value == null || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

/** Short locale date, e.g. "Nov 3, 2026". @param {string|null} isoDate @param {string} [locale] */
export function formatDate(isoDate, locale = "en-US") {
  if (!isoDate) return "—";
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(locale, { year: "numeric", month: "short", day: "numeric" });
}

const MARKET_STATE_IDS = { pre: "pre", regular: "open", post: "after", closed: "closed" };

/**
 * Stable id for a stock's market state, e.g. "pre"/"open"/"after"/"closed".
 * Translate for display via `t(lang, "chip_" + marketStateLabel(state))`.
 * @param {string|null|undefined} state
 */
export function marketStateLabel(state) {
  return (state && MARKET_STATE_IDS[state]) || "closed";
}

/**
 * Stable status-badge id per kind, e.g. "resolved"/"closed"/"closing_soon"/
 * "live"/"open"/"stale"/"updated_today". Translate for display via
 * `t(lang, "badge_" + statusBadge(row))`; also doubles as the CSS class
 * suffix (`badge-${id.replace(/_/g, "-")}`).
 * @param {{kind: string, resolutionStatus?: string|null, closed?: boolean|null,
 *   endDate?: string|null, marketState?: string|null, publishedDate?: string|null}} row
 * @param {Date} [now]
 */
export function statusBadge(row, now = new Date()) {
  if (row.kind === "outcome") {
    if (row.resolutionStatus === "resolved") return "resolved";
    if (row.closed) return "closed";
    if (row.endDate) {
      const hoursLeft = (new Date(row.endDate).getTime() - now.getTime()) / 3_600_000;
      if (hoursLeft >= 0 && hoursLeft <= 24) return "closing_soon";
    }
    return "live";
  }
  if (row.kind === "stock") {
    return row.marketState && row.marketState !== "closed" ? "open" : "closed";
  }
  if (row.kind === "fx") {
    if (!row.publishedDate) return "stale";
    const published = new Date(row.publishedDate);
    return published.toDateString() === now.toDateString() ? "updated_today" : "stale";
  }
  return "";
}
