# Data Model: Mondel

## Ownership and relationships

`EvolutionStep` is owned by Mondel and represents one improvement from a parent Run to a result Run. `RunSnapshot` represents an immutable point-in-time import of one MLflow Run and is reusable: it may be a parent of many Evolution Steps but result of at most one. The logical Lineage edge is `$parent_run_id \rightarrow result_run_id$` for an Evolution Step with both links. Lineage is reconstructed from current `evolution_step` values; no derived Lineage table is stored.

## Tables

### `evolution_step`

| Field | Type | Rules |
|---|---|---|
| `id` | bigint PK | Application identifier |
| `purpose` | text | Required; must contain at least one non-whitespace character |
| `hypothesis` | text | Required; must contain at least one non-whitespace character |
| `change_description` | text nullable | Optional manual intent/plan/qualitative description; when present, must contain at least one non-whitespace character |
| `parent_run_id` | varchar(64) nullable FK | References `run_snapshot.run_id`; zero or one parent |
| `result_run_id` | varchar(64) nullable FK | References `run_snapshot.run_id`; zero or one result; `UNIQUE` |
| `created_at`, `updated_at` | datetime(6) | UTC timestamps |

Indexes: `UNIQUE(result_run_id)`, `INDEX(parent_run_id)`, and `INDEX(created_at DESC, id DESC)` for the list. The `result_run_id` uniqueness permits multiple `NULL` values in MySQL.

### `run_snapshot`

| Field | Type | Rules |
|---|---|---|
| `run_id` | varchar(64) PK | MLflow Run identifier |
| `mlflow_experiment_id` | varchar(64) nullable | External experiment identifier |
| `run_name`, `status` | varchar(255) nullable | Imported Run metadata |
| `started_at`, `ended_at` | datetime(6) nullable | Converted MLflow times in UTC |
| `imported_at` | datetime(6) | UTC import time |
| `raw_metadata` | json nullable | Retained unmodeled fields for diagnosis |

Each MLflow Run ID has exactly one snapshot. A snapshot and its child Parameters, metric observations, and dataset inputs are inserted only on the first import and are never updated or deleted by application code. Later associations to the same Run ID reuse the existing snapshot.

### `run_parameter`

`run_id` (FK), `name`, `value`; primary key `(run_id, name)`. Values remain strings as supplied by MLflow. This is the source for parameter differences.

### `metric_observation`

`id` (PK), `run_id` (FK), `name`, `value` (double), `step` (bigint), `timestamp` (datetime(6)). Unique `(run_id, name, step, timestamp, value)` prevents accidental duplicate import while retaining complete metric histories. `INDEX(run_id, name, value)` supports `max(accuracy)`.

### `dataset_input`

`id` (PK), `run_id` (FK), `ordinal` (int), `name`, `digest`, `source_type`, `source_uri`, `schema`, `profile`, `context`, and `raw_metadata` (json nullable). Unique `(run_id, ordinal)`. The service exposes the identifier fields supplied by MLflow and marks an absent field unavailable.

### `evolution_step_history`

| Field | Type | Rules |
|---|---|---|
| `id` | bigint PK | Append-only audit record |
| `evolution_step_id` | bigint FK | References edited Evolution Step |
| `field` | enum | `purpose`, `hypothesis`, `change_description`, `parent_run_id`, `result_run_id` |
| `old_value` | text nullable | `NULL` is an unlinked/absent value |
| `new_value` | text nullable | `NULL` records unlinking |
| `changed_at` | datetime(6) | UTC; list ascending |

History is inserted whenever a user edit changes a supported field, including Run changes and removals. It is never updated or deleted by application code.

## Mutation validation

1. For each selected Run ID, reuse its saved snapshot when present. When absent, retrieve and validate the MLflow Run and insert a new immutable snapshot before association. Never overwrite an existing snapshot.
2. In one transaction, lock the target Evolution Step row and validate non-blank `purpose` and `hypothesis`.
3. Reject equal non-null parent and result Run IDs.
4. Let `UNIQUE(result_run_id)` reject a result Run claimed by another Evolution Step; map the database conflict to API `409`.
5. Substitute proposed links for the target Evolution Step, construct all complete current edges, and detect a Run-ID cycle by DFS with `visiting` and `visited` sets. Reject a cycle with `409` before commit.
6. Update only the target row and append one history record per changed field. Do not modify any dependent Evolution Step.

An Evolution Step may be created without either Run. A parent-only Evolution Step makes its parent an external Lineage root when no Evolution Step currently has that Run as its result.

## Derived views

- **Evolution Step list**: Evolution Step ID, purpose, hypothesis, parent/result Run summary, timestamps, and a compact comparison summary. The summary reports comparison availability, Parameter change count, best parent/result `accuracy` and delta when available, and dataset status as changed, unchanged, or unavailable. It does not include the full Parameter or dataset differences.
- **Detail**: current Evolution Step fields, both snapshots, all Parameters, all metric observations, dataset inputs, ordered history.
- **Comparison**: only when both current Run links exist. Return only added, changed, or removed Parameters from the union of names. `accuracy` is available only if both snapshots contain values in the specified 0-to-1 range; best values are `MAX(metric_observation.value WHERE name = 'accuracy')` and `$delta = result - parent$`. Persist and return these ratios unchanged; the frontend formats best values as percentages and the delta as percentage points. Dataset comparison returns the status separately from the available parent/result identifiers so unchanged and unavailable are distinguishable.
- **Lineage**: traverse reverse ownership (`result_run_id = current parent`) for ancestors until no owner, then show an external Run root; traverse `parent_run_id = current result` breadth-first for descendants. Include only current links and stable order by Evolution Step ID.
