import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,

  reporter: [
    ["list"],
    ["html", {
      outputFolder: "playwright-report",
      open: "never"
    }],
    ["json", {
      outputFile: "test-results/frontend-audit-results.json"
    }]
  ],

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 30000,
    navigationTimeout: 60000
  },

  expect: {
    timeout: 30000
  },

  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120000
  },

  projects: [
    {
      name: "mobile-360",
      use: {
        ...devices["iPhone SE"],
        viewport: { width: 360, height: 800 }
      }
    },
    {
      name: "mobile-390",
      use: {
        ...devices["iPhone 13"],
        viewport: { width: 390, height: 844 }
      }
    },
    {
      name: "tablet-portrait",
      use: {
        viewport: { width: 768, height: 1024 },
        isMobile: true,
        hasTouch: true
      }
    },
    {
      name: "tablet-landscape",
      use: {
        viewport: { width: 1024, height: 768 },
        hasTouch: true
      }
    },
    {
      name: "laptop",
      use: {
        viewport: { width: 1366, height: 768 }
      }
    },
    {
      name: "desktop",
      use: {
        viewport: { width: 1440, height: 900 }
      }
    },
    {
      name: "large-desktop",
      use: {
        viewport: { width: 1920, height: 1080 }
      }
    }
  ]
});
