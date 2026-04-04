"""Health and readiness endpoints.

/healthz -- Liveness probe. Returns 200 if the process is running.
            Kubernetes restarts the pod if this fails.

/readyz  -- Readiness probe. Returns 200 if the service can handle traffic.
            Kubernetes removes the pod from the load balancer if this fails.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe -- is the process alive?"""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    """Readiness probe -- can the service handle requests?

    In production, this checks downstream dependencies:
    - Can we reach agent-engine?
    - Can we reach the database?
    - Is the cache service responsive?
    """
    # TODO (Phase 4): Check downstream service health
    return {"status": "ready"}
