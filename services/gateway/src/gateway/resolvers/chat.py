"""Chat resolvers for conversation management.

Stub implementation. Will be wired to agent-engine + cache-service in Phase 4.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from gateway.schema import ChatMessage, ChatSession, MessageRole, SendMessageInput

# ── Mock session store ─────────────────────────────────────────────────
_mock_sessions: dict[UUID, ChatSession] = {}


def resolve_chat_sessions() -> list[ChatSession]:
    """List all chat sessions."""
    return list(_mock_sessions.values())


def resolve_chat_session(session_id: UUID) -> ChatSession | None:
    """Get a single chat session."""
    return _mock_sessions.get(session_id)


def resolve_send_message(input: SendMessageInput) -> ChatMessage:
    """Send a message and get an AI response.

    In production (Phase 4+), this:
    1. Checks semantic cache for similar queries
    2. Routes to agent-engine for LangGraph execution
    3. Streams response via GraphQL subscription
    4. Records cost and caches the response
    """
    session_id = input.session_id or uuid4()
    now = datetime.now(tz=timezone.utc)

    # Create user message
    user_msg = ChatMessage(
        id=uuid4(),
        role=MessageRole.USER,
        content=input.content,
        created_at=now,
    )

    # Mock AI response
    assistant_msg = ChatMessage(
        id=uuid4(),
        role=MessageRole.ASSISTANT,
        content=f"[Mock response] I received your message: '{input.content}'. "
        "In Phase 4, this will be processed by a real LangGraph agent.",
        cost_usd=0.002,
        latency_ms=150,
        created_at=now,
    )

    # Store in session
    if session_id not in _mock_sessions:
        _mock_sessions[session_id] = ChatSession(
            id=session_id,
            agent_id=input.agent_id,
            messages=[],
            created_at=now,
        )

    _mock_sessions[session_id].messages.extend([user_msg, assistant_msg])
    return assistant_msg
