"""OpenCost API collector for per-pod cost data.

Polls the OpenCost allocation API and transforms responses into typed PodCost models.
Handles connection errors gracefully by returning empty results.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import structlog

from cost_tracker.models import CostBreakdown, PodCost

logger = structlog.get_logger()


class OpenCostCollector:
    """Collects cost allocation data from the OpenCost API."""

    def __init__(
        self,
        opencost_url: str = "http://opencost.opencost:9003",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.opencost_url = opencost_url.rstrip("/")
        self._client = http_client or httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def get_pod_costs(
        self,
        namespace: str = "agent-platform",
        window: str = "1h",
    ) -> list[PodCost]:
        """Fetch per-pod cost allocations from OpenCost.

        Args:
            namespace: Kubernetes namespace to filter by.
            window: Time window for the query (e.g. '1h', '24h', '7d').

        Returns:
            List of PodCost entries. Empty list on connection failure.
        """
        url = f"{self.opencost_url}/allocation/compute"
        params = {"window": window, "namespace": namespace}

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return self._parse_allocation_response(data, namespace)
        except (httpx.HTTPError, httpx.ConnectError, KeyError, ValueError) as exc:
            await logger.awarning(
                "opencost_request_failed",
                url=url,
                error=str(exc),
            )
            return []

    def _parse_allocation_response(
        self,
        data: dict,
        namespace: str,
    ) -> list[PodCost]:
        """Parse the OpenCost allocation API JSON response.

        OpenCost returns: {"code": 200, "data": [{"pod-name": {...}, ...}]}
        Each allocation object has cpuCost, gpuCost, ramCost, totalCost, etc.
        """
        pod_costs: list[PodCost] = []

        # OpenCost wraps results in a "data" array of window dicts
        allocations_list = data.get("data", [])
        if not allocations_list:
            return pod_costs

        # Each element in data is a dict of {pod_name: allocation_info}
        for window_data in allocations_list:
            if not isinstance(window_data, dict):
                continue
            for pod_name, alloc in window_data.items():
                if not isinstance(alloc, dict):
                    continue
                if alloc.get("namespace", "") != namespace:
                    continue

                pod_costs.append(
                    PodCost(
                        pod_name=alloc.get("name", pod_name),
                        namespace=alloc.get("namespace", namespace),
                        container=alloc.get("container", ""),
                        cpu_cost=float(alloc.get("cpuCost", 0)),
                        gpu_cost=float(alloc.get("gpuCost", 0)),
                        memory_cost=float(alloc.get("ramCost", 0)),
                        total_cost=float(alloc.get("totalCost", 0)),
                        window_start=_parse_ts(alloc.get("start", "")),
                        window_end=_parse_ts(alloc.get("end", "")),
                    )
                )

        return pod_costs

    async def get_total_cost(
        self,
        namespace: str = "agent-platform",
        window: str = "24h",
    ) -> CostBreakdown:
        """Aggregate pod costs into a resource-type breakdown.

        Args:
            namespace: Kubernetes namespace to filter by.
            window: Time window for the query.

        Returns:
            CostBreakdown with compute, memory, gpu, and total costs.
            Returns zeroed breakdown on failure.
        """
        pods = await self.get_pod_costs(namespace=namespace, window=window)

        if not pods:
            return CostBreakdown(
                compute=0.0, memory=0.0, gpu=0.0, storage=0.0, network=0.0, total=0.0
            )

        compute = sum(p.cpu_cost for p in pods)
        memory = sum(p.memory_cost for p in pods)
        gpu = sum(p.gpu_cost for p in pods)
        total = sum(p.total_cost for p in pods)

        return CostBreakdown(
            compute=compute,
            memory=memory,
            gpu=gpu,
            storage=0.0,  # OpenCost allocation API doesn't split storage per pod
            network=0.0,  # Network costs tracked separately
            total=total,
        )


def _parse_ts(value: str) -> datetime:
    """Parse an ISO timestamp string, returning epoch on failure."""
    if not value:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
