# Shared Libraries

## py-common (Python)
Shared code used by all Python microservices:
- `config.py` -- Pydantic Settings for 12-factor config
- `logging.py` -- structlog JSON logging
- `telemetry.py` -- OTEL bootstrap (traces, metrics, logs)
- `errors.py` -- Structured error hierarchy
- `auth.py` -- JWT/OIDC token validation
- `middleware.py` -- Common FastAPI middleware
- `types.py` -- Shared Pydantic models and enums

## ts-common (TypeScript)
Shared code used by the frontend:
- `api-client.ts` -- Generated GraphQL client (codegen)
- `types.ts` -- Shared TypeScript types
- `utils.ts` -- Utility functions

## proto (Protocol Buffers)
Future gRPC service definitions in `agent_platform/v1/agent.proto`.
