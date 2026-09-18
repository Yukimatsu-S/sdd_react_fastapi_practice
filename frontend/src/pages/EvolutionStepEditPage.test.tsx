import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { EvolutionStepEditPage } from "./EvolutionStepEditPage";

test("shows a saved Evolution Step in edit mode", () => {
  render(<EvolutionStepEditPage evolutionStepId={12} />);

  expect(
    screen.getByRole("heading", { name: "Edit Evolution Step" }),
  ).toBeInTheDocument();
});
