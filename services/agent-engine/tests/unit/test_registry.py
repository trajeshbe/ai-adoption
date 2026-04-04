"""Tests for the agent registry factory pattern."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_engine.agents.base import BaseAgent
from agent_engine.registry import AgentRegistry
from agent_platform_common.errors import NotFoundError


class TestAgentRegistry:
    """Test registry register/create/list_types operations."""

    def test_auto_registered_types(self) -> None:
        """Built-in agents (WEATHER, QUIZ, RAG) are auto-registered at import."""
        types = AgentRegistry.list_types()
        assert "WEATHER" in types
        assert "QUIZ" in types
        assert "RAG" in types

    def test_list_types_returns_sorted(self) -> None:
        types = AgentRegistry.list_types()
        assert types == sorted(types)

    def test_create_weather_agent(self, mock_llm_client: MagicMock) -> None:
        agent = AgentRegistry.create("WEATHER", llm_client=mock_llm_client)
        assert isinstance(agent, BaseAgent)
        assert agent.agent_type == "WEATHER"

    def test_create_is_case_insensitive(self, mock_llm_client: MagicMock) -> None:
        agent = AgentRegistry.create("weather", llm_client=mock_llm_client)
        assert agent.agent_type == "WEATHER"

    def test_create_unknown_type_raises_not_found(self, mock_llm_client: MagicMock) -> None:
        with pytest.raises(NotFoundError) as exc_info:
            AgentRegistry.create("NONEXISTENT", llm_client=mock_llm_client)
        assert exc_info.value.code == "NOT_FOUND"

    def test_register_custom_agent(self, mock_llm_client: MagicMock) -> None:
        """Registering a new agent type makes it available via create."""

        class CustomAgent(BaseAgent):
            @property
            def agent_type(self) -> str:
                return "CUSTOM"

            @property
            def system_prompt(self) -> str:
                return "custom"

            @property
            def available_tools(self) -> list[dict]:
                return []

            async def execute_tool(self, tool_name: str, arguments: dict) -> str:
                return "{}"

        AgentRegistry.register("CUSTOM", CustomAgent)
        agent = AgentRegistry.create("CUSTOM", llm_client=mock_llm_client)
        assert agent.agent_type == "CUSTOM"
        assert "CUSTOM" in AgentRegistry.list_types()

        # Clean up to avoid polluting other tests
        del AgentRegistry._registry["CUSTOM"]
