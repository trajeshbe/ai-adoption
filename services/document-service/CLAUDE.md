# Document Service

## Purpose
Document ingestion pipeline for RAG. Uploads raw files to MinIO, chunks text,
generates vector embeddings, and stores in Postgres/pgvector for similarity search.

## Tech
FastAPI, SQLAlchemy + asyncpg, pgvector, MinIO (minio SDK), sentence-transformers

## Key Files
- `src/document_service/ingest.py` -- Upload -> chunk -> embed -> upsert pipeline
- `src/document_service/store.py` -- MinIO object storage client
- `src/document_service/embeddings.py` -- Embedding model client (all-MiniLM-L6-v2)
- `src/document_service/retriever.py` -- pgvector cosine similarity search
- `src/document_service/models.py` -- Document and DocumentChunk Pydantic/SQLAlchemy models

## Patterns
- Chunking: recursive character split, 512 tokens, 50 token overlap
- Embeddings: 384-dimensional vectors (all-MiniLM-L6-v2)
- Index: HNSW with m=16, ef_construction=200
- Raw files in MinIO, metadata + vectors in Postgres (transactional consistency)

## Run
`uv run uvicorn document_service.main:create_app --factory --reload --port 8001`
