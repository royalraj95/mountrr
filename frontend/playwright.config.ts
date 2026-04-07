import {defineConfig, devices} from "@playwright/test";

/**
 * Frontend E2E tests using Playwright.
 *
 * These tests require the backend to be running against seeded dev data.
 * Run `cd ../backend && uv run python scripts/seed_dev_data.py` first.
 *
 * The webServer block auto-starts the backend; if it's already running
 * on :8484, Playwright will reuse it.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",

  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: [
    {
      // Backend: seed data must already exist at /tmp/mountrr-dev
      command:
        "DB_PATH=/tmp/mountrr-dev/data/symlinks.db uv run uvicorn mountrr.main:app --port 8484",
      cwd: "../backend",
      url: "http://localhost:8484/api/health",
      reuseExistingServer: !process.env.CI,
      timeout: 15_000,
    },
    {
      // Frontend dev server
      command: "pnpm dev",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 15_000,
    },
  ],
});
