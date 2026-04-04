"""Cost calculator that correlates OpenCost data with inference metrics.

Combines pod-level cost data from OpenCost with inference counts from Prometheus
to calculate $/inference for each LLM model.
"""

from __future__ import annotations

import httpx
import structlog

from cost_tracker.collector import OpenCostCollector
from cost_tracker.models import CostSummary, InferenceCost

logger = structlog.get_logger()

# Pod name patterns that indicate LLM runtime workloads
LLM_POD_PREFIXES = ("vllm", "llm-runtime", "ollama", "llama", "ray-worker")


class CostCalculator:
    """Calculates $/inference by correlating pod costs with inference counts."""

    def __init__(
        self,
        collector: OpenCostCollector,
        prometheus_url: str = "http://prometheus:9090",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.collector = collector
        self.prometheus_url = prometheus_url.rstrip("/")
        self._client = http_client or httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def calculate_inference_costs(
        self,
        period: str = "24h",
    ) -> list[InferenceCost]:
        """Calculate per-model $/inference costs.

        Steps:
        1. Get pod costs from OpenCost (filtered to LLM runtime pods).
        2. Query Prometheus for inference counts per model.
        3. Divide total pod cost by inference count for each model.

        Args:
            period: Time window (e.g. '1h', '24h', '7d').

        Returns:
            Per-model InferenceCost list. Returns estimated data if Prometheus
            is unavailable.
        """
        # Step 1: Get LLM pod costs
        all_pods = await self.collector.get_pod_costs(
            namespace="agent-platform",
            window=period,
        )
        llm_pods = [
            p for p in all_pods
            if any(p.pod_name.startswith(prefix) for prefix in LLM_POD_PREFIXES)
        ]
        total_llm_cost = sum(p.total_cost for p in llm_pods)

        # Step 2: Query Prometheus for inference counts
        model_metrics = await self._query_inference_metrics(period)

        # Step 3: Calculate per-model costs
        if not model_metrics:
            # No Prometheus data -- return estimated breakdown
            return self._estimated_costs(total_llm_cost, period)

        total_inferences = sum(m["count"] for m in model_metrics)
        inference_costs: list[InferenceCost] = []

        for metric in model_metrics:
            model_name = metric["model"]
            count = metric["count"]
            prompt_tokens = metric.get("prompt_tokens", 0)
            completion_tokens = metric.get("completion_tokens", 0)

            # Proportional cost allocation based on inference count
            if total_inferences > 0:
                model_cost = total_llm_cost * (count / total_inferences)
            else:
                model_cost = 0.0

            cost_per_inference = model_cost / count if count > 0 else 0.0

            inference_costs.append(
                InferenceCost(
                    model=model_name,
                    total_cost_usd=round(model_cost, 6),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    inference_count=count,
                    cost_per_inference=round(cost_per_inference, 6),
                    period=period,
                )
            )

        return inference_costs

    async def get_summary(self, period: str = "24h") -> CostSummary:
        """Get an aggregated cost summary across all models.

        Args:
            period: Time window for the summary.

        Returns:
            CostSummary with totals and per-model breakdown.
        """
        by_model = await self.calculate_inference_costs(period)

        total_cost = sum(m.total_cost_usd for m in by_model)
        total_inferences = sum(m.inference_count for m in by_model)
        avg_cost = total_cost / total_inferences if total_inferences > 0 else 0.0

        return CostSummary(
            total_cost_usd=round(total_cost, 6),
            total_inferences=total_inferences,
            avg_cost_per_inference=round(avg_cost, 6),
            period=period,
            by_model=by_model,
        )

    async def _query_inference_metrics(
        self,
        period: str,
    ) -> list[dict]:
        """Query Prometheus for inference counts grouped by model.

        Queries: sum(inference_total) by (model)

        Returns:
            List of dicts with 'model', 'count', 'prompt_tokens', 'completion_tokens'.
            Empty list if Prometheus is unavailable.
        """
        query = 'sum(inference_total) by (model)'
        url = f"{self.prometheus_url}/api/v1/query"

        try:
            response = await self._client.get(url, params={"query": query})
            response.raise_for_status()
            data = response.json()

            results: list[dict] = []
            for result in data.get("data", {}).get("result", []):
                model = result.get("metric", {}).get("model", "unknown")
                count = int(float(result.get("value", [0, "0"])[1]))
                results.append({
                    "model": model,
                    "count": count,
                    "prompt_tokens": 0,  # Token counts from separate metric
                    "completion_tokens": 0,
                })

            # Query token counts if available
            await self._enrich_token_counts(results, period)
            return results

        except (httpx.HTTPError, httpx.ConnectError, KeyError, ValueError) as exc:
            await logger.awarning(
                "prometheus_query_failed",
                url=url,
                error=str(exc),
            )
            return []

    async def _enrich_token_counts(
        self,
        results: list[dict],
        period: str,
    ) -> None:
        """Enrich results with prompt/completion token counts from Prometheus."""
        for token_type in ("prompt", "completion"):
            query = f'sum(inference_{token_type}_tokens_total) by (model)'
            url = f"{self.prometheus_url}/api/v1/query"

            try:
                response = await self._client.get(url, params={"query": query})
                response.raise_for_status()
                data = response.json()

                token_map: dict[str, int] = {}
                for result in data.get("data", {}).get("result", []):
                    model = result.get("metric", {}).get("model", "unknown")
                    tokens = int(float(result.get("value", [0, "0"])[1]))
                    token_map[model] = tokens

                for r in results:
                    r[f"{token_type}_tokens"] = token_map.get(r["model"], 0)

            except (httpx.HTTPError, httpx.ConnectError, KeyError, ValueError):
                pass  # Token enrichment is best-effort

    def _estimated_costs(
        self,
        total_llm_cost: float,
        period: str,
    ) -> list[InferenceCost]:
        """Return estimated costs when Prometheus is unavailable.

        Uses the total LLM pod cost with an estimated inference count
        based on typical throughput.
        """
        if total_llm_cost <= 0:
            return [
                InferenceCost(
                    model="unknown",
                    total_cost_usd=0.0,
                    prompt_tokens=0,
                    completion_tokens=0,
                    inference_count=0,
                    cost_per_inference=0.0,
                    period=period,
                )
            ]

        # Estimate: assume ~100 inferences per hour for a running LLM pod
        hours = _period_to_hours(period)
        estimated_count = int(100 * hours)
        cost_per = total_llm_cost / estimated_count if estimated_count > 0 else 0.0

        return [
            InferenceCost(
                model="estimated",
                total_cost_usd=round(total_llm_cost, 6),
                prompt_tokens=0,
                completion_tokens=0,
                inference_count=estimated_count,
                cost_per_inference=round(cost_per, 6),
                period=period,
            )
        ]


def _period_to_hours(period: str) -> float:
    """Convert a period string like '24h' or '7d' to hours."""
    period = period.strip().lower()
    try:
        if period.endswith("d"):
            return float(period[:-1]) * 24
        if period.endswith("h"):
            return float(period[:-1])
        if period.endswith("m"):
            return float(period[:-1]) / 60
        # Default: treat as hours
        return float(period)
    except ValueError:
        return 24.0
