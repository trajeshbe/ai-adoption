"""Abstract base class for all agents."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass
class ToolCallResult:
    """Result of a single tool invocation."""

    tool_name: str
    arguments: str
    result: str


@dataclass
class AgentResponse:
    """Unified response returned by every agent."""

    content: str
    tool_calls: list[ToolCallResult] = field(default_factory=list)
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0


class BaseAgent(abc.ABC):
    """Abstract base class that every agent must implement.

    Subclasses define the agent_type, system_prompt, available tools,
    and the tool dispatch logic. The ``run`` method orchestrates a single
    turn of LLM inference with optional tool execution.
    """

    def __init__(self, llm_client, http_client=None) -> None:  # noqa: ANN001
        self.llm_client = llm_client
        self.http_client = http_client

    @property
    @abc.abstractmethod
    def agent_type(self) -> str:
        """Unique identifier for this agent type (e.g. 'WEATHER')."""

    @property
    @abc.abstractmethod
    def system_prompt(self) -> str:
        """System prompt sent to the LLM for this agent."""

    @property
    @abc.abstractmethod
    def available_tools(self) -> list[dict]:
        """Tool definitions in OpenAI function-calling format."""

    @abc.abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Dispatch a tool call and return the result as a string."""

    async def run(self, user_message: str, history: list[dict] | None = None) -> AgentResponse:
        """Execute one agent turn: LLM call -> optional tool loop -> final answer."""
        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        tools = self.available_tools or None
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_latency_ms = 0.0
        tool_results: list[ToolCallResult] = []

        # Tool-use loop (max 5 iterations to prevent infinite loops)
        for _ in range(5):
            llm_result = await self.llm_client.chat(messages=messages, tools=tools)
            total_prompt_tokens += llm_result.get("prompt_tokens", 0)
            total_completion_tokens += llm_result.get("completion_tokens", 0)
            total_latency_ms += llm_result.get("latency_ms", 0.0)

            if "tool_calls" not in llm_result or not llm_result["tool_calls"]:
                # No tool calls -- we have the final answer
                return AgentResponse(
                    content=llm_result["content"],
                    tool_calls=tool_results,
                    model=llm_result.get("model", ""),
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=total_completion_tokens,
                    latency_ms=total_latency_ms,
                )

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

            # Execute each tool call
            import json

            for tc in llm_result["tool_calls"]:
                try:
                    args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                except json.JSONDecodeError:
                    args = {}

                result_str = await self.execute_tool(tc["name"], args)
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

        # If we exhausted iterations, return what we have
        return AgentResponse(
            content=llm_result.get("content", "I was unable to complete the request."),
            tool_calls=tool_results,
            model=llm_result.get("model", ""),
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            latency_ms=total_latency_ms,
        )
