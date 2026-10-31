import { describe, expect, it } from "vitest";
import { filterByKind, groupRows } from "../src/grouping.js";

const ROWS = [
  { kind: "outcome", provider: "polymarket", name: "A" },
  { kind: "stock", provider: "finnhub", name: "B" },
  { kind: "stock", provider: "alpaca", name: "C" },
  { kind: "fx", provider: "fx", name: "D" },
];

describe("filterByKind", () => {
  it("returns all rows when kinds is undefined or empty", () => {
    expect(filterByKind(ROWS, undefined)).toHaveLength(4);
    expect(filterByKind(ROWS, [])).toHaveLength(4);
  });

  it("filters to the requested kinds", () => {
    const result = filterByKind(ROWS, ["stock"]);
    expect(result.map((r) => r.name)).toEqual(["B", "C"]);
  });
});

describe("groupRows", () => {
  it("returns a single ungrouped bucket for 'none'", () => {
    const groups = groupRows(ROWS, "none");
    expect(groups).toHaveLength(1);
    expect(groups[0].label).toBeNull();
    expect(groups[0].rows).toHaveLength(4);
  });

  it("returns an empty array for no rows", () => {
    expect(groupRows([], "none")).toEqual([]);
  });

  it("groups by provider", () => {
    const groups = groupRows(ROWS, "provider");
    const labels = groups.map((g) => g.label);
    expect(labels).toEqual(["polymarket", "finnhub", "alpaca", "fx"]);
  });

  it("groups by kind", () => {
    const groups = groupRows(ROWS, "kind");
    const byLabel = Object.fromEntries(groups.map((g) => [g.label, g.rows.map((r) => r.name)]));
    expect(byLabel.stock).toEqual(["B", "C"]);
    expect(byLabel.outcome).toEqual(["A"]);
    expect(byLabel.fx).toEqual(["D"]);
  });
});
