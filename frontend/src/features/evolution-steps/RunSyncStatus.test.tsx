import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { RunSyncStatus } from "./RunSyncStatus";

describe("RunSyncStatus", () => {
  test("renders saved-detail warning without hiding local content", () => {
    render(<RunSyncStatus state="failed" />);

    expect(screen.getByRole("alert")).toHaveTextContent("Showing saved local data");
  });

  test("renders pending and successful synchronization states", () => {
    const { rerender } = render(<RunSyncStatus state="syncing" />);
    expect(screen.getByText("Synchronizing Run data…")).toBeInTheDocument();

    rerender(<RunSyncStatus state="succeeded" />);
    expect(screen.getByText("Run data synchronized.")).toBeInTheDocument();
  });
});
