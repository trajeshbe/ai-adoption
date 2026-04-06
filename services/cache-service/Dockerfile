# ============================================================================
# Cache Service Dockerfile
# Multi-stage build for minimal production image
# ============================================================================

FROM python:3.11-slim AS base
WORKDIR /app
RUN pip install --no-cache-dir uv

# ── Dependencies layer ────────────────────────────────────────────────
FROM base AS deps
COPY libs/py-common/pyproject.toml /libs/py-common/pyproject.toml
COPY libs/py-common/src /libs/py-common/src
COPY services/cache-service/pyproject.toml .
COPY services/cache-service/src ./src
RUN uv pip install --system --no-cache /libs/py-common && \
    sed -i '/\[tool.uv.sources\]/,/^$/d' pyproject.toml && \
    uv pip install --system --no-cache .

EXPOSE 8002

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

CMD ["uvicorn", "cache_service.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8002"]
