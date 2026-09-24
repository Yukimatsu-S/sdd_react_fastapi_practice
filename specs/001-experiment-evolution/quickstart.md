# Quickstart: Mondel

## Prerequisites

- Python 3.12+, `uv`, Node.js 24 with `npm`, and Docker Desktop.
- A normal-use MySQL database and reachable MLflow Tracking Server for manual application use. Their credentials belong only in `backend/.env`; do not commit them.
- For manual acceptance, prepare MLflow Runs with Parameters, an `accuracy` history, other Metrics at the same steps, and Dataset Input metadata.

## Setup and run

All commands below start at the repository root unless a step says otherwise.

1. Install locked dependencies and start the dedicated automated-test DB.

   ```bash
   cd backend && uv sync --locked --all-groups && cd ..
   cd frontend && npm ci && npx playwright install chromium && cd ..
   docker compose -f docker-compose.test.yml up -d --wait --wait-timeout 180
   ```

   `mondel_test` is only for automated tests and listens at `127.0.0.1:3307`. Its local test-only credentials are in `backend/.env.example` and in `docker-compose.test.yml`.

2. Create `backend/.env` from the example, replace the normal database username/password and the MLflow URL with real values, then apply the schema to the normal-use database.

   ```bash
   cp -n backend/.env.example backend/.env
   cd backend && uv run --env-file .env alembic -x database=application upgrade head && cd ..
   ```

   `-x database=application` selects `MONDEL_DATABASE_URL`; it prevents accidentally applying the application schema to an unspecified connection. The test suite manages its own test schema.

3. In terminal A, start FastAPI. In terminal B, start Vite.

   ```bash
   # terminal A
   cd backend && uv run --env-file .env fastapi run main.py --host 127.0.0.1 --port 8000

   # terminal B
   cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
   ```

4. Open `http://127.0.0.1:5173`. Browser code sends relative `/api/v1/...` requests to Vite on port 5173. Vite's proxy sends the same method, path, and body to FastAPI on `127.0.0.1:8000`; the browser does not call port 8000 directly.

## Automated verification

Run the following after the test DB becomes healthy. These commands do not need normal MySQL or a live MLflow server because tests use the dedicated DB and MLflow fixtures.

```bash
cd backend
uv run --env-file .env.example pytest
uv run ruff check .
cd ../frontend
npm test -- --run
npm run build
npm run test:e2e
```

The E2E command starts configured FastAPI and Vite servers. It uses deterministic browser fixtures for the MLflow-backed create-and-attach flow; a pass verifies browser form behavior and the relative Vite-origin request path, not a live MLflow account.

## Failure triage

- Test DB is not healthy: run `docker compose -f docker-compose.test.yml ps` and `docker compose -f docker-compose.test.yml logs mysql-test`.
- Migration or API startup fails: inspect non-secret `backend/.env` values. `MONDEL_DATABASE_URL` must name an existing normal-use database, while `MLFLOW_TRACKING_URI` must reach a Tracking Server.
- Vite cannot reach the API: confirm FastAPI is listening at `http://127.0.0.1:8000/docs`, then confirm Vite is listening at `http://127.0.0.1:5173`.
- Chromium is missing: rerun `cd frontend && npx playwright install chromium` after `npm ci`.
- E2E fails: retain the generated Playwright trace and screenshot under `frontend/test-results/` before rerunning the case.

## Validation scenarios

US1 must demonstrate single-Run saved-detail and best-step Metric viewing without the US3 comparison endpoint. Comparison and Lineage scenarios are added at their respective story checkpoints.

1. **Create and attach**: Create an Evolution Step with non-empty purpose and hypothesis. Select an MLflow parent Run and a distinct result Run. Expect both Run References to be saved immediately. For a terminal Run, expect captured Parameters, best accuracy and its smallest matching step, only Metrics from that step, Dataset Input metadata, and current links. Confirm the Evolution Step change history records each later edit.
2. **Single-Run saved detail and best-step Metrics (US1)**: Prepare a terminal MLflow Run with repeated observations for the same Metric/step, including timestamp ties, negative, out-of-order, and non-contiguous signed 64-bit steps, and repeated maximum accuracy values. Link only this result Run and open its detail. Verify saved Step text/timestamps, linked Run reference fields, all captured Parameter key/value pairs, and every Dataset Input's ordinal, name, digest, source type/source, schema, profile, and context, including explicit unset states. Confirm capture keeps the greatest timestamp, then the greatest numeric value if timestamps tie, and selects the smallest step containing the canonical maximum accuracy. Confirm GET `/runs/{runId}/best-step-metrics` and its UI show only canonical Metrics at that exact step, with no substitution from another step and no full history. Separately link a snapshot-pending Run and expect `snapshot_pending`; a captured Run without accuracy returns `accuracy_missing`, while Parameters/Datasets remain visible. Available responses have a null reason; unavailable responses have their defined reason and an empty item list. These cases must pass without a parent Run or comparison request.
3. **Run ownership and cycles**: Attach one result Run to Evolution Step A, then attempt to attach it to Evolution Step B. Expect `409`. Attempt same parent/result IDs and a multi-generation back-edge. Expect `409`, a human-readable reason, and no persisted partial change. Also issue concurrent mutations on different Evolution Steps that are individually valid but together form a cycle. Verify the shared guard serializes them, one request validates first, and the later request sees the committed edge and returns `409` without creating a cycle.
4. **Link updates and history boundary**: Create an Evolution Step and expect no history rows for the initial values. Open its separate edit page from the detail view and confirm the reusable form is prefilled. Change and then unlink a parent Run; attach, change, and then unlink a result Run through PATCH, returning to a freshly loaded detail after each successful edit. Expect one ordered history item for each successful value change, with a supported camel-case `field` and explicit nullable `oldValue` and `newValue`. Change multiple fields in one request and verify equal `changedAt` values are returned in stable internal-ID order. Resend a current value and expect `200` without a history item. Separately attempt a conflicting result-Run change; expect actionable `409` feedback and no history item for the rejected operation. Submit empty, whitespace-containing, and over-64-character Run IDs in create or patch bodies and expect `422`; also expect `422` for invalid Run or Evolution Step path parameters. Verify Evolution Steps that already reference the former Run do not change and that the detail view reloads the Lineage reconstructed from the remaining current links.
5. **Comparison (US3)**: For finalized parent and result Runs, verify Parameter additions/changes/removals and the accuracy delta `resultBest - parentBest` from the stored best values. Verify each available comparison state has a null unavailable reason and each unavailable state has its defined reason. For Dataset Inputs, verify a unique matching `(context, name)` pair with a different digest or source is `changed`, unmatched recorded inputs are `parent_only` or `result_only`, and unchanged pairs are omitted. Confirm an empty Dataset Input list or ambiguous duplicate pairing key produces an explicit unavailable state and that the UI does not describe these metadata differences as row additions or deletions. No Metric other than `accuracy` gets an automatic best value or delta. A comparison failure must not suppress the US1 single-Run information.
6. **Lineage**: Create a branched, multi-generation lineage and select a middle Evolution Step. Verify ancestors and descendants are returned nearest-first, descendants at the same distance use Evolution Step ID order, and every branch has the correct `parentEvolutionStepId`. Verify a null parent Run means no upstream Run, while a parent Run with no producing Evolution Step is shown as the upstream boundary.
7. **MLflow failure boundary and local detail**: Make the MLflow gateway time out when linking a previously unknown Run. Expect the attach/update API to return `502` with a trace ID and leave existing Evolution Step links untouched. Then load an existing Evolution Step detail and confirm local Run Reference, Snapshot, comparison, and Lineage data remain available without MLflow.
8. **Active-to-terminal Snapshot lifecycle**: Attach a `RUNNING` Run and expect a saved Run Reference with `snapshotState: pending`, null `snapshotCapturedAt`, and no Snapshot payload. Simulate the detail page's `POST /runs/{runId}/sync` while the Run remains active and confirm it stays pending. Change the MLflow Run to `FINISHED` with final Metric observations and Dataset inputs. Confirm neither a closed detail page nor elapsed time on an open page triggers polling; reopen or reload detail to trigger the next synchronization. Expect one immutable Snapshot containing only the best-step Metrics with `snapshotState: captured` and matching non-null capture times. A Snapshot without valid accuracy must return all three best-accuracy fields as null; a Snapshot with valid accuracy must return all three. Reject response combinations where Snapshot state, presence, capture time, or best-accuracy fields disagree. Confirm the successful-sync detail and best-step Metric reload displays the newly captured values without starting another sync loop. Repeat synchronization and confirm no Snapshot row or captured value is replaced.
9. **Run metadata synchronization and failure**: Change a finalized linked Run's name, status, or execution times in MLflow and synchronize it. Expect the current name, status, start/end times, and `lastSyncedAt` on its Run Reference to reflect the successful synchronization while the immutable Snapshot and comparison result remain unchanged. Re-read Lineage and confirm its selected/ancestor/descendant Evolution Step IDs, parent-Step IDs, distances, branches, and ordering are unchanged; embedded Run summaries may contain the newly synchronized mutable display metadata. Next make MLflow unavailable. Expect the synchronization request to return `502`, while the already-rendered local detail retains the last-known reference and Snapshot and displays a non-blocking warning.
10. **Run candidate paging**: Prepare more than 20 active-lifecycle MLflow Runs, one deleted-lifecycle Run, duplicate names, and Runs in different MLflow Experiments. Request the first candidate page and confirm the deleted Run is absent, the remaining candidates use newest-first stable ordering, 20 items, and a non-null `nextPageToken`. Verify the picker displays every candidate's Run ID/name, MLflow Experiment ID/name, execution status, and start/end times, using explicit unset states for nullable fields. Request the next page with the same search term and confirm no duplicate boundary item. Verify case-insensitive Run-name filtering and `nextPageToken: null` on the final page.
11. **Evolution Step list paging**: Prepare more than 20 Evolution Steps, including multiple rows with the same `created_at`. Confirm the first response returns at most 20 items ordered by `created_at DESC, id DESC` and includes `nextPageToken` only when more rows exist. Insert a newer Evolution Step, request the continuation page, and verify the new row is not mixed into the existing traversal and no boundary item is duplicated. Reload without a token and verify the new row appears on the first page. Expect `422` for a malformed token. Verify each visible item includes ID, purpose, hypothesis, parent/result Run summaries or unset states, created/updated times, comparison availability/reason, Parameter change count, best accuracies/delta, and Dataset change status; distinguish unchanged from unavailable.

## Timed manual acceptance procedure

Record every run in `validation-results.md` with the commit ID from `git rev-parse HEAD`, date, browser, normal-use MySQL database name, MLflow fixture/run IDs, start condition, end condition, elapsed time, result, and evidence. Do not record secrets.

1. **SC-001 (within 3 minutes):** begin when the empty create form is displayed. Choose distinct prepared parent/result Runs, enter non-empty purpose and hypothesis, save, and end when the resulting detail displays the selected result Run.
2. **SC-002 (within 1 minute):** begin when a prepared captured-Step detail page opens. End when Parameter differences, best accuracy, and accuracy delta are identified from the Comparison panel.
3. **SC-003 (within 1 minute):** begin when a prepared multi-generation Step detail page opens. End when every expected ancestor, descendant, and their order are identified in the Lineage panel.
4. **SC-004 (100% agreement):** create the prepared records, stop FastAPI and Vite with `Ctrl+C`, restart both using the commands above without resetting MySQL, then compare all expected detail fields and reconstructed Lineage with the fixture worksheet. Record the matched count and expected count; pass only when they are equal.

For a failed criterion, preserve the Playwright trace/screenshot when available or browser/API diagnostic information, write the observed state and time, and mark the criterion failed rather than altering expected values.

## Stop the local test DB

After verification, stop (rather than delete) the dedicated test DB:

```bash
docker compose -f docker-compose.test.yml stop
```

`stop` keeps the container available for the next `up`; `down` removes the container. Do not run `down -v` unless intentionally discarding test data.

See [data-model.md](data-model.md) for persistence and integrity rules, and [contracts/openapi.yaml](contracts/openapi.yaml) for HTTP responses and error semantics.
