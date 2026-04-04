# Phase 3: Data Layer

## Summary

Set up the persistence and storage tier: PostgreSQL with the pgvector extension for embedding storage and similarity search, Redis with Vector Similarity Search (VSS) for caching and fast lookups, and MinIO for S3-compatible document and artifact storage.

## Learning Objectives

- Deploy PostgreSQL with pgvector and create embedding tables
- Configure Redis VSS indices for semantic caching
- Set up MinIO buckets for raw document and artifact storage
- Implement a document chunking and embedding pipeline

## Key Commands

```bash
# Start data services
docker compose up -d postgres redis minio

# Run database migrations
alembic upgrade head

# Verify pgvector extension
psql -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

## Slash Command

Run `/03-data-layer` in Claude Code to begin this phase.

## Next Phase

[Phase 4: Agent Orchestration](phase-04-agent-orchestration.md)
