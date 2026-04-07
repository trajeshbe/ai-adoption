"""Chat resolvers — wired to agent-engine for real LLM responses.

Flow: gateway → agent-engine → Ollama (qwen2.5:1.5b)
Fallback: if agent-engine is unreachable, return a helpful error message.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
import structlog

from gateway.schema import (
    ChatMessage,
    ChatSession,
    MessageRole,
    SendMessageInput,
    ToolCall,
)

logger = structlog.get_logger()

# ── Session store (in-memory, replaced by DB in production) ──────────
_sessions: dict[UUID, ChatSession] = {}

# ── Agent type lookup (agent_id -> agent_type) ───────────────────────
_agent_types: dict[str, str] = {
    "00000000-0000-0000-0000-000000000001": "QUIZ",
    "00000000-0000-0000-0000-000000000002": "WEATHER",
    "00000000-0000-0000-0000-000000000003": "RAG",
}


def resolve_chat_sessions() -> list[ChatSession]:
    """List all chat sessions."""
    return list(_sessions.values())


def resolve_chat_session(session_id: UUID) -> ChatSession | None:
    """Get a single chat session."""
    return _sessions.get(session_id)


async def resolve_send_message(input: SendMessageInput) -> ChatMessage:
    """Send a message and get an AI response via agent-engine.

    1. Determines agent type from agent_id
    2. Calls agent-engine /agents/execute
    3. Returns the real LLM response with cost/latency metadata
    """
    import os

    agent_engine_url = os.environ.get(
        "AGENT_ENGINE_URL", "http://localhost:8053"
    )

    session_id = input.session_id or uuid4()
    now = datetime.now(tz=timezone.utc)

    # Create user message
    user_msg = ChatMessage(
        id=uuid4(),
        role=MessageRole.USER,
        content=input.content,
        created_at=now,
    )

    # Determine agent type (default to QUIZ for movie chat bot)
    agent_type = _agent_types.get(str(input.agent_id), "QUIZ")

    # Build conversation history from session
    history = []
    if session_id in _sessions:
        for msg in _sessions[session_id].messages:
            history.append({
                "role": "user" if msg.role == MessageRole.USER else "assistant",
                "content": msg.content,
            })

    # Build request payload
    payload: dict = {
        "agent_type": agent_type,
        "message": input.content,
        "history": history,
        "session_id": str(session_id),
    }
    if input.llm_config and input.llm_config.provider:
        payload["llm_config"] = {
            "provider": input.llm_config.provider,
            "model": input.llm_config.model,
            "api_key": input.llm_config.api_key,
        }

    # Call agent-engine
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{agent_engine_url}/agents/execute",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        tool_calls = [
            ToolCall(
                tool_name=tc["tool_name"],
                arguments=tc["arguments"],
                result=tc["result"],
            )
            for tc in data.get("tool_calls", [])
        ]

        cost_usd = (
            (data.get("prompt_tokens", 0) + data.get("completion_tokens", 0))
            * 0.000001
        )

        assistant_msg = ChatMessage(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            content=data["content"],
            tool_calls=tool_calls if tool_calls else None,
            cost_usd=round(cost_usd, 6),
            latency_ms=data.get("latency_ms", 0),
            created_at=datetime.now(tz=timezone.utc),
        )

    except Exception as exc:
        logger.error("agent_engine_call_failed", error=str(exc))
        assistant_msg = ChatMessage(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            content=f"Sorry, I couldn't process your message. Error: {exc}",
            cost_usd=0.0,
            latency_ms=0,
            created_at=datetime.now(tz=timezone.utc),
        )

    # Store in session
    if session_id not in _sessions:
        _sessions[session_id] = ChatSession(
            id=session_id,
            agent_id=input.agent_id,
            messages=[],
            created_at=now,
        )

    _sessions[session_id].messages.extend([user_msg, assistant_msg])
    return assistant_msg


def register_agent_type(agent_id: str, agent_type: str) -> None:
    """Register an agent_id -> agent_type mapping."""
    _agent_types[agent_id] = agent_type
