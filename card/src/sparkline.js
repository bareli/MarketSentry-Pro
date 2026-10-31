/**
 * Pure inline-SVG sparkline path builder. No DOM — returns an SVG path `d`
 * attribute string the card embeds directly.
 */

/**
 * @param {Array<{t: string, p: number}>} points
 * @param {number} [width]
 * @param {number} [height]
 * @returns {string|null} an SVG path `d` string, or null if there isn't
 *   enough data to draw a line.
 */
export function buildSparklinePath(points, width = 80, height = 24) {
  if (!points || points.length < 2) return null;

  const prices = points.map((point) => point.p);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const stepX = width / (points.length - 1);

  const coords = points.map((point, index) => {
    const x = index * stepX;
    const y = height - ((point.p - min) / range) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return `M${coords.join(" L")}`;
}
