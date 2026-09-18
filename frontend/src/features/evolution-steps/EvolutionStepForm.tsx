/** Reusable create/edit form for one Evolution Step. */

import { useState } from "react";

import type { CreateEvolutionStepRequest } from "../../api/evolutionSteps";
import { RunPicker } from "./RunPicker";

type EvolutionStepFormProps = {
  initialValues?: CreateEvolutionStepRequest;
  onSubmit: (request: CreateEvolutionStepRequest) => Promise<void> | void;
};

type FormValues = Required<CreateEvolutionStepRequest>;

const EMPTY_VALUES: FormValues = {
  purpose: "",
  hypothesis: "",
  changeDescription: null,
  parentRunId: null,
  resultRunId: null,
};

/**
 * Edit Evolution Step text and optional Run links before handing data to a page.
 *
 * @param props - Optional initial values and the page-owned asynchronous save action.
 * @returns Accessible form with local required-text validation and save feedback.
 */
export function EvolutionStepForm({
  initialValues,
  onSubmit,
}: EvolutionStepFormProps): React.JSX.Element {
  const [values, setValues] = useState<FormValues>({ ...EMPTY_VALUES, ...initialValues });
  const [errors, setErrors] = useState<{ purpose?: string; hypothesis?: string }>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  /** Validate required text then pass a normalized request to the owning page. */
  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const nextErrors = requiredTextErrors(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setIsSaving(true);
    setSubmitError(null);
    try {
      await onSubmit({
        ...values,
        changeDescription: blankToNull(values.changeDescription),
      });
    } catch {
      setSubmitError("Evolution Step could not be saved. Please review the selected Runs.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)}>
      <label>
        Purpose
        <input
          aria-label="Purpose"
          value={values.purpose}
          onChange={(event) => setValues((current) => ({ ...current, purpose: event.target.value }))}
        />
      </label>
      {errors.purpose === undefined ? null : <p role="alert">{errors.purpose}</p>}

      <label>
        Hypothesis
        <textarea
          aria-label="Hypothesis"
          value={values.hypothesis}
          onChange={(event) => setValues((current) => ({ ...current, hypothesis: event.target.value }))}
        />
      </label>
      {errors.hypothesis === undefined ? null : <p role="alert">{errors.hypothesis}</p>}

      <label>
        Change description
        <textarea
          aria-label="Change description"
          value={values.changeDescription ?? ""}
          onChange={(event) =>
            setValues((current) => ({ ...current, changeDescription: event.target.value }))
          }
        />
      </label>

      <RunPicker
        label="Parent Run"
        value={values.parentRunId}
        onChange={(parentRunId) => setValues((current) => ({ ...current, parentRunId }))}
      />
      <RunPicker
        label="Result Run"
        value={values.resultRunId}
        onChange={(resultRunId) => setValues((current) => ({ ...current, resultRunId }))}
      />
      {submitError === null ? null : <p role="alert">{submitError}</p>}
      <button disabled={isSaving} type="submit">
        Save Evolution Step
      </button>
    </form>
  );
}

/**
 * Convert whitespace-only optional text into the explicit JSON clear value.
 *
 * @param value - Optional field value from the text area.
 * @returns Null for blank text, otherwise the original text.
 */
function blankToNull(value: string | null): string | null {
  return value === null || value.trim() === "" ? null : value;
}

/**
 * Return visible messages for required fields that contain only whitespace.
 *
 * @param values - Current form fields before submission.
 * @returns Field-to-message map with no entries when input is valid.
 */
function requiredTextErrors(values: FormValues): { purpose?: string; hypothesis?: string } {
  return {
    ...(values.purpose.trim() === "" ? { purpose: "Purpose is required." } : {}),
    ...(values.hypothesis.trim() === "" ? { hypothesis: "Hypothesis is required." } : {}),
  };
}
