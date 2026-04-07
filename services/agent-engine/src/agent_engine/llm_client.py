"""LLM client with vLLM primary and llama.cpp CPU fallback.

Uses circuit breaker pattern: after N consecutive failures on primary,
switches to fallback for a cooldown period before retrying primary.
"""

from __future__ import annotations

import enum
import time

import structlog
from openai import AsyncOpenAI

from agent_platform_common.errors import LLMError

logger = structlog.get_logger()


class CircuitState(str, enum.Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests go to primary
    OPEN = "open"  # Primary failed too many times, using fallback
    HALF_OPEN = "half_open"  # Testing if primary has recovered


class CircuitBreaker:
    """Circuit breaker for LLM endpoint resilience.

    CLOSED  -> primary works normally. Failures increment counter.
    OPEN    -> after failure_threshold consecutive failures, all traffic
               goes to fallback for recovery_timeout seconds.
    HALF_OPEN -> after cooldown expires, one request is sent to primary.
                 If it succeeds, state returns to CLOSED. If it fails,
                 state returns to OPEN with a fresh cooldown.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        """Return current state, transitioning OPEN -> HALF_OPEN if cooldown expired."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    @property
    def should_use_primary(self) -> bool:
        """True if the circuit allows a request to primary."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Record a successful request to primary."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed request to primary."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                failure_count=self._failure_count,
                recovery_timeout=self.recovery_timeout,
            )


class LLMClient:
    """Unified LLM client targeting OpenAI-compatible endpoints (vLLM / llama.cpp / OpenAI).

    Tries the primary endpoint first. On failure, consults the circuit breaker
    to decide whether to fall back to the secondary endpoint.
    """

    def __init__(
        self,
        primary_url: str,
        fallback_url: str,
        model: str,
        timeout: float = 60.0,
        api_key: str = "not-needed",
    ) -> None:
        self.model = model
        self._primary = AsyncOpenAI(base_url=primary_url, api_key=api_key, timeout=timeout)
        self._fallback = AsyncOpenAI(base_url=fallback_url, api_key=api_key, timeout=timeout)
        self._circuit = CircuitBreaker()

    @classmethod
    def for_provider(
        cls,
        provider: str,
        model: str,
        api_key: str = "",
        fallback_url: str = "http://localhost:8080/v1",
        default_primary_url: str = "http://localhost:11434/v1",
    ) -> "LLMClient":
        """Create an LLMClient for a specific provider.

        Supported providers: "ollama" (default), "openai".
        """
        if provider.lower() == "openai":
            return cls(
                primary_url="https://api.openai.com/v1",
                fallback_url=fallback_url,
                model=model or "gpt-4o-mini",
                api_key=api_key,
            )
        # Default: Ollama / vLLM / llama.cpp
        return cls(
            primary_url=default_primary_url,
            fallback_url=fallback_url,
            model=model or "qwen2.5:1.5b",
        )

    # ── Public API ────────────────────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        tools: list[dict] | None = None,
    ) -> dict:
        """Send a chat completion request with automatic failover.

        Returns:
            dict with keys: content, model, prompt_tokens, completion_tokens,
            latency_ms, tool_calls (optional).
        """
        if self._circuit.should_use_primary:
            try:
                return await self._call(self._primary, messages, temperature, max_tokens, tools)
            except Exception as exc:
                self._circuit.record_failure()
                await logger.awarning("primary_llm_failed", error=str(exc))
        else:
            await logger.ainfo(
                "circuit_open_skipping_primary",
                state=self._circuit.state.value,
            )

        # Fallback attempt
        try:
            result = await self._call(self._fallback, messages, temperature, max_tokens, tools)
            return result
        except Exception as fallback_exc:
            raise LLMError(
                f"Both primary and fallback LLM endpoints failed: {fallback_exc}"
            ) from fallback_exc

    async def close(self) -> None:
        """Close underlying HTTP connections."""
        await self._primary.close()
        await self._fallback.close()

    # ── Internal ──────────────────────────────────────────────────────────

    async def _call(
        self,
        client: AsyncOpenAI,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        tools: list[dict] | None,
    ) -> dict:
        """Execute a single chat completion request."""
        start = time.perf_counter()

        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await client.chat.completions.create(**kwargs)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        choice = response.choices[0]
        message = choice.message

        result: dict = {
            "content": message.content or "",
            "model": response.model,
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "latency_ms": latency_ms,
        }

        # Extract tool calls if present
        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in message.tool_calls
            ]

        # Record success for circuit breaker (only matters for primary)
        if client is self._primary:
            self._circuit.record_success()

        return result
