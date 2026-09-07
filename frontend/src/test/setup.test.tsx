import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import App from "../App";

test("renders a React component in the browser-like test environment", () => {
  render(<App />);

  expect(
    screen.getByRole("heading", { level: 1, name: "Mondel" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText("ML Experiment Evolution Manager"),
  ).toBeInTheDocument();
});
