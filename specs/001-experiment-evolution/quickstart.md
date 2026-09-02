# Quickstart: ML Experiment Evolution Manager

## Prerequisites

- Python 3.12+, `uv`, Node.js LTS with `npm`, Docker-compatible container runtime, MySQL 8.0+, and a reachable MLflow Tracking Server.
- Configure backend environment variables for a MySQL connection and MLflow tracking URI. Do not commit credentials.
- Prepare MLflow Runs that include Parameters, at least one metric history (including `accuracy` for its comparison scenario), and dataset input metadata.

## Setup and run

1. From `backend/`, run `uv sync`, apply Alembic migrations, then start FastAPI with the project command defined in `pyproject.toml`.
2. From `frontend/`, run `npm ci` and `npm run dev`.
3. Open the frontend URL printed by Vite. Confirm it can load the empty experiment list through the API.

Before implementation, these commands are expected to become the reproducible project entry points. Their exact environment variable names and scripts are assigned during task generation.

## Validation scenarios

1. **Create and attach**: Create an experiment with non-empty purpose and hypothesis. Select an MLflow parent Run and a distinct result Run. Expect imported Parameters, all metric observations, dataset data, and current links in the detail response. Confirm the history records each later edit.
2. **Run ownership and cycles**: Attach one result Run to Experiment A, then attempt to attach it to Experiment B. Expect `409`. Attempt same parent/result IDs and a multi-generation back-edge. Expect `409`, a human-readable reason, and no persisted partial change.
3. **Link updates**: Change and then unlink a parent Run; change and then unlink a result Run. Expect one ordered history item for each changed link. Verify experiments that already reference the former Run do not change.
4. **Comparison**: For linked Runs, verify parameter additions/changes/removals. With multiple `accuracy` samples, verify the API uses each maximum and reports `$resultMax - parentMax$`. Confirm missing parent, result, metric, or dataset produces an explicit unavailable state; no other metric gets an automatic best value or delta.
5. **Lineage**: Create a branched, multi-generation lineage. Verify ancestor and descendant order and that a parent Run not owned as an application result appears as an external root.
6. **MLflow failure boundary**: Make the MLflow gateway time out or return an unreadable selected Run. Expect the attach/update API to return `502` with a trace ID, leave existing experiment links untouched, and allow saved details/lineage to continue reading from MySQL.

## Automated verification

- Backend: `uv run pytest` for unit, integration, MLflow-gateway mock, migration, and OpenAPI contract suites.
- Frontend: `npm test` for form, request state, error, and comparison/lineage display tests.
- End-to-end: `npm run test:e2e` with FastAPI, MySQL, and MLflow test fixtures running. It must cover the six validation scenarios above and preserve screenshots/traces for failures.

See [data-model.md](data-model.md) for persistence and integrity rules, and [contracts/openapi.yaml](contracts/openapi.yaml) for HTTP responses and error semantics.