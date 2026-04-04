"""Pydantic models for cost tracking and $/inference calculations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PodCost(BaseModel):
    """Cost data for a single Kubernetes pod from OpenCost."""

    pod_name: str
    namespace: str
    container: str
    cpu_cost: float = Field(ge=0, description="CPU cost in USD")
    gpu_cost: float = Field(ge=0, description="GPU cost in USD")
    memory_cost: float = Field(ge=0, description="Memory cost in USD")
    total_cost: float = Field(ge=0, description="Total cost in USD")
    window_start: datetime
    window_end: datetime


class InferenceCost(BaseModel):
    """Per-model inference cost breakdown."""

    model: str
    total_cost_usd: float = Field(ge=0)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    inference_count: int = Field(ge=0)
    cost_per_inference: float = Field(ge=0)
    period: str = Field(description="Time period, e.g. '24h'")


class CostSummary(BaseModel):
    """Aggregated cost summary across all models."""

    total_cost_usd: float = Field(ge=0)
    total_inferences: int = Field(ge=0)
    avg_cost_per_inference: float = Field(ge=0)
    period: str
    by_model: list[InferenceCost] = Field(default_factory=list)


class CostBreakdown(BaseModel):
    """Cost breakdown by resource type."""

    compute: float = Field(ge=0, description="CPU compute cost in USD")
    memory: float = Field(ge=0, description="Memory cost in USD")
    gpu: float = Field(ge=0, description="GPU cost in USD")
    storage: float = Field(ge=0, default=0.0, description="Storage cost in USD")
    network: float = Field(ge=0, default=0.0, description="Network cost in USD")
    total: float = Field(ge=0, description="Total cost in USD")
