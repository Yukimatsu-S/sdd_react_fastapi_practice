/** Typed browser requests for MLflow Run selection and local synchronization. */

import { ApiClientError, requestJson } from "./client";
import type { LinkedRun, RunStatus } from "./evolutionSteps";

export type RunCandidate = {
  runId: string;
  runName: string | null;
  mlflowExperimentId: string;
  mlflowExperimentName: string;
  status: RunStatus;
  startedAt: string | null;
  endedAt: string | null;
};

export type RunCandidatePage = {
  items: RunCandidate[];
  nextPageToken: string | null;
};

export type RunSearchRequest = {
  query?: string;
  pageToken?: string;
};

export type RunSyncResult = {
  run: LinkedRun;
};

/**
 * Search the current MLflow Runs available for an Evolution Step link.
 *
 * @param request - Optional name filter and opaque continuation token.
 * @returns One server-sized Run candidate page and its next opaque token.
 */
export async function searchRuns(request: RunSearchRequest = {}): Promise<RunCandidatePage> {
  const parameters = new URLSearchParams();
  if (request.query !== undefined) {
    parameters.set("query", request.query);
  }
  if (request.pageToken !== undefined) {
    parameters.set("pageToken", request.pageToken);
  }
  const query = parameters.toString();
  const path = query === "" ? "/runs" : `/runs?${query}`;

  return requestJson<RunCandidatePage>(path);
}

/**
 * Fetch one Run from MLflow and update its local Reference/Snapshot state.
 *
 * @param runId - MLflow Run identifier chosen by the user.
 * @returns The locally stored Run Reference and optional terminal Snapshot.
 */
export async function syncRun(runId: string): Promise<RunSyncResult> {
  return requestJson<RunSyncResult>(`/runs/${runId}/sync`, { method: "POST" });
}

/**
 * Identify an API error caused by the unavailable upstream MLflow service.
 *
 * @param error - Unknown error thrown while searching or synchronizing a Run.
 * @returns Whether the error is the public MLflow-unavailable response.
 */
export function isMlflowUnavailableError(error: unknown): error is ApiClientError {
  return error instanceof ApiClientError
    && error.status === 502
    && error.code === "mlflow_unavailable";
}
