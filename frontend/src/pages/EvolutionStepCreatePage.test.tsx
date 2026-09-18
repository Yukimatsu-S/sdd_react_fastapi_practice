import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test } from "vitest";

import { EvolutionStepCreatePage } from "./EvolutionStepCreatePage";

test("shows the create form", () => {
  render(
    <MemoryRouter>
      <EvolutionStepCreatePage />
    </MemoryRouter>,
  );

  expect(
    screen.getByRole("heading", { name: "Create Evolution Step" }),
  ).toBeInTheDocument();
});
