import { buildStrategyView } from "./strategy-view-logic.js";

/**
 * Lovelace view strategy: add a new dashboard view with
 * `strategy: { type: "custom:marketsentry" }` and it fills itself in with
 * an overview list card plus one detail card per tracked instrument - no
 * manual card placement, and it follows new/removed instruments on every
 * view load.
 *
 * HA resolves `custom:marketsentry` to the custom element
 * `ll-strategy-view-marketsentry` and calls its static `generate(config,
 * hass)`, exactly like `static getConfigElement`/`getStubConfig` on a card.
 * Not verified against a live HA frontend session in this project (no
 * running instance available for this specific wiring); built against the
 * documented view-strategy contract.
 */
export class MarketSentryViewStrategy extends HTMLElement {
  static async generate(config, hass) {
    return buildStrategyView(config, hass);
  }
}

customElements.define("ll-strategy-view-marketsentry", MarketSentryViewStrategy);
