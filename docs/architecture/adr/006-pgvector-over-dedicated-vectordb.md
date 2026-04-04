# ADR-006: pgvector over Dedicated Vector Database

## Status: Accepted

## Date: 2026-04-04

## Context

The RAG (Retrieval-Augmented Generation) pipeline requires vector similarity search to
retrieve relevant document chunks at query time. Documents are chunked (512-token
segments with 50-token overlap), embedded via a sentence-transformer model (producing
768-dimensional vectors), and stored for nearest-neighbor retrieval. The corpus is
projected to reach 2-5 million vectors within the first year. Each vector has associated
metadata: source document ID, chunk position, creation timestamp, access control tags,
and full-text content for reranking.

The platform already runs PostgreSQL 16 as the primary relational database for user
accounts, agent configurations, execution history, and cost tracking data.

## Decision

We use PostgreSQL with the pgvector extension (v0.7+) for vector storage and similarity
search. Vectors are stored in a dedicated `document_embeddings` table with HNSW indexing
(`CREATE INDEX ON document_embeddings USING hnsw (embedding vector_cosine_ops)`). HNSW
index parameters are tuned for our workload: `m=16, ef_construction=256` for indexing,
`hnsw.ef_search=100` at query time, balancing recall (>95% at top-10) against latency
(<50ms p99 at 2M vectors).

## Consequences

**Positive:**
- Eliminates an entire infrastructure component from the stack. No separate vector
  database cluster to provision, monitor, back up, upgrade, or secure. This reduces
  operational burden significantly for a small platform team.
- Transactional consistency between metadata and vectors: document ingestion writes
  the chunk text, metadata, and embedding vector in a single ACID transaction. No
  risk of orphaned vectors or metadata without corresponding embeddings.
- Existing PostgreSQL operational knowledge transfers directly: pgBackRest for backups,
  pg_stat_statements for query analysis, standard connection pooling (PgBouncer),
  familiar EXPLAIN ANALYZE for query optimization.
- Rich hybrid queries combining vector similarity with SQL filters in a single query:
  `SELECT * FROM document_embeddings WHERE tenant_id = $1 ORDER BY embedding <=> $2
  LIMIT 10` -- this is awkward or impossible in dedicated vector DBs that separate
  metadata filtering from vector search.
- pgvector HNSW provides competitive recall and latency at millions-scale. Benchmarks
  show >95% recall@10 with sub-50ms latency at 2M vectors on a 4-vCPU instance.

**Negative:**
- pgvector shares resources (CPU, memory, I/O) with relational workloads. Heavy vector
  search queries could impact transactional query latency. We mitigate this with a
  dedicated read replica for vector search and connection pool isolation.
- At 10M+ vectors, pgvector's performance may lag behind purpose-built systems like
  Milvus or Qdrant that implement GPU-accelerated indexing and distributed sharding.
  We accept this ceiling given our projected scale.
- HNSW index builds are memory-intensive and block writes to the indexed table during
  creation. Index rebuilds (after bulk ingestion) must be scheduled during maintenance
  windows. pgvector 0.7's parallel index builds reduce but do not eliminate this.
- pgvector does not support advanced features like multi-vector retrieval (ColBERT-style)
  or product quantization for memory-efficient storage of very large collections.

## Alternatives Considered

- **Pinecone:** Fully managed, excellent developer experience, but SaaS-only model
  conflicts with our data sovereignty requirements. Per-query pricing becomes expensive
  at high volume, and vendor lock-in limits future flexibility.
- **Weaviate:** Feature-rich with built-in vectorization modules, but introduces a
  Java/Go-based system the team lacks operational experience with. The additional
  cluster adds monitoring, backup, and upgrade complexity.
- **Qdrant:** Strong performance characteristics and Rust-based efficiency, but same
  operational overhead argument as Weaviate. Qdrant's filtering capabilities, while
  good, do not surpass what SQL+pgvector provides.
- **Milvus:** Best raw performance at very large scale (100M+ vectors), but significantly
  over-engineered for our 2-5M vector workload. Requires etcd, MinIO, and Pulsar
  dependencies, adding substantial infrastructure complexity.
