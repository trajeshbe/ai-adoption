# Cache Service

## Purpose
Semantic cache using Redis 7.2 with Vector Similarity Search (VSS). Caches LLM
responses keyed by query embedding. Similar queries (cosine > 0.95) return cached
responses in sub-millisecond latency instead of multi-second LLM inference.

## Tech
FastAPI, redis-py with RediSearch module, sentence-transformers

## Key Files
- `src/cache_service/semantic_cache.py` -- VSS-based get/put with similarity threshold
- `src/cache_service/embeddings.py` -- Query embedding for cache lookup
- `src/cache_service/models.py` -- CacheEntry Pydantic model

## Patterns
- FT.CREATE index with VECTOR field (HNSW, FLOAT32, 384 dims, COSINE)
- Similarity threshold: 0.95 (configurable via env var)
- TTL: 1 hour per cache entry (configurable)
- Cache invalidation on document re-ingestion

## Run
`uv run uvicorn cache_service.main:create_app --factory --reload --port 8002`
