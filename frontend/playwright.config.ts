import { defineConfig, devices } from "@playwright/test";

/**
 * ローカルサーバーで実行 (デフォルト):
 *   npm run test:e2e
 *
 * 本番 URL で実行:
 *   PLAYWRIGHT_BASE_URL=https://your-url.vercel.app npm run test:e2e
 *
 * 本番保護バイパス:
 *   PLAYWRIGHT_BASE_URL=... VERCEL_BYPASS=<secret> npm run test:e2e
 */

const USE_LOCAL = !process.env.PLAYWRIGHT_BASE_URL;
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 1,
  workers: 1,
  reporter: [["html", { open: "never" }], ["list"]],

  use: {
    baseURL: BASE_URL,
    locale: "ja",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "on-first-retry",
    extraHTTPHeaders: process.env.VERCEL_BYPASS
      ? { "x-vercel-protection-bypass": process.env.VERCEL_BYPASS }
      : {},
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: USE_LOCAL
    ? {
        command: "npm run dev",
        port: 3000,
        reuseExistingServer: true,
        timeout: 120_000,
      }
    : undefined,
});
