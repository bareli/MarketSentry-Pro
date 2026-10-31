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
});

test("instrument card: fx kind shows the published date", async ({ page }) => {
  await openHarness(page);
  const card = page.locator("#instrument-fx");
  await expect(card.locator(".value").first()).toHaveText("3.9123 ILS");
  await expect(card.locator(".footer")).toContainText("Published");
});
