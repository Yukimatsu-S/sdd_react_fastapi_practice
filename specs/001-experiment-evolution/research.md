# Research: Mondel

## MLflow integration

- **Decision**: Implement an `MlflowRunGateway` behind a backend interface using the MLflow Python client (MLflow 2.x+). List candidates with paginated `search_runs`, load a selected Run with `get_run`, load each metric history with `get_metric_history`, and load dataset inputs from `RunInputs.dataset_inputs` returned by `get_run` when the tracking server supports it. Preserve unavailable optional dataset fields as absent, not invented from tags.
- **Rationale**: `Run.data.params` is the complete MLflow parameter map, while `Run.data.metrics` only exposes the latest metric values. Full accuracy history is required to select the maximum correctly. Dataset inputs retain MLflow dataset metadata such as name, digest, source and schema; this is more reliable than an application-specific tag convention.
- **Alternatives considered**: Reading only `Run.data.metrics` was rejected because it cannot meet the multiple-accuracy requirement. Browser-to-MLflow access was rejected because it leaks external configuration and bypasses API validation.

## Backend execution model

- **Decision**: Use synchronous SQLAlchemy 2.x with PyMySQL and the synchronous MLflow Python client. FastAPI path operations and dependencies that perform these blocking I/O calls use normal `def`, with one SQLAlchemy Session per request. Complete any required MLflow retrieval before opening the database transaction that persists a new snapshot and association.
- **Rationale**: The initial MVP is a low-concurrency, single-team learning application. A synchronous request flow makes API, service, database, commit, and rollback behavior easier to trace while still allowing FastAPI to execute blocking path operations in its thread pool. Keeping external MLflow waits outside the database transaction avoids holding database connections and locks during network I/O.
- **Alternatives considered**: Asynchronous SQLAlchemy and an async MySQL driver were deferred because they add coroutine, async session, driver, and async-test concepts before the core HTTP and transaction flow is understood. Reconsider asynchronous data access only if measured concurrency or latency shows that the synchronous thread and connection pools are a bottleneck.

## Snapshot and service boundary

- **Decision**: Separate a mutable `RunReference` from an optional immutable `RunSnapshot`. Linking a Run always persists its reference after confirming that the Run exists in MLflow. A `RUNNING` or `SCHEDULED` Run remains snapshot-pending. A `FINISHED`, `FAILED`, or `KILLED` Run is terminal and causes its Parameters, metric histories, dataset inputs, status, execution timestamps, and raw metadata to be captured once. The detail page first loads local data, then automatically calls a separate Run synchronization action for each linked Run. Synchronization updates the reference's current name, current status, and timestamp; if a pending Run has become terminal, it also creates the snapshot and child rows in one transaction. A finalized snapshot is never overwritten.
- **Rationale**: Developers can link a Run when long-running training starts and cannot forget which Evolution Step it belongs to. The association is useful immediately, while comparison evidence becomes available only when the Run reaches a terminal state. Keeping the first detail read local preserves responsiveness and outage tolerance; using a separate synchronization action makes the network call and database mutation explicit.
- **Alternatives considered**: Requiring a terminal Run before linking was rejected because multi-hour training makes delayed manual association easy to forget. Capturing a `RUNNING` Run immediately was rejected because it permanently freezes incomplete Metrics and Dataset inputs. Polling MLflow in a background worker was deferred because it introduces scheduling, retry, and operational concerns not needed for the initial MVP. Refreshing a finalized snapshot was rejected because it could rewrite historical conclusions. Resuming a finalized Run may change its live status, but a separately tracked continuation should use a new Run ID and Evolution Step.

## Data persistence

- **Decision**: Use MySQL 8.0+ and SQLAlchemy 2.x with normalized `evolution_step`, `run_reference`, optional one-to-one `run_snapshot`, `run_parameter`, `metric_observation`, `dataset_input`, and append-only `evolution_step_history` tables. Save the current MLflow name, status, execution times, and synchronization timestamp on `run_reference`; save finalized values and capture time on `run_snapshot`.
- **Rationale**: The relational schema makes result-Run ownership enforceable and preserves all metric samples without opaque JSON comparison logic. JSON payload columns retain unmodeled MLflow metadata for troubleshooting without becoming the comparison source.
- **Alternatives considered**: A graph database is unnecessary for the expected bounded MVP graph. Storing only JSON prevents indexed uniqueness and simple, deterministic comparisons.

## Result Run exclusivity and lineage validation

- **Decision**: Place a nullable unique constraint on `evolution_step.result_run_id`, with both Run-link foreign keys referencing `run_reference.run_id`. In the same transaction as every create/update, lock the edited Evolution Step row, build the proposed set of edges where both parent and result Run exist, and run deterministic depth-first cycle detection by Run ID. The database unique constraint is the final protection against concurrent result-Run claims.
- **Rationale**: An Evolution Step represents an edge `$parentRun \rightarrow resultRun$`. A cycle exists exactly when the proposed directed Run graph cannot be topologically traversed. Building edges from current rows ensures a change or unlink affects only the selected Evolution Step while validating the complete current graph.
- **Alternatives considered**: Checking only direct parent/result equality misses multi-generation cycles. Cascading child updates violates FR-024.

## Differences

- **Decision**: Treat Parameters as string key/value maps. For the union of keys, return `added` when only the result contains a key, `removed` when only the parent contains it, and `changed` when both values differ. For metric key exactly `accuracy`, calculate each Run's `max(value)` from all stored observations and return `$resultMax - parentMax$`; return an explicit unavailable reason if either history is missing. Compare dataset identifier fields supplied by MLflow as equal, different, or unavailable.
- **Rationale**: This directly implements FR-012, FR-014, FR-015, and FR-016 without inferring optimization direction for other metrics.
- **Alternatives considered**: Comparing latest accuracy would produce the wrong result for non-monotonic training. General metric selection or min/max heuristics are explicitly out of scope.

## API and frontend state

- **Decision**: Version FastAPI routes under `/api/v1`. React uses React Router for list, create, and detail pages and a hand-written typed wrapper around browser `fetch` for API calls. Each feature explicitly manages loading, success, empty, and error states and refreshes affected data after mutations. The detail page renders the local detail response first, calls `POST /runs/{runId}/sync` for each linked Run, and reloads local detail when synchronization succeeds. The frontend displays snapshot-pending states, `409` integrity violations, and non-blocking `502` synchronization warnings.
- **Rationale**: The HTTP/OpenAPI contract is the sole cross-stack boundary. Using browser `fetch` keeps the request and response flow visible during learning, while the small typed wrapper prevents duplicated URL and error-handling code. The frontend remains responsible for usability and local form feedback; FastAPI remains the authority for constraints.
- **Alternatives considered**: TanStack Query was deferred because its caching and server-state abstractions would hide the initial request-state flow and add a library before the MVP needs advanced cache behavior. Generated OpenAPI clients were deferred so the first API types and calls remain inspectable. Duplicating lineage checks in React was rejected because clients can be stale and constraints must hold for all callers.

## Testing

- **Decision**: Test pure diff and graph functions with pytest unit tests; test MySQL constraints, migrations, transactions, and FastAPI responses against a dedicated MySQL test database; mock the MLflow gateway for active linking, terminal snapshot capture, repeated synchronization, Run-name changes, incomplete data, and failures; verify that finalized snapshots are inserted once and never overwritten; validate OpenAPI against API responses; introduce Vitest and React Testing Library with the frontend to test loading, pending, synchronized, error, empty, warning, and constraint states; add one Playwright end-to-end test for the critical create-and-attach flow after frontend/backend integration.
- **Rationale**: The highest-risk rules are graph integrity and external-service failure, both of which need verification below the browser and across the HTTP boundary.
- **Alternatives considered**: Testcontainers was deferred because automatic container lifecycle management adds another abstraction before database integration testing is understood; the test database connection is supplied explicitly instead. Playwright is used for the critical end-to-end user flow and representative validation errors, while exhaustive validation cases are covered by faster backend integration and frontend component tests to avoid duplication. Manual-only validation is rejected by the constitution and cannot reliably cover concurrent ownership or all cycle shapes.
