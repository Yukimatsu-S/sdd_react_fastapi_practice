import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { ComparisonPanel } from "./ComparisonPanel";

describe("ComparisonPanel", () => {
  test("renders available Parameter, accuracy, and Dataset differences", () => {
    render(
      <ComparisonPanel
        comparison={{
          status: "available",
          unavailableReason: null,
          parameters: [
            {
              name: "epochs",
              status: "changed",
              parentValue: "10",
              resultValue: "20",
            },
          ],
          accuracy: {
            status: "available",
            unavailableReason: null,
            parentBest: 0.9,
            resultBest: 0.92345,
            delta: 0.02345,
          },
          datasets: {
            status: "changed",
            unavailableReason: null,
            differences: [
              {
                status: "changed",
                parent: {
                  name: "images",
                  digest: "v1",
                  sourceType: "s3",
                  source: "s3://datasets/v1",
                  context: "train",
                },
                result: {
                  name: "images",
                  digest: "v2",
                  sourceType: "s3",
                  source: "s3://datasets/v2",
                  context: "train",
                },
                changedFields: ["digest", "source"],
              },
            ],
          },
        }}
      />,
    );

    expect(screen.getByText("epochs")).toBeInTheDocument();
    expect(screen.getByText("10 → 20")).toBeInTheDocument();
    expect(screen.getByText("90.00% → 92.35% (+2.35 pp)")).toBeInTheDocument();
    expect(screen.getByText("images: digest, source changed")).toBeInTheDocument();
  });

  test("renders explicit unavailable reasons instead of unchanged values", () => {
    render(
      <ComparisonPanel
        comparison={{
          status: "available",
          unavailableReason: null,
          parameters: [],
          accuracy: {
            status: "unavailable",
            unavailableReason: "parent_accuracy_missing",
            parentBest: null,
            resultBest: null,
            delta: null,
          },
          datasets: {
            status: "unavailable",
            unavailableReason: "dataset_pairing_ambiguous",
            differences: [],
          },
        }}
      />,
    );

    expect(screen.getByText("parent_accuracy_missing")).toBeInTheDocument();
    expect(screen.getByText("dataset_pairing_ambiguous")).toBeInTheDocument();
  });
});
