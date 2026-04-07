"""Prefect flow wrapping LangGraph agent execution.

Provides operational reliability: retries, timeouts, observability,
and structured logging for every agent invocation.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from prefect import flow, task

from agent_platform_common.config import Settings

from agent_engine.agents.base import AgentResponse
from agent_engine.graphs.agent_graph import build_agent_graph
from agent_engine.llm_client import LLMClient
from agent_engine.registry import AgentRegistry

logger = structlog.get_logger()


@task(name="create-llm-client", retries=0)
def create_llm_client(settings: Settings) -> LLMClient:
    """Instantiate the LLM client from settings."""
    return LLMClient(
        primary_url=settings.llm_primary_url,
        fallback_url=settings.llm_fallback_url,
        model=settings.llm_model,
    )


@task(name="create-agent", retries=0)
def create_agent(
    agent_type: str,
    llm_client: LLMClient,
    http_client: httpx.AsyncClient | None,
):  # noqa: ANN201
    """Look up and instantiate the requested agent."""
    return AgentRegistry.create(agent_type, llm_client, http_client)


@task(name="run-agent-graph", retries=3, retry_delay_seconds=2)
async def run_agent_graph(
    agent: Any,
    user_message: str,
    history: list[dict],
) -> AgentResponse:
    """Build and invoke the LangGraph state machine for the agent."""
    graph = build_agent_graph(agent)
    result = await graph.ainvoke({
        "user_message": user_message,
        "history": history,
    })
    response: AgentResponse | None = result.get("final_response")
    if response is None:
        return AgentResponse(content="Agent did not produce a response.")

    # Merge accumulated tool calls into the final response
    accumulated_tools = result.get("tool_calls", [])
    if accumulated_tools and not response.tool_calls:
        response.tool_calls = accumulated_tools

    return response


def _make_llm_client(
    settings: Settings,
    llm_override: dict | None = None,
) -> LLMClient:
    """Create an LLMClient, using per-request override if provided."""
    if llm_override and llm_override.get("provider"):
        return LLMClient.for_provider(
            provider=llm_override["provider"],
            model=llm_override.get("model", ""),
            api_key=llm_override.get("api_key", ""),
            fallback_url=settings.llm_fallback_url,
            default_primary_url=settings.llm_primary_url,
        )
    return LLMClient(
        primary_url=settings.llm_primary_url,
        fallback_url=settings.llm_fallback_url,
        model=settings.llm_model,
    )


async def _direct_execute(
    agent_type: str,
    user_message: str,
    history: list[dict],
    settings: Settings,
    llm_override: dict | None = None,
) -> AgentResponse:
    """Execute agent directly via LangGraph (no Prefect orchestration)."""
    llm_client = _make_llm_client(settings, llm_override)
    http_client: httpx.AsyncClient | None = None
    if agent_type.upper() == "RAG":
        http_client = httpx.AsyncClient(
            base_url=settings.document_service_url,
            timeout=30.0,
        )
    try:
        agent = AgentRegistry.create(agent_type, llm_client, http_client)
        graph = build_agent_graph(agent)
        result = await graph.ainvoke({
            "user_message": user_message,
            "history": history,
        })
        response: AgentResponse | None = result.get("final_response")
        if response is None:
            return AgentResponse(content="Agent did not produce a response.")
        accumulated_tools = result.get("tool_calls", [])
        if accumulated_tools and not response.tool_calls:
            response.tool_calls = accumulated_tools
        return response
    finally:
        await llm_client.close()
        if http_client is not None:
            await http_client.aclose()


@flow(name="agent-execution", timeout_seconds=120)
async def _prefect_agent_flow(
    agent_type: str,
    user_message: str,
    history: list[dict] | None = None,
    settings: Settings | None = None,
    llm_override: dict | None = None,
) -> AgentResponse:
    """Orchestrate a single agent execution turn via Prefect.

    1. Create LLM client and HTTP client
    2. Instantiate the requested agent from the registry
    3. Build and run the LangGraph state machine
    4. Return the structured AgentResponse
    """
    if settings is None:
        settings = Settings(service_name="agent-engine")
    if history is None:
        history = []

    llm_client = _make_llm_client(settings, llm_override)

    http_client: httpx.AsyncClient | None = None
    if agent_type.upper() == "RAG":
        http_client = httpx.AsyncClient(
            base_url=settings.document_service_url,
            timeout=30.0,
        )

    try:
        agent = create_agent(agent_type, llm_client, http_client)
        response = await run_agent_graph(agent, user_message, history)

        await logger.ainfo(
            "agent_flow_completed",
            agent_type=agent_type,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=response.latency_ms,
            tool_call_count=len(response.tool_calls),
        )

        return response
    finally:
        await llm_client.close()
        if http_client is not None:
            await http_client.aclose()


async def agent_flow(
    agent_type: str,
    user_message: str,
    history: list[dict] | None = None,
    settings: Settings | None = None,
    llm_override: dict | None = None,
) -> AgentResponse:
    """Execute agent with Prefect orchestration, falling back to direct execution."""
    if settings is None:
        settings = Settings(service_name="agent-engine")
    if history is None:
        history = []

    provider = llm_override.get("provider", "ollama") if llm_override else "ollama"
    await logger.ainfo(
        "agent_flow_started",
        agent_type=agent_type,
        message_length=len(user_message),
        llm_provider=provider,
    )

    try:
        return await _prefect_agent_flow(
            agent_type=agent_type,
            user_message=user_message,
            history=history,
            settings=settings,
            llm_override=llm_override,
        )
    except Exception as prefect_err:
        await logger.awarning(
            "prefect_flow_failed_falling_back_to_direct",
            error=str(prefect_err),
        )
        return await _direct_execute(agent_type, user_message, history, settings, llm_override)
