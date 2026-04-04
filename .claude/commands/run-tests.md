# Run Tests -- Execute the Full Test Suite

## Usage
Run this command to execute all tests across the monorepo.

## What It Does
1. **Unit tests (Python):** `uv run pytest services/*/tests/unit/ libs/py-common/tests/ -v --tb=short`
2. **Unit tests (TypeScript):** `cd frontend && pnpm test`
3. **Integration tests:** `uv run pytest services/*/tests/integration/ tests/integration/ -v`
4. **Type checking:** `uv run mypy services/ libs/py-common/ --strict`
5. **Linting:** `uv run ruff check services/ libs/py-common/`

## Instructions
Run each test layer in order. Stop at the first failure and fix it before proceeding.
Unit tests should run in < 30 seconds. Integration tests require local infra (Postgres, Redis, MinIO).

If a test fails:
1. Read the error message and traceback
2. Identify the failing assertion
3. Fix the code (not the test, unless the test is wrong)
4. Re-run only the failing test: `uv run pytest path/to/test.py::test_name -v`
5. Once fixed, re-run the full suite to check for regressions
