import { expect, test, type Page, type Route } from "@playwright/test";

const RESULT_RUN_ID = "run-result-001";

test("shows validation, creates a Step, and displays the attached result Run", async ({ page }) => {
  const apiRequests: string[] = [];
  await stubApi(page, apiRequests);

  await page.goto("/evolution-steps/new");
  await page.getByRole("button", { name: "Save Evolution Step" }).click();
  await expect(page.getByText("Purpose is required.")).toBeVisible();
  await expect(page.getByText("Hypothesis is required.")).toBeVisible();

  await page.getByLabel("Purpose").fill("Improve image classification");
  await page.getByLabel("Hypothesis").fill("Data augmentation improves accuracy.");
  await page.getByLabel("Result Run", { exact: true }).selectOption(RESULT_RUN_ID);
  await page.getByRole("button", { name: "Save Evolution Step" }).click();

  await expect(page).toHaveURL("/evolution-steps/42");
  await expect(page.getByRole("heading", { name: "Improve image classification" })).toBeVisible();
  await expect(page.getByText(RESULT_RUN_ID).first()).toBeVisible();
  expect(apiRequests).toContain("http://127.0.0.1:5173/api/v1/evolution-steps");
});

/**
 * Fulfill deterministic API fixtures while retaining the browser's Vite-origin URLs.
 *
 * @param page - Browser page issuing relative `/api/v1` requests.
 * @param apiRequests - Collected complete browser request URLs for the assertion.
 */
async function stubApi(page: Page, apiRequests: string[]): Promise<void> {
  await page.route("**/api/v1/**", async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    apiRequests.push(url.toString());

    if (url.pathname === "/api/v1/runs" && request.method() === "GET") {
      await route.fulfill({ json: { items: [candidate()], nextPageToken: null } });
      return;
    }
    if (url.pathname === "/api/v1/evolution-steps" && request.method() === "POST") {
      await route.fulfill({ status: 201, json: { id: 42 } });
      return;
    }
    if (url.pathname === "/api/v1/evolution-steps/42" && request.method() === "GET") {
      await route.fulfill({ json: detail() });
      return;
    }
    if (url.pathname === "/api/v1/evolution-steps/42/comparison") {
      await route.fulfill({
        json: {
          status: "unavailable",
          unavailableReason: "parent_run_missing",
          parameters: [],
          accuracy: unavailableAccuracy(),
          datasets: unavailableDatasets(),
        },
      });
      return;
    }
    if (url.pathname === "/api/v1/evolution-steps/42/lineage") {
      await route.fulfill({ json: { selected: lineageStep(), ancestors: [], descendants: [] } });
      return;
    }
    await route.fulfill({ status: 404, json: { code: "not_found" } });
  });
}

function candidate(): object {
  return {
    runId: RESULT_RUN_ID,
    runName: "result-run",
    mlflowExperimentId: "experiment-1",
    mlflowExperimentName: "image-classification",
    status: "FINISHED",
    startedAt: "2026-09-24T10:00:00Z",
    endedAt: "2026-09-24T10:10:00Z",
  };
}

function detail(): object {
  return {
    id: 42,
    purpose: "Improve image classification",
    hypothesis: "Data augmentation improves accuracy.",
    changeDescription: null,
    parentRun: null,
    resultRun: { reference: runSummary(), snapshot: null },
    createdAt: "2026-09-24T10:00:00Z",
    updatedAt: "2026-09-24T10:00:00Z",
    history: [],
  };
}

function lineageStep(): object {
  return {
    id: 42,
    purpose: "Improve image classification",
    hypothesis: "Data augmentation improves accuracy.",
    parentEvolutionStepId: null,
    distanceFromSelected: 0,
    parentRun: null,
    resultRun: runSummary(),
  };
}

function runSummary(): object {
  return {
    runId: RESULT_RUN_ID,
    runName: "result-run",
    currentStatus: "FINISHED",
    startedAt: "2026-09-24T10:00:00Z",
    endedAt: "2026-09-24T10:10:00Z",
    lastSyncedAt: "2026-09-24T10:10:00Z",
    snapshotState: "pending",
    snapshotCapturedAt: null,
  };
}

function unavailableAccuracy(): object {
  return {
    status: "unavailable",
    unavailableReason: "comparison_unavailable",
    parentBest: null,
    resultBest: null,
    delta: null,
  };
}

function unavailableDatasets(): object {
  return {
    status: "unavailable",
    unavailableReason: "comparison_unavailable",
    differences: [],
  };
}
