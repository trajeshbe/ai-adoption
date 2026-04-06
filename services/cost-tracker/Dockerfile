# ============================================================================
# Cost Tracker Service Dockerfile
# Multi-stage build for minimal production image
# ============================================================================

FROM python:3.11-slim AS base
WORKDIR /app
RUN pip install --no-cache-dir uv

# -- Dependencies layer (cached unless pyproject.toml changes) ----------------
FROM base AS deps
COPY libs/py-common/pyproject.toml /libs/py-common/pyproject.toml
COPY libs/py-common/src /libs/py-common/src
COPY services/cost-tracker/pyproject.toml .
RUN uv pip install --system --no-cache /libs/py-common && \
    sed -i '/\[tool.uv.sources\]/,/^$/d' pyproject.toml && \
    uv pip install --system --no-cache -e .

# -- Runtime layer ------------------------------------------------------------
FROM deps AS runtime
COPY services/cost-tracker/src ./src

EXPOSE 8004

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

CMD ["uvicorn", "cost_tracker.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8004"]
