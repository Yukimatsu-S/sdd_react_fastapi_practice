# Quickstart: Mondel

## Prerequisites

- Python 3.12+, `uv`, Node.js LTS with `npm`, Docker-compatible container runtime, MySQL 8.0+, and a reachable MLflow Tracking Server.
- Configure backend environment variables for a MySQL connection and MLflow tracking URI. Do not commit credentials.
- Prepare MLflow Runs that include Parameters, an `accuracy` history with other Metrics logged at the same steps, and dataset input metadata.

## Setup and run

1. From `backend/`, run `uv sync`, apply Alembic migrations, then start FastAPI with the project command defined in `pyproject.toml`.
2. From `frontend/`, run `npm ci` and `npm run dev`.
3. Open the frontend URL printed by Vite. Confirm it can load the empty Evolution Step list through the API.

Before implementation, these commands are expected to become the reproducible project entry points. Their exact environment variable names and scripts are assigned during task generation.

## Validation scenarios

1. **Create and attach**: Create an Evolution Step with non-empty purpose and hypothesis. Select an MLflow parent Run and a distinct result Run. Expect both Run References to be saved immediately. For a terminal Run, expect captured Parameters, best accuracy and its smallest matching step, only Metrics from that step, dataset data, and current links. Confirm the Evolution Step change history records each later edit.
2. **Run ownership and cycles**: Attach one result Run to Evolution Step A, then attempt to attach it to Evolution Step B. Expect `409`. Attempt same parent/result IDs and a multi-generation back-edge. Expect `409`, a human-readable reason, and no persisted partial change.
3. **Link updates and history boundary**: Create an Evolution Step and expect no history rows for the initial values. After creation, change and then unlink a parent Run; attach, change, and then unlink a result Run. Expect one ordered history item for each successful value change. Resend a current value and attempt a conflicting result-Run change; expect no history item for either the no-op or rejected operation. Verify Evolution Steps that already reference the former Run do not change.
4. **Comparison**: For linked Runs, verify parameter additions/changes/removals. Log multiple values for the same Metric and step, and verify the greatest timestamp wins; when timestamps also tie, verify the greatest numeric value wins. After this canonicalization, verify repeated maximum `accuracy` values select the smallest step and the API reports `$resultBest - parentBest$`. Confirm `GET /runs/{runId}/best-step-metrics` returns only canonical Metrics recorded at that exact step and does not substitute values from another step. For Dataset Inputs, verify a unique matching `(context, name)` pair with a different digest or source is `changed`, unmatched recorded inputs are `parent_only` or `result_only`, and unchanged pairs are omitted. Confirm an empty Dataset Input list or ambiguous duplicate pairing key produces an explicit unavailable state and that the UI does not describe these metadata differences as row additions or deletions. No metric other than `accuracy` gets an automatic best value or delta.
5. **Lineage**: Create a branched, multi-generation lineage and select a middle Evolution Step. Verify ancestors and descendants are returned nearest-first, descendants at the same distance use Evolution Step ID order, and every branch has the correct `parentEvolutionStepId`. Verify a null parent Run means no upstream Run, while a parent Run with no producing Evolution Step is shown as the upstream boundary.
6. **MLflow failure boundary and local detail**: Make the MLflow gateway time out when linking a previously unknown Run. Expect the attach/update API to return `502` with a trace ID and leave existing Evolution Step links untouched. Then load an existing Evolution Step detail and confirm local Run Reference, Snapshot, comparison, and Lineage data remain available without MLflow.
7. **Active-to-terminal Snapshot lifecycle**: Attach a `RUNNING` Run and expect a saved Run Reference with `snapshotState: pending` and no Snapshot payload. Simulate the detail page's `POST /runs/{runId}/sync` while the Run remains active and confirm it stays pending. Change the MLflow Run to `FINISHED`, add final Metric observations and Dataset inputs, then synchronize again. Expect one immutable Snapshot containing only the best-step Metrics with `snapshotState: captured`. Repeat synchronization and confirm no Snapshot row or captured value is replaced.
8. **Run metadata synchronization failure**: Rename a linked Run in MLflow and synchronize it. Expect the current name, status, and `lastSyncedAt` to change while a finalized Snapshot and comparison results remain unchanged. Next make MLflow unavailable. Expect the synchronization request to return `502`, while the already-rendered local detail retains the last-known reference and Snapshot and displays a non-blocking warning.
9. **Run candidate paging**: Prepare more than 20 non-deleted MLflow Runs, including duplicate names and Runs in different MLflow Experiments. Request the first candidate page and confirm newest-first stable ordering, 20 items, distinguishing metadata, and a non-null `nextPageToken`. Request the next page with the same search term and confirm no duplicate boundary item. Verify case-insensitive Run-name filtering and `nextPageToken: null` on the final page.
10. **Evolution Step list paging**: Prepare more than 20 Evolution Steps, including multiple rows with the same `created_at`. Confirm the first response returns at most 20 items ordered by `created_at DESC, id DESC` and includes `nextPageToken` only when more rows exist. Insert a newer Evolution Step, request the continuation page, and verify the new row is not mixed into the existing traversal and no boundary item is duplicated. Reload without a token and verify the new row appears on the first page. Expect `422` for a malformed token.

## Automated verification

- Backend: `uv run pytest` for unit, integration, MLflow-gateway mock, migration, and OpenAPI contract suites. Integration tests use an explicitly configured dedicated MySQL test database; Testcontainers is not required.
- Frontend: `npm test` for form, request state, error, and comparison/lineage display tests.
- End-to-end: After frontend/backend integration, `npm run test:e2e` runs one Playwright test for the critical create-and-attach journey with FastAPI, MySQL, and MLflow test fixtures. The remaining validation scenarios are covered by backend integration and frontend component tests. Preserve screenshots/traces for end-to-end failures.

See [data-model.md](data-model.md) for persistence and integrity rules, and [contracts/openapi.yaml](contracts/openapi.yaml) for HTTP responses and error semantics.
