import { afterEach, describe, expect, test, vi } from "vitest";

import { ApiClientError } from "./client";
import {
  createEvolutionStep,
  getEvolutionStep,
  getLineage,
  patchEvolutionStep,
  listEvolutionSteps,
} from "./evolutionSteps";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("listEvolutionSteps", () => {
  test("reuses the server-issued opaque token without exposing an input", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], nextPageToken: null }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await listEvolutionSteps("opaque+/=");
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/evolution-steps?pageToken=opaque%2B%2F%3D");
  });
});

describe("createEvolutionStep", () => {
  test("posts the documented request body to Evolution Steps", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 1 }), { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await createEvolutionStep({
      purpose: "Improve baseline",
      hypothesis: "Augmentation helps.",
      changeDescription: null,
      parentRunId: null,
      resultRunId: "run-001",
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/evolution-steps", {
      body: JSON.stringify({
        purpose: "Improve baseline",
        hypothesis: "Augmentation helps.",
        changeDescription: null,
        parentRunId: null,
        resultRunId: "run-001",
      }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });
  });

  test("preserves a typed conflict response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "lineage_conflict",
            message: "The selected Run would create a lineage cycle.",
            traceId: "trace-001",
          }),
          { status: 409 },
        ),
      ),
    );

    await expect(
      createEvolutionStep({ purpose: "p", hypothesis: "h" }),
    ).rejects.toBeInstanceOf(ApiClientError);
  });
});

describe("getEvolutionStep", () => {
  test("requests the documented detail URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 12 }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await getEvolutionStep(12);

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/evolution-steps/12", {});
  });
});

describe("getLineage", () => {
  test("requests the documented URL without changing ordered arrays or null boundaries", async () => {
    const lineage = {
      selected: {
        id: 2,
        purpose: "Selected",
        hypothesis: "Current links are shown.",
        parentEvolutionStepId: 1,
        distanceFromSelected: 0,
        parentRun: null,
        resultRun: null,
      },
      ancestors: [],
      descendants: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(lineage), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await getLineage(2);

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/evolution-steps/2/lineage", {});
    expect(response).toEqual(lineage);
  });
});

describe("patchEvolutionStep", () => {
  test("sends only the supplied patch fields, including explicit null", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 12 }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await patchEvolutionStep(12, { changeDescription: null, resultRunId: null });

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/evolution-steps/12", {
      body: JSON.stringify({ changeDescription: null, resultRunId: null }),
      headers: { "content-type": "application/json" },
      method: "PATCH",
    });
  });
});
