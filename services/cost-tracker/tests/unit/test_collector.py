"""Tests for OpenCostCollector with mocked HTTP responses."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from cost_tracker.collector import OpenCostCollector, _parse_ts
from cost_tracker.models import CostBreakdown, PodCost


class TestOpenCostCollector:
    """Tests for the OpenCostCollector class."""

    @pytest.mark.asyncio
    async def test_get_pod_costs_success(
        self,
        collector: OpenCostCollector,
        mock_http_client: AsyncMock,
        opencost_response: dict,
    ) -> None:
        """Successful pod cost retrieval parses all matching pods."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = opencost_response
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response

        costs = await collector.get_pod_costs(namespace="agent-platform", window="1h")

        assert len(costs) == 3
        assert all(isinstance(c, PodCost) for c in costs)
        vllm_pod = next(c for c in costs if c.pod_name == "vllm-llama-0")
        assert vllm_pod.gpu_cost == 1.20
        assert vllm_pod.total_cost == 1.28

    @pytest.mark.asyncio
    async def test_get_pod_costs_connection_error(
        self,
        collector: OpenCostCollector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Connection error returns empty list instead of raising."""
        mock_http_client.get.side_effect = httpx.ConnectError("connection refused")

        costs = await collector.get_pod_costs()

        assert costs == []

    @pytest.mark.asyncio
    async def test_get_pod_costs_http_error(
        self,
        collector: OpenCostCollector,
        mock_http_client: AsyncMock,
    ) -> None:
        """HTTP error (e.g. 500) returns empty list."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=MagicMock(),
        )
        mock_http_client.get.return_value = mock_response

        costs = await collector.get_pod_costs()

        assert costs == []

    @pytest.mark.asyncio
    async def test_get_pod_costs_empty_data(
        self,
        collector: OpenCostCollector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Empty data array returns empty list."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 200, "data": []}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response

        costs = await collector.get_pod_costs()

        assert costs == []

    @pytest.mark.asyncio
    async def test_get_total_cost_aggregation(
        self,
        collector: OpenCostCollector,
        mock_http_client: AsyncMock,
        opencost_response: dict,
    ) -> None:
        """Total cost correctly aggregates pod costs by resource type."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = opencost_response
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response

        breakdown = await collector.get_total_cost(
            namespace="agent-platform", window="1h"
        )

        assert isinstance(breakdown, CostBreakdown)
        # compute = 0.05 + 0.02 + 0.04 = 0.11
        assert abs(breakdown.compute - 0.11) < 1e-9
        # gpu = 1.20 + 0.0 + 0.80 = 2.00
        assert abs(breakdown.gpu - 2.00) < 1e-9
        # memory = 0.03 + 0.01 + 0.02 = 0.06
        assert abs(breakdown.memory - 0.06) < 1e-9
        # total = 1.28 + 0.03 + 0.86 = 2.17
        assert abs(breakdown.total - 2.17) < 1e-9

    @pytest.mark.asyncio
    async def test_get_total_cost_no_pods(
        self,
        collector: OpenCostCollector,
        mock_http_client: AsyncMock,
    ) -> None:
        """No pods returns zeroed breakdown."""
        mock_http_client.get.side_effect = httpx.ConnectError("connection refused")

        breakdown = await collector.get_total_cost()

        assert breakdown.total == 0.0
        assert breakdown.compute == 0.0
        assert breakdown.gpu == 0.0

    @pytest.mark.asyncio
    async def test_get_pod_costs_filters_namespace(
        self,
        collector: OpenCostCollector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Only pods matching the requested namespace are returned."""
        response_data = {
            "code": 200,
            "data": [
                {
                    "pod-a": {
                        "name": "pod-a",
                        "namespace": "agent-platform",
                        "container": "main",
                        "cpuCost": 0.01,
                        "gpuCost": 0.0,
                        "ramCost": 0.005,
                        "totalCost": 0.015,
                        "start": "2026-01-15T10:00:00Z",
                        "end": "2026-01-15T11:00:00Z",
                    },
                    "pod-b": {
                        "name": "pod-b",
                        "namespace": "kube-system",
                        "container": "main",
                        "cpuCost": 0.01,
                        "gpuCost": 0.0,
                        "ramCost": 0.005,
                        "totalCost": 0.015,
                        "start": "2026-01-15T10:00:00Z",
                        "end": "2026-01-15T11:00:00Z",
                    },
                }
            ],
        }
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response

        costs = await collector.get_pod_costs(namespace="agent-platform")

        assert len(costs) == 1
        assert costs[0].pod_name == "pod-a"


class TestParseTimestamp:
    """Tests for the _parse_ts helper."""

    def test_iso_format(self) -> None:
        result = _parse_ts("2026-01-15T10:00:00Z")
        assert result == datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    def test_empty_string(self) -> None:
        result = _parse_ts("")
        assert result == datetime(1970, 1, 1, tzinfo=timezone.utc)

    def test_invalid_string(self) -> None:
        result = _parse_ts("not-a-date")
        assert result == datetime(1970, 1, 1, tzinfo=timezone.utc)
