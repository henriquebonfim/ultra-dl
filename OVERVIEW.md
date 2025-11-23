# Test Overview & QA Summary

This document summarizes the repository's test surface, current coverage state, test architecture, folder layout, and prioritized QA recommendations. I'm direct and honest: the project is not 100% tested and the CI/pipeline coverage is incomplete.

**Quick answers**
- **Is the project 100% tested?**: No. Backend coverage (HTML report) shows ~73% overall coverage.
- **Does the repo cover the full pipeline (CI runs/tests/coverage)?**: No obvious CI configuration found (no `.github/workflows` or other CI files). Tests appear locally runnable but are not enforced in a pipeline.

**Where tests live (high level)**
- `backend/tests/` — contains unit, integration, e2e, performance and contract tests.
- `frontend/tests/` — contains Vitest React component/performance tests and a bundle-size test that expects built artifacts.

**Backend test architecture**
- Unit tests: `backend/tests/unit/` — domain logic, value objects, services, error handling, job service, etc.
- Integration tests: `backend/tests/integration/` — many integration scenarios (Redis, storage, API, event handlers, publishers). Several integration tests reference real infra (Redis, local storage, GCS adapter), so CI will need services or well-scoped mocks.
- E2E tests: `backend/tests/e2e/` — full workflows such as download workflow and rate-limiting end-to-end tests.
- Contract tests: `backend/tests/contracts/` — repository/file-storage/metadata extractor contracts used to validate implementations.
- Performance tests: `backend/tests/performance/` — API perf tests (likely not intended for CI but useful in benchmarking).

**Frontend test architecture**
- Uses `vitest`. Tests live under `frontend/tests/` and exercise React components (render and memoization/perf checks) and a `bundle-size.test.ts` that asserts built output sizes.
- No coverage output found for frontend in repository artifacts (no `coverage` or `htmlcov` in `frontend`). Package scripts: `test`, `test:run`, `test:ui` — but `test` alone does not include `--coverage`.

**Coverage artifacts (what I found)**
- `backend/htmlcov/index.html` — shows an overall coverage of **73%** (coverage.py v7.11.3). The `htmlcov/status.json` lists per-file statements/missing counts.
- `backend/coverage.json` appears empty or not populated in the repository snapshot.
- No frontend coverage HTML/JSON discovered.

**Folder structure (tests-focused view)**
- `backend/`
  - `tests/unit/` — unit tests
  - `tests/integration/` — integration tests (Redis, storage, services)
  - `tests/e2e/` — end-to-end tests
  - `tests/contracts/` — contract tests for repository adapters
  - `tests/performance/` — performance tests
  - `htmlcov/` — generated coverage report (73%)
- `frontend/`
  - `tests/` — vitest tests (components, performance, bundle-size)
  - `package.json` — `test` scripts (no coverage flag)

**Honest assessment / What is missing**
- Backend: 73% coverage is good but not complete. Many files in `application/`, `infrastructure/`, and `tasks/` show missing statements in the HTML coverage; important infra adapters (GCS, local storage, event handlers) have substantial missing lines.
- Frontend: tests exist but there is no evidence of a coverage run or enforced thresholds. The `bundle-size.test.ts` expects a build artifact (`dist/assets`), so CI must run `npm run build` before that test or the test will fail.
- Pipeline/CI: There is no CI configuration in the repository. Tests and coverage are not enforced on merge.

**Concrete, prioritized QA recommendations**
1. Continuous Integration
   - Add CI (GitHub Actions / GitLab CI / Cloud Build) that runs backend tests (pytest) and frontend tests (vitest) on PRs.
   - Steps: install deps, start required services (Redis) via service containers, run `pytest --maxfail=1 -q` and `npm ci && npm run build && npm run test:run`.
2. Coverage & Gates
   - Publish backend coverage to CI artifacts and fail PRs below a threshold (start with 70% and raise over time). Currently backend ~73% — set gate at 70% then increase.
   - Enable frontend coverage in Vitest: add `--coverage` to `test:run` or create `test:coverage` script; publish the report and set thresholds.
3. CI for integration/e2e tests
   - Separate fast unit tests from slower integration/e2e tests. Run unit tests on every PR; run integration/e2e in a scheduled pipeline or only on main branch (or with matrix jobs when needed).
   - For integration tests requiring Redis/GCS, either spin up containers in CI (Redis) and use an emulator for GCS (or mock/stub network calls), or mark tests with a pytest marker (e.g., `@pytest.mark.integration`) and run only when infra is available.
4. Stabilize flaky tests & test data
   - Some tests interact with real storage or network. Use fixtures to create isolated temp storage and deterministic data. Ensure tests clean up resources and avoid time-sensitive assertions.
5. Frontend test improvements
   - Add unit tests for core logic (hooks, utilities) in addition to render/perf tests.
   - Add a `test:coverage` script (`vitest --run --coverage`) and ensure CI publishes coverage. The bundle-size test should run after `npm run build` in CI.
6. Reporting & mutation testing
   - Add codecov.io or similar badge, and publish coverage artifacts.
   - Consider mutation testing (e.g., MutPy, Stryker) for critical modules over time.

**Low-effort short wins (do these first)**
- Add a simple GitHub Actions workflow that runs unit tests and records coverage for backend and frontend. Example jobs:
  - `backend-tests`: run `pip install -r backend/requirements.txt`, run `pytest --cov=./ --cov-report=xml` and upload `coverage.xml`.
  - `frontend-tests`: run `npm ci`, `npm run build`, `npm run test:run -- --coverage` and upload coverage.
- Add `pytest.ini` configuration in backend already exists — ensure CI uses it.

**Final note**
The repository has a healthy test structure: unit, integration, e2e, contract and performance tests are present and organized. However, tests are not enforced in CI, backend coverage is ~73% (so not 100%), and frontend lacks a coverage workflow. My recommendation: add CI, publish coverage, enforce thresholds, and gradually increase test coverage focusing on critical infrastructure adapters and the `application/` layer.

If you want, I can:
- scaffold a GitHub Actions workflow that runs backend unit tests with coverage and frontend build+tests (quickly), or
- add a `frontend` `test:coverage` script and example CI job.

— QA (GitHub Copilot)

**Test run (Docker) — results summary**
- I executed tests inside Docker containers for both services (backend + frontend).
- Backend: `465` tests collected, **374 passed**, **91 failed**. Full run log saved in terminal output. Many failures are concentrated in a few areas (see below).
- Frontend: `48` tests collected, **47 passed**, **1 failed** (a timeout in `ResolutionPicker` test). The frontend bundle-size and most component tests passed; Vitest coverage was generated.

**Top-level failure patterns observed (backend)**
- Missing top-level module shims: some tests patch top-level module names (e.g., `websocket_events`) — I added a compatibility shim `backend/websocket_events.py` to allow those imports. This helped, but other similar expectations remain.
- Attribute/mocking mismatches: many tests expect attributes to be present on modules (e.g., `tasks.cleanup_task.GCSRepository`, `domain.errors.logger`, `infrastructure.event_handlers.emit_job_completed`, `infrastructure.storage_service`). Those attributes either aren't exported where tests expect, or the test expects different module structure.
- Request/context issues: several websocket handler tests failed with "Working outside of request context." They expect a Flask request context for patching `request`/`current_app` or they depend on event registration having run inside an app context.
- Integration assumptions: rate-limit and video metadata tests produced different HTTP statuses (202/400 vs expected 429) or failed metadata extraction (youtube errors). Those tests depend on mocking external services (youtube-dl/yt-dlp) or specific Redis state.
- Value-object exceptions: some unit tests expected ValueError/TypeError on invalid inputs but domain value objects raise domain-specific errors (e.g., `InvalidUrlError`, `InvalidFormatIdError`). Tests make mixed assumptions about error types.

**What I changed while running tests**
- Added `backend/websocket_events.py` shim to expose `api.websocket_events` at top-level so tests that patch `websocket_events` can import it. This was necessary to make the pytest run reach further tests.

**Next steps I recommend (concrete)**
1. Triage failing tests by category (priority order):
   - Fix request context tests: ensure tests that patch `request/current_app` run inside a Flask test request/context fixture or update tests to use `app.test_request_context()`.
   - Standardize module exports: either update modules to expose the symbols tests patch, or update tests to patch the correct import path (prefer patching the exact import path used by the production code).
   - Align domain errors vs tests: either have tests expect domain-specific exceptions (preferred) or map domain exceptions to standard exceptions where appropriate.
   - For integration tests relying on external services (youtube metadata): mock the metadata extractor or provide a deterministic emulator to avoid flaky network-dependent failures.
2. Add CI that runs two jobs: `backend-tests` (pytest) and `frontend-tests` (npm build + vitest). Ensure Redis is started for integration tests and set env flags to mock external services where necessary.
3. Make tests deterministic: mark truly slow/perf tests with pytest markers (`performance`, `e2e`, `integration`) and run them separately in CI (not on every PR).

If you want, I can now:
- open a focused PR that fixes the most common failing patterns (e.g., add a few shims, or update tests to patch `api.*` instead of top-level names), or
- scaffold a `/.github/workflows/ci.yml` that runs the backend/frontend tests in Docker (I can include Redis service and steps to run unit+integration separately).
