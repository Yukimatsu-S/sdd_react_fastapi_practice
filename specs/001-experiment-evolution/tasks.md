# Tasks: Mondel Initial MVP

**Input**: Design documents from `specs/001-experiment-evolution/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/openapi.yaml`, `quickstart.md`, and `.specify/memory/constitution.md`

**Tests**: Required. Constitution Principle IV, Test-First Verification, requires each behavior-changing implementation task to be preceded by a focused test task that is run red before its implementation begins.

**Task notation**: Every task names its target file or files, corresponding user story, prerequisite task IDs, and an executable or observable verification. `P` means the task can run in parallel after its stated dependencies are complete and does not modify the same files as the other parallel tasks.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish reproducible Python, Node.js, test-database, and configuration entry points for every user story.

- [ ] T001 Configure FastAPI runtime, database, migration, MLflow, pytest, and lint dependencies in `backend/pyproject.toml` and lock them in `backend/uv.lock`; 対応: 共通 (US1-US4); 依存: なし; 検証: `cd backend && uv sync --all-groups` completes and exposes `pytest`, `alembic`, `sqlalchemy`, `pymysql`, `mlflow`, and `ruff`.
- [ ] T002 Create the minimal React/Vite/TypeScript application shell and dependencies in `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`, and `frontend/src/App.tsx`; 対応: 共通 (US1-US4); 依存: なし; 検証: `cd frontend && npm ci && npm run build` completes with the minimal application entry point.
- [ ] T003 [P] Define non-secret backend configuration names and sample values in `backend/.env.example`; 対応: 共通 (US1-US4); 依存: なし; 検証: the file documents `MONDEL_DATABASE_URL`, `MONDEL_TEST_DATABASE_URL`, and `MLFLOW_TRACKING_URI` without embedding credentials.
- [ ] T004 [P] Provision the dedicated MySQL 8 test service with a health check in `./docker-compose.test.yml`; 対応: 共通 (US1-US4); 依存: なし; 検証: `docker compose -f docker-compose.test.yml up -d` reports the database healthy and accepts the configured test connection.
- [ ] T005 Configure backend test discovery and test-only environment selection in `backend/pytest.ini`, and add a test-environment smoke test in `backend/tests/unit/test_test_environment.py`; 対応: 共通 (US1-US4); 依存: T001, T003, T004; 検証: `cd backend && uv run pytest tests/unit/test_test_environment.py` passes and confirms tests use `MONDEL_TEST_DATABASE_URL` rather than a production database URL.
- [ ] T006 Configure Vitest, React Testing Library setup, and the browser-like test environment in `frontend/vitest.config.ts` and `frontend/src/test/setup.ts`, and add a rendering smoke test in `frontend/src/test/setup.test.tsx`; 対応: 共通 (US1-US4); 依存: T002; 検証: `cd frontend && npm test -- --run src/test/setup.test.tsx` passes and confirms a component can render in the test environment.
- [ ] T007 Document the reproducible backend, frontend, and test-database bootstrap commands in `./README.md`; 対応: 共通 (US1-US4); 依存: T001-T006; 検証: the commands in `./README.md` match the scripts and environment variable names created in T001-T006.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared persistence, API, error, and HTTP-client boundaries that all user stories require.

**Critical**: Complete this phase before implementing a user-story increment.

- [ ] T008 Create reusable MySQL session, transaction rollback, MLflow fake, and API-client fixtures in `backend/tests/conftest.py`; 対応: 共通 (US1-US4); 依存: T004, T005; 検証: `cd backend && uv run pytest --collect-only` imports the fixtures while targeting only `MONDEL_TEST_DATABASE_URL`.
- [ ] T009 [P] Write a failing schema and migration integration test for all normalized tables, indexes, and constraints in `backend/tests/integration/test_initial_schema.py`; 対応: 共通 (US1-US4); 依存: T008; 検証: before T014-T016, `cd backend && uv run pytest tests/integration/test_initial_schema.py` fails because the required schema is absent.
- [ ] T010 [P] Write failing direct-handler and HTTP contract tests for the API error envelope and trace ID in `backend/tests/contract/test_error_responses.py`; 対応: 共通 (US1-US4); 依存: T008; 検証: before T017-T018, `cd backend && uv run pytest tests/contract/test_error_responses.py` fails because the handlers and their FastAPI registration are absent.
- [ ] T011 [P] Write a failing typed-fetch success, API-error, and network-error test in `frontend/src/api/client.test.ts`; 対応: 共通 (US1-US4); 依存: T006; 検証: before T019, `cd frontend && npm test -- --run src/api/client.test.ts` fails because the shared client is absent.
- [ ] T012 Implement validated environment loading and application settings in `backend/app/config.py`; 対応: 共通 (US1-US4); 依存: T003, T009; 検証: the configuration rejects missing required connection settings and `cd backend && uv run pytest tests/integration/test_initial_schema.py` progresses past settings initialization.
- [ ] T013 Implement synchronous SQLAlchemy engine, scoped request session dependency, and transaction helpers in `backend/app/infrastructure/database.py`; 対応: 共通 (US1-US4); 依存: T012; 検証: a fixture can open and roll back a test-database transaction without sharing state between tests.
- [ ] T014 Model `evolution_step`, `lineage_mutation_guard`, `run_reference`, `run_snapshot`, `run_parameter`, `best_step_metric`, `dataset_input`, and `evolution_step_history` in `backend/app/infrastructure/models.py`; 対応: 共通 (US1-US4); 依存: T013, T009; 検証: model metadata contains the nullable unique result-run constraint, required foreign keys, and the specified pagination indexes.
- [ ] T015 Initialize Alembic configuration and metadata discovery in `backend/alembic.ini` and `backend/migrations/env.py`; 対応: 共通 (US1-US4); 依存: T013, T014; 検証: `cd backend && uv run alembic revision --autogenerate -m smoke --rev-id smoke` can detect the model metadata, then the temporary revision is removed.
- [ ] T016 Create the initial MySQL schema and singleton lineage guard seed in `backend/migrations/versions/001_initial_schema.py`; 対応: 共通 (US1-US4); 依存: T014, T015; 検証: `cd backend && uv run pytest tests/integration/test_initial_schema.py` passes after applying migrations to the dedicated test database.
- [ ] T017 [P] Implement structured API exceptions, `code`/`message`/`traceId` responses, and trace-ID logging in `backend/app/api/errors.py`; 対応: 共通 (US1-US4); 依存: T010, T012; 検証: `cd backend && uv run pytest tests/contract/test_error_responses.py -k direct_handler` passes for direct handler serialization while HTTP registration cases remain red until T018.
- [ ] T018 Create the `/api/v1` router registration, request-session lifecycle, and exception middleware in `backend/app/api/router.py` and `backend/main.py`; 対応: 共通 (US1-US4); 依存: T013, T016, T017; 検証: `cd backend && uv run pytest tests/contract/test_error_responses.py` passes and `GET /api/v1/unknown` returns the T017 error envelope.
- [ ] T019 Implement the typed browser `fetch` wrapper with JSON parsing and typed API errors in `frontend/src/api/client.ts`; 対応: 共通 (US1-US4); 依存: T011; 検証: `cd frontend && npm test -- --run src/api/client.test.ts` passes for success, server error, and network failure cases.

**Checkpoint**: Shared persistence, migrations, versioned API errors, and the typed HTTP client are ready. The three foundational red tests now pass.

---

## Phase 3: User Story 1 - Evolution Stepを定義してRunを紐付ける (Priority: P1)

**Goal**: Create and edit an Evolution Step, select valid MLflow Runs, preserve change history, and show locally saved details while synchronizing linked Run state.

**Independent Test**: With MLflow test fixtures, create a Step with purpose and hypothesis, optionally choose a parent Run and change description, attach a distinct result Run, then verify the detail page shows saved text, Run reference state, Snapshot state, and post-creation history.

### Tests for User Story 1 - Write and Run Red First

- [ ] T020 [P] [US1] Write failing domain tests for non-blank fields, nullable change descriptions, signed Metric steps, and canonical terminal Snapshot selection in `backend/tests/unit/domain/test_evolution_step_and_snapshot_rules.py`; 対応: US1; 依存: T008-T019; 検証: before T028-T029, `cd backend && uv run pytest tests/unit/domain/test_evolution_step_and_snapshot_rules.py` fails for the unimplemented rules.
- [ ] T021 [P] [US1] Write failing duplicate-result, equal-parent/result, and multi-generation cycle validation tests in `backend/tests/unit/domain/test_run_link_validation.py`; 対応: US1; 依存: T008-T019; 検証: before T030, `cd backend && uv run pytest tests/unit/domain/test_run_link_validation.py` fails for link validation.
- [ ] T022 [P] [US1] Write failing MLflow candidate mapping and terminal/active Run payload tests in `backend/tests/unit/infrastructure/test_mlflow_run_gateway.py`; 対応: US1; 依存: T008-T019; 検証: before T031-T032, `cd backend && uv run pytest tests/unit/infrastructure/test_mlflow_run_gateway.py` fails for the missing gateway.
- [ ] T023 [P] [US1] Write a failing create/patch/history integration test covering no-op updates, link changes, unlinking, and `409` result ownership in `backend/tests/integration/test_evolution_step_mutations.py`; 対応: US1; 依存: T008-T019; 検証: before T033-T034, `cd backend && uv run pytest tests/integration/test_evolution_step_mutations.py` fails for the missing use case.
- [ ] T024 [P] [US1] Write a failing active-to-terminal synchronization integration test with immutable Snapshot assertions in `backend/tests/integration/test_run_link_and_sync.py`; 対応: US1; 依存: T008-T019; 検証: before T035, `cd backend && uv run pytest tests/integration/test_run_link_and_sync.py` fails for missing synchronization behavior.
- [ ] T025 [P] [US1] Write failing OpenAPI contract tests for Run search, Evolution Step create/read/patch, validation, conflict, and MLflow `502` responses in `backend/tests/contract/test_runs_and_evolution_steps.py`; 対応: US1; 依存: T008-T019; 検証: before T036-T040, `cd backend && uv run pytest tests/contract/test_runs_and_evolution_steps.py` fails for absent endpoints.
- [ ] T026 [P] [US1] Write failing form tests for required fields, optional change description, Run selection, and backend validation feedback in `frontend/src/features/evolution-steps/EvolutionStepForm.test.tsx`; 対応: US1; 依存: T006, T019; 検証: before T043-T045, `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepForm.test.tsx` fails because the form is absent.
- [ ] T027 [P] [US1] Write failing local-detail, pending-Snapshot, captured-Snapshot, ordered-history, and non-blocking-sync-warning tests in `frontend/src/features/evolution-steps/EvolutionStepDetailPage.test.tsx`; 対応: US1; 依存: T006, T019; 検証: before T046-T048, `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepDetailPage.test.tsx` fails because the detail experience is absent.

### Implementation for User Story 1

- [ ] T028 [P] [US1] Implement Evolution Step value objects and purpose/hypothesis/change-description validation in `backend/app/domain/evolution_step.py`; 対応: US1; 依存: T020; 検証: `cd backend && uv run pytest tests/unit/domain/test_evolution_step_and_snapshot_rules.py -k 'blank or change_description'` passes.
- [ ] T029 [P] [US1] Implement Metric canonicalization and immutable Snapshot payload selection in `backend/app/domain/run_snapshot.py`; 対応: US1; 依存: T020; 検証: `cd backend && uv run pytest tests/unit/domain/test_evolution_step_and_snapshot_rules.py -k 'metric or snapshot'` passes, including signed and tied steps.
- [ ] T030 [P] [US1] Implement proposed-link validation and deterministic DFS cycle detection in `backend/app/domain/lineage.py`; 対応: US1; 依存: T021; 検証: `cd backend && uv run pytest tests/unit/domain/test_run_link_validation.py` passes for duplicate, same-Run, and cyclic links.
- [ ] T031 [P] [US1] Define MLflow gateway protocols and normalized Run, Metric, and Dataset transfer types in `backend/app/infrastructure/mlflow_gateway.py`; 対応: US1; 依存: T022; 検証: gateway unit tests can inject an in-memory fake without importing the MLflow client.
- [ ] T032 [US1] Implement the MLflow client adapter for active-experiment Run search, opaque paging, current Run lookup, and terminal capture data in `backend/app/infrastructure/mlflow_client.py`; 対応: US1; 依存: T022, T029, T031; 検証: `cd backend && uv run pytest tests/unit/infrastructure/test_mlflow_run_gateway.py` passes, including case-insensitive search and terminal status mapping.
- [ ] T033 [P] [US1] Implement repositories for Evolution Steps, Run References, Snapshots, history, and guard-row locking in `backend/app/infrastructure/repositories.py`; 対応: US1; 依存: T014, T016, T023; 検証: repository operations execute in the test transaction and preserve `NULL` link values without creating history rows.
- [ ] T034 [US1] Implement atomic create and patch use cases, MLflow prevalidation, history append rules, result uniqueness handling, and cycle checks in `backend/app/services/evolution_step_service.py`; 対応: US1; 依存: T028, T030, T032, T033, T023; 検証: `cd backend && uv run pytest tests/integration/test_evolution_step_mutations.py` passes with no partial writes on rejected mutations.
- [ ] T035 [P] [US1] Implement local Run synchronization, active-state retention, one-time terminal Snapshot capture, and immutable recapture protection in `backend/app/services/run_sync_service.py`; 対応: US1; 依存: T029, T032, T033, T024; 検証: `cd backend && uv run pytest tests/integration/test_run_link_and_sync.py` passes for active, terminal, repeat-sync, and MLflow-failure cases.
- [ ] T036 [P] [US1] Define create, patch, detail, history, and linked-Run request/response schemas in `backend/app/api/schemas/evolution_steps.py`; 対応: US1; 依存: T025, T034; 検証: schema serialization emits camel-case fields and explicit JSON `null` values required by `contracts/openapi.yaml`.
- [ ] T037 [P] [US1] Define Run search, synchronization, and Snapshot-state response schemas in `backend/app/api/schemas/runs.py`; 対応: US1; 依存: T025, T035; 検証: schema serialization represents pending and captured Snapshot states consistently.
- [ ] T038 [P] [US1] Implement Evolution Step create, read, and patch routes with request validation and error mapping in `backend/app/api/routes/evolution_steps.py`; 対応: US1; 依存: T034, T036; 検証: the Evolution Step portions of `cd backend && uv run pytest tests/contract/test_runs_and_evolution_steps.py` pass.
- [ ] T039 [P] [US1] Implement MLflow Run search and synchronization routes in `backend/app/api/routes/runs.py`; 対応: US1; 依存: T035, T037; 検証: the Run-search and sync portions of `cd backend && uv run pytest tests/contract/test_runs_and_evolution_steps.py` pass. The best-step Metrics route is added only when US3 is implemented in T074.
- [ ] T040 [US1] Register Evolution Step and Run routers under `/api/v1` in `backend/app/api/router.py`; 対応: US1; 依存: T018, T038, T039; 検証: `cd backend && uv run pytest tests/contract/test_runs_and_evolution_steps.py` passes end to end.
- [ ] T041 [P] [US1] Add typed Evolution Step create, read, and patch API functions in `frontend/src/api/evolutionSteps.ts`; 対応: US1; 依存: T019, T025; 検証: mocked requests use the documented `/api/v1/evolution-steps` URLs and surface typed conflict errors.
- [ ] T042 [P] [US1] Add typed Run-search and synchronization API functions in `frontend/src/api/runs.ts`; 対応: US1; 依存: T019, T025; 検証: mocked requests retain opaque page tokens and classify `502` as an upstream synchronization failure.
- [ ] T043 [US1] Implement pageable, searchable, distinguishable MLflow Run selection in `frontend/src/features/evolution-steps/RunPicker.tsx`; 対応: US1; 依存: T022, T042, T026; 検証: the form test can choose duplicate Run names by Run ID and load a second candidate page.
- [ ] T044 [US1] Implement the accessible Evolution Step form with local validation, parent/result selection, and submit feedback in `frontend/src/features/evolution-steps/EvolutionStepForm.tsx`; 対応: US1; 依存: T041, T043, T026; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepForm.test.tsx` passes.
- [ ] T045 [US1] Implement the create-page submission and navigation flow in `frontend/src/pages/EvolutionStepCreatePage.tsx`; 対応: US1; 依存: T044; 検証: a successful submit redirects to the created Step detail and a `409` remains actionable in the form.
- [ ] T046 [US1] Implement saved text, Run reference/Snapshot state, and ordered history rendering in `frontend/src/features/evolution-steps/EvolutionStepDetail.tsx`; 対応: US1; 依存: T041, T042, T027; 検証: detail tests render pending and captured states, nullable history values, and no full Metric history.
- [ ] T047 [US1] Implement local-first detail loading, per-Run automatic synchronization, reload-on-success, and non-blocking warning handling in `frontend/src/pages/EvolutionStepDetailPage.tsx`; 対応: US1; 依存: T042, T046, T027; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepDetailPage.test.tsx` passes without hiding locally saved detail on sync failure.
- [ ] T048 [US1] Add create and detail navigation routes and connect the application bootstrap in `frontend/src/routes/AppRoutes.tsx` and `frontend/src/main.tsx`; 対応: US1; 依存: T045, T047; 検証: `cd frontend && npm run build` completes and direct navigation to create and detail routes resolves. The list route is added with the US2 list page in T063.

**Checkpoint**: US1 is independently demonstrable with MLflow fakes and has red-to-green unit, integration, contract, and component-test evidence.

---

## Phase 4: User Story 2 - Evolution Stepの全体像を確認する (Priority: P2)

**Goal**: Show a stable, token-paginated Evolution Step list with comparison summaries and preserve detail readability during synchronization failures.

**Independent Test**: Seed more than 20 Steps and inspect two list pages. Verify newest-first ordering, no duplicated boundary item, the correct compact comparison state, and navigation to a saved detail view.

### Tests for User Story 2 - Write and Run Red First

- [ ] T049 [P] [US2] Write a failing keyset token encode/decode and stable-order unit test in `backend/tests/unit/domain/test_evolution_step_pagination.py`; 対応: US2; 依存: T008-T019, T048; 検証: before T055, `cd backend && uv run pytest tests/unit/domain/test_evolution_step_pagination.py` fails for absent pagination helpers.
- [ ] T050 [P] [US2] Write a failing compact comparison-summary state and reason-code unit test in `backend/tests/unit/domain/test_comparison_summary.py`; 対応: US2; 依存: T008-T019, T048; 検証: before T056, `cd backend && uv run pytest tests/unit/domain/test_comparison_summary.py` fails for missing summary logic.
- [ ] T051 [P] [US2] Write a failing 20-item keyset-list integration test including same-timestamp and newly-inserted-row cases in `backend/tests/integration/test_evolution_step_list.py`; 対応: US2; 依存: T008-T019, T048; 検証: before T057-T059, `cd backend && uv run pytest tests/integration/test_evolution_step_list.py` fails for missing list behavior.
- [ ] T052 [P] [US2] Write a failing list endpoint contract test for summary fields, opaque tokens, and malformed-token `422` behavior in `backend/tests/contract/test_evolution_step_list_contract.py`; 対応: US2; 依存: T008-T019, T048; 検証: before T059, `cd backend && uv run pytest tests/contract/test_evolution_step_list_contract.py` fails for the incomplete GET contract.
- [ ] T053 [P] [US2] Write a failing loading, empty, paged, summary-state, and detail-navigation test in `frontend/src/features/evolution-steps/EvolutionStepListPage.test.tsx`; 対応: US2; 依存: T006, T048; 検証: before T060, T062-T063, `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepListPage.test.tsx` fails because the list page is absent.
- [ ] T054 [P] [US2] Write a failing successful-sync, pending-sync, and retained-detail warning-state test in `frontend/src/features/evolution-steps/RunSyncStatus.test.tsx`; 対応: US2; 依存: T006, T048; 検証: before T061, `cd frontend && npm test -- --run src/features/evolution-steps/RunSyncStatus.test.tsx` fails because reusable sync feedback is absent.

### Implementation for User Story 2

- [ ] T055 [P] [US2] Implement opaque `(created_at, id)` cursor encoding, validation, and keyset predicates in `backend/app/domain/pagination.py`; 対応: US2; 依存: T049; 検証: `cd backend && uv run pytest tests/unit/domain/test_evolution_step_pagination.py` passes for valid and malformed tokens.
- [ ] T056 [P] [US2] Implement compact availability, Parameter-count, accuracy, and Dataset summary calculation in `backend/app/domain/comparison.py`; 対応: US2; 依存: T050; 検証: `cd backend && uv run pytest tests/unit/domain/test_comparison_summary.py` passes with null reasons only for available states.
- [ ] T057 [US2] Add 21-row keyset reads and summary-ready Snapshot joins to `backend/app/infrastructure/repositories.py`; 対応: US2; 依存: T033, T055, T056, T051; 検証: repository queries return at most 20 records plus a next token only when the twenty-first row exists.
- [ ] T058 [US2] Implement Evolution Step list orchestration and list-item mapping in `backend/app/services/evolution_step_list_service.py`; 対応: US2; 依存: T056, T057, T051; 検証: the integration list test gets deterministic ordering and summary objects from stored data only.
- [ ] T059 [US2] Add the token-paginated GET `/evolution-steps` route to `backend/app/api/routes/evolution_steps.py`; 対応: US2; 依存: T052, T058; 検証: `cd backend && uv run pytest tests/integration/test_evolution_step_list.py tests/contract/test_evolution_step_list_contract.py` passes.
- [ ] T060 [US2] Add typed paginated list retrieval and page-token types in `frontend/src/api/evolutionSteps.ts`; 対応: US2; 依存: T041, T052, T059; 検証: mocked list requests retain the server-issued token without exposing it as a text input.
- [ ] T061 [P] [US2] Implement compact Run synchronization progress, success, pending, and non-blocking failure feedback in `frontend/src/features/evolution-steps/RunSyncStatus.tsx`; 対応: US2; 依存: T054, T047; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/RunSyncStatus.test.tsx` passes.
- [ ] T062 [US2] Implement loading, empty, list-summary, next-page, and selected-Step behavior in `frontend/src/features/evolution-steps/EvolutionStepListPage.tsx`; 対応: US2; 依存: T053, T060; 検証: the list-page test passes for empty and multi-page datasets without duplicated rows.
- [ ] T063 [US2] Wire the list page and reusable synchronization status into application routes and detail composition in `frontend/src/pages/EvolutionStepListPage.tsx` and `frontend/src/pages/EvolutionStepDetailPage.tsx`; 対応: US2; 依存: T047, T061, T062; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepListPage.test.tsx src/features/evolution-steps/RunSyncStatus.test.tsx` passes.

**Checkpoint**: US2 can be tested from seeded local database state; a failed MLflow synchronization never prevents list or saved-detail inspection.

---

## Phase 5: User Story 3 - 派生元との差分を振り返る (Priority: P3)

**Goal**: Return and display only meaningful Parameter, accuracy, and Dataset Input differences from finalized Snapshots with explicit unavailable reasons.

**Independent Test**: Seed finalized parent and result Snapshots with changed Parameters, repeated Metrics, and Dataset Inputs. Confirm the comparison shows additions, changes, removals, percentage-formatted accuracy delta, and only valid Dataset difference states.

### Tests for User Story 3 - Write and Run Red First

- [ ] T064 [P] [US3] Write failing Parameter and Dataset Input difference tests, including ambiguous pairing and no-row-data cases, in `backend/tests/unit/domain/test_parameter_and_dataset_differences.py`; 対応: US3; 依存: T008-T019, T063; 検証: before T069, `cd backend && uv run pytest tests/unit/domain/test_parameter_and_dataset_differences.py` fails for missing difference rules.
- [ ] T065 [P] [US3] Write failing comparison availability and unavailable-reason precedence tests in `backend/tests/unit/domain/test_comparison_availability.py`; 対応: US3; 依存: T008-T019, T063; 検証: before T070, `cd backend && uv run pytest tests/unit/domain/test_comparison_availability.py` fails for incomplete comparison state mapping.
- [ ] T066 [P] [US3] Write a failing finalized-Snapshot integration test for Parameter, accuracy, Dataset, and best-step Metric reads in `backend/tests/integration/test_snapshot_comparison.py`; 対応: US3; 依存: T008-T019, T063; 検証: before T069-T074, `cd backend && uv run pytest tests/integration/test_snapshot_comparison.py` fails for missing comparison services and endpoints.
- [ ] T067 [P] [US3] Write failing Comparison and BestStepMetrics OpenAPI contract tests in `backend/tests/contract/test_comparison_contract.py`; 対応: US3; 依存: T008-T019, T063; 検証: before T072-T074, `cd backend && uv run pytest tests/contract/test_comparison_contract.py` fails for incomplete response contracts.
- [ ] T068 [P] [US3] Write a failing available, unavailable, percentage-format, and Dataset-status rendering test in `frontend/src/features/evolution-steps/ComparisonPanel.test.tsx`; 対応: US3; 依存: T006, T063; 検証: before T075-T079, `cd frontend && npm test -- --run src/features/evolution-steps/ComparisonPanel.test.tsx` fails because comparison UI is absent.

### Implementation for User Story 3

- [ ] T069 [US3] Implement Parameter union and Dataset Input pairing/difference functions in `backend/app/domain/differences.py`; 対応: US3; 依存: T064; 検証: `cd backend && uv run pytest tests/unit/domain/test_parameter_and_dataset_differences.py` passes, including `changed`, `parent_only`, `result_only`, and unavailable cases.
- [ ] T070 [US3] Implement full comparison assembly, fixed unavailable-reason precedence, and summary reuse in `backend/app/services/comparison_service.py`; 対応: US3; 依存: T056, T065, T069; 検証: `cd backend && uv run pytest tests/unit/domain/test_comparison_availability.py` passes with mutually exclusive status/reason fields.
- [ ] T071 [US3] Implement persisted best-step Metric reads and pending/accuracy-missing state mapping in `backend/app/services/best_step_metrics_service.py`; 対応: US3; 依存: T029, T033, T066; 検証: the integration test returns only Metrics recorded at the selected best-accuracy step.
- [ ] T072 [US3] Define Comparison, accuracy, Dataset, and BestStepMetrics response schemas in `backend/app/api/schemas/comparison.py`; 対応: US3; 依存: T067, T070, T071; 検証: schema serialization preserves ratios, signed steps, explicit `null`s, and allowed reason enums.
- [ ] T073 [P] [US3] Add the GET `/evolution-steps/{evolutionStepId}/comparison` route in `backend/app/api/routes/evolution_steps.py`; 対応: US3; 依存: T070, T072; 検証: comparison portions of `cd backend && uv run pytest tests/integration/test_snapshot_comparison.py tests/contract/test_comparison_contract.py` pass.
- [ ] T074 [P] [US3] Replace the best-step placeholder with GET `/runs/{runId}/best-step-metrics` in `backend/app/api/routes/runs.py`; 対応: US3; 依存: T071, T072; 検証: best-step Metric portions of `cd backend && uv run pytest tests/integration/test_snapshot_comparison.py tests/contract/test_comparison_contract.py` pass.
- [ ] T075 [P] [US3] Add typed comparison retrieval and response types in `frontend/src/api/evolutionSteps.ts`; 対応: US3; 依存: T067, T073; 検証: mock responses distinguish unavailable comparison, accuracy, and Dataset reasons.
- [ ] T076 [P] [US3] Add typed best-step Metric retrieval and response types in `frontend/src/api/runs.ts`; 対応: US3; 依存: T067, T074; 検証: mock responses retain negative `bestAccuracyStep` values and empty unavailable lists.
- [ ] T077 [US3] Implement Parameter, accuracy, and Dataset difference rendering in `frontend/src/features/evolution-steps/ComparisonPanel.tsx`; 対応: US3; 依存: T068, T075; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/ComparisonPanel.test.tsx` passes without calling Dataset metadata changes row additions or deletions.
- [ ] T078 [US3] Implement selected best-step Metric status and item rendering in `frontend/src/features/evolution-steps/BestStepMetrics.tsx`; 対応: US3; 依存: T076; 検証: captured, pending, and accuracy-missing values render from local API data only.
- [ ] T079 [US3] Integrate comparison and lazy best-step Metric loads into `frontend/src/pages/EvolutionStepDetailPage.tsx`; 対応: US3; 依存: T047, T077, T078; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/ComparisonPanel.test.tsx src/features/evolution-steps/EvolutionStepDetailPage.test.tsx` passes.

**Checkpoint**: US3 reads immutable Snapshots only and makes partial comparison availability explicit instead of representing unavailable data as unchanged.

---

## Phase 6: User Story 4 - Lineageを確認する (Priority: P4)

**Goal**: Reconstruct current Lineage around a selected Evolution Step and display ordered ancestors, descendants, branches, and upstream boundaries.

**Independent Test**: Seed a branched multi-generation set of current Run links, select a middle Step, and confirm nearest-first ancestors, breadth-first descendants ordered by Step ID, distances, and parent-Step identifiers.

### Tests for User Story 4 - Write and Run Red First

- [ ] T080 [P] [US4] Write failing nearest-first ancestor, breadth-first descendant, branch-order, and upstream-boundary unit tests in `backend/tests/unit/domain/test_lineage_traversal.py`; 対応: US4; 依存: T008-T019, T048; 検証: before T084, `cd backend && uv run pytest tests/unit/domain/test_lineage_traversal.py` fails for missing traversal behavior.
- [ ] T081 [P] [US4] Write a failing current-links-only multi-generation lineage integration test in `backend/tests/integration/test_lineage.py`; 対応: US4; 依存: T008-T019, T048; 検証: before T085-T088, `cd backend && uv run pytest tests/integration/test_lineage.py` fails for missing persisted graph reads.
- [ ] T082 [P] [US4] Write a failing Lineage endpoint contract test for distances, parent Evolution Step IDs, and boundary Run representation in `backend/tests/contract/test_lineage_contract.py`; 対応: US4; 依存: T008-T019, T048; 検証: before T087-T088, `cd backend && uv run pytest tests/contract/test_lineage_contract.py` fails for absent endpoint output.
- [ ] T083 [P] [US4] Write a failing ancestor, descendant, branch, root, and external-boundary rendering test in `frontend/src/features/evolution-steps/LineagePanel.test.tsx`; 対応: US4; 依存: T006, T048; 検証: before T089-T091, `cd frontend && npm test -- --run src/features/evolution-steps/LineagePanel.test.tsx` fails because the panel is absent.

### Implementation for User Story 4

- [ ] T084 [US4] Extend the shared graph rules with deterministic ancestor and descendant traversal functions in `backend/app/domain/lineage.py`; 対応: US4; 依存: T030, T080; 検証: `cd backend && uv run pytest tests/unit/domain/test_lineage_traversal.py` passes for all order and boundary cases.
- [ ] T085 [P] [US4] Add current-link ancestor and descendant lookup queries in `backend/app/infrastructure/repositories.py`; 対応: US4; 依存: T033, T081; 検証: queries exclude stale history links and return enough data to identify direct parent Steps.
- [ ] T086 [US4] Implement selected-centered Lineage assembly in `backend/app/services/lineage_service.py`; 対応: US4; 依存: T084, T085, T081; 検証: `cd backend && uv run pytest tests/integration/test_lineage.py` passes for branched and external-boundary graphs.
- [ ] T087 [US4] Define selected, ancestor, and descendant Lineage response schemas in `backend/app/api/schemas/lineage.py`; 対応: US4; 依存: T082, T086; 検証: response schemas require `distanceFromSelected` and `parentEvolutionStepId` for every returned Step.
- [ ] T088 [US4] Add GET `/evolution-steps/{evolutionStepId}/lineage` to `backend/app/api/routes/evolution_steps.py`; 対応: US4; 依存: T082, T086, T087; 検証: `cd backend && uv run pytest tests/integration/test_lineage.py tests/contract/test_lineage_contract.py` passes.
- [ ] T089 [US4] Add typed Lineage retrieval and response types in `frontend/src/api/evolutionSteps.ts`; 対応: US4; 依存: T082, T088; 検証: mock requests preserve ordered arrays and nullable boundary fields.
- [ ] T090 [US4] Implement the selected-centered ancestor and descendant display in `frontend/src/features/evolution-steps/LineagePanel.tsx`; 対応: US4; 依存: T083, T089; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/LineagePanel.test.tsx` passes for root, branch, and external-boundary states.
- [ ] T091 [US4] Add Lineage loading and display to `frontend/src/pages/EvolutionStepDetailPage.tsx`; 対応: US4; 依存: T079, T090; 検証: the detail page can render comparison and Lineage failures independently without suppressing saved detail.

**Checkpoint**: US4 reconstructs the current graph without a stored Lineage table and remains independently verifiable from seeded current links.

---

## Phase 7: Overall Integration and Cross-Cutting Verification

**Purpose**: Confirm the documented HTTP boundary, critical browser journey, performance constraints, and reproducible operating instructions across all completed stories.

- [ ] T092 [P] Write and run an OpenAPI response-conformance suite against every implemented route in `backend/tests/contract/test_openapi_conformance.py`; 対応: 全体統合 (US1-US4); 依存: T040, T059, T073, T074, T088; 検証: `cd backend && uv run pytest tests/contract/test_openapi_conformance.py` initially exposes any contract drift, then passes against `specs/001-experiment-evolution/contracts/openapi.yaml`.
- [ ] T093 [P] Configure Playwright's web-server, trace, and screenshot behavior in `frontend/playwright.config.ts`; 対応: 全体統合 (US1-US4); 依存: T002, T048, T063, T079, T091; 検証: `cd frontend && npm run test:e2e -- --list` discovers the configured browser project without starting an uncontrolled server.
- [ ] T094 Create the critical create-and-attach browser flow with one visible validation failure in `frontend/e2e/create-and-attach.spec.ts`; 対応: 全体統合 (US1-US4); 依存: T093, T048, T091; 検証: `cd frontend && npm run test:e2e -- create-and-attach` creates a Step, attaches a Run, verifies its detail, and retains trace/screenshot artifacts on failure.
- [ ] T095 [P] Add seeded read-performance checks for the list, comparison, detail, and 100-Step Lineage budgets in `backend/tests/integration/test_read_performance.py`; 対応: 全体統合 (US1-US4); 依存: T059, T070, T086; 検証: `cd backend && uv run pytest tests/integration/test_read_performance.py` verifies the stated 500 ms and 1 s targets against the dedicated test database.
- [ ] T096 Update actual setup, migration, test, MLflow fixture, and failure-triage commands in `README.md` and `specs/001-experiment-evolution/quickstart.md`; 対応: 全体統合 (US1-US4); 依存: T092-T095; 検証: a clean environment can follow both documents to start MySQL, migrate, run backend/frontend tests, and execute the E2E flow without undocumented credentials.
- [ ] T097 Execute the final backend, frontend, E2E, lint, and quickstart verification matrix recorded in `specs/001-experiment-evolution/quickstart.md`; 対応: 全体統合 (US1-US4); 依存: T092-T096; 検証: `cd backend && uv run pytest && uv run ruff check .`, `cd frontend && npm test && npm run build && npm run test:e2e`, and the documented quickstart scenario all pass with results attached to the implementation review.

---

## Dependencies and Execution Order

### Phase Dependencies

- Phase 1 Setup has no prerequisites.
- Phase 2 Foundational depends on Phase 1 and blocks all product behavior.
- US1 depends on Phase 2 and is the MVP implementation increment.
- US2 depends on US1 because it lists and summarizes persisted Evolution Steps.
- US3 depends on US2's shared compact comparison calculation and US1's captured Snapshots.
- US4 depends on US1's current link and Run-reference behavior, but can proceed in parallel with US2 after US1 when separate contributors are available.
- Phase 7 depends on all selected story checkpoints.

### User Story Dependency Graph

```text
Setup -> Foundational -> US1 -> US2 -> US3 -> Overall Integration
                         \-> US4 -----------/
```

### Parallel Opportunities

- Setup: T001, T002, T003, and T004 have no mutual file conflicts; T003 and T004 are explicitly parallel.
- Foundational: T009, T010, and T011 are independent red tests after fixture setup; T017 can proceed once T012 is done.
- US1: T020-T027 are parallel red tests. T028-T031 and T033 are independently implementable after their named tests. T036/T037, T038/T039, and T041/T042 are paired parallel work.
- US2: T049-T054 are parallel red tests, followed by T055/T056 and T061 where dependencies permit.
- US3: T064-T068 are parallel red tests; T073/T074 and T075/T076 can run in parallel after their shared contracts are ready.
- US4: T080-T083 are parallel red tests; T085 can be implemented alongside T084 after their independent tests are written.
- Integration: T092, T093, and T095 can start in parallel after the relevant story checkpoints; T094 follows T093.

## Parallel Execution Examples

### User Story 1

```text
Task: T020 through T027 - write all focused red tests in their separate backend/frontend files
Task: T028 - backend/app/domain/evolution_step.py
Task: T029 - backend/app/domain/run_snapshot.py
Task: T030 - backend/app/domain/lineage.py
Task: T031 - backend/app/infrastructure/mlflow_gateway.py
```

### User Story 2

```text
Task: T049 through T054 - write pagination, summary, API, and UI red tests
Task: T055 - backend/app/domain/pagination.py
Task: T056 - backend/app/domain/comparison.py
Task: T061 - frontend/src/features/evolution-steps/RunSyncStatus.tsx
```

### User Story 3

```text
Task: T064 through T068 - write domain, integration, contract, and UI red tests
Task: T073 - comparison API route
Task: T074 - best-step Metrics API route
Task: T075 - Evolution Step comparison client
Task: T076 - Run best-step Metrics client
```

### User Story 4

```text
Task: T080 through T083 - write traversal, integration, contract, and UI red tests
Task: T084 - backend/app/domain/lineage.py traversal logic
Task: T085 - backend/app/infrastructure/repositories.py graph reads
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2, including their verification commands.
2. Complete T020-T048 as a red-to-green vertical slice for US1.
3. Run the US1 unit, integration, contract, and component checks before treating the MVP as reviewable.
4. Demonstrate creation, attachment, synchronization, and saved-detail behavior with the MLflow fake before beginning broader views.

### Incremental Delivery

1. Deliver US1 for durable Evolution Step creation and Run attachment.
2. Add US2 for browsing and finding stored work with stable pagination.
3. Add US3 for evidence-based comparisons from immutable Snapshots.
4. Add US4 for current-link Lineage tracing.
5. Run Phase 7 once all desired stories are integrated.

### Test-First Completion Rule

- Every task in a `Tests for User Story` subsection is written and executed red before its dependent implementation task starts.
- Each implementation task is complete only when its named focused verification passes.
- A story checkpoint requires its unit, integration, contract, and applicable frontend tests to pass together.

## Format Validation

All 97 tasks use the required `- [ ] T### [P?] [US?] Description` checklist format. User-story tasks carry exactly one `[US1]` through `[US4]` label; setup, foundational, and integration tasks use no user-story label. Every task includes target paths, a corresponding story scope, explicit dependencies, and a verification method.
