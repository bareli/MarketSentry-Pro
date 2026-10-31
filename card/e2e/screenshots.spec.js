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
