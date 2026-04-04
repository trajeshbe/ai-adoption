# Phase 3: Data Layer -- Build Vector Search, Object Storage, and Semantic Cache

## What You Will Learn
- pgvector for vector similarity search in PostgreSQL
- Document chunking strategies for RAG (Retrieval-Augmented Generation)
- MinIO for S3-compatible object storage
- Redis VSS (Vector Similarity Search) for semantic caching
- Integration testing with testcontainers
- Database migrations with Alembic

## Prerequisites
- Phase 1-2 complete (Gateway + Frontend running)
- Postgres with pgvector, Redis with RediSearch, MinIO all running (from DevContainer)

## Background: Why pgvector Over Pinecone/Weaviate?
Adding a dedicated vector database introduces another stateful system to operate,
another failure mode, and another data store to back up. Postgres with pgvector
provides HNSW indexing with recall competitive with specialized databases at our
scale (millions of vectors, not billions). It also enables transactional consistency --
document metadata and embeddings live in the same database, so a failed ingest never
leaves orphaned records.

See: docs/architecture/adr/006-pgvector-over-dedicated-vectordb.md

## Step-by-Step Instructions

### Step 1: Create the Document Service

Create `services/document-service/pyproject.toml` with dependencies:
- fastapi, uvicorn, httpx
- sqlalchemy, asyncpg, alembic, pgvector
- minio
- sentence-transformers (for embeddings)
- agent-platform-common

### Step 2: Design the Database Schema

Create Alembic migration for the document tables:
```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table (metadata)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    object_key VARCHAR(500) NOT NULL,  -- MinIO object path
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Document chunks with vector embeddings
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),  -- all-MiniLM-L6-v2 produces 384-dim vectors
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX ON document_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);
```

**Why HNSW?** It's the state-of-the-art approximate nearest neighbor algorithm.
The `m=16` parameter controls graph connectivity (higher = better recall, more memory).
`ef_construction=200` controls build-time search depth (higher = better index quality).

### Step 3: Implement the Ingestion Pipeline

Create `services/document-service/src/document_service/ingest.py`:

1. **Upload to MinIO** -- Store raw file in `documents/` bucket
2. **Extract text** -- Use PyMuPDF for PDFs, python-docx for DOCX
3. **Chunk** -- Recursive character splitting (512 tokens, 50 token overlap)
4. **Embed** -- Generate vector embeddings via sentence-transformers
5. **Upsert** -- Store chunks + embeddings in pgvector

```python
async def ingest_document(file: UploadFile) -> Document:
    # 1. Store raw file in MinIO
    object_key = f"documents/{uuid4()}/{file.filename}"
    await minio_client.put_object(bucket="documents", key=object_key, data=file)

    # 2. Extract text
    text = await extract_text(file)

    # 3. Chunk with overlap
    chunks = recursive_character_split(text, chunk_size=512, overlap=50)

    # 4. Generate embeddings
    embeddings = embedding_model.encode([c.content for c in chunks])

    # 5. Upsert to pgvector
    await upsert_chunks(document_id, chunks, embeddings)
```

**Why recursive character splitting?** It respects paragraph/sentence boundaries
instead of blindly cutting at character N. The 50-token overlap ensures context
isn't lost at chunk boundaries.

### Step 4: Implement the Retriever

Create `services/document-service/src/document_service/retriever.py`:

```python
async def retrieve_similar(query: str, top_k: int = 5) -> list[ChunkResult]:
    query_embedding = embedding_model.encode(query)
    results = await db.execute(
        text("""
            SELECT id, content, metadata,
                   1 - (embedding <=> :query_vec) AS similarity
            FROM document_chunks
            ORDER BY embedding <=> :query_vec
            LIMIT :top_k
        """),
        {"query_vec": str(query_embedding.tolist()), "top_k": top_k}
    )
    return [ChunkResult(**row) for row in results]
```

**The `<=>` operator** is pgvector's cosine distance. `1 - distance = similarity`.

### Step 5: Create the Cache Service

Create `services/cache-service/src/cache_service/semantic_cache.py`:

```python
import redis
from redis.commands.search.query import Query

class SemanticCache:
    def __init__(self, redis_client: redis.Redis, threshold: float = 0.95):
        self.redis = redis_client
        self.threshold = threshold

    async def get(self, query: str) -> str | None:
        query_embedding = embed(query)
        # Vector similarity search in Redis
        q = Query(f"*=>[KNN 1 @embedding $vec AS score]") \
            .return_fields("response", "score") \
            .dialect(2)
        results = self.redis.ft("cache_idx").search(
            q, query_params={"vec": query_embedding.tobytes()}
        )
        if results.docs and float(results.docs[0].score) >= self.threshold:
            return results.docs[0].response  # Cache hit!
        return None  # Cache miss

    async def put(self, query: str, response: str) -> None:
        embedding = embed(query)
        key = f"cache:{uuid4()}"
        self.redis.hset(key, mapping={
            "query": query,
            "response": response,
            "embedding": embedding.tobytes(),
        })
        self.redis.expire(key, 3600)  # 1 hour TTL
```

### Step 6: Create Redis Vector Index

```python
# Run once at startup
from redis.commands.search.field import VectorField, TextField

schema = [
    TextField("query"),
    TextField("response"),
    VectorField("embedding",
        algorithm="HNSW",
        attributes={"TYPE": "FLOAT32", "DIM": 384, "DISTANCE_METRIC": "COSINE"}
    ),
]
redis_client.ft("cache_idx").create_index(schema)
```

### Step 7: Wire Gateway to Data Services

Update `services/gateway/src/gateway/resolvers/document.py` to call document-service
via httpx instead of returning mock data.

### Step 8: Write Integration Tests

Use testcontainers to spin up real Postgres+pgvector and Redis for tests:
```python
@pytest.fixture
def postgres_container():
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        yield pg

def test_ingest_and_retrieve(postgres_container):
    # Ingest a document
    doc = await ingest_document(sample_pdf)
    assert doc.chunk_count > 0

    # Retrieve similar chunks
    results = await retrieve_similar("What is the weather?")
    assert len(results) > 0
    assert results[0].similarity > 0.7
```

## Verification
```bash
# Start services
cd services/document-service && uv run uvicorn document_service.main:create_app --factory --port 8001
cd services/cache-service && uv run uvicorn cache_service.main:create_app --factory --port 8002

# Upload a document via gateway
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@sample.pdf"

# Query similar chunks via GraphQL
# { documents { id filename chunkCount } }

# Test semantic cache
# Send same query twice -- second should be faster (cache hit)

# Run integration tests
uv run pytest services/document-service/tests/integration/ -v
uv run pytest services/cache-service/tests/ -v
```

## Key Concepts Taught
1. **pgvector HNSW** -- Approximate nearest neighbor search in Postgres
2. **RAG pipeline** -- Ingest -> Chunk -> Embed -> Store -> Retrieve -> Generate
3. **Semantic caching** -- Highest-ROI LLM optimization (sub-ms vs multi-second)
4. **Testcontainers** -- Real databases in tests, not mocks
5. **Object storage** -- MinIO for raw files, Postgres for structured data + vectors

## What's Next
Phase 4 (`/04-build-agent-dag`) builds the agent orchestration engine with LangGraph
state machines wrapped in Prefect flows. This is where AI agents come alive.
