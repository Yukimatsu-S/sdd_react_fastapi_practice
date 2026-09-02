# Data Model: ML Experiment Evolution Manager

## Ownership and relationships

`Experiment` is owned by this product. `RunSnapshot` represents an immutable point-in-time import of one MLflow Run and is reusable: it may be a parent of many experiments but result of at most one. The logical lineage edge is `$parent_run_id \rightarrow result_run_id$` for an experiment with both links. It is reconstructed from current `experiment` values; no derived lineage table is stored.

## Tables

### `experiment`

| Field | Type | Rules |
|---|---|---|
| `id` | bigint PK | Application identifier |
| `purpose` | text | Required, non-blank |
| `hypothesis` | text | Required, non-blank |
| `change_description` | text nullable | Manual intent/plan/qualitative description |
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

### `run_parameter`

`run_id` (FK), `name`, `value`; primary key `(run_id, name)`. Values remain strings as supplied by MLflow. This is the source for parameter differences.

### `metric_observation`

`id` (PK), `run_id` (FK), `name`, `value` (double), `step` (bigint), `timestamp` (datetime(6)). Unique `(run_id, name, step, timestamp, value)` prevents accidental duplicate import while retaining complete metric histories. `INDEX(run_id, name, value)` supports `max(accuracy)`.

### `dataset_input`

`id` (PK), `run_id` (FK), `ordinal` (int), `name`, `digest`, `source_type`, `source_uri`, `schema`, `profile`, `context`, and `raw_metadata` (json nullable). Unique `(run_id, ordinal)`. The service exposes the identifier fields supplied by MLflow and marks an absent field unavailable.

### `experiment_history`

| Field | Type | Rules |
|---|---|---|
| `id` | bigint PK | Append-only audit record |
| `experiment_id` | bigint FK | References edited experiment |
| `field` | enum | `purpose`, `hypothesis`, `change_description`, `parent_run_id`, `result_run_id` |
| `old_value` | text nullable | `NULL` is an unlinked/absent value |
| `new_value` | text nullable | `NULL` records unlinking |
| `changed_at` | datetime(6) | UTC; list ascending |

History is inserted whenever a user edit changes a supported field, including Run changes and removals. It is never updated or deleted by application code.

## Mutation validation

1. Validate a selected MLflow Run and create/update its snapshot before association.
2. In one transaction, lock the target experiment row and validate non-blank `purpose` and `hypothesis`.
3. Reject equal non-null parent and result Run IDs.
4. Let `UNIQUE(result_run_id)` reject a result Run claimed by another experiment; map the database conflict to API `409`.
5. Substitute proposed links for the target experiment, construct all complete current edges, and detect a Run-ID cycle by DFS with `visiting` and `visited` sets. Reject a cycle with `409` before commit.
6. Update only the target row and append one history record per changed field. Do not modify any dependent experiment.

An experiment may be created without either Run. A parent-only experiment makes its parent an external lineage root when no experiment currently has that Run as its result.

## Derived views

- **Experiment list**: experiment ID, purpose excerpt, hypothesis excerpt, parent/result Run summary, timestamps.
- **Detail**: current experiment fields, both snapshots, all Parameters, all metric observations, dataset inputs, ordered history.
- **Comparison**: only when both current Run links exist. Parameters are unioned by name. `accuracy` is available only if both snapshots contain it; best values are `MAX(metric_observation.value WHERE name = 'accuracy')` and `$delta = result - parent$`.
- **Lineage**: traverse reverse ownership (`result_run_id = current parent`) for ancestors until no owner, then show an external Run root; traverse `parent_run_id = current result` breadth-first for descendants. Include only current links and stable order by experiment ID.