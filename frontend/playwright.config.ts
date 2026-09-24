import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: "http://127.0.0.1:5173",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
  webServer: [
    {
      command: "cd ../backend && uv run --env-file .env.example fastapi run main.py --host 127.0.0.1 --port 8000",
      reuseExistingServer: !process.env.CI,
      url: "http://127.0.0.1:8000/docs",
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      reuseExistingServer: !process.env.CI,
      url: "http://127.0.0.1:5173",
    },
  ],
});
