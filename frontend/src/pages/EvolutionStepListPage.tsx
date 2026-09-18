/** Route page that connects the local Evolution Step list to detail navigation. */

import { useNavigate } from "react-router-dom";

import { EvolutionStepListPage as EvolutionStepList } from "../features/evolution-steps/EvolutionStepListPage";

/**
 * Navigate to a selected saved Evolution Step from the local list.
 *
 * @returns List page with detail navigation callback.
 */
export function EvolutionStepListPage(): React.JSX.Element {
  const navigate = useNavigate();
  return <EvolutionStepList onSelect={(id) => navigate(`/evolution-steps/${id}`)} />;
}
