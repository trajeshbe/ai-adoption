"""LangGraph state machine for agent execution.

Defines a simple DAG:
  call_llm -> (tool_calls?) -> execute_tools -> call_llm
                            -> respond (final answer)
"""

from __future__ import annotations

import json
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent_engine.agents.base import AgentResponse, BaseAgent, ToolCallResult


# ── State ─────────────────────────────────────────────────────────────

def _merge_tool_calls(
    existing: list[ToolCallResult], new: list[ToolCallResult]
) -> list[ToolCallResult]:
    return existing + new


class AgentState(TypedDict, total=False):
    """State flowing through the agent graph."""

    user_message: str
    history: list[dict]
    messages: list[dict]
    tool_calls: Annotated[list[ToolCallResult], _merge_tool_calls]
    final_response: AgentResponse | None
    pending_tool_calls: list[dict]
    iteration: int


# ── Node functions ────────────────────────────────────────────────────

def _make_call_llm(agent: BaseAgent):
    """Create the call_llm node bound to a specific agent."""

    async def call_llm(state: AgentState) -> dict[str, Any]:
        messages: list[dict] = list(state.get("messages", []))

        # First call: build initial messages
        if not messages:
            messages = [{"role": "system", "content": agent.system_prompt}]
            for msg in state.get("history", []):
                messages.append(msg)
            messages.append({"role": "user", "content": state["user_message"]})

        tools = agent.available_tools or None
        llm_result = await agent.llm_client.chat(messages=messages, tools=tools)

        iteration = state.get("iteration", 0) + 1

        if "tool_calls" in llm_result and llm_result["tool_calls"]:
            # Append assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": llm_result.get("content", ""),
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in llm_result["tool_calls"]
                ],
            })
            return {
                "messages": messages,
                "pending_tool_calls": llm_result["tool_calls"],
                "iteration": iteration,
                "final_response": AgentResponse(
                    content=llm_result.get("content", ""),
                    model=llm_result.get("model", ""),
                    prompt_tokens=llm_result.get("prompt_tokens", 0),
                    completion_tokens=llm_result.get("completion_tokens", 0),
                    latency_ms=llm_result.get("latency_ms", 0.0),
                ),
            }

        # No tool calls -- final answer
        return {
            "messages": messages,
            "pending_tool_calls": [],
            "iteration": iteration,
            "final_response": AgentResponse(
                content=llm_result["content"],
                model=llm_result.get("model", ""),
                prompt_tokens=llm_result.get("prompt_tokens", 0),
                completion_tokens=llm_result.get("completion_tokens", 0),
                latency_ms=llm_result.get("latency_ms", 0.0),
            ),
        }

    return call_llm


def _make_execute_tools(agent: BaseAgent):
    """Create the execute_tools node bound to a specific agent."""

    async def execute_tools(state: AgentState) -> dict[str, Any]:
        messages: list[dict] = list(state.get("messages", []))
        pending = state.get("pending_tool_calls", [])
        tool_results: list[ToolCallResult] = []

        for tc in pending:
            try:
                args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
            except json.JSONDecodeError:
                args = {}

            result_str = await agent.execute_tool(tc["name"], args)
            tool_results.append(ToolCallResult(
                tool_name=tc["name"],
                arguments=tc["arguments"] if isinstance(tc["arguments"], str) else json.dumps(tc["arguments"]),
                result=result_str,
            ))

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result_str,
            })

        return {
            "messages": messages,
            "tool_calls": tool_results,
            "pending_tool_calls": [],
        }

    return execute_tools


def _respond(state: AgentState) -> dict[str, Any]:
    """Terminal node -- just passes through the final response."""
    return {}


# ── Routing ───────────────────────────────────────────────────────────

def _should_continue(state: AgentState) -> str:
    """Route after call_llm: execute tools or respond."""
    pending = state.get("pending_tool_calls", [])
    iteration = state.get("iteration", 0)
    if pending and iteration < 5:
        return "execute_tools"
    return "respond"


# ── Graph builder ─────────────────────────────────────────────────────

def build_agent_graph(agent: BaseAgent) -> CompiledStateGraph:
    """Build and compile a LangGraph state machine for the given agent.

    Graph:
        call_llm --(has tool_calls)--> execute_tools --> call_llm
                 --(no tool_calls)---> respond --> END
    """
    graph = StateGraph(AgentState)

    graph.add_node("call_llm", _make_call_llm(agent))
    graph.add_node("execute_tools", _make_execute_tools(agent))
    graph.add_node("respond", _respond)

    graph.set_entry_point("call_llm")

    graph.add_conditional_edges("call_llm", _should_continue, {
        "execute_tools": "execute_tools",
        "respond": "respond",
    })

    graph.add_edge("execute_tools", "call_llm")
    graph.add_edge("respond", END)

    return graph.compile()
