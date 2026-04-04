"""Semantic cache backed by Redis 7.2 Vector Similarity Search.

Stores LLM responses keyed by query embedding. On lookup, finds the nearest
cached query via cosine similarity. If similarity >= threshold, returns the
cached response instead of calling the LLM (sub-millisecond vs multi-second).
"""

import time
import uuid
from datetime import datetime, timezone

import numpy as np
import structlog
from redis.asyncio import Redis
from redis.commands.search.field import TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError

from cache_service.embeddings import EMBEDDING_DIM, EmbeddingClient
from cache_service.models import CacheHit, CacheStats

logger = structlog.get_logger()


class SemanticCache:
    """Redis VSS-based semantic cache for LLM responses."""

    def __init__(
        self,
        redis_client: Redis,
        embedding_client: EmbeddingClient,
        similarity_threshold: float = 0.95,
        default_ttl: int = 3600,
        index_name: str = "idx:llm_cache",
    ) -> None:
        self.redis = redis_client
        self.embeddings = embedding_client
        self.similarity_threshold = similarity_threshold
        self.default_ttl = default_ttl
        self.index_name = index_name
        self._prefix = "llm_cache:"

        # Metrics
        self._hits = 0
        self._misses = 0
        self._total_latency_ms = 0.0
        self._request_count = 0

    async def ensure_index(self) -> None:
        """Create the RediSearch index if it does not already exist.

        Schema:
        - query: TAG (exact match filtering)
        - response: TEXT (full-text search)
        - model: TAG (filter by LLM model)
        - embedding: VECTOR (HNSW, FLOAT32, 384 dims, COSINE distance)
        """
        try:
            await self.redis.ft(self.index_name).info()
            await logger.ainfo("redis_index_already_exists", index=self.index_name)
        except ResponseError:
            schema = (
                TagField("query"),
                TextField("response"),
                TagField("model"),
                VectorField(
                    "embedding",
                    "HNSW",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": EMBEDDING_DIM,
                        "DISTANCE_METRIC": "COSINE",
                    },
                ),
            )
            definition = IndexDefinition(
                prefix=[self._prefix],
                index_type=IndexType.HASH,
            )
            await self.redis.ft(self.index_name).create_index(
                schema, definition=definition
            )
            await logger.ainfo("redis_index_created", index=self.index_name)

    async def get(self, query: str) -> CacheHit | None:
        """Look up a semantically similar cached response.

        Args:
            query: The user query to search for.

        Returns:
            CacheHit if a similar query is found above the threshold, else None.
        """
        start = time.perf_counter()

        query_embedding = await self.embeddings.embed(query)
        query_vector = np.array(query_embedding, dtype=np.float32).tobytes()

        # KNN search: find the single nearest neighbor
        q = (
            Query("(*)=>[KNN 1 @embedding $query_vec AS score]")
            .sort_by("score")
            .return_fields("query", "response", "model", "score", "created_at")
            .dialect(2)
        )

        try:
            results = await self.redis.ft(self.index_name).search(
                q, query_params={"query_vec": query_vector}
            )
        except ResponseError as exc:
            await logger.awarning("cache_search_failed", error=str(exc))
            self._record_latency(start)
            self._misses += 1
            return None

        self._record_latency(start)

        if not results.docs:
            self._misses += 1
            return None

        doc = results.docs[0]
        # Redis COSINE distance: 0 = identical, 2 = opposite
        # Convert to similarity: 1 - distance
        distance = float(doc.score)
        similarity = 1.0 - distance

        if similarity < self.similarity_threshold:
            self._misses += 1
            await logger.adebug(
                "cache_miss_below_threshold",
                similarity=similarity,
                threshold=self.similarity_threshold,
            )
            return None

        self._hits += 1
        await logger.ainfo(
            "cache_hit",
            similarity=similarity,
            model=doc.model,
        )

        cached_at_str = getattr(doc, "created_at", None)
        cached_at = (
            datetime.fromisoformat(cached_at_str)
            if cached_at_str
            else datetime.now(tz=timezone.utc)
        )

        return CacheHit(
            query=doc.query,
            response=doc.response,
            model=doc.model,
            similarity=round(similarity, 4),
            cached_at=cached_at,
        )

    async def put(
        self,
        query: str,
        response: str,
        model: str,
        ttl: int | None = None,
    ) -> str:
        """Store an LLM response in the cache.

        Args:
            query: The original user query.
            response: The LLM response text.
            model: The LLM model that generated the response.
            ttl: Time-to-live in seconds (defaults to self.default_ttl).

        Returns:
            The cache entry key.
        """
        query_embedding = await self.embeddings.embed(query)
        embedding_bytes = np.array(query_embedding, dtype=np.float32).tobytes()

        entry_id = str(uuid.uuid4())
        key = f"{self._prefix}{entry_id}"
        ttl_value = ttl if ttl is not None else self.default_ttl
        now = datetime.now(tz=timezone.utc).isoformat()

        mapping = {
            "query": query,
            "response": response,
            "model": model,
            "embedding": embedding_bytes,
            "created_at": now,
            "ttl_seconds": str(ttl_value),
        }

        await self.redis.hset(key, mapping=mapping)  # type: ignore[arg-type]
        if ttl_value > 0:
            await self.redis.expire(key, ttl_value)

        await logger.ainfo(
            "cache_entry_stored",
            key=key,
            model=model,
            ttl=ttl_value,
        )
        return key

    async def invalidate(self, pattern: str = "*") -> int:
        """Delete cache entries matching the given pattern.

        Args:
            pattern: Glob pattern for keys to delete. Defaults to all.

        Returns:
            Number of keys deleted.
        """
        full_pattern = f"{self._prefix}{pattern}"
        deleted = 0
        async for key in self.redis.scan_iter(match=full_pattern):
            await self.redis.delete(key)
            deleted += 1

        await logger.ainfo("cache_invalidated", pattern=pattern, deleted=deleted)
        return deleted

    async def stats(self) -> CacheStats:
        """Return cache index statistics.

        Returns:
            CacheStats with total entries, hit rate, and average latency.
        """
        try:
            info = await self.redis.ft(self.index_name).info()
            total_entries = int(info.get("num_docs", 0))
        except (ResponseError, Exception):
            total_entries = 0

        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests) if total_requests > 0 else 0.0
        avg_latency = (
            (self._total_latency_ms / self._request_count)
            if self._request_count > 0
            else 0.0
        )

        return CacheStats(
            total_entries=total_entries,
            hit_rate=round(hit_rate, 4),
            avg_latency_ms=round(avg_latency, 3),
        )

    def _record_latency(self, start: float) -> None:
        """Record a request latency measurement."""
        elapsed_ms = (time.perf_counter() - start) * 1000
        self._total_latency_ms += elapsed_ms
        self._request_count += 1
