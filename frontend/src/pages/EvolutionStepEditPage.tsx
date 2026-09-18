/** Route page for editing the current fields and Run links of one Evolution Step. */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiClientError } from "../api/client";
import {
  getEvolutionStep,
  patchEvolutionStep,
  type CreateEvolutionStepRequest,
  type EvolutionStepDetail,
} from "../api/evolutionSteps";
import { EvolutionStepForm } from "../features/evolution-steps/EvolutionStepForm";

type EvolutionStepEditPageProps = {
  evolutionStepId: number;
};

/**
 * Load saved editable values, submit a PATCH, then navigate to refreshed detail.
 *
 * @param props - Local Evolution Step identifier selected by the edit route.
 * @returns Edit form after local data is loaded.
 */
export function EvolutionStepEditPage({
  evolutionStepId,
}: EvolutionStepEditPageProps): React.JSX.Element {
  const navigate = useNavigate();
  const [detail, setDetail] = useState<EvolutionStepDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getEvolutionStep(evolutionStepId)
      .then((loaded) => setDetail(loaded))
      .catch(() => setError("Evolution Step could not be loaded for editing."));
  }, [evolutionStepId]);

  /** Patch supplied values and return the user to newly loaded saved detail. */
  async function handleSubmit(request: CreateEvolutionStepRequest): Promise<void> {
    try {
      await patchEvolutionStep(evolutionStepId, request);
      navigate(`/evolution-steps/${evolutionStepId}`);
    } catch (caught) {
      if (caught instanceof ApiClientError && caught.status === 409) {
        throw new Error("The selected Result Run conflicts with existing lineage.");
      }
      throw caught;
    }
  }

  return (
    <main>
      <h1>Edit Evolution Step</h1>
      {error === null ? null : <p role="alert">{error}</p>}
      {detail === null ? <p>Loading saved values…</p> : (
        <EvolutionStepForm
          key={detail.id}
          initialValues={{
            purpose: detail.purpose,
            hypothesis: detail.hypothesis,
            changeDescription: detail.changeDescription,
            parentRunId: detail.parentRun?.reference.runId ?? null,
            resultRunId: detail.resultRun?.reference.runId ?? null,
          }}
          onSubmit={handleSubmit}
        />
      )}
    </main>
  );
}
