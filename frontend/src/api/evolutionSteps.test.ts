import { afterEach, describe, expect, test, vi } from "vitest";

import { createEvolutionStep } from "./evolutionSteps";

afterEach(() => {
  vi.unstubAllGlobals();
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
});
