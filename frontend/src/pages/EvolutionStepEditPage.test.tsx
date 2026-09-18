import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test } from "vitest";

import { EvolutionStepEditPage } from "./EvolutionStepEditPage";

test("shows a saved Evolution Step in edit mode", () => {
  render(
    <MemoryRouter>
      <EvolutionStepEditPage evolutionStepId={12} />
    </MemoryRouter>,
  );

  expect(
    screen.getByRole("heading", { name: "Edit Evolution Step" }),
  ).toBeInTheDocument();
});
