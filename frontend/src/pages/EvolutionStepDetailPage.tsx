/** Lifecycle page for one saved Evolution Step and its local Run state. */

import { useEffect, useState } from "react";

import {
  getEvolutionStep,
  type EvolutionStepDetail as EvolutionStepDetailData,
} from "../api/evolutionSteps";
import { getBestStepMetrics, syncRun, type BestStepMetricsResult } from "../api/runs";
import { BestStepMetrics } from "../features/evolution-steps/BestStepMetrics";
import { EvolutionStepDetail } from "../features/evolution-steps/EvolutionStepDetail";
import { RunSyncStatus } from "../features/evolution-steps/RunSyncStatus";

type EvolutionStepDetailPageProps = {
  evolutionStepId: number;
};

/**
 * Load local detail first, then synchronize each linked Run once and refresh it.
 *
 * @param props - Local Step identifier selected by the route.
 * @returns Detail, non-blocking synchronization warning, and local Metric views.
 */
export function EvolutionStepDetailPage({
  evolutionStepId,
}: EvolutionStepDetailPageProps): React.JSX.Element {
  const [detail, setDetail] = useState<EvolutionStepDetailData | null>(null);
  const [metrics, setMetrics] = useState<BestStepMetricsResult[]>([]);
  const [warning, setWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    /** Perform one local-first lifecycle for the currently selected Step. */
    async function load(): Promise<void> {
      try {
        const initial = await getEvolutionStep(evolutionStepId);
        if (!active) {
          return;
        }
        setDetail(initial);
        const linkedRunIds = [initial.parentRun, initial.resultRun]
          .flatMap((linkedRun) => (linkedRun === null ? [] : [linkedRun.reference.runId]));
        const uniqueRunIds = [...new Set(linkedRunIds)];

        try {
          await Promise.all(uniqueRunIds.map((runId) => syncRun(runId)));
          const refreshed = await getEvolutionStep(evolutionStepId);
          if (active) {
            setDetail(refreshed);
          }
        } catch {
          if (active) {
            setWarning("Some Run data could not be synchronized. Showing saved local data.");
          }
        }

        try {
          const metricResults = await Promise.all(
            uniqueRunIds.map((runId) => getBestStepMetrics(runId)),
          );
          if (active) {
            setMetrics(metricResults);
          }
        } catch {
          if (active) {
            setWarning("Best-step Metrics could not be loaded. Showing saved local detail.");
          }
        }
      } catch {
        if (active) {
          setError("Evolution Step detail could not be loaded.");
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [evolutionStepId]);

  if (error !== null) {
    return <p role="alert">{error}</p>;
  }
  if (detail === null) {
    return <p>Loading Evolution Step…</p>;
  }

  return (
    <main>
      {warning === null ? null : <RunSyncStatus state="failed" />}
      <EvolutionStepDetail detail={detail} />
      {metrics.map((result) => (
        <BestStepMetrics key={result.runId} result={result} />
      ))}
    </main>
  );
}
