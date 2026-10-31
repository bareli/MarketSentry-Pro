import { resolveLang, t } from "./i18n.js";

const KIND_OPTIONS = [
  { value: "outcome", labelKey: "group_predictions" },
  { value: "stock", labelKey: "group_stocks" },
  { value: "fx", labelKey: "group_fx" },
];

export class MarketSentryCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    const next = { group_by: "none", kinds: undefined, ...config };
    const nextKey = JSON.stringify(next);
    // HA's card editor dialog calls setConfig() again every time we emit
    // config-changed (even for our own edits), echoing back the same
    // config. Rebuilding the whole shadow DOM on that echo would blow
    // away focus/cursor position on every keystroke, so skip it when
    // nothing actually changed.
    if (this._configKey === nextKey) return;
    this._config = next;
    this._configKey = nextKey;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
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
    const lang = resolveLang(this._hass);

    root.appendChild(this._buildTitleField(lang));
    root.appendChild(this._buildGroupByField(lang));
    root.appendChild(this._buildKindsField(lang));

    this.shadowRoot.appendChild(root);
  }

  _buildTitleField(lang) {
    const wrapper = document.createElement("div");
    wrapper.className = "field";
    const label = document.createElement("label");
    label.textContent = t(lang, "editor_title");
    const input = document.createElement("input");
    input.type = "text";
    input.value = this._config.title || "";
    input.addEventListener("input", () => {
      this._config = { ...this._config, title: input.value || undefined };
      this._emitChange();
    });
    wrapper.append(label, input);
    return wrapper;
  }

  _buildGroupByField(lang) {
    const wrapper = document.createElement("div");
    wrapper.className = "field";
    const label = document.createElement("label");
    label.textContent = t(lang, "editor_group_by");
    const select = document.createElement("select");
    for (const value of ["none", "provider", "kind"]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = t(lang, `editor_group_${value}`);
      option.selected = this._config.group_by === value;
      select.appendChild(option);
    }
    select.addEventListener("change", () => {
      this._config = { ...this._config, group_by: select.value };
      this._emitChange();
    });
    wrapper.append(label, select);
    return wrapper;
  }

  _buildKindsField(lang) {
    const wrapper = document.createElement("div");
    wrapper.className = "field";
    const label = document.createElement("label");
    label.textContent = t(lang, "editor_kinds");
    wrapper.appendChild(label);

    const selected = new Set(this._config.kinds || []);
    for (const { value, labelKey } of KIND_OPTIONS) {
      const row = document.createElement("label");
      row.className = "checkbox-row";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = selected.has(value);
      checkbox.addEventListener("change", () => {
        const current = new Set(this._config.kinds || []);
        if (checkbox.checked) current.add(value);
        else current.delete(value);
        this._config = { ...this._config, kinds: current.size ? Array.from(current) : undefined };
        this._emitChange();
      });
      row.append(checkbox, document.createTextNode(` ${t(lang, labelKey)}`));
      wrapper.appendChild(row);
    }
    return wrapper;
  }
}

const STYLE = `
  .editor { display: flex; flex-direction: column; gap: 16px; padding: 8px 0; }
  .field { display: flex; flex-direction: column; gap: 6px; }
  label { font-size: 0.9rem; color: var(--primary-text-color); }
  input[type="text"], select {
    padding: 8px;
    border-radius: 4px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color);
    color: var(--primary-text-color);
  }
  .checkbox-row { display: flex; align-items: center; gap: 6px; font-size: 0.9rem; }
`;

customElements.define("marketsentry-card-editor", MarketSentryCardEditor);
