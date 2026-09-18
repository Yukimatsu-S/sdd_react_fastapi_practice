/** Token-paginated local Evolution Step list presentation. */

import { useEffect, useState } from "react";

import { listEvolutionSteps, type EvolutionStepListItem } from "../../api/evolutionSteps";

type EvolutionStepListPageProps = {
  onSelect?: (evolutionStepId: number) => void;
};

/**
 * Load one local list lifetime and append server-issued continuation pages.
 *
 * @param props - Optional callback used by the route page for detail navigation.
 * @returns Loading, empty, list, and next-page states for saved Evolution Steps.
 */
export function EvolutionStepListPage({ onSelect }: EvolutionStepListPageProps): React.JSX.Element {
  const [items, setItems] = useState<EvolutionStepListItem[]>([]);
  const [nextPageToken, setNextPageToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadFirstPage();
  }, []);

  /** Replace the page-lifetime data with a fresh first-page request. */
  async function loadFirstPage(): Promise<void> {
    try {
      const page = await listEvolutionSteps();
      setItems(page.items);
      setNextPageToken(page.nextPageToken);
      setError(null);
    } catch {
      setItems([]);
      setError("Evolution Steps could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  /** Append exactly the next server-issued page when another one exists. */
  async function loadNextPage(): Promise<void> {
    if (nextPageToken === null) {
      return;
    }
    try {
      const page = await listEvolutionSteps(nextPageToken);
      setItems((current) => [...current, ...page.items]);
      setNextPageToken(page.nextPageToken);
    } catch {
      setError("More Evolution Steps could not be loaded.");
    }
  }

  if (loading) {
    return <p>Loading Evolution Steps…</p>;
  }
  if (items.length === 0) {
    return <p>{error === null ? "No Evolution Steps found." : "No Evolution Steps found."}</p>;
  }

  return (
    <section>
      <h1>Evolution Steps</h1>
      {error === null ? null : <p role="alert">{error}</p>}
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <button type="button" onClick={() => onSelect?.(item.id)}>
              #{item.id} {item.purpose}
            </button>
            <p>{item.hypothesis}</p>
            <p>Parent: {item.parentRun?.runId ?? "(unset)"}; Result: {item.resultRun?.runId ?? "(unset)"}</p>
            <p>Created: {item.createdAt}; Updated: {item.updatedAt}</p>
            <p>Comparison: {item.comparisonSummary.status}; Parameter changes: {item.comparisonSummary.parameterChangeCount ?? "(unavailable)"}; Accuracy delta: {item.comparisonSummary.accuracy.delta ?? "(unavailable)"}; Dataset: {item.comparisonSummary.datasetStatus}</p>
          </li>
        ))}
      </ul>
      {nextPageToken === null ? null : <button type="button" onClick={() => void loadNextPage()}>Load more Evolution Steps</button>}
    </section>
  );
}
