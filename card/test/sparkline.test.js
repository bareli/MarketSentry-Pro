import { describe, expect, it } from "vitest";
import { buildSparklinePath } from "../src/sparkline.js";

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
