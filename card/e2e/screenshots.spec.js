import { expect, test } from "@playwright/test";

async function openHarness(page, params = "") {
  await page.goto(`/card/e2e/harness.html${params}`);
  await page.evaluate(() => window.__cardReady);
}

test("light theme renders all three instrument kinds", async ({ page }) => {
  await openHarness(page);
  const card = page.locator("marketsentry-card");
  await expect(card).toBeVisible();
  await expect(page).toHaveScreenshot("card-light.png");
});

test("dark theme", async ({ page }) => {
  await openHarness(page, "?theme=dark");
  await expect(page).toHaveScreenshot("card-dark.png");
});

test("RTL layout", async ({ page }) => {
  await openHarness(page, "?dir=rtl");
  const html = page.locator("html");
  await expect(html).toHaveAttribute("dir", "rtl");
  await expect(page).toHaveScreenshot("card-rtl.png");
});

test("renders a row per mixed instrument with kind-appropriate chips", async ({ page }) => {
  await openHarness(page);
  const rows = page.locator("marketsentry-card").locator("css=.row");
  await expect(rows).toHaveCount(3);

  const names = await rows.locator(".row-name").allTextContents();
  expect(names.join(" ")).toContain("Yes");
  expect(names.join(" ")).toContain("AAPL");
  expect(names.join(" ")).toContain("EUR/ILS");
});

test("outcome row links out to Polymarket, FX row has no link", async ({ page }) => {
  await openHarness(page);
  const rows = page.locator("marketsentry-card").locator("css=.row");

  const outcomeRow = rows.filter({ hasText: "Yes" });
  await expect(outcomeRow.locator("a")).toHaveAttribute("href", /polymarket\.com/);

  const fxRow = rows.filter({ hasText: "EUR/ILS" });
  await expect(fxRow.locator("a")).toHaveCount(0);
});

test("instrument card: outcome kind shows a probability bar and volume/liquidity stats", async ({ page }) => {
  await openHarness(page);
  const card = page.locator("#instrument-outcome");
  await expect(card.locator(".prob-bar")).toBeVisible();
  await expect(card.locator(".value")).toHaveText("62.3%");
  const statLabels = await card.locator(".stat-label").allTextContents();
  expect(statLabels).toEqual(["Volume 24h", "Liquidity"]);
  const statValues = await card.locator(".stat-value").allTextContents();
  expect(statValues).toEqual(["$1.2M", "$340.0K"]);
});

test("instrument card: stock kind shows a sparkline and previous close", async ({ page }) => {
  await openHarness(page);
  const card = page.locator("#instrument-stock");
  await expect(card.locator(".big-spark svg")).toBeVisible();
  await expect(card.locator(".value").first()).toHaveText("$150.52");
  await expect(card.locator(".stat-label")).toHaveText("Prev close");
  await expect(card.locator(".stat-value")).toHaveText("$148.20");

  // Richer chart: filled area under the line, a "now" marker dot, and a
  // min/max range label overlay.
  await expect(card.locator(".big-spark svg path[fill-opacity]")).toHaveCount(1);
  await expect(card.locator(".big-spark svg circle")).toHaveCount(1);
  const rangeLabels = await card.locator(".spark-range span").allTextContents();
  expect(rangeLabels).toHaveLength(2);
  expect(rangeLabels[0]).toMatch(/^\$\d/); // max
  expect(rangeLabels[1]).toMatch(/^\$\d/); // min
});

test("instrument card: fx kind shows the published date", async ({ page }) => {
  await openHarness(page);
  const card = page.locator("#instrument-fx");
  await expect(card.locator(".value").first()).toHaveText("3.9123 ILS");
  await expect(card.locator(".footer")).toContainText("Published");
});

test("renders in Hebrew when hass's language is he", async ({ page }) => {
  await openHarness(page, "?lang=he&dir=rtl");
  const list = page.locator("marketsentry-card");
  const groupLabels = await list.locator(".group-label").allTextContents();
  expect(groupLabels).toContain("שוקי חיזוי"); // "Prediction markets"
  expect(groupLabels).toContain("מניות"); // "Stocks"
  expect(groupLabels).toContain("שערי חליפין"); // "Exchange rates"

  const stockCard = page.locator("#instrument-stock");
  await expect(stockCard.locator(".stat-label")).toHaveText("סגירה קודמת"); // "Prev close"
});
