/**
 * Pure grouping/filtering helpers for marketsentry-card. No DOM, no hass.
 */

/** @param {Array<{kind: string}>} rows @param {string[]|undefined} kinds */
export function filterByKind(rows, kinds) {
  if (!kinds || kinds.length === 0) return rows;
  return rows.filter((row) => kinds.includes(row.kind));
}

/**
 * @param {Array<{provider: string, kind: string}>} rows
 * @param {"provider"|"kind"|"none"|undefined} groupBy
 * @returns {Array<{label: string|null, rows: object[]}>}
 */
export function groupRows(rows, groupBy) {
  if (!groupBy || groupBy === "none") {
    return rows.length ? [{ label: null, rows }] : [];
  }
  const groups = new Map();
  for (const row of rows) {
    const key = groupBy === "provider" ? row.provider : row.kind;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return Array.from(groups.entries()).map(([label, groupedRows]) => ({ label, rows: groupedRows }));
}
