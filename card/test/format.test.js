import { describe, expect, it } from "vitest";
import { formatChange, formatValue, marketStateLabel, statusBadge } from "../src/format.js";

describe("formatValue", () => {
  it("formats outcome as one-decimal percent", () => {
    expect(formatValue("outcome", 62.345)).toBe("62.3%");
  });

  it("formats fx with four decimals and unit", () => {
    expect(formatValue("fx", 3.91234, "ILS")).toBe("3.9123 ILS");
  });

  it("formats stock USD with a dollar sign and two decimals", () => {
    expect(formatValue("stock", 150.5, "USD")).toBe("$150.50");
  });

  it("formats stock with a non-USD unit as a prefix", () => {
    expect(formatValue("stock", 150.5, "EUR")).toBe("EUR 150.50");
  });

  it("returns an em dash for null/NaN", () => {
    expect(formatValue("outcome", null)).toBe("—");
    expect(formatValue("stock", Number.NaN, "USD")).toBe("—");
  });
});

describe("formatChange", () => {
  it("formats outcome change in percentage points with explicit sign", () => {
    expect(formatChange("outcome", null, 5.2)).toBe("+5.2pp");
    expect(formatChange("outcome", null, -3.1)).toBe("-3.1pp");
  });

  it("formats stock/fx change as percent", () => {
    expect(formatChange("stock", 2.567, null)).toBe("+2.57%");
    expect(formatChange("fx", -0.4, null)).toBe("-0.40%");
  });

  it("returns null when the relevant value is missing", () => {
    expect(formatChange("outcome", 5, null)).toBeNull();
    expect(formatChange("stock", null, 5)).toBeNull();
  });
});

describe("marketStateLabel", () => {
  it("maps known states", () => {
    expect(marketStateLabel("pre")).toBe("Pre");
    expect(marketStateLabel("regular")).toBe("Open");
    expect(marketStateLabel("post")).toBe("After");
    expect(marketStateLabel("closed")).toBe("Closed");
  });

  it("defaults to Closed for unknown/missing state", () => {
    expect(marketStateLabel(null)).toBe("Closed");
    expect(marketStateLabel(undefined)).toBe("Closed");
  });
});

describe("statusBadge", () => {
  const now = new Date("2026-06-10T12:00:00Z");

  it("outcome: resolved takes priority", () => {
    expect(statusBadge({ kind: "outcome", resolutionStatus: "resolved", closed: true }, now)).toBe(
      "Resolved"
    );
  });

  it("outcome: closed (not resolved) shows Closed", () => {
    expect(statusBadge({ kind: "outcome", resolutionStatus: "open", closed: true }, now)).toBe("Closed");
  });

  it("outcome: within 24h of end date shows Closing soon", () => {
    expect(
      statusBadge(
        { kind: "outcome", resolutionStatus: "open", closed: false, endDate: "2026-06-11T06:00:00Z" },
        now
      )
    ).toBe("Closing soon");
  });

  it("outcome: far from end date shows Live", () => {
    expect(
      statusBadge(
        { kind: "outcome", resolutionStatus: "open", closed: false, endDate: "2026-07-01T00:00:00Z" },
        now
      )
    ).toBe("Live");
  });

  it("stock: regular/pre/post market state shows Open", () => {
    expect(statusBadge({ kind: "stock", marketState: "regular" })).toBe("Open");
    expect(statusBadge({ kind: "stock", marketState: "pre" })).toBe("Open");
  });

  it("stock: closed market state shows Closed", () => {
    expect(statusBadge({ kind: "stock", marketState: "closed" })).toBe("Closed");
  });

  it("fx: published today shows Updated today", () => {
    expect(statusBadge({ kind: "fx", publishedDate: "2026-06-10" }, now)).toBe("Updated today");
  });

  it("fx: published on an earlier date shows Stale", () => {
    expect(statusBadge({ kind: "fx", publishedDate: "2026-06-08" }, now)).toBe("Stale");
  });

  it("fx: no published date shows Stale", () => {
    expect(statusBadge({ kind: "fx", publishedDate: null }, now)).toBe("Stale");
  });
});
