"""Pydantic models for the cache service."""

from datetime import datetime

from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    """A cached LLM response with its embedding vector."""

    query: str
    response: str
    model: str
    embedding: list[float]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: int = 3600


class CacheHit(BaseModel):
    """Returned when a semantically similar query is found in cache."""

    query: str
    response: str
    model: str
    similarity: float
    cached_at: datetime


class CacheStats(BaseModel):
    """Cache index statistics."""

    total_entries: int
    hit_rate: float
    avg_latency_ms: float
