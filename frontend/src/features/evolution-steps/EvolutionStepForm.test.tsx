import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { EvolutionStepForm } from "./EvolutionStepForm";

describe("EvolutionStepForm", () => {
  test("requires non-blank purpose and hypothesis before submitting", async () => {
    const onSubmit = vi.fn();

    render(<EvolutionStepForm onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Save Evolution Step" }));

    expect(await screen.findByText("Purpose is required.")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("sends an explicit null when an existing change description is cleared", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <EvolutionStepForm
        initialValues={{
          purpose: "Improve baseline",
          hypothesis: "Augmentation helps.",
          changeDescription: "Use a crop.",
          parentRunId: "run-parent",
          resultRunId: "run-result",
        }}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText("Change description"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Evolution Step" }));

    expect(onSubmit).toHaveBeenCalledWith({
      purpose: "Improve baseline",
      hypothesis: "Augmentation helps.",
      changeDescription: null,
      parentRunId: "run-parent",
      resultRunId: "run-result",
    });
  });
});
