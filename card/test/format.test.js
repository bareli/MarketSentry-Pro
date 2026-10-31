import { describe, expect, it } from "vitest";
import { formatChange, formatCompactUsd, formatDate, formatValue, marketStateLabel, statusBadge } from "../src/format.js";

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

describe("formatCompactUsd", () => {
  it("formats millions with one decimal", () => {
    expect(formatCompactUsd(1_234_000)).toBe("$1.2M");
  });

  it("formats thousands with one decimal", () => {
    expect(formatCompactUsd(340_000)).toBe("$340.0K");
  });

  it("formats sub-thousand values as whole dollars", () => {
    expect(formatCompactUsd(980)).toBe("$980");
  });

  it("returns an em dash for null/NaN", () => {
    expect(formatCompactUsd(null)).toBe("—");
    expect(formatCompactUsd(Number.NaN)).toBe("—");
  });
});

describe("formatDate", () => {
  it("formats an ISO date as a short locale date", () => {
    expect(formatDate("2026-11-03T00:00:00Z")).toMatch(/Nov.*3.*2026/);
  });

  it("returns an em dash for missing/invalid dates", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("not-a-date")).toBe("—");
  });
});

describe("marketStateLabel", () => {
  it("maps known states to stable ids", () => {
    expect(marketStateLabel("pre")).toBe("pre");
    expect(marketStateLabel("regular")).toBe("open");
    expect(marketStateLabel("post")).toBe("after");
    expect(marketStateLabel("closed")).toBe("closed");
  });

  it("defaults to closed for unknown/missing state", () => {
    expect(marketStateLabel(null)).toBe("closed");
    expect(marketStateLabel(undefined)).toBe("closed");
  });
});

describe("statusBadge", () => {
  const now = new Date("2026-06-10T12:00:00Z");

  it("outcome: resolved takes priority", () => {
    expect(statusBadge({ kind: "outcome", resolutionStatus: "resolved", closed: true }, now)).toBe(
      "resolved"
    );
  });

  it("outcome: closed (not resolved) shows closed", () => {
    expect(statusBadge({ kind: "outcome", resolutionStatus: "open", closed: true }, now)).toBe("closed");
  });

  it("outcome: within 24h of end date shows closing_soon", () => {
    expect(
      statusBadge(
        { kind: "outcome", resolutionStatus: "open", closed: false, endDate: "2026-06-11T06:00:00Z" },
        now
      )
    ).toBe("closing_soon");
  });

  it("outcome: far from end date shows live", () => {
    expect(
      statusBadge(
        { kind: "outcome", resolutionStatus: "open", closed: false, endDate: "2026-07-01T00:00:00Z" },
        now
      )
    ).toBe("live");
  });

  it("stock: regular/pre/post market state shows open", () => {
    expect(statusBadge({ kind: "stock", marketState: "regular" })).toBe("open");
    expect(statusBadge({ kind: "stock", marketState: "pre" })).toBe("open");
  });

  it("stock: closed market state shows closed", () => {
    expect(statusBadge({ kind: "stock", marketState: "closed" })).toBe("closed");
  });

  it("fx: published today shows updated_today", () => {
    expect(statusBadge({ kind: "fx", publishedDate: "2026-06-10" }, now)).toBe("updated_today");
  });

  it("fx: published on an earlier date shows stale", () => {
    expect(statusBadge({ kind: "fx", publishedDate: "2026-06-08" }, now)).toBe("stale");
  });

  it("fx: no published date shows stale", () => {
    expect(statusBadge({ kind: "fx", publishedDate: null }, now)).toBe("stale");
  });

  it("crypto: always shows live (trades 24/7)", () => {
    expect(statusBadge({ kind: "crypto" }, now)).toBe("live");
  });
});
