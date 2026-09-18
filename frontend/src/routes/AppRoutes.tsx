/** Application routes for the initial Evolution Step user flow. */

import { Navigate, Route, Routes, useParams } from "react-router-dom";

import { EvolutionStepCreatePage } from "../pages/EvolutionStepCreatePage";
import { EvolutionStepDetailPage } from "../pages/EvolutionStepDetailPage";
import { EvolutionStepEditPage } from "../pages/EvolutionStepEditPage";
import { EvolutionStepListPage } from "../pages/EvolutionStepListPage";

/**
 * Resolve the documented create and saved-detail browser routes.
 *
 * @returns Route tree for the initial MVP flow.
 */
export function AppRoutes(): React.JSX.Element {
  return (
    <Routes>
      <Route path="/evolution-steps" element={<EvolutionStepListPage />} />
      <Route path="/evolution-steps/new" element={<EvolutionStepCreatePage />} />
      <Route path="/evolution-steps/:evolutionStepId/edit" element={<EditRoute />} />
      <Route path="/evolution-steps/:evolutionStepId" element={<DetailRoute />} />
      <Route path="*" element={<Navigate to="/evolution-steps/new" replace />} />
    </Routes>
  );
}

/** Resolve an edit URL parameter into the page's positive local identifier. */
function EditRoute(): React.JSX.Element {
  const { evolutionStepId } = useParams();
  const parsedId = Number(evolutionStepId);
  if (!Number.isInteger(parsedId) || parsedId < 1) {
    return <p role="alert">Evolution Step ID must be a positive integer.</p>;
  }
  return <EvolutionStepEditPage evolutionStepId={parsedId} />;
}

/**
 * Convert the route parameter into the positive number required by the page.
 *
 * @returns Saved-detail page or an explicit invalid-path message.
 */
function DetailRoute(): React.JSX.Element {
  const { evolutionStepId } = useParams();
  const parsedId = Number(evolutionStepId);
  if (!Number.isInteger(parsedId) || parsedId < 1) {
    return <p role="alert">Evolution Step ID must be a positive integer.</p>;
  }
  return <EvolutionStepDetailPage evolutionStepId={parsedId} />;
}
