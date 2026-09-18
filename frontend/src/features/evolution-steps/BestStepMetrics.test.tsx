import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { BestStepMetrics } from "./BestStepMetrics";

describe("BestStepMetrics", () => {
  test("shows a pending message until a Snapshot is captured", () => {
    render(
      <BestStepMetrics
        result={{
          runId: "run-pending",
          status: "unavailable",
          unavailableReason: "snapshot_pending",
          bestAccuracy: null,
          bestAccuracyStep: null,
          bestAccuracyRecordedAt: null,
          items: [],
        }}
      />,
    );

    expect(screen.getByText("Snapshot pending")).toBeInTheDocument();
  });

  test("shows each Metric from the selected best step", () => {
    render(
      <BestStepMetrics
        result={{
          runId: "run-finished",
          status: "available",
          unavailableReason: null,
          bestAccuracy: 0.91,
          bestAccuracyStep: -1,
          bestAccuracyRecordedAt: "2026-09-18T11:00:00Z",
          items: [
            {
              name: "accuracy",
              value: 0.91,
              step: -1,
              recordedAt: "2026-09-18T11:00:00Z",
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("accuracy")).toBeInTheDocument();
    expect(screen.getByText("0.91")).toBeInTheDocument();
    expect(screen.getByText("-1")).toBeInTheDocument();
  });
});
