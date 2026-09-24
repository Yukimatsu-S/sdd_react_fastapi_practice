import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { EvolutionStepDetailPage } from "./EvolutionStepDetailPage";

const { getComparison, getEvolutionStep, getLineage, getBestStepMetrics, syncRun } = vi.hoisted(() => ({
  getComparison: vi.fn(),
  getEvolutionStep: vi.fn(),
  getLineage: vi.fn(),
  getBestStepMetrics: vi.fn(),
  syncRun: vi.fn(),
}));

vi.mock("../api/evolutionSteps", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/evolutionSteps")>()),
  getComparison,
  getEvolutionStep,
  getLineage,
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
    getComparison.mockResolvedValue({
      status: "unavailable",
      unavailableReason: "parent_run_missing",
      parameters: [],
      accuracy: {
        status: "unavailable",
        unavailableReason: "comparison_unavailable",
        parentBest: null,
        resultBest: null,
        delta: null,
      },
      datasets: {
        status: "unavailable",
        unavailableReason: "comparison_unavailable",
        differences: [],
      },
    });
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

  test("keeps local detail and best-step Metrics when comparison loading fails", async () => {
    getEvolutionStep.mockResolvedValue({
      id: 13,
      purpose: "Compare captured Runs",
      hypothesis: "Comparison remains local.",
      changeDescription: null,
      parentRun: null,
      resultRun: null,
      createdAt: "2026-09-18T10:00:00Z",
      updatedAt: "2026-09-18T10:00:00Z",
      history: [],
    });
    getComparison.mockRejectedValue(new Error("unavailable"));

    render(<EvolutionStepDetailPage evolutionStepId={13} />);

    expect(await screen.findByText("Compare captured Runs")).toBeInTheDocument();
    expect(await screen.findByText("Comparison could not be loaded.")).toBeInTheDocument();
    expect(getComparison).toHaveBeenCalledWith(13);
  });

  test("reloads current Lineage when returning to a saved Step", async () => {
    getEvolutionStep.mockResolvedValue({
      id: 14,
      purpose: "Refresh current Lineage",
      hypothesis: "The saved links are read again.",
      changeDescription: null,
      parentRun: null,
      resultRun: null,
      createdAt: "2026-09-24T10:00:00Z",
      updatedAt: "2026-09-24T10:00:00Z",
      history: [],
    });
    getComparison.mockResolvedValue({
      status: "unavailable",
      unavailableReason: "parent_run_missing",
      parameters: [],
      accuracy: {
        status: "unavailable",
        unavailableReason: "comparison_unavailable",
        parentBest: null,
        resultBest: null,
        delta: null,
      },
      datasets: {
        status: "unavailable",
        unavailableReason: "comparison_unavailable",
        differences: [],
      },
    });
    getLineage.mockResolvedValue({ selected: null, ancestors: [], descendants: [] });

    const { unmount } = render(<EvolutionStepDetailPage evolutionStepId={14} />);
    expect(await screen.findByText("Refresh current Lineage")).toBeInTheDocument();
    unmount();
    render(<EvolutionStepDetailPage evolutionStepId={14} />);

    expect(await screen.findByText("Refresh current Lineage")).toBeInTheDocument();
    expect(getLineage).toHaveBeenCalledTimes(2);
    expect(getLineage).toHaveBeenLastCalledWith(14);
  });
});
