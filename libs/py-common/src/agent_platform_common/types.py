"""Shared Pydantic models and enums used across services."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Types of AI agents the platform supports."""

    WEATHER = "weather"
    QUIZ = "quiz"
    RAG = "rag"
    CUSTOM = "custom"


class MessageRole(str, Enum):
    """Roles in a chat conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AgentCreate(BaseModel):
    """Schema for creating a new agent."""

    name: str = Field(..., min_length=1, max_length=100)
    agent_type: AgentType
    instructions: str = Field(..., min_length=1, max_length=10000)


class AgentResponse(BaseModel):
    """Schema for agent responses."""

    id: UUID
    name: str
    agent_type: AgentType
    instructions: str
    created_at: datetime


class ChatMessageCreate(BaseModel):
    """Schema for sending a chat message."""

    agent_id: UUID
    session_id: UUID | None = None
    content: str = Field(..., min_length=1, max_length=50000)


class ChatMessageResponse(BaseModel):
    """Schema for chat message responses."""

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    role: MessageRole
    content: str
    tool_calls: list[dict[str, str]] | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentResponse(BaseModel):
    """Schema for document metadata."""

    id: UUID
    filename: str
    content_type: str
    chunk_count: int
    created_at: datetime


class InferenceCostResponse(BaseModel):
    """Schema for inference cost data."""

    total_cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    model: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
