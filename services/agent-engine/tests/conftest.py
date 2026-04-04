"""Shared test fixtures for agent-engine tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Return a mock LLMClient with a default chat response."""
    client = MagicMock()
    client.chat = AsyncMock(return_value={
        "content": "Hello from the LLM!",
        "model": "test-model",
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "latency_ms": 50.0,
    })
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Return a mock httpx.AsyncClient."""
    client = AsyncMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"results": []}
    response.raise_for_status = MagicMock()
    client.post = AsyncMock(return_value=response)
    client.get = AsyncMock(return_value=response)
    return client
