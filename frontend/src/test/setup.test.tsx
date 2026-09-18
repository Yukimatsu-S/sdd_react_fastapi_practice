import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import App from "../App";

test("redirects an unspecified path to the Evolution Step creation page", () => {
  render(<App />);

  expect(
    screen.getByRole("heading", { level: 1, name: "Create Evolution Step" }),
  ).toBeInTheDocument();
});
