import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { EvolutionStepDetail } from "./EvolutionStepDetail";

describe("EvolutionStepDetail rendering", () => {
  test("renders saved Step text, a pending Run, and captured Parameters", () => {
    render(
      <EvolutionStepDetail
        detail={{
          id: 12,
          purpose: "Improve baseline",
          hypothesis: "Augmentation helps.",
          changeDescription: null,
          parentRun: null,
          resultRun: {
            reference: {
              runId: "run-12",
              runName: "training-v2",
              status: "RUNNING",
              startedAt: "2026-09-18T10:00:00Z",
              endedAt: null,
              snapshotState: "pending",
              snapshotCapturedAt: null,
            },
            snapshot: null,
          },
          createdAt: "2026-09-18T10:00:00Z",
          updatedAt: "2026-09-18T10:00:00Z",
          history: [],
        }}
      />,
    );

    expect(screen.getByText("Improve baseline")).toBeInTheDocument();
    expect(screen.getByText("Snapshot pending")).toBeInTheDocument();
    expect(screen.getByText("run-12")).toBeInTheDocument();
  });
});
