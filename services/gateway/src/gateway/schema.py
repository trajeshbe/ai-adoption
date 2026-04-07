"""Root GraphQL schema -- the API contract for the Agent Platform.

This file defines ALL GraphQL types. Resolvers implement the logic.
Schema-first: change types here BEFORE implementing resolvers.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

import strawberry


@strawberry.enum
class AgentType(Enum):
    """Types of AI agents the platform supports."""

    WEATHER = "weather"
    QUIZ = "quiz"
    RAG = "rag"
    CUSTOM = "custom"


@strawberry.enum
class MessageRole(Enum):
    """Roles in a chat conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@strawberry.type
class Agent:
    """An AI agent configuration."""

    id: UUID
    name: str
    agent_type: AgentType
    instructions: str
    created_at: datetime


@strawberry.type
class ToolCall:
    """A tool invocation made by an agent during response generation."""

    tool_name: str
    arguments: str
    result: str


@strawberry.type
class ChatMessage:
    """A single message in a chat conversation."""

    id: UUID
    role: MessageRole
    content: str
    tool_calls: list[ToolCall] | None = None
    cost_usd: float | None = None
    latency_ms: float | None = None
    created_at: datetime


@strawberry.type
class ChatSession:
    """A conversation session between a user and an agent."""

    id: UUID
    agent_id: UUID
    messages: list[ChatMessage]
    created_at: datetime


@strawberry.type
class Document:
    """An uploaded document with vector embeddings for RAG."""

    id: UUID
    filename: str
    content_type: str
    chunk_count: int
    created_at: datetime


@strawberry.type
class InferenceCost:
    """Cost breakdown for a single LLM inference call."""

    total_cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    model: str


@strawberry.type
class CostSummary:
    """Aggregated cost summary over a time period."""

    total_cost_usd: float
    total_inferences: int
    avg_cost_per_inference: float
    period: str


@strawberry.type
class HealthStatus:
    """Health check response for a service."""

    service: str
    status: str
    latency_ms: float


# ── Input Types ────────────────────────────────────────────────────────


@strawberry.input
class CreateAgentInput:
    """Input for creating a new agent."""

    name: str
    agent_type: AgentType
    instructions: str


@strawberry.input
class LLMConfigInput:
    """Optional per-request LLM provider override."""

    provider: str = ""  # "ollama" or "openai"
    model: str = ""  # e.g. "gpt-4o-mini", "qwen2.5:1.5b"
    api_key: str = ""  # Required for OpenAI


@strawberry.input
class SendMessageInput:
    """Input for sending a chat message."""

    agent_id: UUID
    session_id: UUID | None = None
    content: str
    llm_config: LLMConfigInput | None = None
