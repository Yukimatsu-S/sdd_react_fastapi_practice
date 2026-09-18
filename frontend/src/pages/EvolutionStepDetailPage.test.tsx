import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { EvolutionStepDetailPage } from "./EvolutionStepDetailPage";

const { getEvolutionStep, getBestStepMetrics, syncRun } = vi.hoisted(() => ({
  getEvolutionStep: vi.fn(),
  getBestStepMetrics: vi.fn(),
  syncRun: vi.fn(),
}));

vi.mock("../api/evolutionSteps", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/evolutionSteps")>()),
  getEvolutionStep,
}));
vi.mock("../api/runs", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/runs")>()),
  getBestStepMetrics,
  syncRun,
}));

describe("EvolutionStepDetailPage", () => {
  test("shows local detail before retaining it after a synchronization failure", async () => {
    getEvolutionStep.mockResolvedValue({
      id: 12,
      purpose: "Improve baseline",
      hypothesis: "Augmentation helps.",
      changeDescription: null,
      parentRun: null,
      resultRun: {
        reference: {
          runId: "run-12",
          runName: null,
          currentStatus: "RUNNING",
          startedAt: null,
          endedAt: null,
          lastSyncedAt: "2026-09-18T10:00:00Z",
          snapshotState: "pending",
          snapshotCapturedAt: null,
        },
        snapshot: null,
      },
      createdAt: "2026-09-18T10:00:00Z",
      updatedAt: "2026-09-18T10:00:00Z",
      history: [],
    });
    syncRun.mockRejectedValue(new Error("unavailable"));
    getBestStepMetrics.mockResolvedValue({
      runId: "run-12",
      status: "unavailable",
      unavailableReason: "snapshot_pending",
      bestAccuracy: null,
      bestAccuracyStep: null,
      bestAccuracyRecordedAt: null,
      items: [],
    });

    render(<EvolutionStepDetailPage evolutionStepId={12} />);

    expect(await screen.findByText("Improve baseline")).toBeInTheDocument();
    expect(await screen.findByText(/Showing saved local data/)).toBeInTheDocument();
    expect(syncRun).toHaveBeenCalledTimes(1);
  });
});
