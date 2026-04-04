#!/bin/bash
# ============================================================================
# Seed Data: Load sample data into Postgres and MinIO
# Usage: ./scripts/seed-data.sh
# ============================================================================
set -euo pipefail

echo "==> Seeding database with sample agents..."
PGPASSWORD=agent_platform psql -h localhost -U agent_platform -d agent_platform <<'SQL'
INSERT INTO agents (id, name, agent_type, instructions, created_at) VALUES
    ('weather-1', 'Weather Bot', 'weather', 'You are a helpful weather assistant. When asked about weather, use the weather tool to fetch real-time data.', now()),
    ('quiz-1', 'Movie Quiz Bot', 'quiz', 'You are a movie quiz master specializing in South Indian cinema. Ask 3 questions and provide recommendations based on answers.', now()),
    ('rag-1', 'Document Assistant', 'rag', 'You are a document Q&A assistant. Search uploaded documents to answer questions. Always cite your sources.', now())
ON CONFLICT (id) DO NOTHING;
SQL

echo "==> Creating MinIO buckets..."
mc alias set local http://localhost:9000 minioadmin minioadmin 2>/dev/null || true
mc mb local/documents --ignore-existing 2>/dev/null || true
mc mb local/models --ignore-existing 2>/dev/null || true
mc mb local/artifacts --ignore-existing 2>/dev/null || true

echo "==> Seed data loaded successfully."
