import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { EvolutionStepListPage } from "./EvolutionStepListPage";

describe("EvolutionStepListPage", () => {
  test("shows an explicit empty state before stored Evolution Steps exist", () => {
    render(<EvolutionStepListPage />);

    expect(screen.getByText("No Evolution Steps found.")).toBeInTheDocument();
  });
});
