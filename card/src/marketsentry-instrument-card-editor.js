import { buildRows } from "./rows.js";

export class MarketSentryInstrumentCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  _emitChange() {
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
