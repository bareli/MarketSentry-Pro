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

/**
 * Same path as {@link buildSparklinePath}, closed down to the baseline so
 * it can be filled as an area under the line.
 * @param {Array<{t: string, p: number}>} points
 * @param {number} [width]
 * @param {number} [height]
 * @returns {string|null}
 */
export function buildSparklineArea(points, width = 80, height = 24) {
  const line = buildSparklinePath(points, width, height);
  if (!line) return null;
  const stepX = width / (points.length - 1);
  const lastX = (points.length - 1) * stepX;
  return `${line} L${lastX.toFixed(1)},${height} L0,${height} Z`;
}

/**
 * Pixel coordinates (in the same width/height viewBox as the path builders
 * above) of the most recent point, for drawing a "now" marker.
 * @param {Array<{t: string, p: number}>} points
 * @param {number} [width]
 * @param {number} [height]
 * @returns {{x: number, y: number}|null}
 */
export function sparklineLastPoint(points, width = 80, height = 24) {
  if (!points || points.length < 2) return null;
  const prices = points.map((point) => point.p);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const stepX = width / (points.length - 1);
  const lastIndex = points.length - 1;
  return {
    x: lastIndex * stepX,
    y: height - ((points[lastIndex].p - min) / range) * height,
  };
}

/**
 * The min/max price over the window, for a small range label next to the
 * chart. @param {Array<{t: string, p: number}>} points
 * @returns {{min: number, max: number}|null}
 */
export function sparklineRange(points) {
  if (!points || points.length === 0) return null;
  const prices = points.map((point) => point.p);
  return { min: Math.min(...prices), max: Math.max(...prices) };
}
