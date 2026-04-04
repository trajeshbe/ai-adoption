# Database Architecture Guide

> Everything about how this platform stores, retrieves, and caches data.
> Written for fresh graduates — no prior database experience beyond basic SQL assumed.

---

## Table of Contents

1. [Overview — Three Storage Systems](#1-overview--three-storage-systems)
2. [PostgreSQL + pgvector — The Brain](#2-postgresql--pgvector--the-brain)
3. [Redis 7.2 + VSS — The Fast Memory](#3-redis-72--vss--the-fast-memory)
4. [MinIO — The Filing Cabinet](#4-minio--the-filing-cabinet)
5. [Database Schema (Complete)](#5-database-schema-complete)
6. [pgvector Deep Dive — How AI Search Works](#6-pgvector-deep-dive--how-ai-search-works)
7. [Alembic Migrations — Schema Evolution](#7-alembic-migrations--schema-evolution)
8. [Seed Data](#8-seed-data)
9. [How Data Flows Through the System](#9-how-data-flows-through-the-system)
10. [Connecting to the Database](#10-connecting-to-the-database)
11. [Key Queries](#11-key-queries)
12. [Production Considerations](#12-production-considerations)

---

## 1. Overview — Three Storage Systems

This platform uses three complementary storage systems, each optimized for a different
type of data:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Storage Architecture                     │
├──────────────────┬──────────────────┬───────────────────────────┤
│   PostgreSQL     │   Redis 7.2      │   MinIO                   │
│   + pgvector     │   + RediSearch    │   (S3-compatible)         │
├──────────────────┼──────────────────┼───────────────────────────┤
│ Structured data  │ Semantic cache   │ Raw files                 │
│ • agents         │ • LLM responses  │ • PDFs, docs, images      │
│ • chat sessions  │ • Query embeddings│ • Model artifacts        │
│ • chat messages  │ • Cache hits     │ • Uploaded documents      │
│ • documents      │                  │                           │
│ • vector chunks  │ Sub-millisecond  │ S3-compatible API         │
│ • inference costs│ similarity search│ Unlimited storage         │
│                  │                  │                           │
│ ACID compliant   │ In-memory speed  │ Object storage            │
│ SQL + vectors    │ VSS (cosine)     │ Bucket-based              │
└──────────────────┴──────────────────┴───────────────────────────┘
```

**Think of it like a library:**
- **PostgreSQL** = the card catalog (organized, searchable, relational)
- **Redis** = the librarian's memory ("someone just asked the same thing 5 minutes ago")
- **MinIO** = the shelves where actual books are stored

---

## 2. PostgreSQL + pgvector — The Brain

### What is PostgreSQL?
PostgreSQL (Postgres) is the world's most advanced open-source relational database.
It stores data in tables with rows and columns, supports SQL queries, and guarantees
ACID transactions (your data is always consistent).

### What is pgvector?
pgvector is a PostgreSQL extension that adds **vector data types and similarity search**.
This lets you store AI embeddings (arrays of numbers representing meaning) and search
for similar items using cosine distance, L2 distance, or inner product.

**Version in our stack:** pgvector 0.8.1 on PostgreSQL 16

### Why not use a dedicated vector database?
We evaluated Pinecone, Weaviate, and Qdrant (see ADR-006). We chose pgvector because:

| Factor              | pgvector          | Pinecone           | Weaviate            |
|---------------------|-------------------|--------------------|---------------------|
| Operational overhead| Zero (use existing PG) | New service   | New service         |
| ACID transactions   | Full              | No                 | No                  |
| SQL joins           | Native            | No                 | GraphQL-like        |
| Scale ceiling       | ~100M vectors     | Billions           | Hundreds of millions|
| Cost                | Free              | $70+/month         | Free tier limited   |
| Metadata queries    | Full SQL          | Limited filters    | GraphQL             |

**Bottom line:** For < 100M vectors (which covers 99% of applications), pgvector gives
you vectors + relational data in one database. One less thing to operate.

---

## 3. Redis 7.2 + VSS — The Fast Memory

### What is Redis?
Redis is an in-memory data store. Data lives in RAM, so reads and writes are
sub-millisecond (0.1-0.5ms vs 2-10ms for disk-based databases).

### What is VSS (Vector Similarity Search)?
Redis 7.2 with the RediSearch module supports vector fields. We use this for
**semantic caching** — the highest-ROI optimization for LLM applications.

### How Semantic Caching Works

```
WITHOUT cache:
  User: "What's the weather in NYC?"     → LLM call → 2000ms, $0.003
  User: "How's the weather in New York?" → LLM call → 2000ms, $0.003  ← WASTED!

WITH semantic cache (cosine similarity > 0.95):
  User: "What's the weather in NYC?"     → LLM call → 2000ms, $0.003
  User: "How's the weather in New York?" → Cache HIT → 0.5ms,  $0.000  ← 4000x faster!
```

The cache doesn't need exact string match. It converts queries to vectors and checks
if a semantically similar query was already answered.

### Cache Configuration

```python
# From: services/cache-service/src/cache_service/semantic_cache.py

# RediSearch index schema
INDEX_NAME = "idx:llm_cache"
PREFIX = "llm_cache:"

# Vector field: HNSW index, 384 dimensions, cosine distance
# Similarity threshold: 0.95 (95% similar = cache hit)
# TTL: 1 hour per entry
```

---

## 4. MinIO — The Filing Cabinet

### What is MinIO?
MinIO is an S3-compatible object store. It speaks the same API as Amazon S3, so any
code that works with S3 works with MinIO. We use it for storing raw files
(PDFs, documents, images) before they're chunked and embedded.

### Buckets

| Bucket      | Purpose                                     |
|-------------|---------------------------------------------|
| `documents` | Uploaded user documents (PDFs, TXT, DOCX)   |
| `models`    | Model artifacts and weights                 |
| `artifacts` | Generated outputs, exports, backups         |

### Storage Path
Documents are stored at: `documents/{document_id}/{filename}`

When a user uploads a PDF:
1. Raw file → MinIO (`documents/` bucket)
2. Text extracted → chunked into 512-token segments
3. Each chunk → embedded (384-dim vector)
4. Chunks + vectors → PostgreSQL (`document_chunks` table)

---

## 5. Database Schema (Complete)

### Entity Relationship Diagram

```
┌─────────────────────┐       ┌─────────────────────────┐
│       agents        │       │      documents          │
├─────────────────────┤       ├─────────────────────────┤
│ id          UUID PK │──┐    │ id            UUID PK   │──┐
│ name        VARCHAR │  │    │ filename      VARCHAR   │  │
│ agent_type  VARCHAR │  │    │ content_type  VARCHAR   │  │
│ instructions TEXT   │  │    │ minio_key     VARCHAR   │  │
│ model       VARCHAR │  │    │ chunk_count   INTEGER   │  │
│ is_active   BOOLEAN │  │    │ created_at    TIMESTAMP │  │
│ created_at  TIMESTAMP│  │    └─────────────────────────┘  │
│ updated_at  TIMESTAMP│  │                                 │
└─────────────────────┘  │    ┌─────────────────────────┐  │
                         │    │   document_chunks       │  │
┌─────────────────────┐  │    ├─────────────────────────┤  │
│   chat_sessions     │  │    │ id            UUID PK   │  │
├─────────────────────┤  │    │ document_id   UUID FK ──┘  │
│ id          UUID PK │──┤    │ chunk_index   INTEGER   │
│ agent_id    UUID FK ─┘  │    │ content       TEXT      │
│ title       VARCHAR │       │ embedding     VECTOR(384)│ ← pgvector!
│ created_at  TIMESTAMP│       │ created_at    TIMESTAMP │
│ updated_at  TIMESTAMP│       └─────────────────────────┘
└─────────────────────┘           ↑ HNSW index (cosine)
         │
         │ 1:many
         ▼
┌─────────────────────┐       ┌─────────────────────────┐
│   chat_messages     │       │   inference_costs       │
├─────────────────────┤       ├─────────────────────────┤
│ id          UUID PK │       │ id              UUID PK │
│ session_id  UUID FK │       │ model           VARCHAR │
│ role        VARCHAR │       │ prompt_tokens   INTEGER │
│ content     TEXT    │       │ completion_tokens INT   │
│ tool_calls  JSON   │       │ total_cost_usd  FLOAT   │
│ cost_usd    FLOAT  │       │ agent_type      VARCHAR │
│ latency_ms  FLOAT  │       │ session_id      UUID    │
│ model       VARCHAR │       │ created_at      TIMESTAMP│
│ prompt_tokens INT  │       └─────────────────────────┘
│ completion_tokens INT│
│ created_at  TIMESTAMP│
└─────────────────────┘
```

### Table Details

#### `agents` — AI Agent Configurations
Stores the definition of each agent type the platform supports.

| Column       | Type         | Description                                |
|--------------|-------------|--------------------------------------------|
| id           | UUID (PK)    | Unique identifier (well-known UUIDs for built-in agents) |
| name         | VARCHAR(256) | Human-readable name ("Weather Agent")      |
| agent_type   | VARCHAR(50)  | WEATHER, QUIZ, RAG, or CUSTOM              |
| instructions | TEXT         | System prompt sent to the LLM              |
| model        | VARCHAR(128) | LLM model name (default: qwen2.5:1.5b)    |
| is_active    | BOOLEAN      | Whether the agent is available for use     |
| created_at   | TIMESTAMPTZ  | When the agent was created                 |
| updated_at   | TIMESTAMPTZ  | When the agent was last modified           |

**Seed data (3 built-in agents):**
```sql
-- Movie Quiz Bot (direct LLM conversation, no tools)
INSERT INTO agents (id, name, agent_type, instructions, model) VALUES
  ('00000000-0000-0000-0000-000000000001', 'Movie Quiz Bot', 'QUIZ',
   'You are a fun movie trivia quiz bot...', 'qwen2.5:1.5b');

-- Weather Agent (uses get_weather tool)
INSERT INTO agents (id, name, agent_type, instructions, model) VALUES
  ('00000000-0000-0000-0000-000000000002', 'Weather Agent', 'WEATHER',
   'You are a helpful weather assistant...', 'qwen2.5:1.5b');

-- Document Assistant (uses search_documents tool for RAG)
INSERT INTO agents (id, name, agent_type, instructions, model) VALUES
  ('00000000-0000-0000-0000-000000000003', 'Document Assistant', 'RAG',
   'You are a document assistant...', 'qwen2.5:1.5b');
```

#### `chat_sessions` — Conversation Threads
Each chat session links a user conversation to an agent.

| Column     | Type         | Description                               |
|------------|-------------|-------------------------------------------|
| id         | UUID (PK)    | Session identifier (generated by frontend)|
| agent_id   | UUID (FK)    | Which agent this session uses             |
| title      | VARCHAR(512) | Auto-generated session title              |
| created_at | TIMESTAMPTZ  | When the session started                  |
| updated_at | TIMESTAMPTZ  | Last activity timestamp                   |

**Indexes:** agent_id (lookup sessions by agent), updated_at (sort by recency)

#### `chat_messages` — Individual Messages
Every message in every conversation, including tool calls and cost data.

| Column            | Type         | Description                           |
|-------------------|-------------|---------------------------------------|
| id                | UUID (PK)    | Message identifier                    |
| session_id        | UUID (FK)    | Which session this message belongs to |
| role              | VARCHAR(20)  | user, assistant, system, or tool      |
| content           | TEXT         | The message text                      |
| tool_calls        | JSON         | Array of {tool_name, arguments, result} |
| cost_usd          | FLOAT        | Cost of this inference in USD         |
| latency_ms        | FLOAT        | End-to-end latency in milliseconds    |
| model             | VARCHAR(128) | Which LLM model generated this        |
| prompt_tokens     | INTEGER      | Number of input tokens                |
| completion_tokens | INTEGER      | Number of output tokens               |
| created_at        | TIMESTAMPTZ  | When the message was created          |

**Indexes:** session_id (load conversation history), created_at (chronological order)

#### `documents` — Uploaded Document Metadata
Metadata for files uploaded for RAG (Retrieval Augmented Generation).

| Column       | Type         | Description                              |
|-------------|-------------|------------------------------------------|
| id           | UUID (PK)    | Document identifier                      |
| filename     | VARCHAR(512) | Original filename                        |
| content_type | VARCHAR(128) | MIME type (application/pdf, text/plain)  |
| minio_key    | VARCHAR(1024)| Path in MinIO object store               |
| chunk_count  | INTEGER      | Number of text chunks extracted          |
| created_at   | TIMESTAMPTZ  | Upload timestamp                         |

#### `document_chunks` — Vector Embeddings for RAG
Text chunks with their 384-dimensional vector embeddings for semantic search.

| Column      | Type          | Description                              |
|-------------|--------------|------------------------------------------|
| id          | UUID (PK)     | Chunk identifier                         |
| document_id | UUID (FK)     | Parent document (CASCADE delete)         |
| chunk_index | INTEGER       | Position in original document            |
| content     | TEXT          | The actual text of this chunk            |
| embedding   | VECTOR(384)   | 384-dim embedding (all-MiniLM-L6-v2)    |
| created_at  | TIMESTAMPTZ   | When the chunk was created               |

**Indexes:**
- `ix_document_chunks_document_id` — B-tree for fast document lookups
- `ix_document_chunks_embedding_hnsw` — **HNSW vector index** for similarity search

#### `inference_costs` — LLM Usage Tracking
Every LLM inference call is recorded with its token counts and cost.

| Column            | Type         | Description                          |
|-------------------|-------------|--------------------------------------|
| id                | UUID (PK)    | Cost record identifier               |
| model             | VARCHAR(128) | Which model was used                 |
| prompt_tokens     | INTEGER      | Input tokens consumed                |
| completion_tokens | INTEGER      | Output tokens generated              |
| total_cost_usd    | FLOAT        | Calculated cost in USD               |
| agent_type        | VARCHAR(50)  | Which agent type incurred the cost   |
| session_id        | UUID         | Which chat session (nullable)        |
| created_at        | TIMESTAMPTZ  | When the inference happened          |

**Indexes:** created_at (time-range queries), model (per-model cost analysis)

---

## 6. pgvector Deep Dive — How AI Search Works

### The Problem: Computers Don't Understand Meaning

Traditional databases search by exact match:
```sql
SELECT * FROM chunks WHERE content LIKE '%weather%';
-- Misses: "climate conditions", "temperature forecast", "how hot is it"
```

### The Solution: Vector Embeddings

An **embedding model** converts text into a point in 384-dimensional space,
where similar meanings are close together:

```
"What's the weather in Tokyo?"  → [0.12, -0.45, 0.78, ..., 0.33]  (384 numbers)
"Tokyo climate conditions"      → [0.11, -0.44, 0.77, ..., 0.34]  (very close!)
"Best pizza in New York"        → [-0.56, 0.23, -0.12, ..., 0.89] (very different)
```

### How pgvector Stores and Searches Vectors

```sql
-- 1. The embedding column stores vectors
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(384)    -- ← pgvector type: array of 384 floats
);

-- 2. HNSW index makes search fast (O(log n) instead of O(n))
CREATE INDEX ix_embedding_hnsw ON document_chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 200);

-- 3. Similarity search: find the 5 most similar chunks to a query
SELECT content, 1 - (embedding <=> $query_vector) AS similarity
FROM document_chunks
ORDER BY embedding <=> $query_vector  -- <=> is cosine distance
LIMIT 5;
```

### HNSW Index Explained

**HNSW** (Hierarchical Navigable Small World) is an approximate nearest neighbor
algorithm. Think of it like a skip list for vectors:

```
Level 2:  [A] ─────────────────── [M] ─────────────────── [Z]
Level 1:  [A] ─── [E] ─── [I] ── [M] ─── [Q] ─── [U] ── [Z]
Level 0:  [A][B][C][D][E][F][G][H][I][J][K][L][M][N]...[Z]

Search for similar to "weather in Tokyo":
  Start at Level 2 → jump to nearest node
  Drop to Level 1 → refine
  Drop to Level 0 → exact neighbors
```

**Our HNSW parameters:**
- `m = 16` — each node connects to 16 neighbors (more = better recall, more memory)
- `ef_construction = 200` — build-time search depth (more = better index quality, slower build)

**Performance:**
- Build: ~1 minute for 100K vectors
- Search: < 5ms for 1M vectors (vs 500ms+ for brute force)
- Recall: 99%+ for our parameters

### How RAG Uses pgvector

```
User asks: "What did the Q3 report say about revenue?"

1. Embed the question → [0.23, -0.67, ...]  (384 dims)

2. Search pgvector:
   SELECT content, 1 - (embedding <=> $query) AS score
   FROM document_chunks
   ORDER BY embedding <=> $query
   LIMIT 5;

3. Results:
   ┌─────────────────────────────────────────┬───────┐
   │ content                                  │ score │
   ├─────────────────────────────────────────┼───────┤
   │ "Q3 revenue grew 15% to $2.3B driven..." │ 0.94  │
   │ "Revenue breakdown by segment shows..."  │ 0.91  │
   │ "Compared to Q2, revenue increased..."   │ 0.88  │
   │ "Operating margins improved alongside..."│ 0.82  │
   │ "The CFO noted revenue targets were..."  │ 0.79  │
   └─────────────────────────────────────────┴───────┘

4. Feed top chunks + question to LLM → accurate, sourced answer
```

---

## 7. Alembic Migrations — Schema Evolution

### What is Alembic?
Alembic is a database migration tool for SQLAlchemy. It tracks schema changes
as numbered revision files, so you can upgrade and downgrade your database
reproducibly.

### Our Migration Files

```
services/document-service/alembic/
├── alembic.ini                              # Config (database URL)
├── env.py                                   # Async migration runner
└── versions/
    ├── 001_initial_schema.py                # documents + document_chunks + pgvector
    └── 002_agents_chat_costs.py             # agents + chat_sessions + chat_messages + inference_costs
```

### Migration 001: Document Storage + pgvector
```python
def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")  # Enable pgvector

    op.create_table("documents", ...)        # Document metadata
    op.create_table("document_chunks", ...)  # Text chunks + VECTOR(384) column

    # HNSW index for fast cosine similarity search
    op.execute("""
        CREATE INDEX ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 200)
    """)
```

### Migration 002: Agents, Chat, Costs
```python
def upgrade():
    op.create_table("agents", ...)           # Agent configurations
    op.create_table("chat_sessions", ...)    # Conversation threads
    op.create_table("chat_messages", ...)    # Individual messages + tool_calls JSON
    op.create_table("inference_costs", ...)  # Per-inference cost tracking

    # Seed 3 built-in agents
    op.execute("INSERT INTO agents ...")
```

### Running Migrations
```bash
cd services/document-service

# Apply all migrations
DATABASE_URL=postgresql://agent_platform:agent_platform@localhost:20432/agent_platform \
  uv run alembic upgrade head

# Check current version
uv run alembic current

# Create a new migration
uv run alembic revision --autogenerate -m "add_new_table"

# Rollback one step
uv run alembic downgrade -1
```

---

## 8. Seed Data

### Built-in Agents (seeded in migration 002)

| ID | Name | Type | Model | Tools |
|----|------|------|-------|-------|
| `00000000-...-000000000001` | Movie Quiz Bot | QUIZ | qwen2.5:1.5b | None (direct LLM) |
| `00000000-...-000000000002` | Weather Agent | WEATHER | qwen2.5:1.5b | get_weather |
| `00000000-...-000000000003` | Document Assistant | RAG | qwen2.5:1.5b | search_documents |

### MinIO Buckets (created by bootstrap.sh)
- `documents` — uploaded user files
- `models` — model artifacts
- `artifacts` — exports and backups

---

## 9. How Data Flows Through the System

### Chat Message Flow
```
Browser                                            PostgreSQL
  │                                                    │
  ├─ POST /graphql (sendMessage) ──→ Gateway           │
  │                                    │               │
  │                                    ├─ INSERT chat_messages (user msg)
  │                                    │               │
  │                                    ├─→ Agent Engine │
  │                                    │     │         │
  │                                    │     ├─→ Redis (check semantic cache)
  │                                    │     │   ├─ HIT? → return cached response
  │                                    │     │   └─ MISS? → continue
  │                                    │     │         │
  │                                    │     ├─→ Ollama (LLM inference)
  │                                    │     │         │
  │                                    │     ├─→ Redis (store in cache)
  │                                    │     │         │
  │                                    │     └─ return response
  │                                    │               │
  │                                    ├─ INSERT chat_messages (assistant msg)
  │                                    ├─ INSERT inference_costs
  │                                    │               │
  │  ←── GraphQL response ────────────┘               │
```

### Document Upload Flow
```
Browser                     Gateway        Document Service       MinIO    PostgreSQL
  │                           │                  │                  │          │
  ├─ Upload PDF ──→           │                  │                  │          │
  │                           ├─→ POST /docs/upload                │          │
  │                           │                  │                  │          │
  │                           │                  ├─ Store raw file ─→          │
  │                           │                  │                  │          │
  │                           │                  ├─ Extract text               │
  │                           │                  ├─ Chunk (512 tokens)         │
  │                           │                  ├─ Embed (384-dim vectors)    │
  │                           │                  │                             │
  │                           │                  ├─ INSERT documents ──────────→
  │                           │                  ├─ INSERT document_chunks ────→
  │                           │                  │   (with VECTOR(384))        │
  │                           │                  │                             │
  │  ←── Success ─────────────┘                  │                  │          │
```

---

## 10. Connecting to the Database

### From Host Machine
```bash
# psql (command line)
PGPASSWORD=agent_platform psql -h localhost -p 20432 -U agent_platform -d agent_platform

# Connection string
postgresql://agent_platform:agent_platform@localhost:20432/agent_platform
```

### From Docker Compose Services
```bash
# Inside containers, use service name (not localhost)
postgresql://agent_platform:agent_platform@postgres:5432/agent_platform
redis://redis:6379/0
```

### Redis CLI
```bash
# Connect to Redis
redis-cli -h localhost -p 20379

# Check semantic cache index
FT.INFO idx:llm_cache

# List cached entries
KEYS llm_cache:*
```

### MinIO Console
- URL: http://localhost:20901 (or 9001 in Docker Compose mode)
- Username: minioadmin
- Password: minioadmin

---

## 11. Key Queries

### List all agents
```sql
SELECT id, name, agent_type, model, is_active FROM agents;
```

### Recent chat sessions with message count
```sql
SELECT
    s.id, s.title, a.name AS agent_name,
    COUNT(m.id) AS message_count,
    s.updated_at
FROM chat_sessions s
JOIN agents a ON s.agent_id = a.id
LEFT JOIN chat_messages m ON m.session_id = s.id
GROUP BY s.id, s.title, a.name, s.updated_at
ORDER BY s.updated_at DESC
LIMIT 20;
```

### Conversation history for a session
```sql
SELECT role, content, tool_calls, cost_usd, latency_ms, created_at
FROM chat_messages
WHERE session_id = '...'
ORDER BY created_at ASC;
```

### Semantic search (RAG)
```sql
-- Find the 5 most similar document chunks to a query embedding
SELECT
    dc.content,
    d.filename,
    1 - (dc.embedding <=> $1) AS similarity_score
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
ORDER BY dc.embedding <=> $1
LIMIT 5;
-- $1 is the query embedding vector (384 floats)
```

### Cost analysis by model
```sql
SELECT
    model,
    COUNT(*) AS inference_count,
    SUM(total_cost_usd) AS total_cost,
    AVG(total_cost_usd) AS avg_cost_per_inference,
    SUM(prompt_tokens) AS total_prompt_tokens,
    SUM(completion_tokens) AS total_completion_tokens
FROM inference_costs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY model
ORDER BY total_cost DESC;
```

### Cache hit rate (Redis)
```bash
redis-cli -p 20379 INFO stats | grep keyspace
redis-cli -p 20379 FT.INFO idx:llm_cache
```

---

## 12. Production Considerations

### Use Managed Databases in Cloud
| Local (Docker)        | GCP                    | Azure                    |
|-----------------------|------------------------|--------------------------|
| pgvector container    | Cloud SQL for Postgres | Azure Database for PostgreSQL |
| Redis container       | Memorystore for Redis  | Azure Cache for Redis    |
| MinIO container       | Cloud Storage (GCS)    | Azure Blob Storage       |

### Why Managed Databases?
- Automatic backups
- Point-in-time recovery
- High availability (multi-zone replicas)
- Automatic patching
- Monitoring and alerting built-in
- pgvector is supported on Cloud SQL and Azure Database

### Backup Strategy (Self-Hosted)
```bash
# PostgreSQL backup
docker exec aiadopt-postgres pg_dump -U agent_platform agent_platform > backup.sql

# Restore
cat backup.sql | docker exec -i aiadopt-postgres psql -U agent_platform agent_platform

# Redis backup
docker exec aiadopt-redis redis-cli BGSAVE
docker cp aiadopt-redis:/data/dump.rdb ./redis-backup.rdb
```

### Connection Pooling
For production, use PgBouncer or Postgres connection pooling:
```python
# Our current setup (good for development)
engine = create_async_engine(db_url, pool_size=10)

# Production: increase pool, add overflow
engine = create_async_engine(
    db_url,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
)
```

### pgvector at Scale
| Vectors     | Index Build | Search Latency | Memory    |
|-------------|-------------|----------------|-----------|
| 10K         | 2 seconds   | < 1ms          | ~15 MB    |
| 100K        | 20 seconds  | < 2ms          | ~150 MB   |
| 1M          | 3 minutes   | < 5ms          | ~1.5 GB   |
| 10M         | 30 minutes  | < 10ms         | ~15 GB    |
| 100M        | 5 hours     | < 20ms         | ~150 GB   |

Above 100M vectors, consider Pinecone or Weaviate.

---

*This guide covers the complete database architecture of the AI Agent Platform.*
*For the overall tech stack, see [tech-stack-complete-guide.md](./tech-stack-complete-guide.md).*
*For pgvector vs alternatives, see [ADR-006](../architecture/adr/006-pgvector-over-dedicated-vectordb.md).*
