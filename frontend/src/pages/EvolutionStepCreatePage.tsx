/** Route page for creating a new Evolution Step. */

import { useNavigate } from "react-router-dom";

import { ApiClientError } from "../api/client";
import {
  createEvolutionStep,
  type CreateEvolutionStepRequest,
} from "../api/evolutionSteps";
import { EvolutionStepForm } from "../features/evolution-steps/EvolutionStepForm";

/**
 * Save a new Evolution Step and navigate to its local saved-detail route.
 *
 * @returns Create page with actionable lineage-conflict feedback.
 */
export function EvolutionStepCreatePage(): React.JSX.Element {
  const navigate = useNavigate();

  /** Submit form data, turning a lineage conflict into an actionable message. */
  async function handleSubmit(request: CreateEvolutionStepRequest): Promise<void> {
    try {
      const step = await createEvolutionStep(request);
      navigate(`/evolution-steps/${step.id}`);
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 409) {
        throw new Error("The selected Result Run conflicts with existing lineage.");
      }
      throw error;
    }
  }

  return (
    <main>
      <h1>Create Evolution Step</h1>
      <EvolutionStepForm onSubmit={handleSubmit} />
    </main>
  );
}
