"""Tests for CircuitBreaker and LLMClient."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_engine.llm_client import CircuitBreaker, CircuitState, LLMClient


# ── CircuitBreaker tests ──────────────────────────────────────────────


class TestCircuitBreaker:
    """Test circuit breaker state transitions."""

    def test_initial_state_is_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_should_use_primary_when_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.should_use_primary is True

    def test_single_failure_stays_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.should_use_primary is True

    def test_transitions_to_open_after_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.should_use_primary is False

    def test_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        # After success, counter resets -- need 3 more failures to open
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_open_transitions_to_half_open_after_timeout(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        # Wait for recovery timeout
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.should_use_primary is True

    def test_half_open_success_returns_to_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_returns_to_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


# ── LLMClient tests ──────────────────────────────────────────────────


def _make_mock_completion(content: str = "response", model: str = "test-model"):
    """Build a mock OpenAI ChatCompletion response object."""
    message = MagicMock()
    message.content = content
    message.tool_calls = None

    choice = MagicMock()
    choice.message = message

    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 20

    response = MagicMock()
    response.choices = [choice]
    response.model = model
    response.usage = usage
    return response


class TestLLMClient:
    """Test LLMClient with mocked OpenAI clients."""

    @pytest.mark.asyncio
    async def test_primary_success(self) -> None:
        """When primary succeeds, return its response."""
        with patch("agent_engine.llm_client.AsyncOpenAI") as MockOpenAI:
            primary = MagicMock()
            primary.chat.completions.create = AsyncMock(
                return_value=_make_mock_completion("primary answer")
            )
            fallback = MagicMock()
            fallback.chat.completions.create = AsyncMock()

            MockOpenAI.side_effect = [primary, fallback]

            client = LLMClient(
                primary_url="http://primary:8000/v1",
                fallback_url="http://fallback:8000/v1",
                model="test-model",
            )

            result = await client.chat(messages=[{"role": "user", "content": "hi"}])

        assert result["content"] == "primary answer"
        assert result["model"] == "test-model"
        assert result["prompt_tokens"] == 10
        fallback.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_primary_fails_fallback_succeeds(self) -> None:
        """When primary fails, fall back to secondary."""
        with patch("agent_engine.llm_client.AsyncOpenAI") as MockOpenAI:
            primary = MagicMock()
            primary.chat.completions.create = AsyncMock(
                side_effect=Exception("primary down")
            )
            fallback = MagicMock()
            fallback.chat.completions.create = AsyncMock(
                return_value=_make_mock_completion("fallback answer", "fallback-model")
            )

            MockOpenAI.side_effect = [primary, fallback]

            client = LLMClient(
                primary_url="http://primary:8000/v1",
                fallback_url="http://fallback:8000/v1",
                model="test-model",
            )

            result = await client.chat(messages=[{"role": "user", "content": "hi"}])

        assert result["content"] == "fallback answer"

    @pytest.mark.asyncio
    async def test_both_fail_raises_llm_error(self) -> None:
        """When both primary and fallback fail, raise LLMError."""
        from agent_platform_common.errors import LLMError

        with patch("agent_engine.llm_client.AsyncOpenAI") as MockOpenAI:
            primary = MagicMock()
            primary.chat.completions.create = AsyncMock(
                side_effect=Exception("primary down")
            )
            fallback = MagicMock()
            fallback.chat.completions.create = AsyncMock(
                side_effect=Exception("fallback down")
            )

            MockOpenAI.side_effect = [primary, fallback]

            client = LLMClient(
                primary_url="http://primary:8000/v1",
                fallback_url="http://fallback:8000/v1",
                model="test-model",
            )

            with pytest.raises(LLMError, match="Both primary and fallback"):
                await client.chat(messages=[{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_tool_calls_extracted(self) -> None:
        """When the LLM returns tool_calls, they are included in the result."""
        tc = MagicMock()
        tc.id = "call_123"
        tc.function.name = "get_weather"
        tc.function.arguments = '{"city": "London"}'

        message = MagicMock()
        message.content = ""
        message.tool_calls = [tc]

        choice = MagicMock()
        choice.message = message

        usage = MagicMock()
        usage.prompt_tokens = 5
        usage.completion_tokens = 15

        response = MagicMock()
        response.choices = [choice]
        response.model = "test-model"
        response.usage = usage

        with patch("agent_engine.llm_client.AsyncOpenAI") as MockOpenAI:
            primary = MagicMock()
            primary.chat.completions.create = AsyncMock(return_value=response)
            fallback = MagicMock()

            MockOpenAI.side_effect = [primary, fallback]

            client = LLMClient(
                primary_url="http://primary:8000/v1",
                fallback_url="http://fallback:8000/v1",
                model="test-model",
            )

            result = await client.chat(messages=[{"role": "user", "content": "weather"}])

        assert "tool_calls" in result
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "get_weather"
        assert result["tool_calls"][0]["id"] == "call_123"
