import { buildRows } from "./rows.js";

/**
 * Pure logic for the marketsentry view strategy - no DOM, unit testable in
 * isolation (see test/view-strategy.test.js). Kept out of
 * marketsentry-view-strategy.js so importing it doesn't require a DOM
 * (that file extends HTMLElement at module load time).
 * @param {{title?: string, group_by?: "none"|"provider"|"kind", kinds?: string[]}} config
 * @param {any} hass
 */
export function buildStrategyView(config, hass) {
  const kinds = config?.kinds;
  const rows = buildRows(hass);
  const filtered = kinds ? rows.filter((row) => kinds.includes(row.kind)) : rows;

  if (filtered.length === 0) {
    return {
      cards: [
        {
          type: "markdown",
          content:
            "No MarketSentry Pro instruments are tracked yet. Add one via Settings > Devices & services > MarketSentry Pro > Add instrument.",
        },
      ],
    };
  }

  return {
    cards: [
      {
        type: "custom:marketsentry-card",
        title: config?.title ?? "Markets",
        group_by: config?.group_by ?? "kind",
        ...(kinds ? { kinds } : {}),
      },
      ...filtered.map((row) => ({
        type: "custom:marketsentry-instrument-card",
        entity: row.entityId,
      })),
    ],
  };
}
