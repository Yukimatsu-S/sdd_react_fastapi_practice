/** Display Parameter, accuracy, and Dataset differences from two Snapshots. */

import type { Comparison, DatasetDifference } from "../../api/evolutionSteps";

type ComparisonPanelProps = {
  comparison: Comparison;
};

/**
 * Render the stored comparison without treating unavailable data as unchanged.
 *
 * @param props - Immutable comparison data returned by the local API.
 * @returns Parameter, accuracy, and Dataset comparison sections.
 */
export function ComparisonPanel({ comparison }: ComparisonPanelProps): React.JSX.Element {
  if (comparison.status === "unavailable") {
    return (
      <section>
        <h2>Comparison</h2>
        <p>{comparison.unavailableReason}</p>
      </section>
    );
  }

  return (
    <section>
      <h2>Comparison</h2>
      <section>
        <h3>Parameter differences</h3>
        {comparison.parameters.length === 0 ? <p>No Parameter differences.</p> : (
          <ul>
            {comparison.parameters.map((difference) => (
              <li key={difference.name}>
                <strong>{difference.name}</strong>: {" "}
                <span>{difference.parentValue ?? "(none)"}{" → "}{difference.resultValue ?? "(none)"}</span>
                {" "}({difference.status})
              </li>
            ))}
          </ul>
        )}
      </section>
      <section>
        <h3>Best accuracy</h3>
        {comparison.accuracy.status === "unavailable" ? (
          <p>{comparison.accuracy.unavailableReason}</p>
        ) : (
          <p>
            {formatPercentage(comparison.accuracy.parentBest)}
            {" → "}
            {formatPercentage(comparison.accuracy.resultBest)}
            {" ("}{formatPercentagePointDelta(comparison.accuracy.delta)}{ ")"}
          </p>
        )}
      </section>
      <section>
        <h3>Dataset Input differences</h3>
        <DatasetDifferences comparison={comparison} />
      </section>
    </section>
  );
}

/**
 * Render Dataset status and differences without implying row-level changes.
 *
 * @param props - Full comparison containing Dataset Input comparison data.
 * @returns Dataset status text or a list of recorded identifier differences.
 */
function DatasetDifferences({ comparison }: ComparisonPanelProps): React.JSX.Element {
  const datasets = comparison.datasets;
  if (datasets.status === "unavailable") {
    return <p>{datasets.unavailableReason}</p>;
  }
  if (datasets.status === "unchanged") {
    return <p>Dataset Inputs unchanged.</p>;
  }
  return (
    <ul>
      {datasets.differences.map((difference, index) => (
        <li key={datasetDifferenceKey(difference, index)}>{formatDatasetDifference(difference)}</li>
      ))}
    </ul>
  );
}

/**
 * Format one ratio as a percentage shown to two decimal places.
 *
 * @param value - Available ratio from zero through one.
 * @returns User-facing percentage text.
 */
function formatPercentage(value: number | null): string {
  return `${roundToTwoDecimalPlaces((value ?? 0) * 100).toFixed(2)}%`;
}

/**
 * Format one ratio delta as a signed percentage-point value.
 *
 * @param value - Available result-minus-parent accuracy ratio.
 * @returns User-facing signed percentage-point delta.
 */
function formatPercentagePointDelta(value: number | null): string {
  const percentagePoints = roundToTwoDecimalPlaces((value ?? 0) * 100);
  const sign = percentagePoints >= 0 ? "+" : "";
  return `${sign}${percentagePoints.toFixed(2)} pp`;
}

/**
 * Convert one Dataset Input difference into concise identity-focused text.
 *
 * @param difference - Difference between parent and result Dataset Inputs.
 * @returns Recorded input difference text, never a row-level change description.
 */
function formatDatasetDifference(difference: DatasetDifference): string {
  const dataset = difference.parent ?? difference.result;
  const name = dataset?.name ?? "Dataset Input";
  if (difference.status === "changed") {
    return `${name}: ${difference.changedFields.join(", ")} changed`;
  }
  return `${name}: ${difference.status}`;
}

/**
 * Create a stable React list key from the displayed Dataset Input and status.
 *
 * @param difference - Difference whose list key is needed.
 * @param index - Stable API-order fallback when identifiers are equal.
 * @returns Stable key for one rendered Dataset Input difference.
 */
function datasetDifferenceKey(difference: DatasetDifference, index: number): string {
  const dataset = difference.parent ?? difference.result;
  return `${difference.status}:${dataset?.context ?? ""}:${dataset?.name ?? ""}:${index}`;
}

/**
 * Round a display value to two decimal places before converting it to text.
 *
 * @param value - Numeric value that should use ordinary two-decimal rounding.
 * @returns Value rounded for a stable user-facing percentage display.
 */
function roundToTwoDecimalPlaces(value: number): number {
  const normalizedValue = Number(value.toPrecision(15));
  return Math.round(normalizedValue * 100) / 100;
}
