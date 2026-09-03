# Data Model: Mondel

## Ownership and relationships

`EvolutionStep` is owned by Mondel and represents one improvement from a parent Run to a result Run. `RunReference` records the association and current display metadata as soon as a Run is selected, including while training is active. Its optional one-to-one `RunSnapshot` is created only after the Run reaches a terminal state and is immutable after capture. A Run may be a parent of many Evolution Steps but result of at most one. The logical Lineage edge is `$parent_run_id \rightarrow result_run_id$` for an Evolution Step with both links. Lineage is reconstructed from current `evolution_step` values; no derived Lineage table is stored.

## Tables

### `evolution_step`

| Field | Type | Rules |
|---|---|---|
| `id` | bigint PK | Application identifier |
| `purpose` | text | Required; must contain at least one non-whitespace character |
| `hypothesis` | text | Required; must contain at least one non-whitespace character |
| `change_description` | text nullable | Optional manual intent/plan/qualitative description; when present, must contain at least one non-whitespace character |
| `parent_run_id` | varchar(64) nullable FK | References `run_reference.run_id`; zero or one parent |
| `result_run_id` | varchar(64) nullable FK | References `run_reference.run_id`; zero or one result; `UNIQUE` |
| `created_at`, `updated_at` | datetime(6) | UTC timestamps |

Indexes: `UNIQUE(result_run_id)`, `INDEX(parent_run_id)`, and `INDEX(created_at DESC, id DESC)` for the list. The `result_run_id` uniqueness permits multiple `NULL` values in MySQL.

### `run_reference`

| Field | Type | Rules |
|---|---|---|
| `run_id` | varchar(64) PK | MLflow Run identifier |
| `mlflow_experiment_id` | varchar(64) nullable | External experiment identifier |
| `run_name` | varchar(255) nullable | Last-known MLflow Run name |
| `current_status` | varchar(16) | `RUNNING`, `SCHEDULED`, `FINISHED`, `FAILED`, or `KILLED` |
| `started_at`, `ended_at` | datetime(6) nullable | Last-known converted MLflow times in UTC |
| `last_synced_at` | datetime(6) | UTC time of the last successful MLflow synchronization |
| `created_at` | datetime(6) | UTC time when this reference was first saved |

`run_name`, `current_status`, `started_at`, `ended_at`, and `last_synced_at` are mutable display metadata. Snapshot state is derived as `captured` when a matching `run_snapshot` row exists and `pending` otherwise.

### `run_snapshot`

| Field | Type | Rules |
|---|---|---|
| `run_id` | varchar(64) PK/FK | One-to-one reference to `run_reference.run_id` |
| `status_at_capture` | varchar(16) | Terminal status captured once |
| `started_at`, `ended_at` | datetime(6) nullable | Execution times captured once in UTC |
| `best_accuracy` | double nullable | Maximum canonical `accuracy` value; null when no accuracy was logged |
| `best_accuracy_step` | bigint nullable | Smallest MLflow step at which canonical `best_accuracy` was reached |
| `best_accuracy_recorded_at` | datetime(6) nullable | Timestamp of the selected accuracy observation |
| `captured_at` | datetime(6) | UTC snapshot capture time |
| `raw_metadata` | json nullable | Retained unmodeled fields for diagnosis |

Each Run Reference has zero or one Snapshot. `RUNNING` and `SCHEDULED` references have no Snapshot. When synchronization first observes `FINISHED`, `FAILED`, or `KILLED`, the Snapshot and its child Parameters, best-step Metrics, and dataset inputs are inserted atomically. They are never updated or deleted by application code. Repeated or concurrent synchronization reuses the existing Snapshot instead of overwriting it.

When a terminal Run has no valid `accuracy` observation, `best_accuracy`, `best_accuracy_step`, and `best_accuracy_recorded_at` are all `NULL`, and no `best_step_metric` rows are inserted.

### `run_parameter`

`run_id` (FK to `run_snapshot`), `name`, `value`; primary key `(run_id, name)`. Values remain strings as supplied by MLflow. This is the source for parameter differences.

### `best_step_metric`

`run_id` (FK to `run_snapshot`), `name`, `value` (double), `step` (bigint), and `recorded_at` (datetime(6)); primary key `(run_id, name)`. Before selecting the best step, group observations by `(run_id, name, step)` and retain the greatest `timestamp`; if multiple values have that timestamp, retain the greatest numeric value. Every stored row then uses `run_snapshot.best_accuracy_step`. A Metric with no canonical observation at that exact step is not inserted. Full histories are used only transiently during capture and are not persisted.

### `dataset_input`

`id` (PK), `run_id` (FK to `run_snapshot`), `ordinal` (int), `name`, `digest`, `source_type`, `source`, `schema`, `profile`, `context`, and `raw_metadata` (json nullable). Unique `(run_id, ordinal)`. `name`, `digest`, `source_type`, and `source` retain the values supplied by MLflow; `schema`, `profile`, and `context` are nullable. Comparison pairs inputs by `(context, name)` only when that key is unique within both Run Snapshots.

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

## Linking and mutation validation

1. For each selected Run ID, reuse its saved Run Reference when present. When absent, retrieve the Run from MLflow before the database transaction; failure to confirm its existence rejects the link without partial changes.
2. If the newly retrieved Run is active, prepare only a Run Reference. If it is terminal, also retrieve its complete Snapshot payload before opening the database transaction.
3. In one transaction, lock the target Evolution Step row and validate non-blank `purpose` and `hypothesis`.
4. Reject equal non-null parent and result Run IDs.
5. Let `UNIQUE(result_run_id)` reject a result Run claimed by another Evolution Step; map the database conflict to API `409`.
6. Substitute proposed links for the target Evolution Step, construct all complete current edges, and detect a Run-ID cycle by DFS with `visiting` and `visited` sets. Reject a cycle with `409` before commit.
7. Insert or update Run References, insert any first terminal Snapshots, update only the target Evolution Step, and append one history record per changed field. Do not modify any dependent Evolution Step or overwrite a Snapshot.

## Run synchronization

1. `POST /runs/{runId}/sync` requires an existing Run Reference and retrieves the current MLflow Run outside the database transaction.
2. If the Snapshot is pending and the Run is terminal, retrieve all Parameters and dataset inputs, select the maximum accuracy at the smallest step, and prepare only Metric values recorded at that step before opening the transaction. If it is still active, retrieve only current reference metadata.
3. In a short transaction, lock the Run Reference, update its mutable display metadata, and insert the Snapshot and child rows only when no Snapshot exists. A concurrent request that captured it first wins; the later request returns the stored Snapshot without replacing it.
4. If MLflow retrieval fails, return `502` and leave the Run Reference and Snapshot state unchanged. The frontend retains the local detail already displayed and shows a synchronization warning.

An Evolution Step may be created without either Run. When a parent Run is present but no Evolution Step currently has it as a result, that Run is the upstream boundary of the traceable Lineage. When the parent Run is absent, there is no upstream Run to return.

## Derived views

- **Evolution Step list**: Evolution Step ID, purpose, hypothesis, parent/result Run summary with last-known Run name, current status, synchronization time, and Snapshot state, timestamps, and a compact comparison summary. It reads only MySQL and does not trigger synchronization. Order by `(created_at DESC, id DESC)`, read at most 21 rows, return at most 20, and use the last returned `(created_at, id)` as an opaque continuation cursor only when another row exists. A continuation selects `created_at < cursor.created_at OR (created_at = cursor.created_at AND id < cursor.id)`. The summary reports comparison availability, Parameter change count, best parent/result `accuracy` and delta when available, and dataset status as changed, unchanged, or unavailable. It does not include the full Parameter or dataset differences.
- **Detail**: return current Evolution Step fields, each linked Run Reference and optional Snapshot summary, all captured Parameters, dataset inputs, and ordered Evolution Step change history from MySQL. It does not call MLflow. After this response is rendered, the frontend invokes the separate synchronization action and reloads detail on success, then loads the stored best-step Metric list through `GET /runs/{runId}/best-step-metrics` for each captured Run.
- **Best-step Metrics**: return the stored best accuracy, selected step, selected accuracy timestamp, and only the Metric values recorded at that exact step. Return an unavailable state with an empty list while the Snapshot is pending or when no valid accuracy exists. This endpoint reads only MySQL and never returns full Metric histories.
- **Comparison**: only when both current Run links have finalized Snapshots. Return `snapshot_pending` as the unavailable reason when either Snapshot is absent. Otherwise, return only added, changed, or removed Parameters from the union of names. `accuracy` is available only if both snapshots contain a best accuracy in the specified 0-to-1 range; the delta is `$resultBest - parentBest$`. Persist and return these ratios unchanged; the frontend formats best values as percentages and the delta as percentage points. Pair Dataset Inputs by unique `(context, name)` keys and compare `digest`, `source_type`, and `source`. Return only `changed`, `parent_only`, and `result_only` differences; an empty difference list with `unchanged` means all recorded identifiers match. Return `unavailable` with a reason when either side has no Dataset Inputs or pairing keys are ambiguous. These states describe Dataset Input metadata, not row-level additions or deletions.
- **Lineage**: center the response on the selected Evolution Step. Traverse reverse ownership (`result_run_id = current parent`) for ancestors and return the nearest ancestor first. Traverse `parent_run_id = current result` breadth-first for descendants, returning the nearest generation first and Evolution Step ID ascending within a generation. Each item includes its distance from the selected Step and `parentEvolutionStepId` so branches remain explicit. Do not return a separate external-root object: `parentRun = null` with `parentEvolutionStepId = null` means no upstream Run, while a non-null `parentRun` with `parentEvolutionStepId = null` means the Run is the upstream boundary because its producing Evolution Step is not registered in Mondel. Include only current links.
