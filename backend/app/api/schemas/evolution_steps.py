"""HTTP schemas for creating, editing, and reading Evolution Steps."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _camel_case(name: str) -> str:
    """Convert one snake_case Python field name to its JSON camelCase alias.

    Args:
        name: Python field name written in snake_case.

    Returns:
        str: JSON field name written in camelCase.
    """
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    """Serialize schema fields as camelCase and reject unknown JSON fields."""

    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )


class EvolutionStepCreateRequest(ApiModel):
    """Required and optional values supplied when creating a Step."""

    purpose: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    change_description: str | None = None
    parent_run_id: str | None = Field(default=None, max_length=64, pattern=r"^\S+$")
    result_run_id: str | None = Field(default=None, max_length=64, pattern=r"^\S+$")


class EvolutionStepPatchRequest(ApiModel):
    """Partial editable values for an existing Evolution Step."""

    purpose: str | None = Field(default=None, min_length=1)
    hypothesis: str | None = Field(default=None, min_length=1)
    change_description: str | None = Field(default=None, min_length=1)
    parent_run_id: str | None = Field(default=None, max_length=64, pattern=r"^\S+$")
    result_run_id: str | None = Field(default=None, max_length=64, pattern=r"^\S+$")

    @model_validator(mode="after")
    def require_one_supplied_field(self) -> "EvolutionStepPatchRequest":
        """Reject an empty object while preserving explicit ``null`` updates.

        Returns:
            EvolutionStepPatchRequest: Valid partial update request.

        Raises:
            ValueError: If the JSON body does not name any editable field.
        """
        if not self.model_fields_set:
            raise ValueError("at least one editable field is required")
        for required_text_field in ("purpose", "hypothesis"):
            if (
                required_text_field in self.model_fields_set
                and getattr(self, required_text_field) is None
            ):
                raise ValueError(f"{required_text_field} must not be null")
        return self

    def supplied_changes(self) -> dict[str, str | None]:
        """Return only the fields explicitly supplied by the client.

        Returns:
            dict[str, str | None]: Partial update values including explicit nulls.
        """
        return {
            field: getattr(self, field)
            for field in self.model_fields_set
        }


class HistoryEntryResponse(ApiModel):
    """One append-only user-visible Evolution Step field change."""

    field: str
    old_value: str | None
    new_value: str | None
    changed_at: datetime


class RunSummaryResponse(ApiModel):
    """Current mutable display metadata for one locally linked Run."""

    run_id: str
    mlflow_experiment_id: str | None
    run_name: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    last_synced_at: datetime
    snapshot_state: str
    snapshot_captured_at: datetime | None


class DatasetInputSnapshotResponse(ApiModel):
    """One immutable Dataset Input retained in a captured Snapshot."""

    ordinal: int
    name: str
    digest: str
    source_type: str
    source: str
    schema_value: str | None = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    profile: str | None
    context: str | None


class RunSnapshotResponse(ApiModel):
    """Immutable terminal Run data exposed through a linked Step."""

    run_id: str
    status_at_capture: str
    started_at: datetime | None
    ended_at: datetime | None
    best_accuracy: float | None
    best_accuracy_step: int | None
    best_accuracy_recorded_at: datetime | None
    captured_at: datetime
    parameters: dict[str, str]
    datasets: list[DatasetInputSnapshotResponse]


class LinkedRunResponse(ApiModel):
    """Current Reference and optional immutable Snapshot for one linked Run."""

    reference: RunSummaryResponse
    snapshot: RunSnapshotResponse | None


class EvolutionStepDetailResponse(ApiModel):
    """Saved Evolution Step text, linked Runs, and ordered history."""

    id: int
    purpose: str
    hypothesis: str
    change_description: str | None
    parent_run: LinkedRunResponse | None
    result_run: LinkedRunResponse | None
    history: list[HistoryEntryResponse]
    created_at: datetime
    updated_at: datetime
