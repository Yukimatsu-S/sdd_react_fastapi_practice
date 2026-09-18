import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { RunPicker } from "./RunPicker";

const { searchRuns } = vi.hoisted(() => ({ searchRuns: vi.fn() }));

vi.mock("../../api/runs", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/runs")>()),
  searchRuns,
}));

describe("RunPicker", () => {
  test("selects duplicate Run names by their distinct Run IDs and loads another page", async () => {
    searchRuns
      .mockResolvedValueOnce({
        items: [
          {
            runId: "run-001",
            runName: "baseline",
            mlflowExperimentId: "1",
            mlflowExperimentName: "image-classification",
            status: "RUNNING",
            startedAt: null,
            endedAt: null,
          },
        ],
        nextPageToken: "page-2",
      })
      .mockResolvedValueOnce({
        items: [
          {
            runId: "run-002",
            runName: "baseline",
            mlflowExperimentId: "1",
            mlflowExperimentName: "image-classification",
            status: "FINISHED",
            startedAt: "2026-09-18T10:00:00Z",
            endedAt: "2026-09-18T11:00:00Z",
          },
        ],
        nextPageToken: null,
      });
    const onChange = vi.fn();

    render(<RunPicker label="Result Run" value={null} onChange={onChange} />);

    await screen.findByRole("option", { name: /Run ID: run-001/ });
    fireEvent.click(screen.getByRole("button", { name: "Load more Runs" }));
    await screen.findByRole("option", { name: /Run ID: run-002/ });
    fireEvent.change(screen.getByLabelText("Result Run"), { target: { value: "run-002" } });

    expect(onChange).toHaveBeenCalledWith("run-002");
    await waitFor(() => expect(searchRuns).toHaveBeenLastCalledWith({ query: "", pageToken: "page-2" }));
  });
});
