# Quickstart: Mondel

## Prerequisites

- Python 3.12+, `uv`, Node.js LTS with `npm`, Docker-compatible container runtime, MySQL 8.0+, and a reachable MLflow Tracking Server.
- Configure backend environment variables for a MySQL connection and MLflow tracking URI. Do not commit credentials.
- Prepare MLflow Runs that include Parameters, at least one metric history (including `accuracy` for its comparison scenario), and dataset input metadata.

## Setup and run

1. From `backend/`, run `uv sync`, apply Alembic migrations, then start FastAPI with the project command defined in `pyproject.toml`.
2. From `frontend/`, run `npm ci` and `npm run dev`.
3. Open the frontend URL printed by Vite. Confirm it can load the empty Evolution Step list through the API.

Before implementation, these commands are expected to become the reproducible project entry points. Their exact environment variable names and scripts are assigned during task generation.

## Validation scenarios

1. **Create and attach**: Create an Evolution Step with non-empty purpose and hypothesis. Select an MLflow parent Run and a distinct result Run. Expect both Run References to be saved immediately. For a terminal Run, expect captured Parameters, all metric observations, dataset data, and current links in the detail response. Confirm the history records each later edit.
2. **Run ownership and cycles**: Attach one result Run to Evolution Step A, then attempt to attach it to Evolution Step B. Expect `409`. Attempt same parent/result IDs and a multi-generation back-edge. Expect `409`, a human-readable reason, and no persisted partial change.
3. **Link updates**: Change and then unlink a parent Run; change and then unlink a result Run. Expect one ordered history item for each changed link. Verify Evolution Steps that already reference the former Run do not change.
4. **Comparison**: For linked Runs, verify parameter additions/changes/removals. With multiple `accuracy` samples, verify the API uses each maximum and reports `$resultMax - parentMax$`. Confirm missing parent, result, metric, or dataset produces an explicit unavailable state; no other metric gets an automatic best value or delta.
5. **Lineage**: Create a branched, multi-generation lineage. Verify ancestor and descendant order and that a parent Run not owned as an application result appears as an external root.
6. **MLflow failure boundary and local detail**: Make the MLflow gateway time out when linking a previously unknown Run. Expect the attach/update API to return `502` with a trace ID and leave existing Evolution Step links untouched. Then load an existing Evolution Step detail and confirm local Run Reference, Snapshot, comparison, and Lineage data remain available without MLflow.
7. **Active-to-terminal Snapshot lifecycle**: Attach a `RUNNING` Run and expect a saved Run Reference with `snapshotState: pending` and no Snapshot payload. Simulate the detail page's `POST /runs/{runId}/sync` while the Run remains active and confirm it stays pending. Change the MLflow Run to `FINISHED`, add final metric history and Dataset inputs, then synchronize again. Expect one immutable Snapshot with `snapshotState: captured`. Repeat synchronization and confirm no Snapshot row or captured value is replaced.
8. **Run metadata synchronization failure**: Rename a linked Run in MLflow and synchronize it. Expect the current name, status, and `lastSyncedAt` to change while a finalized Snapshot and comparison results remain unchanged. Next make MLflow unavailable. Expect the synchronization request to return `502`, while the already-rendered local detail retains the last-known reference and Snapshot and displays a non-blocking warning.

## Automated verification

- Backend: `uv run pytest` for unit, integration, MLflow-gateway mock, migration, and OpenAPI contract suites. Integration tests use an explicitly configured dedicated MySQL test database; Testcontainers is not required.
- Frontend: `npm test` for form, request state, error, and comparison/lineage display tests.
- End-to-end: After frontend/backend integration, `npm run test:e2e` runs one Playwright test for the critical create-and-attach journey with FastAPI, MySQL, and MLflow test fixtures. The remaining validation scenarios are covered by backend integration and frontend component tests. Preserve screenshots/traces for end-to-end failures.

See [data-model.md](data-model.md) for persistence and integrity rules, and [contracts/openapi.yaml](contracts/openapi.yaml) for HTTP responses and error semantics.
