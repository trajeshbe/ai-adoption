"""Tests for cost-tracker Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cost_tracker.models import CostBreakdown, CostSummary, InferenceCost, PodCost


class TestPodCost:
    """Tests for the PodCost model."""

    def test_create_valid(self) -> None:
        pod = PodCost(
            pod_name="vllm-llama-0",
            namespace="agent-platform",
            container="vllm",
            cpu_cost=0.05,
            gpu_cost=1.20,
            memory_cost=0.03,
            total_cost=1.28,
            window_start=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
            window_end=datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
        )
        assert pod.pod_name == "vllm-llama-0"
        assert pod.namespace == "agent-platform"
        assert pod.gpu_cost == 1.20
        assert pod.total_cost == 1.28

    def test_serialization_roundtrip(self) -> None:
        pod = PodCost(
            pod_name="test-pod",
            namespace="default",
            container="main",
            cpu_cost=0.01,
            gpu_cost=0.0,
            memory_cost=0.005,
            total_cost=0.015,
            window_start=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
            window_end=datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
        )
        data = pod.model_dump(mode="json")
        restored = PodCost(**data)
        assert restored.pod_name == pod.pod_name
        assert restored.total_cost == pod.total_cost

    def test_negative_cost_rejected(self) -> None:
        with pytest.raises(ValueError):
            PodCost(
                pod_name="bad-pod",
                namespace="default",
                container="main",
                cpu_cost=-0.01,
                gpu_cost=0.0,
                memory_cost=0.0,
                total_cost=0.0,
                window_start=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
                window_end=datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
            )


class TestInferenceCost:
    """Tests for the InferenceCost model."""

    def test_create_valid(self) -> None:
        ic = InferenceCost(
            model="llama3.1:8b",
            total_cost_usd=1.28,
            prompt_tokens=50000,
            completion_tokens=25000,
            inference_count=150,
            cost_per_inference=0.008533,
            period="24h",
        )
        assert ic.model == "llama3.1:8b"
        assert ic.inference_count == 150
        assert ic.period == "24h"

    def test_zero_inferences(self) -> None:
        ic = InferenceCost(
            model="unused-model",
            total_cost_usd=0.0,
            prompt_tokens=0,
            completion_tokens=0,
            inference_count=0,
            cost_per_inference=0.0,
            period="1h",
        )
        assert ic.inference_count == 0
        assert ic.cost_per_inference == 0.0

    def test_negative_tokens_rejected(self) -> None:
        with pytest.raises(ValueError):
            InferenceCost(
                model="bad",
                total_cost_usd=0.0,
                prompt_tokens=-1,
                completion_tokens=0,
                inference_count=0,
                cost_per_inference=0.0,
                period="1h",
            )


class TestCostSummary:
    """Tests for the CostSummary model."""

    def test_create_with_models(self) -> None:
        model_cost = InferenceCost(
            model="llama3.1:8b",
            total_cost_usd=1.28,
            prompt_tokens=50000,
            completion_tokens=25000,
            inference_count=150,
            cost_per_inference=0.008533,
            period="24h",
        )
        summary = CostSummary(
            total_cost_usd=1.28,
            total_inferences=150,
            avg_cost_per_inference=0.008533,
            period="24h",
            by_model=[model_cost],
        )
        assert summary.total_inferences == 150
        assert len(summary.by_model) == 1
        assert summary.by_model[0].model == "llama3.1:8b"

    def test_empty_models(self) -> None:
        summary = CostSummary(
            total_cost_usd=0.0,
            total_inferences=0,
            avg_cost_per_inference=0.0,
            period="1h",
        )
        assert summary.by_model == []


class TestCostBreakdown:
    """Tests for the CostBreakdown model."""

    def test_create_valid(self) -> None:
        bd = CostBreakdown(
            compute=0.50,
            memory=0.10,
            gpu=2.00,
            storage=0.05,
            network=0.01,
            total=2.66,
        )
        assert bd.gpu == 2.00
        assert bd.total == 2.66

    def test_defaults_for_optional(self) -> None:
        bd = CostBreakdown(
            compute=0.10,
            memory=0.05,
            gpu=0.0,
            total=0.15,
        )
        assert bd.storage == 0.0
        assert bd.network == 0.0

    def test_serialization(self) -> None:
        bd = CostBreakdown(
            compute=0.50,
            memory=0.10,
            gpu=2.00,
            storage=0.0,
            network=0.0,
            total=2.60,
        )
        data = bd.model_dump()
        assert data["gpu"] == 2.00
        assert data["total"] == 2.60
