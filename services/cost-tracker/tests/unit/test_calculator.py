"""Tests for CostCalculator with mocked collector and Prometheus."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cost_tracker.calculator import CostCalculator, _period_to_hours
from cost_tracker.collector import OpenCostCollector
from cost_tracker.models import CostSummary, InferenceCost, PodCost


class TestCostCalculator:
    """Tests for the CostCalculator class."""

    @pytest.mark.asyncio
    async def test_calculate_inference_costs_with_prometheus(
        self,
        calculator: CostCalculator,
        mock_http_client: AsyncMock,
        sample_pod_costs: list[PodCost],
        prometheus_inference_response: dict,
        prometheus_token_response: dict,
    ) -> None:
        """Full calculation with OpenCost + Prometheus data."""
        # Mock collector.get_pod_costs
        calculator.collector.get_pod_costs = AsyncMock(return_value=sample_pod_costs)

        # Mock Prometheus responses: first call = inference counts,
        # then token enrichment calls
        inference_resp = MagicMock(spec=httpx.Response)
        inference_resp.status_code = 200
        inference_resp.json.return_value = prometheus_inference_response
        inference_resp.raise_for_status = MagicMock()

        token_resp = MagicMock(spec=httpx.Response)
        token_resp.status_code = 200
        token_resp.json.return_value = prometheus_token_response
        token_resp.raise_for_status = MagicMock()

        mock_http_client.get.return_value = inference_resp
        # All subsequent calls (token enrichment) also return token_resp
        mock_http_client.get.side_effect = [inference_resp, token_resp, token_resp]

        costs = await calculator.calculate_inference_costs(period="1h")

        assert len(costs) == 2
        assert all(isinstance(c, InferenceCost) for c in costs)

        # LLM pods: vllm-llama-0 (1.28) + ollama-runner-0 (0.86) = 2.14
        # gateway is NOT an LLM pod
        total_llm_cost = 1.28 + 0.86  # = 2.14
        # llama3.1:8b = 150/200 * 2.14 = 1.605
        llama = next(c for c in costs if c.model == "llama3.1:8b")
        assert llama.inference_count == 150
        assert abs(llama.total_cost_usd - round(total_llm_cost * 150 / 200, 6)) < 0.01

        # codellama:7b = 50/200 * 2.14 = 0.535
        codellama = next(c for c in costs if c.model == "codellama:7b")
        assert codellama.inference_count == 50

    @pytest.mark.asyncio
    async def test_calculate_inference_costs_no_prometheus(
        self,
        calculator: CostCalculator,
        mock_http_client: AsyncMock,
        sample_pod_costs: list[PodCost],
    ) -> None:
        """When Prometheus is unavailable, returns estimated costs."""
        calculator.collector.get_pod_costs = AsyncMock(return_value=sample_pod_costs)
        mock_http_client.get.side_effect = httpx.ConnectError("connection refused")

        costs = await calculator.calculate_inference_costs(period="1h")

        assert len(costs) == 1
        assert costs[0].model == "estimated"
        assert costs[0].inference_count == 100  # 100 per hour * 1 hour
        # Total LLM cost = 1.28 + 0.86 = 2.14
        assert abs(costs[0].total_cost_usd - 2.14) < 0.01

    @pytest.mark.asyncio
    async def test_calculate_inference_costs_no_pods(
        self,
        calculator: CostCalculator,
        mock_http_client: AsyncMock,
    ) -> None:
        """No pods and no Prometheus returns zero cost."""
        calculator.collector.get_pod_costs = AsyncMock(return_value=[])
        mock_http_client.get.side_effect = httpx.ConnectError("connection refused")

        costs = await calculator.calculate_inference_costs(period="24h")

        assert len(costs) == 1
        assert costs[0].model == "unknown"
        assert costs[0].total_cost_usd == 0.0
        assert costs[0].inference_count == 0

    @pytest.mark.asyncio
    async def test_get_summary(
        self,
        calculator: CostCalculator,
        mock_http_client: AsyncMock,
        sample_pod_costs: list[PodCost],
        prometheus_inference_response: dict,
        prometheus_token_response: dict,
    ) -> None:
        """Summary aggregates per-model costs correctly."""
        calculator.collector.get_pod_costs = AsyncMock(return_value=sample_pod_costs)

        inference_resp = MagicMock(spec=httpx.Response)
        inference_resp.status_code = 200
        inference_resp.json.return_value = prometheus_inference_response
        inference_resp.raise_for_status = MagicMock()

        token_resp = MagicMock(spec=httpx.Response)
        token_resp.status_code = 200
        token_resp.json.return_value = prometheus_token_response
        token_resp.raise_for_status = MagicMock()

        mock_http_client.get.side_effect = [inference_resp, token_resp, token_resp]

        summary = await calculator.get_summary(period="1h")

        assert isinstance(summary, CostSummary)
        assert summary.total_inferences == 200
        assert summary.period == "1h"
        assert len(summary.by_model) == 2
        # Total cost should be approximately 2.14 (LLM pods only)
        assert abs(summary.total_cost_usd - 2.14) < 0.01
        assert summary.avg_cost_per_inference > 0

    @pytest.mark.asyncio
    async def test_get_summary_no_data(
        self,
        calculator: CostCalculator,
        mock_http_client: AsyncMock,
    ) -> None:
        """Summary with no data returns zeroed summary."""
        calculator.collector.get_pod_costs = AsyncMock(return_value=[])
        mock_http_client.get.side_effect = httpx.ConnectError("connection refused")

        summary = await calculator.get_summary(period="24h")

        assert summary.total_inferences == 0
        assert summary.total_cost_usd == 0.0
        assert summary.avg_cost_per_inference == 0.0


class TestPeriodToHours:
    """Tests for the _period_to_hours helper."""

    def test_hours(self) -> None:
        assert _period_to_hours("24h") == 24.0

    def test_days(self) -> None:
        assert _period_to_hours("7d") == 168.0

    def test_minutes(self) -> None:
        assert _period_to_hours("30m") == 0.5

    def test_bare_number(self) -> None:
        assert _period_to_hours("12") == 12.0

    def test_invalid(self) -> None:
        assert _period_to_hours("invalid") == 24.0
