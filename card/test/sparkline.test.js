import { describe, expect, it } from "vitest";
import { buildSparklineArea, buildSparklinePath, sparklineLastPoint, sparklineRange } from "../src/sparkline.js";

describe("buildSparklinePath", () => {
  it("returns null for fewer than 2 points", () => {
    expect(buildSparklinePath([])).toBeNull();
    expect(buildSparklinePath([{ t: "2026-01-01", p: 1 }])).toBeNull();
    expect(buildSparklinePath(null)).toBeNull();
  });

  it("builds an SVG path starting with M for 2+ points", () => {
    const path = buildSparklinePath([
      { t: "1", p: 1 },
      { t: "2", p: 2 },
      { t: "3", p: 3 },
    ]);
    expect(path).toMatch(/^M/);
    expect(path).toContain("L");
  });

  it("handles a flat series (zero range) without dividing by zero", () => {
    const path = buildSparklinePath([
      { t: "1", p: 5 },
      { t: "2", p: 5 },
    ]);
    expect(path).not.toContain("NaN");
    expect(path).not.toContain("Infinity");
  });

  it("spans the requested width across points", () => {
    const path = buildSparklinePath(
      [
        { t: "1", p: 0 },
        { t: "2", p: 10 },
      ],
      100,
      24
    );
    // Last x coordinate should be close to the requested width.
    const lastCoord = path.split(" ").pop().replace("L", "").split(",")[0];
    expect(Number(lastCoord)).toBeCloseTo(100, 0);
  });
});

describe("buildSparklineArea", () => {
  it("returns null for fewer than 2 points", () => {
    expect(buildSparklineArea([])).toBeNull();
  });

  it("closes the line path down to the baseline", () => {
    const area = buildSparklineArea(
      [
        { t: "1", p: 0 },
        { t: "2", p: 10 },
      ],
      100,
      24
    );
    expect(area).toMatch(/^M/);
    expect(area.trim().endsWith("Z")).toBe(true);
    expect(area).toContain("L0,24");
  });
});

describe("sparklineLastPoint", () => {
  it("returns null for fewer than 2 points", () => {
    expect(sparklineLastPoint([{ t: "1", p: 1 }])).toBeNull();
  });

  it("places the last point at the requested width/height", () => {
    const point = sparklineLastPoint(
      [
        { t: "1", p: 0 },
        { t: "2", p: 10 },
      ],
      100,
      24
    );
    expect(point.x).toBeCloseTo(100, 0);
    expect(point.y).toBeCloseTo(0, 0); // highest price -> top of the chart
  });
});

describe("sparklineRange", () => {
  it("returns null for an empty series", () => {
    expect(sparklineRange([])).toBeNull();
  });

  it("returns the min and max price", () => {
    expect(
      sparklineRange([
        { t: "1", p: 3 },
        { t: "2", p: 7 },
        { t: "3", p: 1 },
      ])
    ).toEqual({ min: 1, max: 7 });
  });
});
