"""Shared fixtures for cost-tracker tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

from cost_tracker.collector import OpenCostCollector
from cost_tracker.calculator import CostCalculator
from cost_tracker.models import PodCost


@pytest.fixture
def sample_datetime() -> datetime:
    """A deterministic datetime for test assertions."""
    return datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """A mocked httpx.AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def opencost_response() -> dict:
    """Sample OpenCost allocation API response."""
    return {
        "code": 200,
        "data": [
            {
                "vllm-llama-0": {
                    "name": "vllm-llama-0",
                    "namespace": "agent-platform",
                    "container": "vllm",
                    "cpuCost": 0.05,
                    "gpuCost": 1.20,
                    "ramCost": 0.03,
                    "totalCost": 1.28,
                    "start": "2026-01-15T10:00:00Z",
                    "end": "2026-01-15T11:00:00Z",
                },
                "gateway-abc123": {
                    "name": "gateway-abc123",
                    "namespace": "agent-platform",
                    "container": "gateway",
                    "cpuCost": 0.02,
                    "gpuCost": 0.0,
                    "ramCost": 0.01,
                    "totalCost": 0.03,
                    "start": "2026-01-15T10:00:00Z",
                    "end": "2026-01-15T11:00:00Z",
                },
                "ollama-runner-0": {
                    "name": "ollama-runner-0",
                    "namespace": "agent-platform",
                    "container": "ollama",
                    "cpuCost": 0.04,
                    "gpuCost": 0.80,
                    "ramCost": 0.02,
                    "totalCost": 0.86,
                    "start": "2026-01-15T10:00:00Z",
                    "end": "2026-01-15T11:00:00Z",
                },
            }
        ],
    }


@pytest.fixture
def prometheus_inference_response() -> dict:
    """Sample Prometheus query response for inference_total."""
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"model": "llama3.1:8b"},
                    "value": [1705312200, "150"],
                },
                {
                    "metric": {"model": "codellama:7b"},
                    "value": [1705312200, "50"],
                },
            ],
        },
    }


@pytest.fixture
def prometheus_token_response() -> dict:
    """Sample Prometheus query response for token counts."""
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"model": "llama3.1:8b"},
                    "value": [1705312200, "75000"],
                },
                {
                    "metric": {"model": "codellama:7b"},
                    "value": [1705312200, "25000"],
                },
            ],
        },
    }


@pytest.fixture
def sample_pod_costs() -> list[PodCost]:
    """Pre-built PodCost list for calculator tests."""
    return [
        PodCost(
            pod_name="vllm-llama-0",
            namespace="agent-platform",
            container="vllm",
            cpu_cost=0.05,
            gpu_cost=1.20,
            memory_cost=0.03,
            total_cost=1.28,
            window_start=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
            window_end=datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
        ),
        PodCost(
            pod_name="gateway-abc123",
            namespace="agent-platform",
            container="gateway",
            cpu_cost=0.02,
            gpu_cost=0.0,
            memory_cost=0.01,
            total_cost=0.03,
            window_start=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
            window_end=datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
        ),
        PodCost(
            pod_name="ollama-runner-0",
            namespace="agent-platform",
            container="ollama",
            cpu_cost=0.04,
            gpu_cost=0.80,
            memory_cost=0.02,
            total_cost=0.86,
            window_start=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
            window_end=datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
        ),
    ]


@pytest.fixture
def collector(mock_http_client: AsyncMock) -> OpenCostCollector:
    """OpenCostCollector with mocked HTTP client."""
    return OpenCostCollector(
        opencost_url="http://opencost-test:9003",
        http_client=mock_http_client,
    )


@pytest.fixture
def calculator(
    collector: OpenCostCollector,
    mock_http_client: AsyncMock,
) -> CostCalculator:
    """CostCalculator with mocked collector and HTTP client."""
    return CostCalculator(
        collector=collector,
        prometheus_url="http://prometheus-test:9090",
        http_client=mock_http_client,
    )
