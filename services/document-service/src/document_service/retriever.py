"""Vector similarity search over document chunks using pgvector."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from document_service.embeddings import EmbeddingClient
from document_service.models import ChunkResponse, DocumentChunk


class Retriever:
    """Cosine-similarity retrieval over pgvector document embeddings."""

    def __init__(
        self,
        db_session: AsyncSession,
        embedding_client: EmbeddingClient,
    ) -> None:
        self._db = db_session
        self._embedder = embedding_client

    async def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[ChunkResponse]:
        """Embed *query* and return the *top_k* nearest document chunks.

        Uses the pgvector cosine distance operator (``<=>``) with an ORDER BY
        to leverage the HNSW index.
        """
        query_embedding = await self._embedder.embed(query)

        # Build raw SQL for pgvector cosine distance
        stmt = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.chunk_index,
                DocumentChunk.content,
                DocumentChunk.created_at,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("score"),
            )
            .order_by(text("score ASC"))
            .limit(top_k)
        )

        result = await self._db.execute(stmt)
        rows = result.all()

        return [
            ChunkResponse(
                id=row.id,
                document_id=row.document_id,
                chunk_index=row.chunk_index,
                content=row.content,
                score=float(row.score),
                created_at=row.created_at,
            )
            for row in rows
        ]
