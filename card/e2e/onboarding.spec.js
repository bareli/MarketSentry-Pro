import { expect, test } from "@playwright/test";

// Regression coverage for the "ease first-run setup" trio:
// - CARD-04b (BUG-002): a zero-instrument stub config must not crash setConfig.
// - ENH-002: the resulting empty state must point back to Settings > Devices &
//   services > MarketSentry Pro, while a genuinely unmatched (non-empty)
//   entity id keeps the specific "not found" text, no link.
// - ENH-001: the list card's zero-instrument state must read as "nothing
//   tracked yet", not "your filters excluded everything", while a real
//   filter-mismatch (rows exist, just filtered out) keeps the old wording.

async function openHarness(page) {
  await page.goto("/card/e2e/harness.html");
  await page.evaluate(() => window.__cardReady);
}

test("CARD-04b: zero-instrument stub config does not throw and shows an onboarding link", async ({ page }) => {
  await openHarness(page);

  const result = await page.evaluate(() => {
    const Ctor = customElements.get("marketsentry-instrument-card");
    const emptyHass = { language: "en", entities: {}, states: {}, devices: {}, callWS: async () => ({ history: [] }) };
    const stub = Ctor.getStubConfig(emptyHass);

    const el = document.createElement("marketsentry-instrument-card");
    document.body.appendChild(el);
    let threw = false;
    let message = null;
    try {
      el.setConfig(stub);
    } catch (e) {
      threw = true;
      message = e.message;
    }
    el.hass = emptyHass;

    const emptyEl = el.shadowRoot?.querySelector(".empty");
    const text = emptyEl?.textContent || "";
    const link = emptyEl?.querySelector("a");
    const href = link?.getAttribute("href") || null;
    el.remove();
    return { stub, threw, message, text, href };
  });

  expect(result.stub).toEqual({ type: "custom:marketsentry-instrument-card", entity: "" });
  expect(result.threw).toBe(false);
  expect(result.message).toBeNull();
  expect(result.href).toBe("/config/integrations/integration/marketsentry");
  expect(result.text).toContain("Settings");
});

test("ENH-002: an unmatched non-empty entity still shows the specific not-found text, no onboarding link", async ({
  page,
}) => {
  await openHarness(page);

  const result = await page.evaluate(() => {
    const emptyHass = { language: "en", entities: {}, states: {}, devices: {}, callWS: async () => ({ history: [] }) };
    const el = document.createElement("marketsentry-instrument-card");
    document.body.appendChild(el);
    el.setConfig({ type: "custom:marketsentry-instrument-card", entity: "sensor.does_not_exist" });
    el.hass = emptyHass;
    const emptyEl = el.shadowRoot?.querySelector(".empty");
    const text = emptyEl?.textContent || "";
    const hasLink = !!emptyEl?.querySelector("a");
    el.remove();
    return { text, hasLink };
  });

  expect(result.text).toContain("sensor.does_not_exist");
  expect(result.hasLink).toBe(false);
});

test("ENH-001: a zero-instrument account shows the 'nothing tracked yet' message on the list card", async ({
  page,
}) => {
  await openHarness(page);

  const text = await page.evaluate(() => {
    const emptyHass = { language: "en", entities: {}, states: {}, devices: {} };
    const el = document.createElement("marketsentry-card");
    document.body.appendChild(el);
    el.setConfig({ type: "custom:marketsentry-card", group_by: "kind" });
    el.hass = emptyHass;
    const t = el.shadowRoot?.querySelector(".empty")?.textContent || "";
    el.remove();
    return t;
  });

  expect(text).toContain("tracked yet");
  expect(text).not.toContain("filters");
});

test("ENH-001: a real filter mismatch (rows exist, all filtered out) keeps the old filters wording", async ({
  page,
}) => {
  await openHarness(page);

  const text = await page.evaluate(() => {
    const el = document.getElementById("card");
    const hass = el._hass;
    const probe = document.createElement("marketsentry-card");
    document.body.appendChild(probe);
    // "crypto" rows exist in the harness's mock data, so filtering to a kind
    // nobody has (e.g. a typo'd kind) leaves rows > 0 but filtered === 0.
    probe.setConfig({ type: "custom:marketsentry-card", kinds: ["nonexistent-kind"] });
    probe.hass = hass;
    const t = probe.shadowRoot?.querySelector(".empty")?.textContent || "";
    probe.remove();
    return t;
  });

  expect(text).toContain("filters");
  expect(text).not.toContain("tracked yet");
});
