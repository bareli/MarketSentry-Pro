import { describe, expect, it } from "vitest";
import { buildStrategyView } from "../src/strategy-view-logic.js";

function mockHass() {
  return {
    entities: {
      "sensor.yes_probability": {
        entity_id: "sensor.yes_probability",
        platform: "marketsentry",
        device_id: "dev1",
        translation_key: "probability",
      },
      "sensor.aapl_price": {
        entity_id: "sensor.aapl_price",
        platform: "marketsentry",
        device_id: "dev2",
        translation_key: "price",
      },
      "sensor.eur_ils_rate": {
        entity_id: "sensor.eur_ils_rate",
        platform: "marketsentry",
        device_id: "dev3",
        translation_key: "rate",
      },
    },
    devices: {
      dev1: { id: "dev1", name: "Will X happen?: Yes", name_by_user: null },
      dev2: { id: "dev2", name: "AAPL Inc", name_by_user: null },
      dev3: { id: "dev3", name: "EUR/ILS (market rate)", name_by_user: null },
    },
    states: {
      "sensor.yes_probability": { state: "62.3", attributes: { kind: "outcome", provider: "polymarket" } },
      "sensor.aapl_price": { state: "150.5", attributes: { kind: "stock", provider: "finnhub", unit_of_measurement: "USD" } },
      "sensor.eur_ils_rate": { state: "3.9", attributes: { kind: "fx", provider: "fx", unit_of_measurement: "ILS" } },
    },
  };
}

describe("buildStrategyView", () => {
  it("returns an overview card plus one detail card per tracked instrument", async () => {
    const view = buildStrategyView({}, mockHass());
    expect(view.cards).toHaveLength(4); // overview + 3 instruments
    expect(view.cards[0]).toMatchObject({ type: "custom:marketsentry-card", title: "Markets", group_by: "kind" });
    const entities = view.cards.slice(1).map((c) => c.entity);
    expect(entities).toEqual(
      expect.arrayContaining(["sensor.yes_probability", "sensor.aapl_price", "sensor.eur_ils_rate"])
    );
    for (const card of view.cards.slice(1)) {
      expect(card.type).toBe("custom:marketsentry-instrument-card");
    }
  });

  it("honors title/group_by/kinds config and filters instrument cards to those kinds", async () => {
    const view = buildStrategyView(
      { title: "My Markets", group_by: "provider", kinds: ["stock"] },
      mockHass()
    );
    expect(view.cards[0]).toMatchObject({
      type: "custom:marketsentry-card",
      title: "My Markets",
      group_by: "provider",
      kinds: ["stock"],
    });
    expect(view.cards).toHaveLength(2); // overview + just the stock
    expect(view.cards[1].entity).toBe("sensor.aapl_price");
  });

  it("falls back to a markdown placeholder when nothing is tracked yet", async () => {
    const view = buildStrategyView({}, { entities: {}, states: {} });
    expect(view.cards).toHaveLength(1);
    expect(view.cards[0].type).toBe("markdown");
  });
});
