"""Cost tracking resolvers.

Stub implementation. Will be wired to cost-tracker service in Phase 9.
"""

from gateway.schema import CostSummary, InferenceCost


def resolve_inference_costs(limit: int = 10) -> list[InferenceCost]:
    """Get recent inference costs."""
    return [
        InferenceCost(
            total_cost_usd=0.002,
            prompt_tokens=150,
            completion_tokens=80,
            model="llama3.1:8b",
        ),
        InferenceCost(
            total_cost_usd=0.005,
            prompt_tokens=300,
            completion_tokens=200,
            model="llama3.1:8b",
        ),
    ][:limit]


def resolve_cost_summary(period: str = "24h") -> CostSummary:
    """Get aggregated cost summary for a time period."""
    return CostSummary(
        total_cost_usd=1.25,
        total_inferences=342,
        avg_cost_per_inference=0.00365,
        period=period,
    )
