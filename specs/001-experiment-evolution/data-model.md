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

### `lineage_mutation_guard`

| Field | Type | Rules |
|---|---|---|
| `id` | tinyint PK | Singleton row; the migration inserts the fixed value `1` |

This row stores no product data. A transaction that can add, change, or remove a parent/result Run link locks row `1` with `SELECT ... FOR UPDATE` before locking an Evolution Step or reading current Lineage edges. This serializes Lineage mutations across application instances while allowing unrelated read requests to proceed.

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
| `best_accuracy_step` | bigint nullable | Smallest signed MLflow step at which canonical `best_accuracy` was reached |
| `best_accuracy_recorded_at` | datetime(6) nullable | Timestamp of the selected accuracy observation |
| `captured_at` | datetime(6) | UTC snapshot capture time |
| `raw_metadata` | json nullable | Retained unmodeled fields for diagnosis |

Each Run Reference has zero or one Snapshot. `RUNNING` and `SCHEDULED` references have no Snapshot. When synchronization first observes `FINISHED`, `FAILED`, or `KILLED`, the Snapshot and its child Parameters, best-step Metrics, and dataset inputs are inserted atomically. They are never updated or deleted by application code. Repeated or concurrent synchronization reuses the existing Snapshot instead of overwriting it.

When a terminal Run has no valid `accuracy` observation, `best_accuracy`, `best_accuracy_step`, and `best_accuracy_recorded_at` are all `NULL`, and no `best_step_metric` rows are inserted.

### `run_parameter`

`run_id` (FK to `run_snapshot`), `name`, `value`; primary key `(run_id, name)`. Values remain strings as supplied by MLflow. This is the source for parameter differences.

### `best_step_metric`

`run_id` (FK to `run_snapshot`), `name`, `value` (double), `step` (signed bigint), and `recorded_at` (datetime(6)); primary key `(run_id, name)`. Preserve signed 64-bit MLflow steps, including negative, out-of-order, and non-contiguous values. Before selecting the best step, group observations by `(run_id, name, step)` and retain the greatest `timestamp`; if multiple values have that timestamp, retain the greatest numeric value. Every stored row then uses `run_snapshot.best_accuracy_step`. A Metric with no canonical observation at that exact step is not inserted. Full histories are used only transiently during capture and are not persisted.

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
| `changed_at` | datetime(6) | UTC; order history by `(changed_at ASC, id ASC)` |

History starts after the Evolution Step has been created. Insert one row whenever a successful user edit actually changes a supported field, including first Run attachment, later Run changes, and removals. Do not insert rows for initial creation, no-op updates that resend the current value, or operations rejected before transaction commit. Existing history is never updated or deleted by application code.

The API serializes the database field names as `purpose`, `hypothesis`, `changeDescription`, `parentRunId`, or `resultRunId`. Every history response includes both `oldValue` and `newValue`; a known absence or unlink is represented by JSON `null`, not by omitting the property. History is returned by `(changed_at ASC, id ASC)` so rows created at the same timestamp retain a stable order. The internal history ID is used as the database tie-breaker and is not exposed in the API response.

## Linking and mutation validation

1. For each selected Run ID, reuse its saved Run Reference when present. When absent, retrieve the Run from MLflow before the database transaction; failure to confirm its existence rejects the link without partial changes.
2. If the newly retrieved Run is active, prepare only a Run Reference. If it is terminal, also retrieve its complete Snapshot payload before opening the database transaction.
3. Begin one database transaction. When the request can change a Run link, lock `lineage_mutation_guard.id = 1` first, then lock the target Evolution Step row when it already exists. Every Lineage mutation must acquire locks in this order.
4. Read the current Lineage edges after acquiring the guard and validate non-blank `purpose` and `hypothesis`.
5. Reject equal non-null parent and result Run IDs.
6. Let `UNIQUE(result_run_id)` reject a result Run claimed by another Evolution Step; map the database conflict to API `409`.
7. Substitute proposed links for the target Evolution Step, construct all complete current edges, and detect a Run-ID cycle by DFS with `visiting` and `visited` sets. Reject a cycle with `409` before commit.
8. Insert or update Run References, insert any first terminal Snapshots, update only the target Evolution Step, and append one history record per changed field. Do not modify any dependent Evolution Step or overwrite a Snapshot. Commit or roll back before another Lineage mutation can acquire the guard.

## Run synchronization

1. `POST /runs/{runId}/sync` requires an existing Run Reference and retrieves the current MLflow Run outside the database transaction.
2. If the Snapshot is pending and the Run is terminal, retrieve all Parameters, Metric histories, and dataset inputs. Canonicalize Metric observations by `(name, step)`, retaining the greatest timestamp and then the greatest numeric value when timestamps tie. Select the maximum canonical accuracy and, when it occurs at multiple steps, the smallest step; prepare only canonical Metric values recorded at that exact step before opening the transaction. If the Run is still active, retrieve only current reference metadata.
3. In a short transaction, lock the Run Reference, update its mutable display metadata, and insert the Snapshot and child rows only when no Snapshot exists. A concurrent request that captured it first wins; the later request returns the stored Snapshot without replacing it.
4. If MLflow retrieval fails, return `502` and leave the Run Reference and Snapshot state unchanged. The frontend retains the local detail already displayed and shows a synchronization warning.

An Evolution Step may be created without either Run. When a parent Run is present but no Evolution Step currently has it as a result, that Run is the upstream boundary of the traceable Lineage. When the parent Run is absent, there is no upstream Run to return.

## Derived views

- **Evolution Step list**: Evolution Step ID, purpose, hypothesis, parent/result Run summary with last-known Run name, current status, synchronization time, and Snapshot state, timestamps, and a compact comparison summary. It reads only MySQL and does not trigger synchronization. Order by `(created_at DESC, id DESC)`, read at most 21 rows, return at most 20, and use the last returned `(created_at, id)` as an opaque continuation cursor only when another row exists. A continuation selects `created_at < cursor.created_at OR (created_at = cursor.created_at AND id < cursor.id)`. The summary reports comparison availability and its reason, Parameter change count, best parent/result `accuracy` and delta or their unavailable reason, and dataset status and its unavailable reason. It does not include the full Parameter or dataset differences.
- **Detail**: return current Evolution Step fields, each linked Run Reference and optional Snapshot summary, all captured Parameters, dataset inputs, and ordered Evolution Step change history from MySQL. It does not call MLflow. After this response is rendered, the frontend invokes the separate synchronization action and reloads detail on success, then loads the stored best-step Metric list through `GET /runs/{runId}/best-step-metrics` for each captured Run.
- **Best-step Metrics**: return the stored best accuracy, selected step, selected accuracy timestamp, and only the Metric values recorded at that exact step. Return `unavailable` with an empty list and `snapshot_pending` while the Snapshot is pending, or `accuracy_missing` when no valid accuracy exists. When `status = available`, `unavailableReason` is null and all best-accuracy fields are present; when `status = unavailable`, a defined reason is present and all best-accuracy fields are null. This endpoint reads only MySQL and never returns full Metric histories.
- **Comparison**: the overall comparison is `available` only when both current Run links have finalized Snapshots. Evaluate unavailable prerequisites in this fixed order: missing parent Run (`parent_run_missing`), missing result Run (`result_run_missing`), pending parent Snapshot (`parent_snapshot_pending`), then pending result Snapshot (`result_snapshot_pending`); return the first matching reason, no Parameter differences, and child comparison states with `comparison_unavailable`. When both finalized Snapshots exist, the overall comparison is `available` with a null reason even if an individual section is unavailable. Return only added, changed, or removed Parameters from the union of names. `accuracy` is available with a null reason only if both snapshots contain a best accuracy in the specified 0-to-1 range; otherwise return `parent_accuracy_missing`, `result_accuracy_missing`, or `both_accuracy_values_missing`, and null best values and delta. Persist and return available ratios unchanged; the frontend formats best values as percentages and the delta as percentage points. Pair Dataset Inputs by unique `(context, name)` keys and compare `digest`, `source_type`, and `source`. Return only `changed`, `parent_only`, and `result_only` differences; an empty difference list with `unchanged` means all recorded identifiers match. Dataset comparison is unavailable with an empty difference list and `parent_dataset_inputs_missing`, `result_dataset_inputs_missing`, `both_dataset_inputs_missing`, or `dataset_pairing_ambiguous`. A Dataset state of `changed` or `unchanged` has a null reason. These states describe Dataset Input metadata, not row-level additions or deletions. The compact list summary applies the same states and reason codes.
- **Lineage**: center the response on the selected Evolution Step. Traverse reverse ownership (`result_run_id = current parent`) for ancestors and return the nearest ancestor first. Traverse `parent_run_id = current result` breadth-first for descendants, returning the nearest generation first and Evolution Step ID ascending within a generation. Each item includes its distance from the selected Step and `parentEvolutionStepId` so branches remain explicit. Do not return a separate external-root object: `parentRun = null` with `parentEvolutionStepId = null` means no upstream Run, while a non-null `parentRun` with `parentEvolutionStepId = null` means the Run is the upstream boundary because its producing Evolution Step is not registered in Mondel. Include only current links.
