import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { LineagePanel } from "./LineagePanel";

type TestRun = {
  runId: string;
  runName: string | null;
  currentStatus: "FINISHED";
  startedAt: string | null;
  endedAt: string | null;
  lastSyncedAt: string;
  snapshotState: "captured";
  snapshotCapturedAt: string;
};

type TestLineageStep = {
  id: number;
  purpose: string;
  hypothesis: string;
  parentEvolutionStepId: number | null;
  distanceFromSelected: number;
  parentRun: TestRun | null;
  resultRun: TestRun | null;
};

describe("LineagePanel", () => {
  test("renders nearest ancestors and breadth-first shared-parent descendants", () => {
    render(
      <LineagePanel
        lineage={{
          selected: step(2, "Improve baseline", 0, 1),
          ancestors: [step(1, "Create baseline", 1, null, "run-external")],
          descendants: [
            step(3, "Augmentation branch", 1, 2),
            step(4, "Scheduler branch", 1, 2),
            step(5, "Continue augmentation", 2, 3),
          ],
        }}
      />,
    );

    expect(screen.getByRole("heading", { name: "Lineage" })).toBeInTheDocument();
    expect(screen.getByText("Selected: Improve baseline")).toBeInTheDocument();
    expect(screen.getByText("Ancestor 1: Create baseline")).toBeInTheDocument();
    expect(screen.getByText("External boundary Run: run-external")).toBeInTheDocument();
    expect(screen.getByText("Descendant 1: Augmentation branch")).toBeInTheDocument();
    expect(screen.getByText("Descendant 1: Scheduler branch")).toBeInTheDocument();
    expect(screen.getByText("Descendant 2: Continue augmentation")).toBeInTheDocument();
  });

  test("renders a root without inventing an ancestor or external boundary", () => {
    render(
      <LineagePanel
        lineage={{
          selected: step(10, "Root step", 0, null, null, null),
          ancestors: [],
          descendants: [],
        }}
      />,
    );

    expect(screen.getByText("No ancestors.")).toBeInTheDocument();
    expect(screen.getByText("No descendants.")).toBeInTheDocument();
    expect(screen.queryByText(/External boundary Run/)).not.toBeInTheDocument();
  });
});

function step(
  id: number,
  purpose: string,
  distanceFromSelected: number,
  parentEvolutionStepId: number | null,
  parentRunId: string | null = "run-parent",
  resultRunId: string | null = "run-result",
): TestLineageStep {
  /** Create one concrete Lineage item for the rendering test.
   *
   * @param id - Local Evolution Step ID.
   * @param purpose - Saved Step purpose shown by the panel.
   * @param distanceFromSelected - Graph distance from the selected Step.
   * @param parentEvolutionStepId - Producing Step for the parent Run, if local.
   * @param parentRunId - Parent Run ID, or null for a root Step.
   * @param resultRunId - Result Run ID, or null when no result is linked.
   * @returns One test-only Lineage Step response value.
   */
  return {
    id,
    purpose,
    hypothesis: "The test hypothesis.",
    parentEvolutionStepId,
    distanceFromSelected,
    parentRun: parentRunId === null ? null : run(parentRunId),
    resultRun: resultRunId === null ? null : run(resultRunId),
  };
}

function run(runId: string): TestRun {
  /** Create one captured Run summary used by a test Lineage item.
   *
   * @param runId - Local Run Reference identifier.
   * @returns Test-only captured Run summary.
   */
  return {
    runId,
    runName: null,
    currentStatus: "FINISHED" as const,
    startedAt: null,
    endedAt: null,
    lastSyncedAt: "2026-09-24T10:00:00Z",
    snapshotState: "captured" as const,
    snapshotCapturedAt: "2026-09-24T10:00:00Z",
  };
}
