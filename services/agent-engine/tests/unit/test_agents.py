"""Tests for agent implementations: WeatherAgent, QuizAgent, RAGAgent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_engine.agents.quiz import QuizAgent
from agent_engine.agents.rag import RAGAgent
from agent_engine.agents.weather import WeatherAgent


# ── WeatherAgent ──────────────────────────────────────────────────────


class TestWeatherAgent:
    def test_agent_type(self, mock_llm_client: MagicMock) -> None:
        agent = WeatherAgent(llm_client=mock_llm_client)
        assert agent.agent_type == "WEATHER"

    def test_system_prompt_mentions_weather(self, mock_llm_client: MagicMock) -> None:
        agent = WeatherAgent(llm_client=mock_llm_client)
        assert "weather" in agent.system_prompt.lower()

    def test_has_get_weather_tool(self, mock_llm_client: MagicMock) -> None:
        agent = WeatherAgent(llm_client=mock_llm_client)
        tools = agent.available_tools
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_execute_tool_get_weather(self, mock_llm_client: MagicMock) -> None:
        agent = WeatherAgent(llm_client=mock_llm_client)
        with patch(
            "agent_engine.agents.weather.get_weather",
            new_callable=AsyncMock,
            return_value={"city": "London", "temperature": "15°C"},
        ):
            result = await agent.execute_tool("get_weather", {"city": "London"})
        parsed = json.loads(result)
        assert parsed["city"] == "London"
        assert parsed["temperature"] == "15°C"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, mock_llm_client: MagicMock) -> None:
        agent = WeatherAgent(llm_client=mock_llm_client)
        result = await agent.execute_tool("unknown_tool", {})
        parsed = json.loads(result)
        assert "error" in parsed


# ── QuizAgent ─────────────────────────────────────────────────────────


class TestQuizAgent:
    def test_agent_type(self, mock_llm_client: MagicMock) -> None:
        agent = QuizAgent(llm_client=mock_llm_client)
        assert agent.agent_type == "QUIZ"

    def test_system_prompt_mentions_quiz(self, mock_llm_client: MagicMock) -> None:
        agent = QuizAgent(llm_client=mock_llm_client)
        assert "quiz" in agent.system_prompt.lower()

    def test_no_tools(self, mock_llm_client: MagicMock) -> None:
        agent = QuizAgent(llm_client=mock_llm_client)
        assert agent.available_tools == []

    @pytest.mark.asyncio
    async def test_execute_tool_returns_error(self, mock_llm_client: MagicMock) -> None:
        agent = QuizAgent(llm_client=mock_llm_client)
        result = await agent.execute_tool("any_tool", {})
        parsed = json.loads(result)
        assert "error" in parsed


# ── RAGAgent ──────────────────────────────────────────────────────────


class TestRAGAgent:
    def test_agent_type(self, mock_llm_client: MagicMock) -> None:
        agent = RAGAgent(llm_client=mock_llm_client)
        assert agent.agent_type == "RAG"

    def test_system_prompt_mentions_documents(self, mock_llm_client: MagicMock) -> None:
        agent = RAGAgent(llm_client=mock_llm_client)
        assert "document" in agent.system_prompt.lower()

    def test_has_search_documents_tool(self, mock_llm_client: MagicMock) -> None:
        agent = RAGAgent(llm_client=mock_llm_client)
        tools = agent.available_tools
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "search_documents"

    @pytest.mark.asyncio
    async def test_execute_tool_search_documents(
        self, mock_llm_client: MagicMock, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post.return_value.json.return_value = {
            "results": [{"text": "relevant chunk", "score": 0.95}]
        }
        agent = RAGAgent(llm_client=mock_llm_client, http_client=mock_http_client)
        result = await agent.execute_tool("search_documents", {"query": "test", "top_k": 3})
        parsed = json.loads(result)
        assert "results" in parsed
        mock_http_client.post.assert_called_once_with(
            "/documents/search",
            json={"query": "test", "top_k": 3},
        )

    @pytest.mark.asyncio
    async def test_execute_tool_no_http_client(self, mock_llm_client: MagicMock) -> None:
        agent = RAGAgent(llm_client=mock_llm_client, http_client=None)
        result = await agent.execute_tool("search_documents", {"query": "test"})
        parsed = json.loads(result)
        assert "error" in parsed
        assert "not configured" in parsed["error"]

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, mock_llm_client: MagicMock) -> None:
        agent = RAGAgent(llm_client=mock_llm_client)
        result = await agent.execute_tool("bad_tool", {})
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_execute_tool_http_error(
        self, mock_llm_client: MagicMock, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post = AsyncMock(side_effect=Exception("connection refused"))
        agent = RAGAgent(llm_client=mock_llm_client, http_client=mock_http_client)
        result = await agent.execute_tool("search_documents", {"query": "test"})
        parsed = json.loads(result)
        assert "error" in parsed
        assert "failed" in parsed["error"].lower()
