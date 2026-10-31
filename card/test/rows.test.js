import { describe, expect, it } from "vitest";
import { buildRows, changeFromHistory } from "../src/rows.js";

function mockHass() {
  return {
    entities: {
      "sensor.yes_probability": {
        entity_id: "sensor.yes_probability",
        platform: "marketsentry",
        device_id: "dev1",
        translation_key: "probability",
      },
      "sensor.yes_resolution_status": {
        entity_id: "sensor.yes_resolution_status",
        platform: "marketsentry",
        device_id: "dev1",
        translation_key: "resolution_status",
      },
      "binary_sensor.yes_closed": {
        entity_id: "binary_sensor.yes_closed",
        platform: "marketsentry",
        device_id: "dev1",
        translation_key: "closed",
      },
      "sensor.aapl_price": {
        entity_id: "sensor.aapl_price",
        platform: "marketsentry",
        device_id: "dev2",
        translation_key: "price",
      },
      "sensor.aapl_market_state": {
        entity_id: "sensor.aapl_market_state",
        platform: "marketsentry",
        device_id: "dev2",
        translation_key: "market_state",
      },
      "sensor.aapl_previous_close": {
        entity_id: "sensor.aapl_previous_close",
        platform: "marketsentry",
        device_id: "dev2",
        translation_key: "previous_close",
      },
      "sensor.yes_volume_24hr": {
        entity_id: "sensor.yes_volume_24hr",
        platform: "marketsentry",
        device_id: "dev1",
        translation_key: "volume_24hr",
      },
      "sensor.yes_liquidity": {
        entity_id: "sensor.yes_liquidity",
        platform: "marketsentry",
        device_id: "dev1",
        translation_key: "liquidity",
      },
      "sensor.unrelated": {
        entity_id: "sensor.unrelated",
        platform: "other_integration",
        device_id: "dev3",
        translation_key: "something",
      },
    },
    devices: {
      dev1: { id: "dev1", name: "Will X happen?: Yes", name_by_user: null },
      dev2: { id: "dev2", name: "AAPL Inc", name_by_user: null },
    },
    states: {
      "sensor.yes_probability": {
        state: "62.3",
        attributes: { kind: "outcome", provider: "polymarket", url: "https://polymarket.com/market/x" },
      },
      "sensor.yes_resolution_status": { state: "open", attributes: {} },
      "binary_sensor.yes_closed": { state: "off", attributes: {} },
      "sensor.aapl_price": {
        state: "150.5",
        attributes: { kind: "stock", provider: "finnhub", unit_of_measurement: "USD" },
      },
      "sensor.aapl_market_state": { state: "regular", attributes: {} },
      "sensor.aapl_previous_close": { state: "148.2", attributes: {} },
      "sensor.yes_volume_24hr": { state: "1234000", attributes: {} },
      "sensor.yes_liquidity": { state: "340000", attributes: {} },
    },
  };
}

describe("buildRows", () => {
  it("returns one row per primary entity, enriched from sibling entities", () => {
    const rows = buildRows(mockHass());
    expect(rows).toHaveLength(2);

    const outcome = rows.find((r) => r.kind === "outcome");
    expect(outcome.name).toBe("Will X happen?: Yes");
    expect(outcome.value).toBeCloseTo(62.3);
    expect(outcome.resolutionStatus).toBe("open");
    expect(outcome.closed).toBe(false);
    expect(outcome.url).toBe("https://polymarket.com/market/x");
    expect(outcome.volume24hr).toBeCloseTo(1_234_000);
    expect(outcome.liquidity).toBeCloseTo(340_000);

    const stock = rows.find((r) => r.kind === "stock");
    expect(stock.name).toBe("AAPL Inc");
    expect(stock.value).toBeCloseTo(150.5);
    expect(stock.marketState).toBe("regular");
    expect(stock.unit).toBe("USD");
    expect(stock.previousClose).toBeCloseTo(148.2);
  });

  it("ignores entities from other integrations", () => {
    const rows = buildRows(mockHass());
    expect(rows.some((r) => r.entityId === "sensor.unrelated")).toBe(false);
  });

  it("returns an empty array when hass is missing required registries", () => {
    expect(buildRows(null)).toEqual([]);
    expect(buildRows({})).toEqual([]);
  });

  it("treats unknown/unavailable state as a null value", () => {
    const hass = mockHass();
    hass.states["sensor.yes_probability"].state = "unavailable";
    const rows = buildRows(hass);
    expect(rows.find((r) => r.kind === "outcome").value).toBeNull();
  });
});

describe("buildRows change attributes (ENH-009)", () => {
  it("reads changePp/changePct verbatim from the sensor attribute, not derived from sparkline history", () => {
    const hass = mockHass();
    // The backend's real windowed figures - the card must surface these exactly.
    hass.states["sensor.yes_probability"].attributes.change_pp = 4.2;
    hass.states["sensor.aapl_price"].attributes.change_pct = -1.75;
    const rows = buildRows(hass);

    const outcome = rows.find((r) => r.kind === "outcome");
    expect(outcome.changePp).toBe(4.2);

    const stock = rows.find((r) => r.kind === "stock");
    expect(stock.changePct).toBe(-1.75);

    // A sparkline-derived approximation over the same instrument's history
    // would disagree with the backend's figure above (different window);
    // buildRows must not reproduce that approximation.
    const sparklineApprox = changeFromHistory([
      { t: "1", p: 148.2 },
      { t: "2", p: 150.5 },
    ]);
    expect(sparklineApprox.changePct).not.toBeCloseTo(stock.changePct);
  });

  it("is null when the sensor attribute is absent", () => {
    const rows = buildRows(mockHass());
    const outcome = rows.find((r) => r.kind === "outcome");
    const stock = rows.find((r) => r.kind === "stock");
    expect(outcome.changePp).toBeNull();
    expect(stock.changePct).toBeNull();
  });
});

describe("changeFromHistory", () => {
  it("computes delta and percent change from first to last point", () => {
    const { changePct, deltaPp } = changeFromHistory([
      { t: "1", p: 100 },
      { t: "2", p: 103 },
    ]);
    expect(deltaPp).toBeCloseTo(3);
    expect(changePct).toBeCloseTo(3);
  });

  it("returns nulls for fewer than 2 points", () => {
    expect(changeFromHistory([])).toEqual({ changePct: null, deltaPp: null });
    expect(changeFromHistory([{ t: "1", p: 1 }])).toEqual({ changePct: null, deltaPp: null });
  });

  it("handles a zero starting price without dividing by zero", () => {
    const { changePct, deltaPp } = changeFromHistory([
      { t: "1", p: 0 },
      { t: "2", p: 5 },
    ]);
    expect(deltaPp).toBe(5);
    expect(changePct).toBeNull();
  });
});
