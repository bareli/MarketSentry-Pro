import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /.*\.spec\.js/,
  fullyParallel: true,
  reporter: "list",
  webServer: {
    command: "node e2e/server.mjs",
    url: "http://localhost:4173/card/e2e/harness.html",
    reuseExistingServer: true,
  },
  use: {
    baseURL: "http://localhost:4173",
  },
});
