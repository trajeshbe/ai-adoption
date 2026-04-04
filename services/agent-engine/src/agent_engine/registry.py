"""Agent registry -- factory pattern for creating agents by type."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from agent_platform_common.errors import NotFoundError

if TYPE_CHECKING:
    import httpx

    from agent_engine.agents.base import BaseAgent
    from agent_engine.llm_client import LLMClient

logger = structlog.get_logger()


class AgentRegistry:
    """Maps agent type strings to agent classes.

    Agents register themselves at import time. The gateway (or flow) can
    then create an agent instance by type string without knowing the
    concrete class.
    """

    _registry: dict[str, type[BaseAgent]] = {}

    @classmethod
    def register(cls, agent_type: str, agent_class: type[BaseAgent]) -> None:
        """Register an agent class for a given type string."""
        cls._registry[agent_type.upper()] = agent_class
        logger.debug("agent_registered", agent_type=agent_type.upper())

    @classmethod
    def create(
        cls,
        agent_type: str,
        llm_client: LLMClient,
        http_client: httpx.AsyncClient | None = None,
    ) -> BaseAgent:
        """Create an agent instance by type string.

        Raises:
            NotFoundError: if agent_type is not registered.
        """
        key = agent_type.upper()
        agent_cls = cls._registry.get(key)
        if agent_cls is None:
            raise NotFoundError("AgentType", key)
        return agent_cls(llm_client=llm_client, http_client=http_client)

    @classmethod
    def list_types(cls) -> list[str]:
        """Return all registered agent type strings."""
        return sorted(cls._registry.keys())


# ── Auto-register built-in agents ─────────────────────────────────────

def _auto_register() -> None:
    from agent_engine.agents.quiz import QuizAgent
    from agent_engine.agents.rag import RAGAgent
    from agent_engine.agents.weather import WeatherAgent

    AgentRegistry.register("WEATHER", WeatherAgent)
    AgentRegistry.register("QUIZ", QuizAgent)
    AgentRegistry.register("RAG", RAGAgent)


_auto_register()
