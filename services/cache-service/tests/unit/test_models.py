"""Unit tests for cache-service Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone


from cache_service.models import CacheEntry, CacheHit, CacheStats


class TestCacheEntry:
    """Tests for the CacheEntry model."""

    def test_create_cache_entry(self) -> None:
        """CacheEntry can be created with all required fields."""
        entry = CacheEntry(
            query="What is Python?",
            response="Python is a programming language.",
            model="gpt-4",
            embedding=[0.1] * 384,
        )

        assert entry.query == "What is Python?"
        assert entry.response == "Python is a programming language."
        assert entry.model == "gpt-4"
        assert len(entry.embedding) == 384
        assert entry.ttl_seconds == 3600  # default

    def test_cache_entry_custom_ttl(self) -> None:
        """CacheEntry accepts a custom TTL."""
        entry = CacheEntry(
            query="test",
            response="resp",
            model="llama",
            embedding=[0.0] * 10,
            ttl_seconds=7200,
        )
        assert entry.ttl_seconds == 7200

    def test_cache_entry_created_at_auto(self) -> None:
        """CacheEntry auto-populates created_at."""
        entry = CacheEntry(
            query="q",
            response="r",
            model="m",
            embedding=[],
        )
        assert isinstance(entry.created_at, datetime)

    def test_cache_entry_serialization(self) -> None:
        """CacheEntry serializes to dict correctly."""
        now = datetime(2026, 1, 15, tzinfo=timezone.utc)
        entry = CacheEntry(
            query="test query",
            response="test response",
            model="test-model",
            embedding=[0.5, -0.5],
            created_at=now,
            ttl_seconds=1800,
        )
        data = entry.model_dump()
        assert data["query"] == "test query"
        assert data["model"] == "test-model"
        assert data["ttl_seconds"] == 1800
        assert data["embedding"] == [0.5, -0.5]

    def test_cache_entry_json_roundtrip(self) -> None:
        """CacheEntry survives JSON serialization roundtrip."""
        original = CacheEntry(
            query="roundtrip",
            response="value",
            model="gpt-4",
            embedding=[0.1, 0.2, 0.3],
        )
        json_str = original.model_dump_json()
        restored = CacheEntry.model_validate_json(json_str)
        assert restored.query == original.query
        assert restored.embedding == original.embedding


class TestCacheHit:
    """Tests for the CacheHit model."""

    def test_create_cache_hit(self) -> None:
        """CacheHit can be created with all fields."""
        now = datetime.now(tz=timezone.utc)
        hit = CacheHit(
            query="What is AI?",
            response="AI is artificial intelligence.",
            model="gpt-4",
            similarity=0.97,
            cached_at=now,
        )

        assert hit.query == "What is AI?"
        assert hit.response == "AI is artificial intelligence."
        assert hit.similarity == 0.97
        assert hit.cached_at == now

    def test_cache_hit_serialization(self) -> None:
        """CacheHit serializes correctly."""
        now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
        hit = CacheHit(
            query="q",
            response="r",
            model="m",
            similarity=0.99,
            cached_at=now,
        )
        data = hit.model_dump(mode="json")
        assert data["similarity"] == 0.99
        assert data["model"] == "m"

    def test_cache_hit_json_roundtrip(self) -> None:
        """CacheHit survives JSON serialization roundtrip."""
        original = CacheHit(
            query="test",
            response="resp",
            model="llama",
            similarity=0.96,
            cached_at=datetime.now(tz=timezone.utc),
        )
        json_str = original.model_dump_json()
        restored = CacheHit.model_validate_json(json_str)
        assert restored.similarity == original.similarity
        assert restored.query == original.query


class TestCacheStats:
    """Tests for the CacheStats model."""

    def test_create_cache_stats(self) -> None:
        """CacheStats can be created with all fields."""
        stats = CacheStats(
            total_entries=100,
            hit_rate=0.75,
            avg_latency_ms=1.234,
        )

        assert stats.total_entries == 100
        assert stats.hit_rate == 0.75
        assert stats.avg_latency_ms == 1.234

    def test_cache_stats_zero_values(self) -> None:
        """CacheStats handles zero values correctly."""
        stats = CacheStats(
            total_entries=0,
            hit_rate=0.0,
            avg_latency_ms=0.0,
        )
        assert stats.total_entries == 0
        assert stats.hit_rate == 0.0

    def test_cache_stats_serialization(self) -> None:
        """CacheStats serializes to dict correctly."""
        stats = CacheStats(
            total_entries=50,
            hit_rate=0.5,
            avg_latency_ms=2.5,
        )
        data = stats.model_dump()
        assert data["total_entries"] == 50
        assert data["hit_rate"] == 0.5
        assert data["avg_latency_ms"] == 2.5
