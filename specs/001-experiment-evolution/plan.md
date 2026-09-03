# Implementation Plan: Mondel Initial MVP

**Branch**: `chore/create-plan` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-experiment-evolution/spec.md`

## Summary

機械学習開発者がEvolution Stepの目的、仮説、手動の変更内容、MLflow Runの結果、差分、およびLineageを登録・確認するWebアプリケーション「Mondel」を構築する。Evolution Stepは派生元Runから実行結果Runへ進む一回の改善工程であり、複数のEvolution Stepを現在のRun紐付けで結んだ全体をLineageと呼ぶ。Reactは入力、一覧・詳細・差分・Lineageの表示を担い、FastAPIはHTTP/JSON API、入力検証、Run取得、履歴記録、Lineage整合性を担う。MySQLはEvolution Step、現在のRun紐付け、変更履歴、MLflowから取得した不変スナップショットを保存する。MLflowは外部で実行された学習のRun情報を提供する参照専用の外部システムであり、本製品は学習を開始・停止・再実行しない。

Runの紐付け時、FastAPIはMLflow上の存在、名前、状態を確認して`run_reference`を保存する。RUNNINGまたはSCHEDULEDならSnapshot未確定のままEvolution Stepへ紐付け、FINISHED、FAILED、またはKILLEDならMetric名とstepが同じ記録を最新timestamp、さらに同一timestampなら最大値で一本化し、Parameters、一本化後のaccuracyが最大となる最小stepとそのstepのMetrics、Dataset Inputを取得してSnapshotを同一トランザクションで確定する。全stepのMetric履歴は永続化しない。Evolution Step一覧は作成日時とIDの降順で20件ずつカーソル取得する。Evolution Step詳細画面は保存済み情報を取得した後、紐付いたRunごとに同期APIを自動実行し、最良stepのMetric一覧を別のローカルAPIで段階取得する。同期時に未確定Runが終了状態ならSnapshotを一度だけ確定し、確定済みなら現在のRun名と状態だけを更新する。Runの紐付け変更は共有ガード行を最初にロックして直列化し、現在の全`parent_run_id -> result_run_id`辺を検査して循環を拒否する。MySQLの一意制約では結果Runの重複利用を防止する。比較は確定済みSnapshotだけで算出し、Parametersはキー単位で追加・変更・削除、accuracyは保存済み最良値の差分、Dataset Inputは用途と名前で対応付けて`changed`、`parent_only`、`result_only`の差分だけを返す。

## Technical Context

**Language/Version**: Python 3.12+ (backend, existing `pyproject.toml`), TypeScript (React; version finalized when frontend is initialized)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x, PyMySQL, Alembic, MLflow Python client; React, TypeScript, Vite, npm, React Router, browser `fetch`; Vitest, React Testing Library, Playwright (one critical flow after integration)

**Storage**: MySQL 8.0+ for application data, mutable MLflow Run references, and immutable finalized Run snapshots; MLflow Tracking Server is an external read-only source

**Testing**: pytest + FastAPI TestClient against a dedicated MySQL test database for backend unit/integration/contract tests; Vitest + React Testing Library when frontend implementation starts; Playwright for one critical end-to-end flow after frontend/backend integration

**Target Platform**: Modern desktop browser for the single-team MVP; Linux-compatible FastAPI service; MySQL 8.0+ and reachable MLflow Tracking Server

**Project Type**: React single-page application plus FastAPI JSON web service

**Performance Goals**: Evolution Step list, comparison, and saved-detail reads respond within 500 ms p95 under an MVP dataset of 1,000 Evolution Steps; Run synchronization is a separate bounded request and does not delay the first saved-detail display; a Lineage response for 100 linked Evolution Steps responds within 1 s; UI enables the SC-001 to SC-003 workflows within their specified times

**Constraints**: `uv` manages backend dependencies and `npm` manages frontend dependencies; backend database access uses synchronous SQLAlchemy with PyMySQL and FastAPI path operations that perform blocking I/O use normal `def`; React calls FastAPI through a hand-written typed wrapper around browser `fetch`; no TanStack Query, Testcontainers, asynchronous SQLAlchemy, or generated OpenAPI client in the initial MVP; browser never accesses MLflow or MySQL directly; no authentication, delete/archive, graphical lineage, learning-job control, background Run polling, or full Metric-history persistence/display; initial linking fails atomically when MLflow existence checks or integrity validation fail; Run references may exist before their Snapshot; finalized Parameters, best-step Metrics, Dataset data, status, timestamps, and raw metadata are immutable; only current Run name, current status, current execution times, and synchronization time remain mutable

**Scale/Scope**: One React application, one FastAPI service, one MySQL schema, one MLflow integration; CRUD is limited to create/read/update for Evolution Steps and Run associations

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

| Principle | Design response | Status |
|-----------|-----------------|--------|
| I. Spec-Driven Delivery | This plan, data model, HTTP contract, quickstart, and subsequent tasks trace to FR-001 through FR-030 and SC-001 through SC-004. | PASS |
| II. Dual-Stack Contract Boundaries | React consumes only versioned FastAPI HTTP/JSON endpoints documented in `contracts/openapi.yaml`; FastAPI owns validation and business rules. | PASS |
| III. Reproducible Tooling | Backend dependencies and commands use `uv`; frontend dependencies and commands use `npm`; test services are containerized. | PASS |
| IV. Test-First Verification | Tests are specified for domain logic, persistence constraints, MLflow adapter behavior, API contracts, UI states, and end-to-end user flows before implementation. | PASS |
| V-VII. Simplicity, Readability, Loose Coupling | A narrow MLflow gateway isolates external calls; pure comparison/lineage services receive explicit repositories and snapshots; no generic workflow engine or graph database is introduced. | PASS |

**Post-design re-check**: The API contract keeps client/server responsibilities explicit. Separating mutable Run references from immutable finalized snapshots permits early linking without rewriting comparison evidence. Detail reads remain local and usable during MLflow outages, while a separate synchronization action makes the external side effect explicit. The MySQL relational model and bounded graph traversal satisfy the feature without a background worker or additional storage technology.

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
