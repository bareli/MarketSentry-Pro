const KIND_OPTIONS = [
  { value: "outcome", label: "Prediction markets" },
  { value: "stock", label: "Stocks" },
  { value: "fx", label: "Exchange rates" },
];

export class MarketSentryCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = { group_by: "none", kinds: undefined, ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
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

    root.appendChild(this._buildTitleField());
    root.appendChild(this._buildGroupByField());
    root.appendChild(this._buildKindsField());

    this.shadowRoot.appendChild(root);
  }

  _buildTitleField() {
    const wrapper = document.createElement("div");
    wrapper.className = "field";
    const label = document.createElement("label");
    label.textContent = "Title (optional)";
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

  _buildGroupByField() {
    const wrapper = document.createElement("div");
    wrapper.className = "field";
    const label = document.createElement("label");
    label.textContent = "Group by";
    const select = document.createElement("select");
    for (const value of ["none", "provider", "kind"]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
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

  _buildKindsField() {
    const wrapper = document.createElement("div");
    wrapper.className = "field";
    const label = document.createElement("label");
    label.textContent = "Kinds (none selected = all)";
    wrapper.appendChild(label);

    const selected = new Set(this._config.kinds || []);
    for (const { value, label: optionLabel } of KIND_OPTIONS) {
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
      row.append(checkbox, document.createTextNode(` ${optionLabel}`));
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
