# Cross-Cutting Tests

## Directories
- `e2e/` -- Full end-to-end tests (frontend -> gateway -> agents -> LLM)
- `integration/` -- Service contract tests (gateway <-> agent-engine API shape)
- `load/` -- Locust + k6 load tests targeting gateway GraphQL
- `chaos/litmus/` -- LitmusChaos experiments (pod kill, network delay)
- `security/` -- Trivy container scan config, OWASP ZAP DAST config

## Running
```bash
make test            # Unit tests only (fast, no infra needed)
make test-integration # Integration tests (requires PG, Redis, MinIO)
make test-e2e        # E2E tests (requires all services running)
make test-load       # Load tests (Locust, 100 users, 60s)
```
