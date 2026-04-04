"""Unit tests for the SemanticCache with mocked Redis and embedding client."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from redis.exceptions import ResponseError

from cache_service.embeddings import EMBEDDING_DIM, EmbeddingClient
from cache_service.models import CacheHit, CacheStats
from cache_service.semantic_cache import SemanticCache


class TestEnsureIndex:
    """Tests for SemanticCache.ensure_index."""

    @pytest.mark.asyncio
    async def test_ensure_index_creates_when_missing(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """ensure_index() creates the index when it does not exist."""
        # Simulate index not existing (ft().info() raises ResponseError)
        ft_mock = MagicMock()
        ft_mock.info = AsyncMock(side_effect=ResponseError("Unknown index"))
        ft_mock.create_index = AsyncMock()
        mock_redis.ft = MagicMock(return_value=ft_mock)

        await semantic_cache.ensure_index()

        ft_mock.create_index.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_index_skips_when_exists(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """ensure_index() does not recreate when the index already exists."""
        ft_mock = MagicMock()
        ft_mock.info = AsyncMock(return_value={"num_docs": 5})
        mock_redis.ft = MagicMock(return_value=ft_mock)

        await semantic_cache.ensure_index()

        ft_mock.create_index.assert_not_called()


class TestGet:
    """Tests for SemanticCache.get (cache lookup)."""

    @pytest.mark.asyncio
    async def test_get_cache_miss_no_docs(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """get() returns None when no documents match."""
        # Mock embedding
        semantic_cache.embeddings.embed = AsyncMock(
            return_value=[0.1] * EMBEDDING_DIM
        )

        # Mock search returning empty results
        search_result = MagicMock()
        search_result.docs = []
        ft_mock = MagicMock()
        ft_mock.search = AsyncMock(return_value=search_result)
        mock_redis.ft = MagicMock(return_value=ft_mock)

        result = await semantic_cache.get("test query")

        assert result is None
        assert semantic_cache._misses == 1

    @pytest.mark.asyncio
    async def test_get_cache_miss_below_threshold(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """get() returns None when similarity is below threshold."""
        semantic_cache.embeddings.embed = AsyncMock(
            return_value=[0.1] * EMBEDDING_DIM
        )

        # Mock a result with low similarity (high distance)
        doc = MagicMock()
        doc.score = 0.5  # distance=0.5 -> similarity=0.5 < 0.95
        doc.query = "cached query"
        doc.response = "cached response"
        doc.model = "gpt-4"
        doc.created_at = datetime.now(tz=timezone.utc).isoformat()

        search_result = MagicMock()
        search_result.docs = [doc]
        ft_mock = MagicMock()
        ft_mock.search = AsyncMock(return_value=search_result)
        mock_redis.ft = MagicMock(return_value=ft_mock)

        result = await semantic_cache.get("test query")

        assert result is None
        assert semantic_cache._misses == 1

    @pytest.mark.asyncio
    async def test_get_cache_hit(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """get() returns CacheHit when similarity exceeds threshold."""
        semantic_cache.embeddings.embed = AsyncMock(
            return_value=[0.1] * EMBEDDING_DIM
        )

        # Mock a result with high similarity (low distance)
        doc = MagicMock()
        doc.score = 0.02  # distance=0.02 -> similarity=0.98 >= 0.95
        doc.query = "What is Python?"
        doc.response = "Python is a programming language."
        doc.model = "gpt-4"
        doc.created_at = datetime.now(tz=timezone.utc).isoformat()

        search_result = MagicMock()
        search_result.docs = [doc]
        ft_mock = MagicMock()
        ft_mock.search = AsyncMock(return_value=search_result)
        mock_redis.ft = MagicMock(return_value=ft_mock)

        result = await semantic_cache.get("What is Python?")

        assert result is not None
        assert isinstance(result, CacheHit)
        assert result.query == "What is Python?"
        assert result.response == "Python is a programming language."
        assert result.model == "gpt-4"
        assert result.similarity == 0.98
        assert semantic_cache._hits == 1

    @pytest.mark.asyncio
    async def test_get_handles_search_error(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """get() returns None and records a miss when search raises ResponseError."""
        semantic_cache.embeddings.embed = AsyncMock(
            return_value=[0.1] * EMBEDDING_DIM
        )

        ft_mock = MagicMock()
        ft_mock.search = AsyncMock(side_effect=ResponseError("index error"))
        mock_redis.ft = MagicMock(return_value=ft_mock)

        result = await semantic_cache.get("test query")

        assert result is None
        assert semantic_cache._misses == 1


class TestPut:
    """Tests for SemanticCache.put (cache store)."""

    @pytest.mark.asyncio
    async def test_put_stores_entry(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """put() stores the entry in Redis with embedding and sets TTL."""
        semantic_cache.embeddings.embed = AsyncMock(
            return_value=[0.1] * EMBEDDING_DIM
        )

        key = await semantic_cache.put(
            query="What is AI?",
            response="AI is artificial intelligence.",
            model="gpt-4",
        )

        assert key.startswith("llm_cache:")
        mock_redis.hset.assert_awaited_once()
        mock_redis.expire.assert_awaited_once()

        # Verify the mapping passed to hset
        call_kwargs = mock_redis.hset.call_args
        mapping = call_kwargs.kwargs.get("mapping") or call_kwargs[1].get("mapping")
        assert mapping["query"] == "What is AI?"
        assert mapping["response"] == "AI is artificial intelligence."
        assert mapping["model"] == "gpt-4"
        assert "embedding" in mapping
        assert "created_at" in mapping

    @pytest.mark.asyncio
    async def test_put_custom_ttl(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """put() uses custom TTL when provided."""
        semantic_cache.embeddings.embed = AsyncMock(
            return_value=[0.1] * EMBEDDING_DIM
        )

        await semantic_cache.put(
            query="q",
            response="r",
            model="m",
            ttl=7200,
        )

        # Verify expire was called with custom TTL
        mock_redis.expire.assert_awaited_once()
        expire_args = mock_redis.expire.call_args
        assert expire_args[0][1] == 7200

    @pytest.mark.asyncio
    async def test_put_default_ttl(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """put() uses default TTL (3600) when no TTL is provided."""
        semantic_cache.embeddings.embed = AsyncMock(
            return_value=[0.1] * EMBEDDING_DIM
        )

        await semantic_cache.put(
            query="q",
            response="r",
            model="m",
        )

        expire_args = mock_redis.expire.call_args
        assert expire_args[0][1] == 3600


class TestInvalidate:
    """Tests for SemanticCache.invalidate."""

    @pytest.mark.asyncio
    async def test_invalidate_deletes_matching_keys(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """invalidate() deletes all keys matching the pattern."""
        # Mock scan_iter to yield some keys
        async def mock_scan_iter(match: str = "*"):
            yield b"llm_cache:key1"
            yield b"llm_cache:key2"

        mock_redis.scan_iter = mock_scan_iter

        deleted = await semantic_cache.invalidate("*")

        assert deleted == 2
        assert mock_redis.delete.await_count == 2

    @pytest.mark.asyncio
    async def test_invalidate_no_matching_keys(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """invalidate() returns 0 when no keys match."""
        async def mock_scan_iter(match: str = "*"):
            return
            yield  # empty generator

        mock_redis.scan_iter = mock_scan_iter

        deleted = await semantic_cache.invalidate("nonexistent*")
        assert deleted == 0


class TestStats:
    """Tests for SemanticCache.stats."""

    @pytest.mark.asyncio
    async def test_stats_empty_cache(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """stats() returns zeroed stats for empty cache."""
        ft_mock = MagicMock()
        ft_mock.info = AsyncMock(return_value={"num_docs": 0})
        mock_redis.ft = MagicMock(return_value=ft_mock)

        stats = await semantic_cache.stats()

        assert isinstance(stats, CacheStats)
        assert stats.total_entries == 0
        assert stats.hit_rate == 0.0
        assert stats.avg_latency_ms == 0.0

    @pytest.mark.asyncio
    async def test_stats_with_hits_and_misses(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """stats() calculates hit rate from recorded hits/misses."""
        # Simulate some hits and misses
        semantic_cache._hits = 3
        semantic_cache._misses = 1

        ft_mock = MagicMock()
        ft_mock.info = AsyncMock(return_value={"num_docs": 10})
        mock_redis.ft = MagicMock(return_value=ft_mock)

        stats = await semantic_cache.stats()

        assert stats.total_entries == 10
        assert stats.hit_rate == 0.75  # 3/(3+1)

    @pytest.mark.asyncio
    async def test_stats_handles_redis_error(
        self, semantic_cache: SemanticCache, mock_redis: AsyncMock
    ) -> None:
        """stats() returns 0 total_entries when Redis raises an error."""
        ft_mock = MagicMock()
        ft_mock.info = AsyncMock(side_effect=ResponseError("index not found"))
        mock_redis.ft = MagicMock(return_value=ft_mock)

        stats = await semantic_cache.stats()
        assert stats.total_entries == 0


class TestRecordLatency:
    """Tests for the _record_latency helper."""

    def test_record_latency_increments_count(
        self, semantic_cache: SemanticCache
    ) -> None:
        """_record_latency increments request count."""
        import time

        start = time.perf_counter()
        semantic_cache._record_latency(start)

        assert semantic_cache._request_count == 1
        assert semantic_cache._total_latency_ms >= 0.0

    def test_record_latency_accumulates(
        self, semantic_cache: SemanticCache
    ) -> None:
        """Multiple calls to _record_latency accumulate correctly."""
        import time

        for _ in range(3):
            start = time.perf_counter()
            semantic_cache._record_latency(start)

        assert semantic_cache._request_count == 3
