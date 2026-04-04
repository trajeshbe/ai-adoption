"""Shared fixtures for cache-service tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from cache_service.embeddings import EMBEDDING_DIM, EmbeddingClient
from cache_service.semantic_cache import SemanticCache


@pytest.fixture
def sample_datetime() -> datetime:
    """A deterministic datetime for test assertions."""
    return datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_embedding_client() -> EmbeddingClient:
    """An EmbeddingClient with mocked HTTP (always falls back to hash-based)."""
    client = EmbeddingClient.__new__(EmbeddingClient)
    client.model_url = "http://localhost:11434/api/embeddings"
    client.model_name = "all-minilm:l6-v2"
    client._client = AsyncMock()
    return client


@pytest.fixture
def mock_redis() -> AsyncMock:
    """A mocked async Redis client."""
    redis = AsyncMock()
    redis.hset = AsyncMock()
    redis.expire = AsyncMock()
    redis.delete = AsyncMock()
    redis.ping = AsyncMock(return_value=True)

    # Mock ft() for RediSearch
    ft_mock = MagicMock()
    ft_mock.info = AsyncMock(return_value={"num_docs": 0})
    ft_mock.create_index = AsyncMock()
    ft_mock.search = AsyncMock()
    redis.ft = MagicMock(return_value=ft_mock)

    # Mock scan_iter as an async generator
    async def empty_scan_iter(match: str = "*"):
        return
        yield  # make it a generator

    redis.scan_iter = empty_scan_iter

    return redis


@pytest.fixture
def semantic_cache(
    mock_redis: AsyncMock,
    mock_embedding_client: EmbeddingClient,
) -> SemanticCache:
    """A SemanticCache with mocked Redis and embedding client."""
    return SemanticCache(
        redis_client=mock_redis,
        embedding_client=mock_embedding_client,
        similarity_threshold=0.95,
        default_ttl=3600,
    )
