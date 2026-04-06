# Tutorial 07: PostgreSQL + pgvector

> **Objective:** Learn how to use PostgreSQL with pgvector for vector similarity search — powering RAG (Retrieval-Augmented Generation) in our AI platform.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [PostgreSQL Refresher](#3-postgresql-refresher)
4. [pgvector Deep Dive](#4-pgvector-deep-dive)
5. [Installation & Setup](#5-installation--setup)
6. [Exercises](#6-exercises)
7. [How It's Used in Our Project](#7-how-its-used-in-our-project)
8. [Performance Tuning](#8-performance-tuning)
9. [Further Reading](#9-further-reading)

---

## 1. Introduction

### What is a Vector Database?

A vector database stores **embeddings** — numerical representations of text, images, or other data. When you ask "find documents similar to this query," it searches by mathematical similarity rather than keyword matching.

```
"What is Kubernetes?" → [0.12, -0.34, 0.56, ...] (1536 dimensions)
"K8s container orchestration" → [0.11, -0.33, 0.55, ...] (very similar!)
"Best pizza in NYC" → [0.89, 0.23, -0.67, ...] (very different)
```

### Why pgvector over Dedicated Vector DBs?

| Feature | pgvector | Pinecone | Weaviate |
|---------|----------|----------|----------|
| Cost | Free (open source) | Pay per query | Open source |
| Ops complexity | You already run PostgreSQL | New service | New service |
| SQL support | Full PostgreSQL | API only | GraphQL |
| Hybrid search | text + vector | Vector only | Text + vector |
| ACID transactions | Yes | No | Limited |
| Joins with relational data | Native | No | No |
| Ecosystem | All PG tools work | Proprietary | Custom |

**Bottom line:** If you already run PostgreSQL, pgvector is the obvious choice.

---

## 2. Core Concepts

### 2.1 Embeddings

An embedding converts text into a fixed-size numerical vector:

```
"Machine learning is great" → [0.023, -0.145, 0.891, ..., 0.034]
                                (typically 384, 768, or 1536 dimensions)
```

Similar meanings → similar vectors → small distance between them.

### 2.2 Distance Metrics

| Metric | Operator | Best For | Range |
|--------|----------|----------|-------|
| **L2 (Euclidean)** | `<->` | General purpose | 0 to ∞ |
| **Cosine** | `<=>` | Text similarity | 0 to 2 |
| **Inner Product** | `<#>` | Recommendation, when vectors are normalized | -∞ to ∞ |

```sql
-- L2 distance (smaller = more similar)
SELECT * FROM documents ORDER BY embedding <-> query_vector LIMIT 5;

-- Cosine distance (smaller = more similar)
SELECT * FROM documents ORDER BY embedding <=> query_vector LIMIT 5;

-- Negative inner product (more negative = more similar)
SELECT * FROM documents ORDER BY embedding <#> query_vector LIMIT 5;
```

### 2.3 Index Types

**IVFFlat** (Inverted File with Flat compression):
- Divides vectors into clusters (lists)
- Searches only nearby clusters
- Faster to build, good for moderate datasets

**HNSW** (Hierarchical Navigable Small World):
- Graph-based index
- More accurate than IVFFlat
- Uses more memory, slower to build
- Better query performance

| Feature | IVFFlat | HNSW |
|---------|---------|------|
| Build time | Fast | Slow |
| Query speed | Good | Better |
| Accuracy | Good | Better |
| Memory | Lower | Higher |
| Recommended for | <1M vectors | Any size |

---

## 3. PostgreSQL Refresher

### Essential SQL

```sql
-- Create table
CREATE TABLE models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20),
    parameters_b FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert
INSERT INTO models (name, version, parameters_b)
VALUES ('llama-3', '3.1.0', 70.0);

-- Query with conditions
SELECT * FROM models WHERE parameters_b > 10 ORDER BY created_at DESC;

-- Update
UPDATE models SET version = '3.2.0' WHERE name = 'llama-3';

-- JSONB — store flexible metadata
ALTER TABLE models ADD COLUMN metadata JSONB DEFAULT '{}';
UPDATE models SET metadata = '{"quantization": "Q4_K_M", "context_length": 4096}'
WHERE name = 'llama-3';

-- Query JSONB
SELECT name, metadata->>'quantization' as quant FROM models;
SELECT * FROM models WHERE metadata->>'context_length' = '4096';

-- Common Table Expressions (CTEs)
WITH active_models AS (
    SELECT * FROM models WHERE metadata->>'status' = 'active'
)
SELECT name, parameters_b FROM active_models ORDER BY parameters_b DESC;

-- Window functions
SELECT
    name,
    parameters_b,
    RANK() OVER (ORDER BY parameters_b DESC) as size_rank
FROM models;
```

---

## 4. pgvector Deep Dive

### 4.1 Vector Data Type

```sql
-- Enable the extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a table with a vector column
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),     -- 1536-dimensional vector (OpenAI ada-002 size)
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.2 Distance Operators

```sql
-- L2 distance
SELECT content, embedding <-> '[0.1, 0.2, ...]'::vector AS distance
FROM documents
ORDER BY distance
LIMIT 5;

-- Cosine distance
SELECT content, embedding <=> '[0.1, 0.2, ...]'::vector AS distance
FROM documents
ORDER BY distance
LIMIT 5;

-- Cosine similarity (1 - cosine distance)
SELECT content, 1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM documents
ORDER BY similarity DESC
LIMIT 5;
```

### 4.3 Creating Indexes

```sql
-- HNSW index (recommended)
CREATE INDEX ON documents
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- IVFFlat index
CREATE INDEX ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- sqrt(num_rows) is a good starting point

-- Index for L2 distance
CREATE INDEX ON documents USING hnsw (embedding vector_l2_ops);

-- Index for inner product
CREATE INDEX ON documents USING hnsw (embedding vector_ip_ops);
```

### 4.4 HNSW Parameters

| Parameter | Description | Default | Recommendation |
|-----------|-------------|---------|----------------|
| `m` | Max connections per node | 16 | 16-64 (higher = more accurate, more memory) |
| `ef_construction` | Build-time search width | 64 | 64-200 (higher = better index, slower build) |
| `ef_search` | Query-time search width | 40 | 40-200 (higher = more accurate, slower query) |

```sql
-- Set query-time parameter
SET hnsw.ef_search = 100;
```

---

## 5. Installation & Setup

### Docker Compose

```yaml
# docker-compose.yml
version: "3.8"
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: aiplatform
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

volumes:
  pgdata:
```

```sql
-- init.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    source VARCHAR(255),
    chunk_index INTEGER,
    metadata JSONB DEFAULT '{}',
    embedding vector(384),    -- Using a smaller dimension for exercises
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);
```

```bash
docker compose up -d
psql postgresql://admin:secret@localhost:5432/aiplatform
```

---

## 6. Exercises

### Exercise 1: Create Tables and Insert Embeddings

```sql
-- Connect to database
-- psql postgresql://admin:secret@localhost:5432/aiplatform

-- Create the extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name TEXT,
    embedding vector(3)   -- 3D vectors for easy visualization
);

-- Insert some vectors
INSERT INTO items (name, embedding) VALUES
    ('apple',  '[1.0, 0.0, 0.0]'),
    ('banana', '[0.9, 0.1, 0.0]'),
    ('orange', '[0.8, 0.2, 0.0]'),
    ('car',    '[0.0, 1.0, 0.0]'),
    ('truck',  '[0.1, 0.9, 0.0]'),
    ('bike',   '[0.0, 0.8, 0.2]');

-- Find items similar to 'apple'
SELECT name, embedding <=> '[1.0, 0.0, 0.0]'::vector AS distance
FROM items
ORDER BY distance
LIMIT 3;

-- Result: apple (0), banana (0.01), orange (0.05)
-- Fruits cluster together!
```

---

### Exercise 2: Similarity Search with Different Metrics

```sql
-- Create a more realistic table
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    title TEXT,
    embedding vector(5)
);

INSERT INTO articles (title, embedding) VALUES
    ('Intro to Machine Learning', '[0.9, 0.8, 0.1, 0.2, 0.3]'),
    ('Deep Learning Basics',      '[0.85, 0.9, 0.15, 0.1, 0.25]'),
    ('Neural Network Guide',      '[0.8, 0.85, 0.2, 0.15, 0.3]'),
    ('Cooking Italian Food',      '[0.1, 0.2, 0.9, 0.8, 0.1]'),
    ('French Cuisine Guide',      '[0.15, 0.1, 0.85, 0.9, 0.15]'),
    ('Kubernetes in Production',   '[0.3, 0.2, 0.1, 0.1, 0.95]');

-- L2 distance (Euclidean)
SELECT title, embedding <-> '[0.88, 0.82, 0.12, 0.18, 0.28]'::vector AS l2_dist
FROM articles ORDER BY l2_dist LIMIT 3;

-- Cosine distance
SELECT title, embedding <=> '[0.88, 0.82, 0.12, 0.18, 0.28]'::vector AS cos_dist
FROM articles ORDER BY cos_dist LIMIT 3;

-- Inner product (negate for similarity)
SELECT title, (embedding <#> '[0.88, 0.82, 0.12, 0.18, 0.28]'::vector) * -1 AS ip_sim
FROM articles ORDER BY embedding <#> '[0.88, 0.82, 0.12, 0.18, 0.28]'::vector LIMIT 3;
```

---

### Exercise 3: HNSW vs IVFFlat Performance

```sql
-- Generate test data (10,000 vectors)
CREATE TABLE bench_hnsw (
    id SERIAL PRIMARY KEY,
    embedding vector(128)
);

CREATE TABLE bench_ivfflat (
    id SERIAL PRIMARY KEY,
    embedding vector(128)
);

-- Insert random vectors
INSERT INTO bench_hnsw (embedding)
SELECT ('[' || array_to_string(ARRAY(SELECT random() FROM generate_series(1,128)), ',') || ']')::vector
FROM generate_series(1, 10000);

INSERT INTO bench_ivfflat SELECT * FROM bench_hnsw;

-- Create HNSW index
\timing on
CREATE INDEX ON bench_hnsw USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);
-- Note the build time

-- Create IVFFlat index
CREATE INDEX ON bench_ivfflat USING ivfflat (embedding vector_cosine_ops) WITH (lists=100);
-- Compare build times

-- Query performance comparison
EXPLAIN ANALYZE
SELECT id FROM bench_hnsw
ORDER BY embedding <=> (SELECT embedding FROM bench_hnsw WHERE id = 1)
LIMIT 10;

EXPLAIN ANALYZE
SELECT id FROM bench_ivfflat
ORDER BY embedding <=> (SELECT embedding FROM bench_ivfflat WHERE id = 1)
LIMIT 10;
```

---

### Exercise 4: Python App with asyncpg

```python
# vector_app.py
import asyncio
import asyncpg
import numpy as np

async def main():
    conn = await asyncpg.connect(
        "postgresql://admin:secret@localhost:5432/aiplatform"
    )

    # Create table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            embedding vector(384)
        )
    """)

    # Insert vectors (simulated embeddings)
    texts = [
        "Kubernetes orchestrates containers",
        "Docker packages applications",
        "Python is a programming language",
        "Machine learning uses neural networks",
        "PostgreSQL is a relational database",
    ]

    for text in texts:
        # In production, use a real embedding model
        embedding = np.random.randn(384).tolist()
        await conn.execute(
            "INSERT INTO embeddings (text, embedding) VALUES ($1, $2)",
            text, str(embedding),
        )

    # Search for similar texts
    query_embedding = np.random.randn(384).tolist()
    results = await conn.fetch("""
        SELECT text, embedding <=> $1::vector AS distance
        FROM embeddings
        ORDER BY distance
        LIMIT 3
    """, str(query_embedding))

    print("Most similar texts:")
    for row in results:
        print(f"  [{row['distance']:.4f}] {row['text']}")

    await conn.close()

asyncio.run(main())
```

---

### Exercise 5: RAG Pipeline

```python
# rag_pipeline.py
import asyncio
import asyncpg
import httpx

EMBED_URL = "http://localhost:8080/v1/embeddings"  # llama.cpp or other
LLM_URL = "http://localhost:8080/v1/chat/completions"
DB_URL = "postgresql://admin:secret@localhost:5432/aiplatform"

async def get_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(EMBED_URL, json={"input": text})
        return response.json()["data"][0]["embedding"]

async def ingest_document(conn, text: str, source: str):
    """Split text into chunks, embed, and store."""
    # Simple chunking (in production, use smarter splitting)
    chunk_size = 500
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    for i, chunk in enumerate(chunks):
        embedding = await get_embedding(chunk)
        await conn.execute("""
            INSERT INTO documents (content, source, chunk_index, embedding)
            VALUES ($1, $2, $3, $4)
        """, chunk, source, i, str(embedding))

    print(f"Ingested {len(chunks)} chunks from {source}")

async def search(conn, query: str, top_k: int = 3) -> list[dict]:
    """Find most relevant document chunks."""
    query_embedding = await get_embedding(query)
    rows = await conn.fetch("""
        SELECT content, source, 1 - (embedding <=> $1::vector) AS similarity
        FROM documents
        ORDER BY embedding <=> $1::vector
        LIMIT $2
    """, str(query_embedding), top_k)
    return [dict(r) for r in rows]

async def ask(conn, question: str) -> str:
    """RAG: retrieve context, then generate answer."""
    # Step 1: Retrieve relevant chunks
    contexts = await search(conn, question)
    context_text = "\n\n".join(
        f"[Source: {c['source']}] {c['content']}" for c in contexts
    )

    # Step 2: Generate answer using LLM with context
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(LLM_URL, json={
            "messages": [
                {"role": "system", "content": f"Answer based on this context:\n{context_text}"},
                {"role": "user", "content": question},
            ],
            "max_tokens": 500,
        })
        return response.json()["choices"][0]["message"]["content"]

async def main():
    conn = await asyncpg.connect(DB_URL)

    # Ingest some documents
    await ingest_document(conn, "Kubernetes is an open-source container orchestration platform...", "k8s-docs")

    # Ask a question
    answer = await ask(conn, "How does Kubernetes work?")
    print(f"Answer: {answer}")

    await conn.close()

asyncio.run(main())
```

---

### Exercise 6: Hybrid Search (Text + Vector)

```sql
-- Add full-text search column
ALTER TABLE documents ADD COLUMN tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX ON documents USING gin(tsv);

-- Hybrid search: combine text relevance + vector similarity
WITH text_results AS (
    SELECT id, ts_rank(tsv, plainto_tsquery('english', 'kubernetes container')) AS text_score
    FROM documents
    WHERE tsv @@ plainto_tsquery('english', 'kubernetes container')
),
vector_results AS (
    SELECT id, 1 - (embedding <=> $1::vector) AS vector_score
    FROM documents
    ORDER BY embedding <=> $1::vector
    LIMIT 20
)
SELECT
    d.id,
    d.content,
    COALESCE(t.text_score, 0) * 0.3 + COALESCE(v.vector_score, 0) * 0.7 AS combined_score
FROM documents d
LEFT JOIN text_results t ON d.id = t.id
LEFT JOIN vector_results v ON d.id = v.id
WHERE t.id IS NOT NULL OR v.id IS NOT NULL
ORDER BY combined_score DESC
LIMIT 5;
```

---

### Exercise 7: Metadata Filtering with Vector Search

```sql
-- Insert documents with metadata
INSERT INTO documents (content, metadata, embedding) VALUES
    ('LLM serving guide', '{"category": "ml", "level": "advanced", "tags": ["llm", "serving"]}', '[...]'),
    ('Python basics', '{"category": "programming", "level": "beginner", "tags": ["python"]}', '[...]');

-- Vector search with metadata filters
SELECT content, metadata, 1 - (embedding <=> $1::vector) AS similarity
FROM documents
WHERE metadata->>'category' = 'ml'                    -- Filter by category
  AND metadata->>'level' IN ('intermediate', 'advanced')  -- Filter by level
  AND metadata->'tags' ? 'llm'                         -- Must have 'llm' tag
ORDER BY embedding <=> $1::vector
LIMIT 5;

-- Create GIN index on metadata for fast filtering
CREATE INDEX ON documents USING gin(metadata);

-- Filter + vector search with minimum similarity
SELECT content, 1 - (embedding <=> $1::vector) AS similarity
FROM documents
WHERE metadata @> '{"category": "ml"}'
  AND (embedding <=> $1::vector) < 0.5   -- Cosine distance < 0.5
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

---

## 7. How It's Used in Our Project

- **Document storage** — RAG documents are chunked, embedded, and stored in pgvector
- **Similarity search** — User queries are embedded and matched against stored chunks
- **Hybrid search** — Combines keyword (tsvector) and semantic (vector) search
- **Metadata filtering** — Filter by source, date, category before vector search
- **Combined with MinIO** — Raw files in MinIO, processed chunks in pgvector
- **Combined with Redis** — Semantic cache in Redis, full search in pgvector

---

## 8. Performance Tuning

### Index Tuning

```sql
-- HNSW: increase ef_search for better accuracy (at cost of speed)
SET hnsw.ef_search = 100;  -- Default: 40

-- IVFFlat: increase probes for better accuracy
SET ivfflat.probes = 10;   -- Default: 1
```

### PostgreSQL Configuration

```ini
# postgresql.conf
shared_buffers = 4GB              # 25% of RAM
effective_cache_size = 12GB       # 75% of RAM
work_mem = 256MB                  # Per-query memory
maintenance_work_mem = 2GB        # For index builds
max_parallel_workers_per_gather = 4
```

### Partitioning for Large Datasets

```sql
-- Partition by source/category for faster filtered searches
CREATE TABLE documents_partitioned (
    id SERIAL,
    content TEXT,
    category TEXT,
    embedding vector(384)
) PARTITION BY LIST (category);

CREATE TABLE documents_ml PARTITION OF documents_partitioned FOR VALUES IN ('ml');
CREATE TABLE documents_ops PARTITION OF documents_partitioned FOR VALUES IN ('ops');
```

---

## 9. Further Reading

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [pgvector Documentation](https://github.com/pgvector/pgvector#readme)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [HNSW Algorithm Explained](https://arxiv.org/abs/1603.09320)
- [Supabase pgvector Guide](https://supabase.com/docs/guides/ai/vector-columns)
