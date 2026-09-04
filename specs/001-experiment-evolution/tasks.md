# Tasks: Mondel Initial MVP

**Input**: Design documents from `specs/001-experiment-evolution/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/openapi.yaml`, `quickstart.md`, and `.specify/memory/constitution.md`

**Tests**: Required. Constitution Principle IV, Test-First Verification, requires each behavior-changing implementation task to be preceded by a focused test task that is run red before its implementation begins. Automated tests remain in the repository as regression tests after they turn green; temporary diagnostics must be identified separately.

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

- [ ] T008 [P] Write failing configuration tests for required variables, invalid database URLs, and explicit test-database selection in `backend/tests/unit/test_config.py`; 対応: 共通 (US1-US4); 依存: T001, T003, T005; 検証: `cd backend && uv run pytest tests/unit/test_config.py` reaches the configuration assertions and fails because validated settings are not implemented.
- [ ] T009 Implement validated environment loading and application settings in `backend/app/config.py`; 対応: 共通 (US1-US4); 依存: T008; 検証: `cd backend && uv run pytest tests/unit/test_config.py` passes for required, invalid, and test-database cases.
- [ ] T010 [P] Write failing database Session lifecycle and transaction commit/rollback tests, with the minimum reusable MySQL test connection setup, in `backend/tests/conftest.py` and `backend/tests/integration/test_database.py`; 対応: 共通 (US1-US4); 依存: T004, T005, T009; 検証: `cd backend && uv run pytest tests/integration/test_database.py` reaches the lifecycle assertions and fails because the Session and transaction helpers are not implemented.
- [ ] T011 Implement the synchronous SQLAlchemy engine, one-Session-per-request dependency, and transaction commit/rollback helpers in `backend/app/infrastructure/database.py`; 対応: 共通 (US1-US4); 依存: T010; 検証: `cd backend && uv run pytest tests/integration/test_database.py` passes without sharing uncommitted state between tests.
- [ ] T012 [P] Write failing model-metadata and migration integration tests for all normalized tables, indexes, constraints, and the singleton lineage guard in `backend/tests/integration/test_initial_schema.py`; 対応: 共通 (US1-US4); 依存: T010, T011; 検証: `cd backend && uv run pytest tests/integration/test_initial_schema.py` reaches schema assertions and fails because the models and migration are absent.
- [ ] T013 Model `evolution_step`, `lineage_mutation_guard`, `run_reference`, `run_snapshot`, `run_parameter`, `best_step_metric`, `dataset_input`, and `evolution_step_history` in `backend/app/infrastructure/models.py`; 対応: 共通 (US1-US4); 依存: T011, T012; 検証: `cd backend && uv run pytest tests/integration/test_initial_schema.py -k model_metadata` passes while migration-backed cases remain red.
- [ ] T014 Initialize Alembic configuration and metadata discovery in `backend/alembic.ini` and `backend/migrations/env.py`; 対応: 共通 (US1-US4); 依存: T013; 検証: `cd backend && uv run alembic revision --autogenerate -m smoke --rev-id smoke` detects the model metadata, after which the temporary revision is removed.
- [ ] T015 Create the initial MySQL schema and singleton lineage guard seed in `backend/migrations/versions/001_initial_schema.py`; 対応: 共通 (US1-US4); 依存: T013, T014; 検証: `cd backend && uv run pytest tests/integration/test_initial_schema.py` passes after applying migrations to the dedicated test database.
- [ ] T016 [P] Write failing direct-handler and HTTP contract tests for the API error envelope and trace ID, with the minimum reusable FastAPI TestClient fixture, in `backend/tests/conftest.py` and `backend/tests/contract/test_error_responses.py`; 対応: 共通 (US1-US4); 依存: T005, T009; 検証: `cd backend && uv run pytest tests/contract/test_error_responses.py` reaches response assertions and fails because the handlers and their FastAPI registration are absent.
- [ ] T017 [P] Implement structured API exceptions, `code`/`message`/`traceId` responses, and trace-ID logging in `backend/app/api/errors.py`; 対応: 共通 (US1-US4); 依存: T016; 検証: `cd backend && uv run pytest tests/contract/test_error_responses.py -k direct_handler` passes for direct handler serialization while HTTP registration cases remain red until T018.
- [ ] T018 Create the `/api/v1` router registration, request-Session lifecycle, and application-level exception and trace middleware registration in `backend/app/api/router.py` and `backend/main.py`; 対応: 共通 (US1-US4); 依存: T011, T015, T017; 検証: `cd backend && uv run pytest tests/contract/test_error_responses.py` passes and `GET /api/v1/unknown` returns the documented error envelope with a trace ID.
- [ ] T019 [P] Write a failing typed-fetch success, API-error, and network-error test in `frontend/src/api/client.test.ts`; 対応: 共通 (US1-US4); 依存: T006; 検証: before T020, `cd frontend && npm test -- --run src/api/client.test.ts` fails because the shared client is absent.
- [ ] T020 Implement the typed browser `fetch` wrapper with JSON parsing and typed API errors in `frontend/src/api/client.ts`; 対応: 共通 (US1-US4); 依存: T019; 検証: `cd frontend && npm test -- --run src/api/client.test.ts` passes for success, server error, and network failure cases.

**Checkpoint**: Configuration, database transactions, migrations, versioned API errors, and the typed HTTP client each have focused red-to-green evidence. All automated tests remain in the repository as regression tests.

---
## Phase 3: User Story 1 - Evolution Stepを定義してRunを紐付ける (Priority: P1)

**Goal**: Create and edit an Evolution Step, select valid MLflow Runs, preserve change history, and show locally saved details while synchronizing linked Run state.

**Independent Test**: With MLflow test fixtures, create a Step with purpose and hypothesis, optionally choose a parent Run and change description, attach a distinct result Run, then verify the detail page shows saved text, Run reference state, Snapshot state, and post-creation history.

### Tests for User Story 1 - Write and Run Red First

- [ ] T021 [P] [US1] Write failing domain tests for non-blank fields, nullable change descriptions, signed Metric steps, and canonical terminal Snapshot selection in `backend/tests/unit/domain/test_evolution_step_and_snapshot_rules.py`; 対応: US1; 依存: T008-T020; 検証: before T032-T033, `cd backend && uv run pytest tests/unit/domain/test_evolution_step_and_snapshot_rules.py` fails for the unimplemented rules.
- [ ] T022 [P] [US1] Write failing duplicate-result, equal-parent/result, and multi-generation cycle validation tests in `backend/tests/unit/domain/test_run_link_validation.py`; 対応: US1; 依存: T008-T020; 検証: before T034, `cd backend && uv run pytest tests/unit/domain/test_run_link_validation.py` fails for link validation.
- [ ] T023 [P] [US1] Write failing MLflow candidate-search tests that distinguish Run lifecycle from execution status and exclude deleted-lifecycle Runs, plus current-Run lookup and terminal/active capture payload tests, in `backend/tests/unit/infrastructure/test_mlflow_run_gateway.py`, with reusable active/deleted lifecycle MLflow fakes in `backend/tests/fakes/mlflow.py`; 対応: US1; 依存: T008-T020; 検証: before T035-T037, `cd backend && uv run pytest tests/unit/infrastructure/test_mlflow_run_gateway.py` fails for the missing gateway, lifecycle filtering, and adapters.
- [ ] T024 [P] [US1] Write failing Evolution Step repository and create/patch/history integration tests covering no-op updates, link changes, unlinking, and `409` result ownership in `backend/tests/integration/test_evolution_step_mutations.py`; 対応: US1; 依存: T008-T020; 検証: before T038, T040, and T041, `cd backend && uv run pytest tests/integration/test_evolution_step_mutations.py` fails for the missing repository and use cases.
- [ ] T025 [P] [US1] Write a failing Run repository and active-to-terminal synchronization integration test with immutable Snapshot assertions in `backend/tests/integration/test_run_link_and_sync.py`; 対応: US1; 依存: T008-T020; 検証: before T039 and T042, `cd backend && uv run pytest tests/integration/test_run_link_and_sync.py` fails for missing persistence and synchronization behavior.
- [ ] T026 [P] [US1] Write failing OpenAPI contract tests for Run search, Evolution Step create/read/patch, validation, conflict, and MLflow `502` responses in `backend/tests/contract/test_runs_and_evolution_steps.py`; 対応: US1; 依存: T008-T020; 検証: before T043-T047, `cd backend && uv run pytest tests/contract/test_runs_and_evolution_steps.py` fails for absent endpoints.
- [ ] T027 [P] [US1] Write failing form tests for required fields, optional change description, Run selection, and backend validation feedback in `frontend/src/features/evolution-steps/EvolutionStepForm.test.tsx`; 対応: US1; 依存: T006, T020; 検証: before T050-T052, `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepForm.test.tsx` fails because the form is absent.
- [ ] T028 [P] [US1] Write failing local-detail, pending-Snapshot, captured-Snapshot, ordered-history, and non-blocking-sync-warning tests in `frontend/src/features/evolution-steps/EvolutionStepDetailPage.test.tsx`; 対応: US1; 依存: T006, T020; 検証: before T053-T055, `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepDetailPage.test.tsx` fails because the detail experience is absent.

- [ ] T029 [P] [US1] Write a failing typed Evolution Step API-client request and error-mapping test in `frontend/src/api/evolutionSteps.test.ts`; 対応: US1; 依存: T006, T020; 検証: before T048, `cd frontend && npm test -- --run src/api/evolutionSteps.test.ts` fails because the feature-specific API functions are absent.
- [ ] T030 [P] [US1] Write a failing typed Run API-client request, opaque-page-token, and upstream-error-mapping test in `frontend/src/api/runs.test.ts`; 対応: US1; 依存: T006, T020; 検証: before T049, `cd frontend && npm test -- --run src/api/runs.test.ts` fails because the feature-specific API functions are absent.
- [ ] T031 [P] [US1] Write a failing create-page submission, conflict-feedback, and successful-navigation test in `frontend/src/pages/EvolutionStepCreatePage.test.tsx`; 対応: US1; 依存: T006, T020; 検証: before T052, `cd frontend && npm test -- --run src/pages/EvolutionStepCreatePage.test.tsx` fails because the create page is absent.

### Implementation for User Story 1

- [ ] T032 [P] [US1] Implement Evolution Step value objects and purpose/hypothesis/change-description validation in `backend/app/domain/evolution_step.py`; 対応: US1; 依存: T021; 検証: `cd backend && uv run pytest tests/unit/domain/test_evolution_step_and_snapshot_rules.py -k 'blank or change_description'` passes.
- [ ] T033 [P] [US1] Implement Metric canonicalization and immutable Snapshot payload selection in `backend/app/domain/run_snapshot.py`; 対応: US1; 依存: T021; 検証: `cd backend && uv run pytest tests/unit/domain/test_evolution_step_and_snapshot_rules.py -k 'metric or snapshot'` passes, including signed and tied steps.
- [ ] T034 [P] [US1] Implement proposed-link validation and deterministic DFS cycle detection in `backend/app/domain/lineage.py`; 対応: US1; 依存: T022; 検証: `cd backend && uv run pytest tests/unit/domain/test_run_link_validation.py` passes for duplicate, same-Run, and cyclic links.
- [ ] T035 [P] [US1] Define MLflow search/loader gateway protocols and normalized Run, Metric, and Dataset transfer types in `backend/app/infrastructure/mlflow_gateway.py`; 対応: US1; 依存: T023; 検証: gateway unit tests can inject in-memory search and loader fakes without importing the MLflow client.
- [ ] T036 [P] [US1] Implement the MLflow Run-candidate search adapter with active-experiment lookup, explicit `run_view_type=ViewType.ACTIVE_ONLY` Run filtering, case-insensitive filtering, stable ordering, and opaque paging in `backend/app/infrastructure/mlflow_run_search.py`; 対応: US1; 依存: T023, T035; 検証: `cd backend && uv run pytest tests/unit/infrastructure/test_mlflow_run_gateway.py -k 'candidate or search or paging or lifecycle'` passes and no deleted-lifecycle Run is returned.
- [ ] T037 [P] [US1] Implement the MLflow selected-Run loader for current metadata and terminal Snapshot capture data in `backend/app/infrastructure/mlflow_run_loader.py`; 対応: US1; 依存: T023, T033, T035; 検証: `cd backend && uv run pytest tests/unit/infrastructure/test_mlflow_run_gateway.py -k 'lookup or active or terminal or capture'` passes.
- [ ] T038 [P] [US1] Implement Evolution Step, change-history, and lineage-guard persistence in `backend/app/infrastructure/evolution_step_repository.py`; 対応: US1; 依存: T013, T015, T024; 検証: `cd backend && uv run pytest tests/integration/test_evolution_step_mutations.py -k repository` passes for current links, explicit `NULL` values, history ordering, and guard-row locking.
- [ ] T039 [P] [US1] Implement Run Reference, immutable Snapshot, Parameter, best-step Metric, and Dataset Input persistence in `backend/app/infrastructure/run_repository.py`; 対応: US1; 依存: T013, T015, T025; 検証: `cd backend && uv run pytest tests/integration/test_run_link_and_sync.py -k repository` passes for pending references, atomic capture, and immutable reuse.
- [ ] T040 [US1] Implement the atomic Evolution Step create use case with selected-Run prevalidation, result ownership, same-Run rejection, and cycle checks in `backend/app/services/evolution_step_service.py`; 対応: US1; 依存: T032, T034, T037-T039, T024; 検証: `cd backend && uv run pytest tests/integration/test_evolution_step_mutations.py -k create` passes without initial history rows or partial writes.
- [ ] T041 [US1] Implement the atomic Evolution Step patch use case with no-op detection, Run link/unlink handling, history appends, result ownership, and cycle checks in `backend/app/services/evolution_step_service.py`; 対応: US1; 依存: T040, T024; 検証: `cd backend && uv run pytest tests/integration/test_evolution_step_mutations.py -k 'patch or history or no_op or conflict'` passes without partial writes.
- [ ] T042 [P] [US1] Implement local Run synchronization, active-state retention, one-time terminal Snapshot capture, immutable recapture protection, and MLflow-failure rollback in `backend/app/services/run_sync_service.py`; 対応: US1; 依存: T033, T037, T039, T025; 検証: `cd backend && uv run pytest tests/integration/test_run_link_and_sync.py` passes for active, terminal, repeat-sync, and MLflow-failure cases.
- [ ] T043 [P] [US1] Define create, patch, detail, history, and linked-Run request/response schemas in `backend/app/api/schemas/evolution_steps.py`; 対応: US1; 依存: T026, T041; 検証: schema serialization emits camel-case fields and explicit JSON `null` values required by `contracts/openapi.yaml`.
- [ ] T044 [P] [US1] Define Run search, synchronization, and Snapshot-state response schemas in `backend/app/api/schemas/runs.py`; 対応: US1; 依存: T026, T042; 検証: schema serialization represents pending and captured Snapshot states consistently.
- [ ] T045 [P] [US1] Implement Evolution Step create, read, and patch routes with request validation and error mapping in `backend/app/api/routes/evolution_steps.py`; 対応: US1; 依存: T041, T043; 検証: the Evolution Step portions of `cd backend && uv run pytest tests/contract/test_runs_and_evolution_steps.py` pass.
- [ ] T046 [P] [US1] Implement MLflow Run search and synchronization routes in `backend/app/api/routes/runs.py`; 対応: US1; 依存: T036, T042, T044; 検証: the Run-search and sync portions of `cd backend && uv run pytest tests/contract/test_runs_and_evolution_steps.py` pass. The best-step Metrics route is added only when US3 is implemented in T082.
- [ ] T047 [US1] Register Evolution Step and Run routers under `/api/v1` in `backend/app/api/router.py`; 対応: US1; 依存: T018, T045, T046; 検証: `cd backend && uv run pytest tests/contract/test_runs_and_evolution_steps.py` passes end to end.
- [ ] T048 [P] [US1] Add typed Evolution Step create, read, and patch API functions in `frontend/src/api/evolutionSteps.ts`; 対応: US1; 依存: T020, T026, T029; 検証: `cd frontend && npm test -- --run src/api/evolutionSteps.test.ts` passes with the documented URLs, methods, request bodies, and typed conflict errors.
- [ ] T049 [P] [US1] Add typed Run-search and synchronization API functions in `frontend/src/api/runs.ts`; 対応: US1; 依存: T020, T026, T030; 検証: `cd frontend && npm test -- --run src/api/runs.test.ts` passes while retaining opaque page tokens and classifying `502` as an upstream synchronization failure.
- [ ] T050 [US1] Implement pageable, searchable, distinguishable MLflow Run selection in `frontend/src/features/evolution-steps/RunPicker.tsx`; 対応: US1; 依存: T049, T027; 検証: the form test can choose duplicate Run names by Run ID and load a second candidate page.
- [ ] T051 [US1] Implement the accessible Evolution Step form with local validation, parent/result selection, and submit feedback in `frontend/src/features/evolution-steps/EvolutionStepForm.tsx`; 対応: US1; 依存: T048, T050, T027; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepForm.test.tsx` passes.
- [ ] T052 [US1] Implement the create-page submission and navigation flow in `frontend/src/pages/EvolutionStepCreatePage.tsx`; 対応: US1; 依存: T031, T051; 検証: `cd frontend && npm test -- --run src/pages/EvolutionStepCreatePage.test.tsx` passes for successful detail navigation and actionable `409` feedback.
- [ ] T053 [US1] Implement saved text, Run reference/Snapshot state, and ordered history rendering in `frontend/src/features/evolution-steps/EvolutionStepDetail.tsx`; 対応: US1; 依存: T048, T049, T028; 検証: detail tests render pending and captured states, nullable history values, and no full Metric history.
- [ ] T054 [US1] Implement local-first detail loading, per-Run automatic synchronization, reload-on-success, and non-blocking warning handling in `frontend/src/pages/EvolutionStepDetailPage.tsx`; 対応: US1; 依存: T049, T053, T028; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepDetailPage.test.tsx` passes without hiding locally saved detail on sync failure.
- [ ] T055 [US1] Add create and detail navigation routes and connect the application bootstrap in `frontend/src/routes/AppRoutes.tsx` and `frontend/src/main.tsx`; 対応: US1; 依存: T052, T054; 検証: `cd frontend && npm run build` completes and direct navigation to create and detail routes resolves. The list route is added with the US2 list page in T070.
**Checkpoint**: US1 is independently demonstrable with MLflow fakes and has red-to-green unit, integration, contract, and component-test evidence.

---

## Phase 4: User Story 2 - Evolution Stepの全体像を確認する (Priority: P2)

**Goal**: Show a stable, token-paginated Evolution Step list with comparison summaries and preserve detail readability during synchronization failures.

**Independent Test**: Seed more than 20 Steps and inspect two list pages. Verify newest-first ordering, no duplicated boundary item, the correct compact comparison state, and navigation to a saved detail view.

### Tests for User Story 2 - Write and Run Red First

- [ ] T056 [P] [US2] Write a failing keyset token encode/decode and stable-order unit test in `backend/tests/unit/domain/test_evolution_step_pagination.py`; 対応: US2; 依存: T008-T020, T055; 検証: before T062, `cd backend && uv run pytest tests/unit/domain/test_evolution_step_pagination.py` fails for absent pagination helpers.
- [ ] T057 [P] [US2] Write a failing compact comparison-summary state and reason-code unit test in `backend/tests/unit/domain/test_comparison_summary.py`; 対応: US2; 依存: T008-T020, T055; 検証: before T063, `cd backend && uv run pytest tests/unit/domain/test_comparison_summary.py` fails for missing summary logic.
- [ ] T058 [P] [US2] Write a failing 20-item keyset-list integration test including same-timestamp and newly-inserted-row cases in `backend/tests/integration/test_evolution_step_list.py`; 対応: US2; 依存: T008-T020, T055; 検証: before T064-T066, `cd backend && uv run pytest tests/integration/test_evolution_step_list.py` fails for missing list behavior.
- [ ] T059 [P] [US2] Write a failing list endpoint contract test for summary fields, opaque tokens, and malformed-token `422` behavior in `backend/tests/contract/test_evolution_step_list_contract.py`; 対応: US2; 依存: T008-T020, T055; 検証: before T066, `cd backend && uv run pytest tests/contract/test_evolution_step_list_contract.py` fails for the incomplete GET contract.
- [ ] T060 [P] [US2] Write a failing loading, empty, paged, summary-state, and detail-navigation test in `frontend/src/features/evolution-steps/EvolutionStepListPage.test.tsx`; 対応: US2; 依存: T006, T055; 検証: before T067, T069-T070, `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepListPage.test.tsx` fails because the list page is absent.
- [ ] T061 [P] [US2] Write a failing successful-sync, pending-sync, and retained-detail warning-state test in `frontend/src/features/evolution-steps/RunSyncStatus.test.tsx`; 対応: US2; 依存: T006, T055; 検証: before T068, `cd frontend && npm test -- --run src/features/evolution-steps/RunSyncStatus.test.tsx` fails because reusable sync feedback is absent.

### Implementation for User Story 2

- [ ] T062 [P] [US2] Implement opaque `(created_at, id)` cursor encoding, validation, and keyset predicates in `backend/app/domain/pagination.py`; 対応: US2; 依存: T056; 検証: `cd backend && uv run pytest tests/unit/domain/test_evolution_step_pagination.py` passes for valid and malformed tokens.
- [ ] T063 [P] [US2] Implement compact availability, Parameter-count, accuracy, and Dataset summary calculation in `backend/app/domain/comparison.py`; 対応: US2; 依存: T057; 検証: `cd backend && uv run pytest tests/unit/domain/test_comparison_summary.py` passes with null reasons only for available states.
- [ ] T064 [US2] Add 21-row keyset reads and summary-ready Snapshot joins to `backend/app/infrastructure/evolution_step_repository.py`; 対応: US2; 依存: T038, T039, T062, T063, T058; 検証: repository queries return at most 20 records plus a next token only when the twenty-first row exists.
- [ ] T065 [US2] Implement Evolution Step list orchestration and list-item mapping in `backend/app/services/evolution_step_list_service.py`; 対応: US2; 依存: T063, T064, T058; 検証: the integration list test gets deterministic ordering and summary objects from stored data only.
- [ ] T066 [US2] Add the token-paginated GET `/evolution-steps` route to `backend/app/api/routes/evolution_steps.py`; 対応: US2; 依存: T059, T065; 検証: `cd backend && uv run pytest tests/integration/test_evolution_step_list.py tests/contract/test_evolution_step_list_contract.py` passes.
- [ ] T067 [US2] Add typed paginated list retrieval and page-token types in `frontend/src/api/evolutionSteps.ts`; 対応: US2; 依存: T048, T059, T066; 検証: mocked list requests retain the server-issued token without exposing it as a text input.
- [ ] T068 [P] [US2] Implement compact Run synchronization progress, success, pending, and non-blocking failure feedback in `frontend/src/features/evolution-steps/RunSyncStatus.tsx`; 対応: US2; 依存: T061, T054; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/RunSyncStatus.test.tsx` passes.
- [ ] T069 [US2] Implement loading, empty, list-summary, next-page, and selected-Step behavior in `frontend/src/features/evolution-steps/EvolutionStepListPage.tsx`; 対応: US2; 依存: T060, T067; 検証: the list-page test passes for empty and multi-page datasets without duplicated rows.
- [ ] T070 [US2] Wire the list page and reusable synchronization status into application routes and detail composition in `frontend/src/pages/EvolutionStepListPage.tsx` and `frontend/src/pages/EvolutionStepDetailPage.tsx`; 対応: US2; 依存: T054, T068, T069; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/EvolutionStepListPage.test.tsx src/features/evolution-steps/RunSyncStatus.test.tsx` passes.

**Checkpoint**: US2 can be tested from seeded local database state; a failed MLflow synchronization never prevents list or saved-detail inspection.

---

## Phase 5: User Story 3 - 派生元との差分を振り返る (Priority: P3)

**Goal**: Return and display only meaningful Parameter, accuracy, and Dataset Input differences from finalized Snapshots with explicit unavailable reasons.

**Independent Test**: Seed finalized parent and result Snapshots with changed Parameters, repeated Metrics, and Dataset Inputs. Confirm the comparison shows additions, changes, removals, percentage-formatted accuracy delta, and only valid Dataset difference states.

### Tests for User Story 3 - Write and Run Red First

- [ ] T071 [P] [US3] Write failing Parameter and Dataset Input difference tests, including ambiguous pairing and no-row-data cases, in `backend/tests/unit/domain/test_parameter_and_dataset_differences.py`; 対応: US3; 依存: T008-T020, T070; 検証: before T077, `cd backend && uv run pytest tests/unit/domain/test_parameter_and_dataset_differences.py` fails for missing difference rules.
- [ ] T072 [P] [US3] Write failing comparison availability and unavailable-reason precedence tests in `backend/tests/unit/domain/test_comparison_availability.py`; 対応: US3; 依存: T008-T020, T070; 検証: before T078, `cd backend && uv run pytest tests/unit/domain/test_comparison_availability.py` fails for incomplete comparison state mapping.
- [ ] T073 [P] [US3] Write a failing finalized-Snapshot integration test for Parameter, accuracy, Dataset, and best-step Metric reads in `backend/tests/integration/test_snapshot_comparison.py`; 対応: US3; 依存: T008-T020, T070; 検証: before T077-T082, `cd backend && uv run pytest tests/integration/test_snapshot_comparison.py` fails for missing comparison services and endpoints.
- [ ] T074 [P] [US3] Write failing Comparison and BestStepMetrics OpenAPI contract tests in `backend/tests/contract/test_comparison_contract.py`; 対応: US3; 依存: T008-T020, T070; 検証: before T080-T082, `cd backend && uv run pytest tests/contract/test_comparison_contract.py` fails for incomplete response contracts.
- [ ] T075 [P] [US3] Write a failing available, unavailable, percentage-format, and Dataset-status rendering test in `frontend/src/features/evolution-steps/ComparisonPanel.test.tsx`; 対応: US3; 依存: T006, T070; 検証: before T083-T087, `cd frontend && npm test -- --run src/features/evolution-steps/ComparisonPanel.test.tsx` fails because comparison UI is absent.

- [ ] T076 [P] [US3] Write a failing captured, pending, accuracy-missing, and Metric-item rendering test in `frontend/src/features/evolution-steps/BestStepMetrics.test.tsx`; 対応: US3; 依存: T006, T070; 検証: before T086, `cd frontend && npm test -- --run src/features/evolution-steps/BestStepMetrics.test.tsx` fails because the component is absent.

### Implementation for User Story 3

- [ ] T077 [US3] Implement Parameter union and Dataset Input pairing/difference functions in `backend/app/domain/differences.py`; 対応: US3; 依存: T071; 検証: `cd backend && uv run pytest tests/unit/domain/test_parameter_and_dataset_differences.py` passes, including `changed`, `parent_only`, `result_only`, and unavailable cases.
- [ ] T078 [US3] Implement full comparison assembly, fixed unavailable-reason precedence, and summary reuse in `backend/app/services/comparison_service.py`; 対応: US3; 依存: T063, T072, T077; 検証: `cd backend && uv run pytest tests/unit/domain/test_comparison_availability.py` passes with mutually exclusive status/reason fields.
- [ ] T079 [US3] Implement persisted best-step Metric reads and pending/accuracy-missing state mapping in `backend/app/services/best_step_metrics_service.py`; 対応: US3; 依存: T033, T039, T073; 検証: the integration test returns only Metrics recorded at the selected best-accuracy step.
- [ ] T080 [US3] Define Comparison, accuracy, Dataset, and BestStepMetrics response schemas in `backend/app/api/schemas/comparison.py`; 対応: US3; 依存: T074, T078, T079; 検証: schema serialization preserves ratios, signed steps, explicit `null`s, and allowed reason enums.
- [ ] T081 [P] [US3] Add the GET `/evolution-steps/{evolutionStepId}/comparison` route in `backend/app/api/routes/evolution_steps.py`; 対応: US3; 依存: T078, T080; 検証: comparison portions of `cd backend && uv run pytest tests/integration/test_snapshot_comparison.py tests/contract/test_comparison_contract.py` pass.
- [ ] T082 [P] [US3] Add GET `/runs/{runId}/best-step-metrics` in `backend/app/api/routes/runs.py`; 対応: US3; 依存: T079, T080; 検証: best-step Metric portions of `cd backend && uv run pytest tests/integration/test_snapshot_comparison.py tests/contract/test_comparison_contract.py` pass.
- [ ] T083 [P] [US3] Add typed comparison retrieval and response types in `frontend/src/api/evolutionSteps.ts`; 対応: US3; 依存: T074, T081; 検証: mock responses distinguish unavailable comparison, accuracy, and Dataset reasons.
- [ ] T084 [P] [US3] Add typed best-step Metric retrieval and response types in `frontend/src/api/runs.ts`; 対応: US3; 依存: T074, T082; 検証: mock responses retain negative `bestAccuracyStep` values and empty unavailable lists.
- [ ] T085 [US3] Implement Parameter, accuracy, and Dataset difference rendering in `frontend/src/features/evolution-steps/ComparisonPanel.tsx`; 対応: US3; 依存: T075, T083; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/ComparisonPanel.test.tsx` passes without calling Dataset metadata changes row additions or deletions.
- [ ] T086 [US3] Implement selected best-step Metric status and item rendering in `frontend/src/features/evolution-steps/BestStepMetrics.tsx`; 対応: US3; 依存: T076, T084; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/BestStepMetrics.test.tsx` passes for captured, pending, accuracy-missing, and Metric-item states using local API data only.
- [ ] T087 [US3] Integrate comparison and lazy best-step Metric loads into `frontend/src/pages/EvolutionStepDetailPage.tsx`; 対応: US3; 依存: T054, T085, T086; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/ComparisonPanel.test.tsx src/features/evolution-steps/EvolutionStepDetailPage.test.tsx` passes.

**Checkpoint**: US3 reads immutable Snapshots only and makes partial comparison availability explicit instead of representing unavailable data as unchanged.

---

## Phase 6: User Story 4 - Lineageを確認する (Priority: P4)

**Goal**: Reconstruct current Lineage around a selected Evolution Step and display ordered ancestors, descendants, branches, and upstream boundaries.

**Independent Test**: Seed a branched multi-generation set of current Run links, select a middle Step, and confirm nearest-first ancestors, breadth-first descendants ordered by Step ID, distances, and parent-Step identifiers.

### Tests for User Story 4 - Write and Run Red First

- [ ] T088 [P] [US4] Write failing nearest-first ancestor, breadth-first descendant, branch-order, and upstream-boundary unit tests in `backend/tests/unit/domain/test_lineage_traversal.py`; 対応: US4; 依存: T008-T020, T055; 検証: before T092, `cd backend && uv run pytest tests/unit/domain/test_lineage_traversal.py` fails for missing traversal behavior.
- [ ] T089 [P] [US4] Write a failing current-links-only multi-generation lineage integration test in `backend/tests/integration/test_lineage.py`; 対応: US4; 依存: T008-T020, T055; 検証: before T093-T096, `cd backend && uv run pytest tests/integration/test_lineage.py` fails for missing persisted graph reads.
- [ ] T090 [P] [US4] Write a failing Lineage endpoint contract test for distances, parent Evolution Step IDs, and boundary Run representation in `backend/tests/contract/test_lineage_contract.py`; 対応: US4; 依存: T008-T020, T055; 検証: before T095-T096, `cd backend && uv run pytest tests/contract/test_lineage_contract.py` fails for absent endpoint output.
- [ ] T091 [P] [US4] Write a failing ancestor, descendant, branch, root, and external-boundary rendering test in `frontend/src/features/evolution-steps/LineagePanel.test.tsx`; 対応: US4; 依存: T006, T055; 検証: before T097-T099, `cd frontend && npm test -- --run src/features/evolution-steps/LineagePanel.test.tsx` fails because the panel is absent.

### Implementation for User Story 4

- [ ] T092 [US4] Extend the shared graph rules with deterministic ancestor and descendant traversal functions in `backend/app/domain/lineage.py`; 対応: US4; 依存: T034, T088; 検証: `cd backend && uv run pytest tests/unit/domain/test_lineage_traversal.py` passes for all order and boundary cases.
- [ ] T093 [P] [US4] Add current-link ancestor and descendant lookup queries in `backend/app/infrastructure/evolution_step_repository.py`; 対応: US4; 依存: T038, T089; 検証: queries exclude stale history links and return enough data to identify direct parent Steps.
- [ ] T094 [US4] Implement selected-centered Lineage assembly in `backend/app/services/lineage_service.py`; 対応: US4; 依存: T092, T093, T089; 検証: `cd backend && uv run pytest tests/integration/test_lineage.py` passes for branched and external-boundary graphs.
- [ ] T095 [US4] Define selected, ancestor, and descendant Lineage response schemas in `backend/app/api/schemas/lineage.py`; 対応: US4; 依存: T090, T094; 検証: response schemas require `distanceFromSelected` and `parentEvolutionStepId` for every returned Step.
- [ ] T096 [US4] Add GET `/evolution-steps/{evolutionStepId}/lineage` to `backend/app/api/routes/evolution_steps.py`; 対応: US4; 依存: T090, T094, T095; 検証: `cd backend && uv run pytest tests/integration/test_lineage.py tests/contract/test_lineage_contract.py` passes.
- [ ] T097 [US4] Add typed Lineage retrieval and response types in `frontend/src/api/evolutionSteps.ts`; 対応: US4; 依存: T090, T096; 検証: mock requests preserve ordered arrays and nullable boundary fields.
- [ ] T098 [US4] Implement the selected-centered ancestor and descendant display in `frontend/src/features/evolution-steps/LineagePanel.tsx`; 対応: US4; 依存: T091, T097; 検証: `cd frontend && npm test -- --run src/features/evolution-steps/LineagePanel.test.tsx` passes for root, branch, and external-boundary states.
- [ ] T099 [US4] Add Lineage loading and display to `frontend/src/pages/EvolutionStepDetailPage.tsx`; 対応: US4; 依存: T087, T098; 検証: the detail page can render comparison and Lineage failures independently without suppressing saved detail.

**Checkpoint**: US4 reconstructs the current graph without a stored Lineage table and remains independently verifiable from seeded current links.

---

## Phase 7: Overall Integration and Cross-Cutting Verification

**Purpose**: Confirm the documented HTTP boundary, critical browser journey, performance constraints, and reproducible operating instructions across all completed stories.

- [ ] T100 [P] Write and run an OpenAPI response-conformance suite against every implemented route in `backend/tests/contract/test_openapi_conformance.py`; 対応: 全体統合 (US1-US4); 依存: T047, T066, T081, T082, T096; 検証: `cd backend && uv run pytest tests/contract/test_openapi_conformance.py` initially exposes any contract drift, then passes against `specs/001-experiment-evolution/contracts/openapi.yaml`.
- [ ] T101 [P] Configure Playwright's web-server, trace, and screenshot behavior in `frontend/playwright.config.ts`; 対応: 全体統合 (US1-US4); 依存: T002, T055, T070, T087, T099; 検証: `cd frontend && npm run test:e2e -- --list` discovers the configured browser project without starting an uncontrolled server.
- [ ] T102 Create the critical create-and-attach browser flow with one visible validation failure in `frontend/e2e/create-and-attach.spec.ts`; 対応: 全体統合 (US1-US4); 依存: T101, T055, T099; 検証: `cd frontend && npm run test:e2e -- create-and-attach` creates a Step, attaches a Run, verifies its detail, and retains trace/screenshot artifacts on failure.
- [ ] T103 [P] Add seeded read-performance checks for list, comparison, detail, and 100-Step Lineage budgets in `backend/tests/integration/test_read_performance.py`; 対応: 全体統合 (US1-US4); 依存: T066, T078, T094; 検証: against exactly 1,000 seeded Evolution Steps including a connected 100-Step Lineage, `cd backend && uv run pytest tests/integration/test_read_performance.py` performs 5 unmeasured warm-ups and 30 measured requests per target, excludes fixture setup and MLflow synchronization, calculates nearest-rank p95, and verifies the stated 500 ms and 1 s targets.
- [ ] T104 Update actual setup, migration, test, MLflow fixture, failure-triage, and timed manual-acceptance procedures in `README.md` and `specs/001-experiment-evolution/quickstart.md`; 対応: 全体統合 (US1-US4); 依存: T100-T103; 検証: a clean environment can follow both documents to start MySQL, migrate, run backend/frontend tests, execute the E2E flow, and identify the start/end conditions for SC-001 through SC-004 without undocumented credentials.
- [ ] T105 Execute the final backend, frontend, E2E, lint, and quickstart verification matrix recorded in `specs/001-experiment-evolution/quickstart.md`; 対応: 全体統合 (US1-US4); 依存: T100-T104; 検証: `cd backend && uv run pytest && uv run ruff check .`, `cd frontend && npm test && npm run build && npm run test:e2e`, and the documented quickstart scenario all pass with results attached to the implementation review.
- [ ] T106 Execute and record timed user acceptance for SC-001 through SC-004 in `specs/001-experiment-evolution/validation-results.md`; 対応: 全体統合 (US1-US4); 依存: T105; 検証: SC-001 is timed from display of an empty create form until the created detail shows the selected result Run, SC-002 from opening a captured detail until the tester identifies Parameter differences, best accuracy, and its delta, and SC-003 from opening a prepared multi-generation Lineage until every expected ancestor, descendant, and order is identified; each stays within its 3-minute or 1-minute limit, and SC-004 records 100% expected-field and reconstructed-Lineage agreement after stopping and restarting the application while retaining the same MySQL data.

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
- Foundational: T008, T010, T012, T016, and T019 are focused red tests. Each implementation follows its named test, and unrelated backend/frontend test paths do not block one another.
- US1: T021-T031 are parallel red tests. T032-T039 are independently implementable where their named dependencies permit. T040 and T041 are sequential because they modify the same service, while T043/T044, T045/T046, and T048/T049 are paired parallel work.
- US2: T056-T061 are parallel red tests, followed by T062/T063 and T068 where dependencies permit.
- US3: T071-T076 are parallel red tests; T081/T082 and T083/T084 can run in parallel after their shared contracts are ready.
- US4: T088-T091 are parallel red tests; T093 can be implemented alongside T092 after their independent tests are written.
- Integration: T100, T101, and T103 can start in parallel after the relevant story checkpoints; T102 follows T101, and final manual acceptance T106 follows the complete verification matrix T105.

## Parallel Execution Examples

### User Story 1

```text
Task: T021 through T031 - write all focused red tests in their separate backend/frontend files
Task: T032 - backend/app/domain/evolution_step.py
Task: T033 - backend/app/domain/run_snapshot.py
Task: T034 - backend/app/domain/lineage.py
Task: T035 - backend/app/infrastructure/mlflow_gateway.py
```

### User Story 2

```text
Task: T056 through T061 - write pagination, summary, API, and UI red tests
Task: T062 - backend/app/domain/pagination.py
Task: T063 - backend/app/domain/comparison.py
Task: T068 - frontend/src/features/evolution-steps/RunSyncStatus.tsx
```

### User Story 3

```text
Task: T071 through T076 - write domain, integration, contract, and UI red tests
Task: T081 - comparison API route
Task: T082 - best-step Metrics API route
Task: T083 - Evolution Step comparison client
Task: T084 - Run best-step Metrics client
```

### User Story 4

```text
Task: T088 through T091 - write traversal, integration, contract, and UI red tests
Task: T092 - backend/app/domain/lineage.py traversal logic
Task: T093 - backend/app/infrastructure/evolution_step_repository.py graph reads
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2, including their verification commands.
2. Complete T021-T055 as a red-to-green vertical slice for US1.
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

All 106 tasks use the required `- [ ] T### [P?] [US?] Description` checklist format. User-story tasks carry exactly one `[US1]` through `[US4]` label; setup, foundational, and integration tasks use no user-story label. Every task includes target paths, a corresponding story scope, explicit dependencies, and a verification method.
