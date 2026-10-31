import { buildRows } from "./rows.js";

export class MarketSentryInstrumentCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    const next = { ...config };
    const nextKey = JSON.stringify(next);
    // HA's card editor dialog calls setConfig() again every time we emit
    // config-changed (even for our own edits), echoing back the same
    // config. Rebuilding the shadow DOM on that echo would close an open
    // <select> or steal focus, so skip it when nothing actually changed.
    if (this._configKey === nextKey) return;
    this._config = next;
    this._configKey = nextKey;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    // `hass` is replaced on every state update (every few seconds), far
    // more often than the list of trackable instruments actually changes.
    // Only rebuild the dropdown when that list has actually changed, so a
    // dropdown the user has open doesn't get yanked shut underneath them.
    const rows = buildRows(hass);
    const rowsKey = JSON.stringify(rows.map((row) => [row.entityId, row.name]));
    if (this._rowsKey === rowsKey) return;
    this._rowsKey = rowsKey;
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  _emitChange() {
    this._configKey = JSON.stringify(this._config);
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }

  _render() {
    if (!this.shadowRoot || !this._config) return;

    this.shadowRoot.textContent = "";
    const style = document.createElement("style");
    style.textContent = STYLE;
    this.shadowRoot.appendChild(style);

    const root = document.createElement("div");
    root.className = "editor";
    root.appendChild(this._buildEntityField());
    this.shadowRoot.appendChild(root);
  }

  _buildEntityField() {
    const wrapper = document.createElement("div");
    wrapper.className = "field";
    const label = document.createElement("label");
    label.textContent = "Instrument";
    wrapper.appendChild(label);

    const rows = this._hass ? buildRows(this._hass) : [];
    const select = document.createElement("select");

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = rows.length ? "Choose an instrument…" : "No MarketSentry Pro instruments found";
    placeholder.disabled = true;
    placeholder.selected = !this._config.entity;
    select.appendChild(placeholder);

    for (const row of rows) {
      const option = document.createElement("option");
      option.value = row.entityId;
      option.textContent = row.name;
      option.selected = this._config.entity === row.entityId;
      select.appendChild(option);
    }

    select.addEventListener("change", () => {
      this._config = { ...this._config, entity: select.value };
      this._emitChange();
    });

    wrapper.appendChild(select);
    return wrapper;
  }
}

const STYLE = `
  .editor { display: flex; flex-direction: column; gap: 16px; padding: 8px 0; }
  .field { display: flex; flex-direction: column; gap: 6px; }
  label { font-size: 0.9rem; color: var(--primary-text-color); }
  select {
    padding: 8px;
    border-radius: 4px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color);
    color: var(--primary-text-color);
  }
`;

customElements.define("marketsentry-instrument-card-editor", MarketSentryInstrumentCardEditor);
