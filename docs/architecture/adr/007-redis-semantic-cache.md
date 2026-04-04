# ADR-007: Redis Semantic Cache for LLM Inference

## Status: Accepted

## Date: 2026-04-04

## Context

LLM inference is the most expensive operation in the platform, both in compute cost
(GPU-hours) and latency (1-10 seconds per request depending on output length). Analysis
of early usage patterns shows that 25-40% of queries are semantically similar to previous
queries -- users ask variations of the same questions ("How do I configure X?" vs "What
is the configuration for X?"). Exact-match caching captures only a fraction of this
overlap because natural language queries vary in phrasing, word order, and verbosity.

A semantic cache that matches queries by meaning rather than exact string equality could
eliminate a significant portion of redundant inference, reducing both cost and latency.
The platform already runs Redis 7.2 for session storage, rate limiting, and Pub/Sub
message brokering.

## Decision

We implement semantic caching using Redis 7.2 with the RediSearch module's vector
similarity search (VSS) capability. Incoming queries are embedded using the same
sentence-transformer model used for RAG (768-dimensional vectors). The embedding is
searched against cached query embeddings in Redis using cosine similarity. A cache hit
is defined as a similarity score above 0.92 (tuned empirically to balance hit rate
against answer relevance). Cache entries include the original query, its embedding,
the LLM response, the model identifier, and a TTL of 24 hours.

The caching layer is implemented as middleware in the inference-router service, executing
before the request reaches vLLM or llama.cpp backends.

## Consequences

**Positive:**
- Sub-millisecond cache hits (< 1ms) versus multi-second inference latency, providing
  a 1000x+ latency improvement for cached queries. At a 30% hit rate, this reduces
  average query latency by approximately 40%.
- Direct GPU cost reduction proportional to cache hit rate. At projected volumes of
  100K queries/day with 30% cache hits, this saves 30K inference calls daily --
  equivalent to approximately 8 GPU-hours per day.
- Redis VSS uses the same HNSW indexing algorithm as pgvector, providing consistent
  >95% recall for similarity matching. The FLAT index option is available for smaller
  cache sizes where exact search is feasible.
- No additional infrastructure: the existing Redis 7.2 deployment already includes the
  RediSearch module. The semantic cache is a new key prefix and index within the same
  Redis cluster, sharing existing monitoring and backup infrastructure.
- Cache invalidation is straightforward: TTL-based expiry handles staleness, and
  model-version tagging in cache keys ensures responses from outdated models are not
  served after model updates.

**Negative:**
- The similarity threshold (0.92) requires careful tuning per use case. Too low and
  semantically different queries return incorrect cached responses; too high and the
  cache hit rate drops, reducing the optimization's value. We implement per-agent-type
  threshold overrides for fine-grained control.
- Embedding computation for cache lookup adds 5-15ms of latency to every request
  (even cache misses). This is negligible compared to inference latency but is
  non-zero overhead. We amortize this by reusing the same embedding for RAG retrieval
  when applicable.
- Cache poisoning risk: if a low-quality or hallucinated response is cached, it will
  be served to multiple users until TTL expiry. We mitigate this with optional quality
  scoring before cache insertion and an admin API for manual cache invalidation.
- Redis memory consumption grows with cache size. Each entry requires approximately
  3.5 KB (768 floats x 4 bytes + metadata). At 100K cached entries, this consumes
  ~350 MB -- acceptable within our Redis cluster capacity but requires monitoring.

## Alternatives Considered

- **Application-level LRU cache (in-memory):** Simple to implement but only supports
  exact-match lookups, missing the semantic similarity that drives the majority of
  cache hit potential. Also not shared across inference-router replicas.
- **Dedicated vector DB for cache (Qdrant/Weaviate):** Would provide semantic matching
  but introduces an additional infrastructure component solely for caching. Redis
  VSS provides equivalent functionality within our existing Redis deployment.
- **No caching:** Simplest approach but leaves significant cost and latency optimization
  on the table. Given the measured query repetition patterns, semantic caching is the
  highest-ROI optimization available with minimal implementation complexity.
