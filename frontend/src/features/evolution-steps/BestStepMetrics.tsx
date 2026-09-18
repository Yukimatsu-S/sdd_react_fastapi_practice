/** Presentation for locally captured Metrics at a Run's best accuracy step. */

import type { BestStepMetricsResult } from "../../api/runs";

type BestStepMetricsProps = {
  result: BestStepMetricsResult;
};

/**
 * Render available Metric items or the explicit reason that local data is unavailable.
 *
 * @param props - Best-step Metric state returned by the local API.
 * @returns Local best-step summary without requesting MLflow directly.
 */
export function BestStepMetrics({ result }: BestStepMetricsProps): React.JSX.Element {
  if (result.status === "unavailable") {
    return (
      <section>
        <h3>Best-step Metrics</h3>
        <p>{unavailableMessage(result.unavailableReason)}</p>
      </section>
    );
  }

  return (
    <section>
      <h3>Best-step Metrics</h3>
      <p>Best accuracy: {result.bestAccuracy}</p>
      <p>Best accuracy step: {result.bestAccuracyStep}</p>
      <ul>
        {result.items.map((item) => (
          <li key={item.name}>
            <span>{item.name}</span>: <span>{item.value}</span> at step <span>{item.step}</span> (
            {item.recordedAt})
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * Translate a documented local availability reason into concise UI text.
 *
 * @param reason - API-provided absence reason for best-step Metric values.
 * @returns Human-readable status message.
 */
function unavailableMessage(reason: BestStepMetricsResult["unavailableReason"]): string {
  return reason === "snapshot_pending" ? "Snapshot pending" : "Accuracy is unavailable";
}
