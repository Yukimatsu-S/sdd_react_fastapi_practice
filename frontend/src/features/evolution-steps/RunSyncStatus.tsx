/** Compact user feedback for one non-blocking Run synchronization attempt. */

type RunSyncStatusProps = {
  state: "syncing" | "succeeded" | "failed";
};

/**
 * Render synchronization progress without owning the page's saved detail state.
 *
 * @param props - Current lifecycle state selected by the detail page.
 * @returns Concise status text, with an alert only for failure.
 */
export function RunSyncStatus({ state }: RunSyncStatusProps): React.JSX.Element {
  if (state === "syncing") {
    return <p>Synchronizing Run data…</p>;
  }
  if (state === "succeeded") {
    return <p>Run data synchronized.</p>;
  }
  return <p role="alert">Run synchronization failed. Showing saved local data.</p>;
}
