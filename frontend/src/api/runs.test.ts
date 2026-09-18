import { afterEach, describe, expect, test, vi } from "vitest";

import { ApiClientError } from "./client";
import {
  getBestStepMetrics,
  isMlflowUnavailableError,
  searchRuns,
  syncRun,
} from "./runs";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("search", () => {
  test("keeps the server-issued page token opaque in the search URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], nextPageToken: null }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await searchRuns({ query: "baseline", pageToken: "opaque-token" });

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/runs?query=baseline&pageToken=opaque-token",
    );
  });
});

describe("sync", () => {
  test("posts a selected Run ID to the synchronization endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ run: {} }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await syncRun("run-001");

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/runs/run-001/sync", {
      method: "POST",
    });
  });

  test("classifies the documented MLflow upstream failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "mlflow_unavailable",
            message: "MLflow Run could not be loaded.",
            traceId: "trace-001",
          }),
          { status: 502 },
        ),
      ),
    );

    try {
      await syncRun("run-001");
      throw new Error("Expected syncRun to reject.");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiClientError);
      expect(isMlflowUnavailableError(error)).toBe(true);
    }
  });
});

describe("best-step metrics", () => {
  test("gets signed best-step Metrics and preserves unavailable fields", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          runId: "run-001",
          status: "unavailable",
          unavailableReason: "accuracy_missing",
          bestAccuracy: null,
          bestAccuracyStep: null,
          bestAccuracyRecordedAt: null,
          items: [],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getBestStepMetrics("run-001");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/runs/run-001/best-step-metrics",
      {},
    );
    expect(result).toMatchObject({ bestAccuracyStep: null, items: [] });
  });
});
