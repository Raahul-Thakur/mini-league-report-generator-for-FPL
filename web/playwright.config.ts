import { defineConfig, devices } from "@playwright/test";

// E2E runs the real FastAPI backend against offline fixture data (scripts/fake_server.py)
// and a production build of this site. No FPL traffic.
const PYTHON = process.env.PYTHON ?? "python3";
// Reusing already-running servers is opt-in: a stale server silently tests old code.
const reuse = process.env.PW_REUSE === "1";
// Run with the production security setup: shared key, and limits high enough for the suite.
const KEY = "e2e-internal-key";
const API_ENV = `INTERNAL_API_KEY=${KEY} RATE_LIMIT_REPORT=1000/minute RATE_LIMIT_CARD=1000/minute`;
const WEB_ENV = `API_URL=http://127.0.0.1:8100 INTERNAL_API_KEY=${KEY}`;

export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      // Instagram in-app browser on a phone: small viewport, touch, IG user agent
      name: "instagram-mobile",
      use: {
        ...devices["Pixel 7"],
        userAgent: `${devices["Pixel 7"].userAgent} Instagram 300.0.0.0 Android`,
      },
    },
  ],
  webServer: [
    {
      command: `cd .. && PORT=8100 ${API_ENV} exec ${PYTHON} -m scripts.fake_server`,
      url: "http://127.0.0.1:8100/api/health",
      reuseExistingServer: reuse,
    },
    {
      // exec so the server is the process Playwright stops (no orphaned next-server)
      command: `${WEB_ENV} npx next build && ${WEB_ENV} exec npx next start -p 3100`,
      url: "http://127.0.0.1:3100",
      timeout: 240_000,
      reuseExistingServer: reuse,
    },
  ],
});
