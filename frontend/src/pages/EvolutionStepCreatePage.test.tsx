import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { EvolutionStepCreatePage } from "./EvolutionStepCreatePage";

test("shows the create form", () => {
  render(<EvolutionStepCreatePage />);

  expect(
    screen.getByRole("heading", { name: "Create Evolution Step" }),
  ).toBeInTheDocument();
});
