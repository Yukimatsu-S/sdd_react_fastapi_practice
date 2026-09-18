/** Pure presentation of one locally saved Evolution Step detail. */

import type {
  EvolutionStepDetail as EvolutionStepDetailData,
  LinkedRun,
} from "../../api/evolutionSteps";

type EvolutionStepDetailProps = {
  detail: EvolutionStepDetailData;
};

/**
 * Render saved local Step and linked Run data without making network requests.
 *
 * @param props - Detail response loaded by the page lifecycle.
 * @returns Read-only Step, Run, Parameter, Dataset, and history presentation.
 */
export function EvolutionStepDetail({ detail }: EvolutionStepDetailProps): React.JSX.Element {
  return (
    <article>
      <h1>{detail.purpose}</h1>
      <p>{detail.hypothesis}</p>
      <p>Change description: {detail.changeDescription ?? "(none)"}</p>
      <p>Created: {detail.createdAt}</p>
      <p>Updated: {detail.updatedAt}</p>
      <RunSection label="Parent Run" linkedRun={detail.parentRun} />
      <RunSection label="Result Run" linkedRun={detail.resultRun} />
      <section>
        <h2>Change history</h2>
        <ul>
          {detail.history.map((entry) => (
            <li key={`${entry.field}-${entry.changedAt}`}>
              {entry.changedAt}: {entry.field} from {entry.oldValue ?? "(none)"} to {entry.newValue ?? "(none)"}
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}

/**
 * Render one optional local Run reference and captured Snapshot content.
 *
 * @param props - Section label and nullable linked Run state.
 * @returns Run summary or an explicit absent-link display.
 */
function RunSection({
  label,
  linkedRun,
}: {
  label: string;
  linkedRun: LinkedRun | null;
}): React.JSX.Element {
  if (linkedRun === null) {
    return (
      <section>
        <h2>{label}</h2>
        <p>Not linked</p>
      </section>
    );
  }

  const { reference, snapshot } = linkedRun;
  return (
    <section>
      <h2>{label}</h2>
      <p>{reference.runId}</p>
      <p>Run name: {reference.runName ?? "(unset)"}</p>
      <p>Status: {reference.currentStatus}</p>
      <p>{snapshot === null ? "Snapshot pending" : "Snapshot captured"}</p>
      {snapshot === null ? null : <SnapshotContent linkedRun={linkedRun} />}
    </section>
  );
}

/**
 * Render captured Parameters and Dataset Input metadata for one finalized Run.
 *
 * @param props - Linked Run known to have a captured Snapshot.
 * @returns Captured Snapshot information, or nothing for a pending Snapshot.
 */
function SnapshotContent({ linkedRun }: { linkedRun: LinkedRun }): React.JSX.Element | null {
  const snapshot = linkedRun.snapshot;
  if (snapshot === null) {
    return null;
  }

  return (
    <>
      <h3>Parameters</h3>
      <ul>
        {Object.entries(snapshot.parameters).map(([name, value]) => (
          <li key={name}>{name}: {value}</li>
        ))}
      </ul>
      <h3>Datasets</h3>
      <ul>
        {snapshot.datasets.map((dataset) => (
          <li key={dataset.ordinal}>
            ordinal={dataset.ordinal}; name={dataset.name ?? "(unset)"}; digest={dataset.digest ?? "(unset)"}; sourceType={dataset.sourceType ?? "(unset)"}; source={dataset.source ?? "(unset)"}; schema={dataset.schema ?? "(unset)"}; profile={JSON.stringify(dataset.profile)}; context={JSON.stringify(dataset.context)}
          </li>
        ))}
      </ul>
    </>
  );
}
