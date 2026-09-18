import { afterEach, describe, expect, test, vi } from "vitest";

import { searchRuns, syncRun } from "./runs";

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
});
