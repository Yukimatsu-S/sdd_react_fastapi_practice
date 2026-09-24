# Timed Manual Acceptance Results

## Status

Manual acceptance is **not run**. The automated verification baseline passed at
commit `0d23e55` on 2026-09-24: backend 314 tests, Ruff, frontend 32 tests,
production build, and one Chromium E2E test. This is supporting evidence only;
it does not replace the timed human checks below.

## Required manual environment

- A non-secret `backend/.env` with a normal-use MySQL database and reachable
  MLflow Tracking Server.
- Prepared MLflow Run IDs and an expected-results worksheet for the four
  scenarios. Do not put credentials in this file.
- FastAPI and Vite started according to [quickstart.md](quickstart.md).

## Results

| Criterion | Start condition | End condition | Limit | Test data / evidence | Measured result | Judgment |
|---|---|---|---|---|---|---|
| SC-001 | Empty create form is visible | Created detail displays the selected result Run | 3 minutes | Not run: requires prepared MLflow Runs | — | Not run |
| SC-002 | Captured-Step detail is open | Parameter differences, best accuracy, and delta are identified | 1 minute | Not run: requires captured parent/result Snapshots | — | Not run |
| SC-003 | Prepared multi-generation Step detail is open | Ancestors, descendants, and order are identified | 1 minute | Not run: requires prepared Lineage fixture | — | Not run |
| SC-004 | Prepared records exist in normal MySQL | Restarted application has 100% expected-field and Lineage agreement | 100% agreement | Not run: requires persistent normal MySQL fixture | — | Not run |

When executing a row, replace `Not run` with the date, commit/ref, browser,
non-secret database name, MLflow fixture/run IDs, elapsed time or matched count,
and a pass/fail judgment. Preserve a diagnostic note or Playwright artifact for
every failure.
