"""HTTP response schemas for selected-centered current Lineage reads."""

from app.api.schemas.evolution_steps import ApiModel, RunSummaryResponse


class LineageStepResponse(ApiModel):
    """One saved Evolution Step at a stable position in the current Lineage."""

    id: int
    purpose: str
    hypothesis: str
    parent_evolution_step_id: int | None
    distance_from_selected: int
    parent_run: RunSummaryResponse | None
    result_run: RunSummaryResponse | None


class LineageResponse(ApiModel):
    """A selected Step with ordered current ancestors and descendants."""

    selected: LineageStepResponse
    ancestors: list[LineageStepResponse]
    descendants: list[LineageStepResponse]
