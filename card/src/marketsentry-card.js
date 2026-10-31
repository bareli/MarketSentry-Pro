import { formatChange, formatValue, marketStateLabel, statusBadge } from "./format.js";
import { filterByKind, groupRows } from "./grouping.js";
import { DATE_LOCALES, resolveLang, t } from "./i18n.js";
import { buildRows, changeFromHistory } from "./rows.js";
import { buildSparklinePath } from "./sparkline.js";

const HISTORY_REFRESH_MS = 60_000;

const PROVIDER_NAMES = { polymarket: "Polymarket", finnhub: "Finnhub", alpaca: "Alpaca" };

export class MarketSentryCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("marketsentry-card-editor");
  }

  static getStubConfig() {
    return { type: "custom:marketsentry-card", group_by: "kind" };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._history = new Map(); // entityId -> {t, p}[]
    this._lastHistoryFetch = 0;
  }

  setConfig(config) {
    if (config.kinds && !Array.isArray(config.kinds)) {
      throw new Error("marketsentry-card: 'kinds' must be a list");
    }
    this._config = {
      group_by: "none",
      kinds: undefined,
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._maybeRefreshHistory();
    this._render();
  }

  getCardSize() {
    return 1 + buildRows(this._hass).length;
  }

  async _maybeRefreshHistory() {
    if (!this._hass) return;
    const now = Date.now();
    if (now - this._lastHistoryFetch < HISTORY_REFRESH_MS) return;
    this._lastHistoryFetch = now;

    const rows = buildRows(this._hass);
    await Promise.all(
      rows.map(async (row) => {
        if (!row.deviceId) return;
        try {
          const result = await this._hass.callWS({
            type: "marketsentry/history",
            device_id: row.deviceId,
          });
          this._history.set(row.entityId, result?.history ?? []);
        } catch {
          // Leave prior history in place (or empty) on failure.
        }
      })
    );
    this._render();
  }

  _render() {
    if (!this.shadowRoot) return;
    if (!this._hass || !this._config) {
      this.shadowRoot.innerHTML = "";
      return;
    }

    const allRows = buildRows(this._hass);
    const filtered = filterByKind(allRows, this._config.kinds);
    const groups = groupRows(filtered, this._config.group_by);
    const lang = resolveLang(this._hass);

    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        ${this._config.title ? `<h1 class="card-header">${escapeHtml(this._config.title)}</h1>` : ""}
        <div class="content">
          ${groups.length === 0 ? `<div class="empty">${escapeHtml(t(lang, "empty_card"))}</div>` : ""}
          ${groups.map((group) => this._renderGroup(group, lang)).join("")}
        </div>
      </ha-card>
    `;
  }

  _groupLabel(value, lang) {
    if (this._config.group_by === "provider") return PROVIDER_NAMES[value] || (value === "fx" ? t(lang, "group_fx") : value);
    if (this._config.group_by === "kind") {
      if (value === "outcome") return t(lang, "group_predictions");
      if (value === "stock") return t(lang, "group_stocks");
      if (value === "fx") return t(lang, "group_fx");
    }
    return value;
  }

  _renderGroup(group, lang) {
    const label = group.label != null ? this._groupLabel(group.label, lang) : null;
    return `
      ${label ? `<div class="group-label">${escapeHtml(label)}</div>` : ""}
      ${group.rows.map((row) => this._renderRow(row, lang)).join("")}
    `;
  }

  _renderRow(row, lang) {
    return row.kind === "outcome" ? this._renderOutcomeRow(row, lang) : this._renderGenericRow(row, lang);
  }

  /** Polymarket-style row: title, status badge, then a probability bar with the live % and move. */
  _renderOutcomeRow(row, lang) {
    const points = this._history.get(row.entityId) || [];
    const { deltaPp } = changeFromHistory(points);
    const changeText = formatChange(row.kind, null, deltaPp);
    const changeClass = (deltaPp ?? 0) >= 0 ? "positive" : "negative";
    const badgeId = statusBadge(row);
    const badge = t(lang, `badge_${badgeId}`);
    const href = safeUrl(row.url);
    const pct = row.value == null ? 0 : Math.min(100, Math.max(0, row.value));

    return `
      <div class="row" part="row">
        <div class="row-name" title="${escapeAttr(row.name)}">
          ${href ? `<a href="${href}" target="_blank" rel="noopener">${escapeHtml(row.name)}</a>` : escapeHtml(row.name)}
        </div>
        <div class="row-chips">
          <span class="badge badge-${slug(badgeId)}">${escapeHtml(badge)}</span>
        </div>
        <div class="prob-line">
          <div class="prob-bar"><div class="prob-fill" style="width:${pct}%"></div></div>
          <div class="prob-value">
            <span class="value" dir="ltr">${escapeHtml(formatValue(row.kind, row.value, row.unit))}</span>
            ${changeText ? `<span class="change ${changeClass}" dir="ltr">${escapeHtml(changeText)}</span>` : ""}
          </div>
        </div>
      </div>
    `;
  }

  /** Stock/FX row: title + value/change up top, chips + sparkline below. */
  _renderGenericRow(row, lang) {
    const points = this._history.get(row.entityId) || [];
    const { changePct, deltaPp } = changeFromHistory(points);
    const path = buildSparklinePath(points);
    const changeText = formatChange(row.kind, changePct, deltaPp);
    const changeClass = (deltaPp ?? changePct ?? 0) >= 0 ? "positive" : "negative";
    const badgeId = statusBadge(row);
    const badge = t(lang, `badge_${badgeId}`);
    const href = safeUrl(row.url);

    return `
      <div class="row" part="row">
        <div class="row-top">
          <div class="row-name" title="${escapeAttr(row.name)}">
            ${href ? `<a href="${href}" target="_blank" rel="noopener">${escapeHtml(row.name)}</a>` : escapeHtml(row.name)}
          </div>
          <div class="row-value">
            <div class="value" dir="ltr">${escapeHtml(formatValue(row.kind, row.value, row.unit))}</div>
            ${changeText ? `<div class="change ${changeClass}" dir="ltr">${escapeHtml(changeText)}</div>` : ""}
          </div>
        </div>
        <div class="row-bottom">
          <div class="row-chips">
            ${
              row.kind === "stock"
                ? // The market-state chip (Pre/Open/After/Closed) is a strict superset of
                  // the Open/Closed status badge for this kind, so skip the redundant badge.
                  `<span class="chip">${escapeHtml(t(lang, `chip_${marketStateLabel(row.marketState)}`))}</span>`
                : ""
            }
            ${row.kind === "fx" ? `<span class="chip">${escapeHtml(row.source === "boi" || /boi/.test(row.source || "") ? t(lang, "fx_boi") : t(lang, "fx_market"))}</span>` : ""}
            ${row.kind !== "stock" ? `<span class="badge badge-${slug(badgeId)}">${escapeHtml(badge)}</span>` : ""}
          </div>
          <div class="row-spark">
            ${path ? `<svg viewBox="0 0 80 24" preserveAspectRatio="none"><path d="${path}" fill="none" stroke="currentColor" stroke-width="1.5" /></svg>` : ""}
          </div>
        </div>
      </div>
    `;
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
}

function escapeAttr(value) {
  return escapeHtml(value);
}

/** Only render http(s) links; drop anything else (defends against a
 * tampered/unexpected `url` attribute value carrying e.g. a javascript: scheme). */
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
  ha-card { padding: 0; }
  .card-header {
    padding: 16px 16px 0;
    font-size: 1.2rem;
    color: var(--ha-card-header-color, var(--primary-text-color));
  }
  .content { padding: 8px 0 16px; }
  .empty {
    padding: 0 16px;
    color: var(--secondary-text-color);
  }
  .group-label {
    padding: 12px 16px 4px;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--secondary-text-color);
    text-transform: uppercase;
  }
  .row {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 16px;
    border-bottom: 1px solid var(--divider-color);
  }
  .row:last-child { border-bottom: none; }
  .row-top {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }
  .row-name {
    flex: 1 1 auto;
    min-width: 0;
    font-weight: 500;
    color: var(--primary-text-color);
    white-space: normal;
    overflow-wrap: break-word;
    line-height: 1.3;
  }
  .row-name a { color: inherit; text-decoration: none; }
  .row-name a:hover { text-decoration: underline; }
  .row-bottom {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .row-chips { display: flex; gap: 6px; flex-wrap: wrap; }
  .chip {
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .badge {
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .badge-live, .badge-open, .badge-updated-today { background: rgba(var(--rgb-green-color, 76, 175, 80), 0.18); color: var(--success-color, #4caf50); }
  .badge-closing-soon { background: rgba(var(--rgb-orange-color, 255, 152, 0), 0.18); color: var(--warning-color, #ff9800); }
  .badge-closed, .badge-resolved, .badge-stale { background: var(--secondary-background-color); color: var(--secondary-text-color); }
  .row-spark {
    flex: 0 0 80px;
    width: 80px;
    height: 24px;
    color: var(--primary-color);
  }
  .row-spark svg { width: 100%; height: 100%; display: block; }
  .prob-line {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .prob-bar {
    flex: 1 1 auto;
    height: 8px;
    border-radius: 999px;
    background: var(--error-color, #f44336);
    overflow: hidden;
  }
  .prob-fill {
    height: 100%;
    border-radius: 999px;
    background: var(--success-color, #4caf50);
  }
  .prob-value {
    flex: 0 0 auto;
    display: flex;
    align-items: baseline;
    gap: 8px;
    white-space: nowrap;
  }
  .prob-value .value { font-size: 1rem; }
  .prob-value .change { font-size: 0.8rem; }
  .row-value {
    flex: 0 0 auto;
    text-align: end;
    min-width: 72px;
  }
  .value {
    font-weight: 600;
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
  }
  .change {
    font-size: 0.8rem;
    font-variant-numeric: tabular-nums;
  }
  .change.positive { color: var(--success-color, #4caf50); }
  .change.negative { color: var(--error-color, #f44336); }
`;

customElements.define("marketsentry-card", MarketSentryCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "marketsentry-card",
  name: "MarketSentry Pro",
  description: "Rows for every tracked Polymarket/Finnhub/Alpaca/FX instrument, grouped and filterable.",
  preview: true,
});
