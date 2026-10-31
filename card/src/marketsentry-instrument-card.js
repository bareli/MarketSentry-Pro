import { formatChange, formatCompactUsd, formatDate, formatValue, marketStateLabel, statusBadge } from "./format.js";
import { DATE_LOCALES, resolveLang, t } from "./i18n.js";
import { buildRows, changeFromHistory } from "./rows.js";
import { buildSparklineArea, buildSparklinePath, sparklineLastPoint, sparklineRange } from "./sparkline.js";

const HISTORY_REFRESH_MS = 60_000;

export class MarketSentryInstrumentCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("marketsentry-instrument-card-editor");
  }

  static getStubConfig(hass) {
    const row = buildRows(hass)[0];
    return { type: "custom:marketsentry-instrument-card", entity: row?.entityId || "" };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._history = [];
    this._lastHistoryFetch = 0;
  }

  setConfig(config) {
    // An empty/missing `entity` is not a malformed config - it's the
    // first-run state (e.g. `getStubConfig()` on a zero-instrument
    // account) and is handled at render time by `_render()`'s empty state,
    // not rejected here.
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._maybeRefreshHistory();
    this._render();
  }

  getCardSize() {
    return 3;
  }

  _findRow() {
    if (!this._hass) return null;
    return buildRows(this._hass).find((row) => row.entityId === this._config.entity) || null;
  }

  async _maybeRefreshHistory() {
    if (!this._hass) return;
    const now = Date.now();
    if (now - this._lastHistoryFetch < HISTORY_REFRESH_MS) return;
    this._lastHistoryFetch = now;

    const row = this._findRow();
    if (!row?.deviceId) return;
    try {
      const result = await this._hass.callWS({ type: "marketsentry/history", device_id: row.deviceId });
      this._history = result?.history ?? [];
    } catch {
      // Leave prior history in place (or empty) on failure.
    }
    this._render();
  }

  _render() {
    if (!this.shadowRoot) return;
    if (!this._hass || !this._config) {
      this.shadowRoot.innerHTML = "";
      return;
    }

    const row = this._findRow();
    const lang = resolveLang(this._hass);
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="content">
          ${row ? this._renderBody(row, lang) : this._renderEmpty(lang)}
        </div>
      </ha-card>
    `;
  }

  /**
   * No matching row. Split on whether an entity was configured at all:
   * - no `entity` configured yet (e.g. the zero-instrument stub config) -
   *   point the user back at the integration's own "Add instrument" step.
   * - a real-but-unmatched `entity` id - keep the specific "not found" text.
   */
  _renderEmpty(lang) {
    if (!this._config.entity) {
      return `
        <div class="empty">
          ${escapeHtml(t(lang, "empty_instrument_no_entity"))}
          <a href="/config/integrations/integration/marketsentry">${escapeHtml(t(lang, "empty_instrument_add_instrument"))}</a>.
        </div>
      `;
    }
    return `<div class="empty">${escapeHtml(t(lang, "empty_instrument", { entity: this._config.entity }))}</div>`;
  }

  _renderBody(row, lang) {
    return row.kind === "outcome" ? this._renderOutcome(row, lang) : this._renderGeneric(row, lang);
  }

  _renderOutcome(row, lang) {
    const { deltaPp } = changeFromHistory(this._history);
    const changeText = formatChange(row.kind, null, deltaPp);
    const changeClass = (deltaPp ?? 0) >= 0 ? "positive" : "negative";
    const badgeId = statusBadge(row);
    const badge = t(lang, `badge_${badgeId}`);
    const href = safeUrl(row.url);
    const pct = row.value == null ? 0 : Math.min(100, Math.max(0, row.value));

    return `
      <div class="title" title="${escapeAttr(row.name)}">
        ${href ? `<a href="${href}" target="_blank" rel="noopener">${escapeHtml(row.name)}</a>` : escapeHtml(row.name)}
      </div>
      <div class="chips">
        <span class="badge badge-${slug(badgeId)}">${escapeHtml(badge)}</span>
      </div>
      <div class="prob-line">
        <div class="prob-bar"><div class="prob-fill" style="width:${pct}%"></div></div>
        <div class="prob-value">
          <span class="value" dir="ltr">${escapeHtml(formatValue(row.kind, row.value, row.unit))}</span>
          ${changeText ? `<span class="change ${changeClass}" dir="ltr">${escapeHtml(changeText)}</span>` : ""}
        </div>
      </div>
      <div class="stats">
        <div class="stat"><span class="stat-label">${escapeHtml(t(lang, "stat_volume_24h"))}</span><span class="stat-value" dir="ltr">${formatCompactUsd(row.volume24hr)}</span></div>
        <div class="stat"><span class="stat-label">${escapeHtml(t(lang, "stat_liquidity"))}</span><span class="stat-value" dir="ltr">${formatCompactUsd(row.liquidity)}</span></div>
      </div>
      <div class="footer">${escapeHtml(t(lang, "footer_ends", { date: formatDate(row.endDate, DATE_LOCALES[lang]) }))}</div>
    `;
  }

  _renderGeneric(row, lang) {
    const { changePct, deltaPp } = changeFromHistory(this._history);
    const path = buildSparklinePath(this._history, 280, 60);
    const areaPath = buildSparklineArea(this._history, 280, 60);
    const lastPoint = sparklineLastPoint(this._history, 280, 60);
    const range = sparklineRange(this._history);
    const changeText = formatChange(row.kind, changePct, deltaPp);
    const changeClass = (deltaPp ?? changePct ?? 0) >= 0 ? "positive" : "negative";
    const badgeId = statusBadge(row);
    const badge = t(lang, `badge_${badgeId}`);
    const href = safeUrl(row.url);

    return `
      <div class="title" title="${escapeAttr(row.name)}">
        ${href ? `<a href="${href}" target="_blank" rel="noopener">${escapeHtml(row.name)}</a>` : escapeHtml(row.name)}
      </div>
      <div class="chips">
        ${
          row.kind === "stock"
            ? // The market-state chip (Pre/Open/After/Closed) is a strict superset of
              // the Open/Closed status badge for this kind, so skip the redundant badge.
              `<span class="chip">${escapeHtml(t(lang, `chip_${marketStateLabel(row.marketState)}`))}</span>`
            : ""
        }
        ${
          row.kind === "fx"
            ? `<span class="chip">${escapeHtml(
                row.source === "boi" || /boi/.test(row.source || "")
                  ? t(lang, "fx_boi")
                  : row.source === "vatcomply" || /vatcomply/.test(row.source || "")
                    ? t(lang, "fx_vatcomply")
                    : t(lang, "fx_market")
              )}</span>`
            : ""
        }
        ${row.kind !== "stock" ? `<span class="badge badge-${slug(badgeId)}">${escapeHtml(badge)}</span>` : ""}
      </div>
      <div class="big-value">
        <span class="value" dir="ltr">${escapeHtml(formatValue(row.kind, row.value, row.unit))}</span>
        ${changeText ? `<span class="change ${changeClass}" dir="ltr">${escapeHtml(changeText)}</span>` : ""}
      </div>
      <div class="big-spark">
        ${
          path
            ? `<svg viewBox="0 0 280 60" preserveAspectRatio="none">
                ${areaPath ? `<path d="${areaPath}" fill="currentColor" fill-opacity="0.12" stroke="none" />` : ""}
                <path d="${path}" fill="none" stroke="currentColor" stroke-width="2" />
                ${lastPoint ? `<circle cx="${lastPoint.x.toFixed(1)}" cy="${lastPoint.y.toFixed(1)}" r="3" fill="currentColor" />` : ""}
              </svg>`
            : ""
        }
        ${
          range && range.max !== range.min
            ? `<div class="spark-range" dir="ltr">
                <span>${escapeHtml(formatValue(row.kind, range.max, row.unit))}</span>
                <span>${escapeHtml(formatValue(row.kind, range.min, row.unit))}</span>
              </div>`
            : ""
        }
      </div>
      ${row.kind === "stock" ? `<div class="stats"><div class="stat"><span class="stat-label">${escapeHtml(t(lang, "stat_prev_close"))}</span><span class="stat-value" dir="ltr">${escapeHtml(formatValue(row.kind, row.previousClose, row.unit))}</span></div></div>` : ""}
      ${row.kind === "fx" ? `<div class="footer">${escapeHtml(t(lang, "footer_published", { date: formatDate(row.publishedDate, DATE_LOCALES[lang]) }))}</div>` : ""}
    `;
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
}

function escapeAttr(value) {
  return escapeHtml(value);
}

function safeUrl(value) {
  if (!value) return null;
  try {
    const url = new URL(value, window.location.origin);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return escapeAttr(url.href);
  } catch {
    return null;
  }
}

function slug(text) {
  return String(text).toLowerCase().replace(/[\s_]+/g, "-");
}

const STYLE = `
  :host { display: block; }
  ha-card { padding: 16px; }
  .content { display: flex; flex-direction: column; gap: 10px; }
  .empty { color: var(--secondary-text-color); }
  .empty a { color: var(--primary-color); }
  .title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--primary-text-color);
    line-height: 1.3;
  }
  .title a { color: inherit; text-decoration: none; }
  .title a:hover { text-decoration: underline; }
  .chips { display: flex; gap: 6px; flex-wrap: wrap; }
  .chip {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .badge {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .badge-live, .badge-open, .badge-updated-today { background: rgba(var(--rgb-green-color, 76, 175, 80), 0.18); color: var(--success-color, #4caf50); }
  .badge-closing-soon { background: rgba(var(--rgb-orange-color, 255, 152, 0), 0.18); color: var(--warning-color, #ff9800); }
  .badge-closed, .badge-resolved, .badge-stale { background: var(--secondary-background-color); color: var(--secondary-text-color); }
  .prob-line { display: flex; align-items: center; gap: 12px; margin-top: 4px; }
  .prob-bar {
    flex: 1 1 auto;
    height: 10px;
    border-radius: 999px;
    background: var(--error-color, #f44336);
    overflow: hidden;
  }
  .prob-fill { height: 100%; border-radius: 999px; background: var(--success-color, #4caf50); }
  .prob-value { flex: 0 0 auto; display: flex; align-items: baseline; gap: 8px; white-space: nowrap; }
  .prob-value .value { font-size: 1.4rem; font-weight: 700; color: var(--primary-text-color); }
  .big-value { display: flex; align-items: baseline; gap: 10px; margin-top: 4px; }
  .big-value .value { font-size: 1.8rem; font-weight: 700; color: var(--primary-text-color); font-variant-numeric: tabular-nums; }
  .change { font-size: 0.95rem; font-variant-numeric: tabular-nums; }
  .change.positive { color: var(--success-color, #4caf50); }
  .change.negative { color: var(--error-color, #f44336); }
  .big-spark { position: relative; width: 100%; height: 60px; color: var(--primary-color); }
  .big-spark svg { width: 100%; height: 100%; display: block; }
  .spark-range {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: flex-end;
    padding: 2px 0;
    pointer-events: none;
    font-size: 0.68rem;
    color: var(--secondary-text-color);
  }
  .spark-range span {
    background: var(--card-background-color);
    border-radius: 4px;
    padding: 1px 4px;
  }
  .stats { display: flex; gap: 20px; margin-top: 2px; }
  .stat { display: flex; flex-direction: column; gap: 2px; }
  .stat-label { font-size: 0.72rem; color: var(--secondary-text-color); text-transform: uppercase; }
  .stat-value { font-size: 0.95rem; font-weight: 600; color: var(--primary-text-color); }
  .footer { font-size: 0.8rem; color: var(--secondary-text-color); }
`;

customElements.define("marketsentry-instrument-card", MarketSentryInstrumentCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "marketsentry-instrument-card",
  name: "MarketSentry Pro (single instrument)",
  description: "One tracked instrument per card, with a kind-specific detailed view (Polymarket probability bar + stats, stock/FX price + sparkline).",
  preview: true,
});
