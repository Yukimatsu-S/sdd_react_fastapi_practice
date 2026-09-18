import { afterEach, describe, expect, test, vi } from "vitest";

import { ApiClientError, NetworkError, requestJson } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("requestJson", () => {
  test("uses the same-origin API base and parses a successful JSON response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 1 }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(requestJson<{ id: number }>("/evolution-steps")).resolves.toEqual({ id: 1 });

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/evolution-steps");
  });

  test("raises a typed API error for a JSON error response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "result_run_conflict",
            message: "The result Run is already linked.",
            traceId: "trace-001",
          }),
          { status: 409, headers: { "content-type": "application/json" } },
        ),
      ),
    );

    await expect(requestJson("/evolution-steps")).rejects.toMatchObject({
      name: ApiClientError.name,
      status: 409,
      code: "result_run_conflict",
      traceId: "trace-001",
    });
  });

  test("raises a typed network error when fetch cannot reach the server", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(requestJson("/evolution-steps")).rejects.toBeInstanceOf(NetworkError);
  });
});
