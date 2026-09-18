/** Searchable, paginated MLflow Run selector used by Evolution Step forms. */

import { useEffect, useState } from "react";

import { isMlflowUnavailableError, searchRuns } from "../../api/runs";
import type { RunCandidate } from "../../api/runs";

type RunPickerProps = {
  label: string;
  value: string | null;
  onChange: (runId: string | null) => void;
};

/**
 * Let a user search and select one MLflow Run by its stable Run ID.
 *
 * @param props - Label, selected Run ID, and callback owned by the parent form.
 * @returns An accessible Run search and selection control.
 */
export function RunPicker({ label, value, onChange }: RunPickerProps): React.JSX.Element {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<RunCandidate[]>([]);
  const [nextPageToken, setNextPageToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadFirstPage();
  }, []);

  /** Load candidates for the current filter, replacing the old page. */
  async function loadFirstPage(): Promise<void> {
    try {
      const page = await searchRuns(query === "" ? {} : { query });
      setItems(page.items);
      setNextPageToken(page.nextPageToken);
      setError(null);
    } catch (caught) {
      setError(
        isMlflowUnavailableError(caught)
          ? "MLflow is currently unavailable."
          : "Run candidates could not be loaded.",
      );
    }
  }

  /** Load and append the next opaque server-issued candidate page. */
  async function loadNextPage(): Promise<void> {
    if (nextPageToken === null) {
      return;
    }

    try {
      const page = await searchRuns({ query, pageToken: nextPageToken });
      setItems((current) => [...current, ...page.items]);
      setNextPageToken(page.nextPageToken);
      setError(null);
    } catch (caught) {
      setError(
        isMlflowUnavailableError(caught)
          ? "MLflow is currently unavailable."
          : "Run candidates could not be loaded.",
      );
    }
  }

  return (
    <fieldset>
      <legend>{label}</legend>
      <label>
        Search Runs
        <input
          aria-label={`${label} search`}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      <button type="button" onClick={() => void loadFirstPage()}>
        Search
      </button>
      <select
        aria-label={label}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value === "" ? null : event.target.value)}
      >
        <option value="">No Run selected</option>
        {items.map((item) => (
          <option key={item.runId} value={item.runId}>
            {formatCandidate(item)}
          </option>
        ))}
      </select>
      {nextPageToken !== null ? (
        <button type="button" onClick={() => void loadNextPage()}>
          Load more Runs
        </button>
      ) : null}
      {error === null ? null : <p role="alert">{error}</p>}
    </fieldset>
  );
}

/**
 * Produce one unambiguous candidate label, including nullable values explicitly.
 *
 * @param item - One MLflow Run candidate returned by the server.
 * @returns Human-readable candidate information that remains unique by Run ID.
 */
function formatCandidate(item: RunCandidate): string {
  return [
    `Run ID: ${item.runId}`,
    `Run name: ${item.runName ?? "(unset)"}`,
    `MLflow Experiment ID: ${item.mlflowExperimentId}`,
    `MLflow Experiment name: ${item.mlflowExperimentName}`,
    `Status: ${item.status}`,
    `Started: ${item.startedAt ?? "(unset)"}`,
    `Ended: ${item.endedAt ?? "(unset)"}`,
  ].join(" | ");
}
