# Implementation Plan: Mondel Initial MVP

**Branch**: `chore/create-plan` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-experiment-evolution/spec.md`

## Summary

機械学習開発者がEvolution Stepの目的、仮説、手動の変更内容、MLflow Runの結果、差分、およびLineageを登録・確認するWebアプリケーション「Mondel」を構築する。Evolution Stepは派生元Runから実行結果Runへ進む一回の改善工程であり、複数のEvolution Stepを現在のRun紐付けで結んだ全体をLineageと呼ぶ。Reactは入力、一覧・詳細・差分・Lineageの表示を担い、FastAPIはHTTP/JSON API、入力検証、Run取得、履歴記録、Lineage整合性を担う。MySQLはEvolution Step、現在のRun紐付け、変更履歴、MLflowから取得した不変スナップショットを保存する。MLflowは外部で実行された学習のRun情報を提供する参照専用の外部システムであり、本製品は学習を開始・停止・再実行しない。

Runの紐付け時、保存済みSnapshotがなければFastAPIがMLflowからRun、Parameters、各Metricの時系列、Dataset Inputを取得し、同一トランザクションでSnapshotと紐付けを保存する。保存済みSnapshotがあればその時点のParameters、Metrics、Dataset情報を再利用し、Run名だけを現在の表示情報として同期する。Run名は候補取得、紐付け・変更、およびEvolution Step詳細表示時に同期し、詳細表示時の同期失敗は保存済み情報の表示を妨げない。現在の全`parent_run_id -> result_run_id`辺を検査して循環を拒否し、MySQLの一意制約で結果Runの重複利用を防止する。比較は保存済みSnapshotだけで算出し、Parametersはキー単位で追加・変更・削除、accuracyは各履歴の最大値の差分、Datasetは識別項目ごとの一致・相違として返す。

## Technical Context

**Language/Version**: Python 3.12+ (backend, existing `pyproject.toml`), TypeScript (React; version finalized when frontend is initialized)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x, PyMySQL, Alembic, MLflow Python client; React, TypeScript, Vite, npm, React Router, browser `fetch`; Vitest, React Testing Library, Playwright (one critical flow after integration)

**Storage**: MySQL 8.0+ for application data, immutable MLflow Run snapshot payloads, and mutable last-known Run names; MLflow Tracking Server is an external read-only source

**Testing**: pytest + FastAPI TestClient against a dedicated MySQL test database for backend unit/integration/contract tests; Vitest + React Testing Library when frontend implementation starts; Playwright for one critical end-to-end flow after frontend/backend integration

**Target Platform**: Modern desktop browser for the single-team MVP; Linux-compatible FastAPI service; MySQL 8.0+ and reachable MLflow Tracking Server

**Project Type**: React single-page application plus FastAPI JSON web service

**Performance Goals**: Evolution Step list, comparison, and saved-detail data reads respond within 500 ms p95 under an MVP dataset of 1,000 Evolution Steps, excluding the bounded best-effort Run-name lookup performed by the detail endpoint; a Lineage response for 100 linked Evolution Steps responds within 1 s; UI enables the SC-001 to SC-003 workflows within their specified times

**Constraints**: `uv` manages backend dependencies and `npm` manages frontend dependencies; backend database access uses synchronous SQLAlchemy with PyMySQL and FastAPI path operations that perform blocking I/O use normal `def`; React calls FastAPI through a hand-written typed wrapper around browser `fetch`; no TanStack Query, Testcontainers, asynchronous SQLAlchemy, or generated OpenAPI client in the initial MVP; browser never accesses MLflow or MySQL directly; no authentication, delete/archive, graphical lineage, or learning-job control; first-time attach/update fails atomically when required MLflow retrieval or integrity validation fails; stored Parameters, Metrics, Dataset data, status, timestamps, and raw metadata are not refreshed; only the last-known Run name and its synchronization timestamp are mutable

**Scale/Scope**: One React application, one FastAPI service, one MySQL schema, one MLflow integration; CRUD is limited to create/read/update for Evolution Steps and Run associations

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

| Principle | Design response | Status |
|-----------|-----------------|--------|
| I. Spec-Driven Delivery | This plan, data model, HTTP contract, quickstart, and subsequent tasks trace to FR-001 through FR-027 and SC-001 through SC-004. | PASS |
| II. Dual-Stack Contract Boundaries | React consumes only versioned FastAPI HTTP/JSON endpoints documented in `contracts/openapi.yaml`; FastAPI owns validation and business rules. | PASS |
| III. Reproducible Tooling | Backend dependencies and commands use `uv`; frontend dependencies and commands use `npm`; test services are containerized. | PASS |
| IV. Test-First Verification | Tests are specified for domain logic, persistence constraints, MLflow adapter behavior, API contracts, UI states, and end-to-end user flows before implementation. | PASS |
| V-VII. Simplicity, Readability, Loose Coupling | A narrow MLflow gateway isolates external calls; pure comparison/lineage services receive explicit repositories and snapshots; no generic workflow engine or graph database is introduced. | PASS |

**Post-design re-check**: The API contract keeps client/server responsibilities explicit. Immutable history and snapshot payloads make persistence and operational failures traceable; the narrowly defined mutable Run name prevents display drift without changing comparison evidence. The MySQL relational model and bounded graph traversal satisfy the feature without additional service or storage components.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/                 # FastAPI routers and request/response schemas
│   ├── domain/              # Entities, comparison and lineage rules
│   ├── infrastructure/      # SQLAlchemy repositories and MLflow gateway
│   └── services/            # Transactional use cases
├── migrations/              # Alembic revisions
├── tests/
│   ├── contract/
│   ├── integration/
│   └── unit/
├── main.py
└── pyproject.toml

frontend/
├── src/
│   ├── api/                 # Hand-written typed HTTP client using browser fetch
│   ├── components/
│   ├── features/evolution-steps/
│   ├── pages/
│   └── routes/
├── tests/
└── package.json

specs/001-experiment-evolution/
├── contracts/openapi.yaml
├── data-model.md
├── quickstart.md
└── research.md
```

**Structure Decision**: Adopt the Web application structure. The existing `backend/` becomes the FastAPI project organized by API, domain, infrastructure, and use-case layers. Add `frontend/` as the independent React/npm project. This keeps the HTTP contract as the only frontend/backend integration surface and confines MLflow to backend infrastructure.

## Complexity Tracking

No constitution violations require justification.
