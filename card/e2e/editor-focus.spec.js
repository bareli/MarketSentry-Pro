import { expect, test } from "@playwright/test";

async function openHarness(page) {
  await page.goto("/card/e2e/harness-editor.html");
  await page.evaluate(() => window.__editorsReady);
}

test("title field keeps focus and element identity while typing, even as HA echoes setConfig back", async ({
  page,
}) => {
  await openHarness(page);

  const input = page.locator("#editor").locator('input[type="text"]');
  await input.click();

  // Tag the live DOM node so we can tell if a later render replaced it
  // with a fresh <input> (which is exactly what drops focus/cursor).
  await input.evaluate((el) => (el.dataset.probe = "same-node"));

  await page.keyboard.type("My title", { delay: 20 });

  await expect(input).toHaveValue("My title");
  await expect(input).toBeFocused();
  await expect(input).toHaveAttribute("data-probe", "same-node");
});

test("instrument entity dropdown keeps its options and isn't rebuilt on unrelated hass updates", async ({
  page,
}) => {
  await openHarness(page);

  const select = page.locator("#instrument-editor").locator("select");
  await select.evaluate((el) => (el.dataset.probe = "same-node"));

  // Simulate HA pushing a routine hass update (e.g. a polled state change)
  // completely unrelated to the editor's own config.
  await page.evaluate(() => {
    const editor = document.getElementById("instrument-editor");
    const hass = editor._hass;
    editor.hass = { ...hass, states: { ...hass.states } };
  });

  await expect(select).toHaveAttribute("data-probe", "same-node");
  await expect(select.locator("option")).toHaveCount(3); // placeholder + 2 instruments

  await select.selectOption("sensor.aapl_price");
  await expect(select).toHaveValue("sensor.aapl_price");
});
