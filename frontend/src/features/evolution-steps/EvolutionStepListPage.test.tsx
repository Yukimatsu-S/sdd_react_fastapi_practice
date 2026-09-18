import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { EvolutionStepListPage } from "./EvolutionStepListPage";

describe("EvolutionStepListPage", () => {
  test("shows an explicit empty state before stored Evolution Steps exist", async () => {
    render(<EvolutionStepListPage />);

    expect(await screen.findByText("No Evolution Steps found.")).toBeInTheDocument();
  });
});
