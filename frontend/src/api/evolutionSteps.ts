/** Typed browser requests and response shapes for Evolution Step resources. */

import { requestJson } from "./client";

export type RunStatus = "RUNNING" | "SCHEDULED" | "FINISHED" | "FAILED" | "KILLED";
export type SnapshotState = "pending" | "captured";

export type RunSummary = {
  runId: string;
  runName: string | null;
  currentStatus: RunStatus;
  startedAt: string | null;
  endedAt: string | null;
  lastSyncedAt: string;
  snapshotState: SnapshotState;
  snapshotCapturedAt: string | null;
};

export type DatasetInputSnapshot = {
  ordinal: number;
  name: string | null;
  digest: string | null;
  sourceType: string | null;
  source: string | null;
  schema: string | null;
  profile: Record<string, unknown> | null;
  context: Record<string, unknown> | null;
};

export type RunSnapshot = {
  runId: string;
  statusAtCapture: "FINISHED" | "FAILED" | "KILLED";
  startedAt: string | null;
  endedAt: string | null;
  bestAccuracy: number | null;
  bestAccuracyStep: number | null;
  bestAccuracyRecordedAt: string | null;
  capturedAt: string;
  parameters: Record<string, string>;
  datasets: DatasetInputSnapshot[];
};

export type LinkedRun = {
  reference: RunSummary;
  snapshot: RunSnapshot | null;
};

export type EvolutionStepHistoryEntry = {
  field: "purpose" | "hypothesis" | "changeDescription" | "parentRunId" | "resultRunId";
  oldValue: string | null;
  newValue: string | null;
  changedAt: string;
};

export type EvolutionStepDetail = {
  id: number;
  purpose: string;
  hypothesis: string;
  changeDescription: string | null;
  parentRun: LinkedRun | null;
  resultRun: LinkedRun | null;
  createdAt: string;
  updatedAt: string;
  history: EvolutionStepHistoryEntry[];
};

export type CreateEvolutionStepRequest = {
  purpose: string;
  hypothesis: string;
  changeDescription?: string | null;
  parentRunId?: string | null;
  resultRunId?: string | null;
};

export type PatchEvolutionStepRequest = Partial<CreateEvolutionStepRequest>;

export type AccuracyComparison = {
  status: "available" | "unavailable";
  unavailableReason: string | null;
  parentBest: number | null;
  resultBest: number | null;
  delta: number | null;
};

export type ComparisonSummary = {
  status: "available" | "unavailable";
  unavailableReason: string | null;
  parameterChangeCount: number | null;
  accuracy: AccuracyComparison;
  datasetStatus: "changed" | "unchanged" | "unavailable";
  datasetUnavailableReason: string | null;
};

export type EvolutionStepListItem = {
  id: number;
  purpose: string;
  hypothesis: string;
  parentRun: RunSummary | null;
  resultRun: RunSummary | null;
  comparisonSummary: ComparisonSummary;
  createdAt: string;
  updatedAt: string;
};

export type EvolutionStepListPage = {
  items: EvolutionStepListItem[];
  nextPageToken: string | null;
};

export type ParameterDifference = {
  name: string;
  status: "added" | "changed" | "removed";
  parentValue: string | null;
  resultValue: string | null;
};

export type DatasetIdentifier = {
  name: string;
  digest: string;
  sourceType: string;
  source: string;
  context: string | null;
};

export type DatasetDifference = {
  status: "changed" | "parent_only" | "result_only";
  parent: DatasetIdentifier | null;
  result: DatasetIdentifier | null;
  changedFields: Array<"digest" | "sourceType" | "source">;
};

export type DatasetComparison = {
  status: "changed" | "unchanged" | "unavailable";
  unavailableReason: string | null;
  differences: DatasetDifference[];
};

export type Comparison = {
  status: "available" | "unavailable";
  unavailableReason: string | null;
  parameters: ParameterDifference[];
  accuracy: AccuracyComparison;
  datasets: DatasetComparison;
};

export type LineageStep = {
  id: number;
  purpose: string;
  hypothesis: string;
  parentEvolutionStepId: number | null;
  distanceFromSelected: number;
  parentRun: RunSummary | null;
  resultRun: RunSummary | null;
};

export type Lineage = {
  selected: LineageStep;
  ancestors: LineageStep[];
  descendants: LineageStep[];
};

/**
 * Create an Evolution Step with the selected optional Run links.
 *
 * @param request - Text fields and optional parent/result Run IDs to save.
 * @returns The newly created local Evolution Step detail.
 */
export async function createEvolutionStep(
  request: CreateEvolutionStepRequest,
): Promise<EvolutionStepDetail> {
  return requestJson<EvolutionStepDetail>("/evolution-steps", {
    body: JSON.stringify(request),
    headers: { "content-type": "application/json" },
    method: "POST",
  });
}

/**
 * Load one saved Evolution Step without synchronizing its linked Runs.
 *
 * @param evolutionStepId - Positive local Evolution Step identifier.
 * @returns The saved detail and locally retained Run data.
 */
export async function getEvolutionStep(evolutionStepId: number): Promise<EvolutionStepDetail> {
  return requestJson<EvolutionStepDetail>(`/evolution-steps/${evolutionStepId}`);
}

/**
 * Load differences calculated from the Step's immutable captured Snapshots.
 *
 * @param evolutionStepId - Positive local Evolution Step identifier.
 * @returns Parameter, accuracy, and Dataset Input comparison values.
 */
export async function getComparison(evolutionStepId: number): Promise<Comparison> {
  return requestJson<Comparison>(`/evolution-steps/${evolutionStepId}/comparison`);
}

/**
 * Load the current-link ancestors and descendants for one saved Evolution Step.
 *
 * @param evolutionStepId - Positive local Evolution Step identifier.
 * @returns Selected Step with server-ordered ancestor and descendant arrays.
 */
export async function getLineage(evolutionStepId: number): Promise<Lineage> {
  return requestJson<Lineage>(`/evolution-steps/${evolutionStepId}/lineage`);
}

/**
 * Update only supplied Evolution Step fields; explicit null clears nullable fields.
 *
 * @param evolutionStepId - Positive local Evolution Step identifier.
 * @param request - Fields to replace, unlink, or clear.
 * @returns The freshly saved Evolution Step detail.
 */
export async function patchEvolutionStep(
  evolutionStepId: number,
  request: PatchEvolutionStepRequest,
): Promise<EvolutionStepDetail> {
  return requestJson<EvolutionStepDetail>(`/evolution-steps/${evolutionStepId}`, {
    body: JSON.stringify(request),
    headers: { "content-type": "application/json" },
    method: "PATCH",
  });
}

/**
 * Load one server-token-paginated page of saved Evolution Steps.
 *
 * @param pageToken - Opaque continuation token returned by a previous list page.
 * @returns Current list items and an optional opaque next-page token.
 */
export async function listEvolutionSteps(pageToken?: string): Promise<EvolutionStepListPage> {
  const path = pageToken === undefined
    ? "/evolution-steps"
    : `/evolution-steps?pageToken=${encodeURIComponent(pageToken)}`;
  return requestJson<EvolutionStepListPage>(path);
}
