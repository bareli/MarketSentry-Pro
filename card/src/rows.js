/**
 * Derive card rows from the HA frontend's `hass.entities` / `hass.devices` /
 * `hass.states` registries — the standard way a custom card reads entity
 * data without a custom WS round trip (see entity.py's `card_attributes`
 * on the Python side, which puts kind/provider/url on each kind's primary
 * sensor for exactly this purpose).
 *
 * Built against the documented/standard shape of `hass.entities` (a
 * Record<string, EntityRegistryDisplayEntry> with `platform`,
 * `device_id`, `translation_key`) and `hass.devices` (a
 * Record<string, DeviceRegistryEntry> with `name`, `name_by_user`) used
 * throughout the HA frontend and HACS card ecosystem. Not verified against
 * a live HA frontend session in this project (no running instance
 * available); the Playwright harness tests exercise this against a mock
 * `hass` shaped the same way.
 */

const PLATFORM = "marketsentry";
const PRIMARY_TRANSLATION_KEYS = new Set(["probability", "price", "rate"]);

/** @param {any} hass @returns {object[]} */
export function buildRows(hass) {
  if (!hass || !hass.entities || !hass.states) return [];

  const allEntities = Object.values(hass.entities).filter((e) => e.platform === PLATFORM);
  const primaryEntities = allEntities.filter((e) => PRIMARY_TRANSLATION_KEYS.has(e.translation_key));

  const rows = [];
  for (const entity of primaryEntities) {
    const state = hass.states[entity.entity_id];
    if (!state) continue;
    const attrs = state.attributes || {};
    const device = entity.device_id ? hass.devices?.[entity.device_id] : null;
    const name = device?.name_by_user || device?.name || attrs.friendly_name || entity.entity_id;

    const row = {
      entityId: entity.entity_id,
      deviceId: entity.device_id,
      name,
      kind: attrs.kind,
      provider: attrs.provider,
      url: attrs.url,
      value: ["unknown", "unavailable"].includes(state.state) ? null : Number(state.state),
      unit: attrs.unit_of_measurement,
      resolutionStatus: null,
      closed: null,
      endDate: null,
      marketState: null,
      publishedDate: attrs.published_date ?? null,
      source: attrs.source ?? null,
      volume24hr: null,
      liquidity: null,
      previousClose: null,
    };

    for (const sibling of allEntities) {
      if (sibling.device_id !== entity.device_id) continue;
      const siblingState = hass.states[sibling.entity_id];
      if (!siblingState) continue;
      const siblingValue = ["unknown", "unavailable"].includes(siblingState.state)
        ? null
        : Number(siblingState.state);
      switch (sibling.translation_key) {
        case "resolution_status":
          row.resolutionStatus = siblingState.state;
          break;
        case "closed":
          row.closed = siblingState.state === "on";
          break;
        case "end_date":
          row.endDate = siblingState.state;
          break;
        case "market_state":
          row.marketState = siblingState.state;
          break;
        case "volume_24hr":
          row.volume24hr = siblingValue;
          break;
        case "liquidity":
          row.liquidity = siblingValue;
          break;
        case "previous_close":
          row.previousClose = siblingValue;
          break;
        default:
          break;
      }
    }

    rows.push(row);
  }

  return rows;
}

/** Rough "change since the sparkline's oldest point" from ring-buffer history. */
export function changeFromHistory(points) {
  if (!points || points.length < 2) return { changePct: null, deltaPp: null };
  const first = points[0].p;
  const last = points[points.length - 1].p;
  const deltaPp = last - first;
  const changePct = first ? (deltaPp / first) * 100 : null;
  return { changePct, deltaPp };
}
