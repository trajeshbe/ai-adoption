"""Chat streaming subscription.

Streams LLM response tokens as they arrive, enabling real-time
chat UI updates. Will be connected to agent-engine in Phase 4.
"""

import asyncio
from collections.abc import AsyncGenerator
from uuid import UUID

import strawberry


@strawberry.type
class ChatToken:
    """A single token in a streaming chat response."""

    session_id: UUID
    token: str
    is_final: bool


async def subscribe_chat_stream(
    session_id: UUID,
) -> AsyncGenerator[ChatToken, None]:
    """Subscribe to streaming chat response tokens.

    In production (Phase 4+), this reads from a message queue
    fed by the agent-engine as LLM tokens arrive.
    """
    # Mock streaming: simulate token-by-token response
    mock_response = "This is a mock streaming response from the AI agent."
    words = mock_response.split()

    for i, word in enumerate(words):
        await asyncio.sleep(0.1)  # Simulate token generation delay
        yield ChatToken(
            session_id=session_id,
            token=word + " ",
            is_final=(i == len(words) - 1),
        )
