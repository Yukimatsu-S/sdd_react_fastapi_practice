# Implementation Plan: ML Experiment Evolution Manager Initial MVP

**Branch**: `chore/create-plan` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-experiment-evolution/spec.md`

## Summary

機械学習開発者が実験の目的、仮説、手動の変更内容、MLflow Run の結果、差分、および派生関係を登録・確認する Web アプリケーションを構築する。React は入力、一覧・詳細・差分・Lineage の表示を担い、FastAPI は HTTP/JSON API、入力検証、Run 取得、履歴記録、Lineage 整合性を担う。MySQL は実験、現在の Run 紐付け、変更履歴、MLflow から取得した不変スナップショットを保存する。MLflow は外部で実行された学習の Run 情報を提供する参照専用の外部システムであり、本製品は学習を開始・停止・再実行しない。

Run の紐付け時、保存済みスナップショットがなければ FastAPI が MLflow から Run、Parameters、各 metric の時系列、dataset input を取得し、同一トランザクションでスナップショットと紐付けを保存する。保存済みスナップショットがあれば MLflow から再取得せず、その不変スナップショットを再利用する。現在の全 `parent_run_id -> result_run_id` 辺を検査して循環を拒否し、MySQL の一意制約で結果 Run の重複利用を防止する。比較は保存済みスナップショットだけで算出し、Parameters はキー単位で追加・変更・削除、accuracy は各履歴の最大値の差分、dataset は識別項目ごとの一致・相違として返す。

## Technical Context

**Language/Version**: Python 3.12+ (backend, existing `pyproject.toml`), TypeScript (React; version finalized when frontend is initialized)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x, PyMySQL, Alembic, MLflow Python client; React, TypeScript, Vite, npm, React Router, browser `fetch`; Vitest, React Testing Library, Playwright (one critical flow after integration)

**Storage**: MySQL 8.0+ for application data and immutable MLflow Run snapshots; MLflow Tracking Server is an external read-only source

**Testing**: pytest + FastAPI TestClient against a dedicated MySQL test database for backend unit/integration/contract tests; Vitest + React Testing Library when frontend implementation starts; Playwright for one critical end-to-end flow after frontend/backend integration

**Target Platform**: Modern desktop browser for the single-team MVP; Linux-compatible FastAPI service; MySQL 8.0+ and reachable MLflow Tracking Server

**Project Type**: React single-page application plus FastAPI JSON web service

**Performance Goals**: Experiment list and saved-detail reads respond within 500 ms p95 under an MVP dataset of 1,000 experiments; a lineage response for 100 linked experiments responds within 1 s excluding MLflow import; UI enables the SC-001 to SC-003 workflows within their specified times

**Constraints**: `uv` manages backend dependencies and `npm` manages frontend dependencies; backend database access uses synchronous SQLAlchemy with PyMySQL and FastAPI path operations that perform blocking I/O use normal `def`; React calls FastAPI through a hand-written typed wrapper around browser `fetch`; no TanStack Query, Testcontainers, asynchronous SQLAlchemy, or generated OpenAPI client in the initial MVP; browser never accesses MLflow or MySQL directly; no authentication, delete/archive, graphical lineage, or learning-job control; attach/update fails atomically when MLflow retrieval or integrity validation fails; MLflow snapshots are not silently refreshed

**Scale/Scope**: One React application, one FastAPI service, one MySQL schema, one MLflow integration; CRUD is limited to create/read/update for experiments and Run associations

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

| Principle | Design response | Status |
|-----------|-----------------|--------|
| I. Spec-Driven Delivery | This plan, data model, HTTP contract, quickstart, and subsequent tasks trace to FR-001 through FR-024 and SC-001 through SC-004. | PASS |
| II. Dual-Stack Contract Boundaries | React consumes only versioned FastAPI HTTP/JSON endpoints documented in `contracts/openapi.yaml`; FastAPI owns validation and business rules. | PASS |
| III. Reproducible Tooling | Backend dependencies and commands use `uv`; frontend dependencies and commands use `npm`; test services are containerized. | PASS |
| IV. Test-First Verification | Tests are specified for domain logic, persistence constraints, MLflow adapter behavior, API contracts, UI states, and end-to-end user flows before implementation. | PASS |
| V-VII. Simplicity, Readability, Loose Coupling | A narrow MLflow gateway isolates external calls; pure comparison/lineage services receive explicit repositories and snapshots; no generic workflow engine or graph database is introduced. | PASS |

**Post-design re-check**: The API contract keeps client/server responsibilities explicit. Immutable history and snapshot tables make persistence and operational failures traceable. The MySQL relational model and bounded graph traversal satisfy the feature without additional service or storage components.

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
│   ├── features/experiments/
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
