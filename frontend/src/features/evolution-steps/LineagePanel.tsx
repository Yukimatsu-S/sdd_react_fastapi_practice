/** Display the current selected-centered Evolution Step Lineage. */

import type { Lineage, LineageStep } from "../../api/evolutionSteps";

type LineagePanelProps = {
  lineage: Lineage;
};

/**
 * Render the selected Step with server-ordered ancestors and descendants.
 *
 * @param props - Current-link Lineage already loaded by the detail page.
 * @returns Read-only Lineage sections without making another API request.
 */
export function LineagePanel({ lineage }: LineagePanelProps): React.JSX.Element {
  return (
    <section>
      <h2>Lineage</h2>
      <p>Selected: {lineage.selected.purpose}</p>
      <LineageItems heading="Ancestors" items={lineage.ancestors} kind="Ancestor" />
      <LineageItems heading="Descendants" items={lineage.descendants} kind="Descendant" />
    </section>
  );
}

type LineageItemsProps = {
  heading: string;
  items: LineageStep[];
  kind: "Ancestor" | "Descendant";
};

/**
 * Render one ordered Lineage direction or its explicit empty state.
 *
 * @param props - Direction label and server-ordered Lineage items.
 * @returns A heading plus the direction's items or no-items message.
 */
function LineageItems({ heading, items, kind }: LineageItemsProps): React.JSX.Element {
  return (
    <section>
      <h3>{heading}</h3>
      {items.length === 0 ? <p>No {heading.toLowerCase()}.</p> : (
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              <p>{kind} {item.distanceFromSelected}: {item.purpose}</p>
              {externalBoundaryRunId(item) === null ? null : (
                <p>External boundary Run: {externalBoundaryRunId(item)}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * Identify an unregistered parent Run at the far end of an ancestor chain.
 *
 * @param item - One Lineage item from the server-ordered ancestor array.
 * @returns External parent Run ID, or null when the item has a local parent Step.
 */
function externalBoundaryRunId(item: LineageStep): string | null {
  if (item.parentEvolutionStepId !== null || item.parentRun === null) {
    return null;
  }
  return item.parentRun.runId;
}
