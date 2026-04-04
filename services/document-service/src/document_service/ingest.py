"""Ingest pipeline: upload -> chunk -> embed -> store."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from agent_platform_common.logging import get_logger

from document_service.embeddings import EmbeddingClient
from document_service.models import (
    Document,
    DocumentChunk,
    DocumentResponse,
)
from document_service.store import ObjectStore

logger = get_logger(__name__)

DOCUMENTS_BUCKET = "documents"


class IngestPipeline:
    """Orchestrates the full document ingestion flow."""

    def __init__(
        self,
        db_session: AsyncSession,
        object_store: ObjectStore,
        embedding_client: EmbeddingClient,
    ) -> None:
        self._db = db_session
        self._store = object_store
        self._embedder = embedding_client

    async def ingest(
        self,
        filename: str,
        content_type: str,
        file_data: bytes,
    ) -> DocumentResponse:
        """Upload, chunk, embed, and persist a document.

        Returns a :class:`DocumentResponse` with the new document metadata.
        """
        # 1. Upload raw file to MinIO
        doc_id = uuid.uuid4()
        minio_key = f"{doc_id}/{filename}"
        self._store.upload_file(
            bucket=DOCUMENTS_BUCKET,
            key=minio_key,
            data=file_data,
            content_type=content_type,
        )
        logger.info("document_uploaded", doc_id=str(doc_id), filename=filename)

        # 2. Extract text
        text = self._extract_text(file_data, content_type)

        # 3. Chunk
        chunks = self._chunk_text(text)
        logger.info("document_chunked", doc_id=str(doc_id), chunk_count=len(chunks))

        # 4. Generate embeddings
        embeddings = await self._embedder.embed_batch(chunks)

        # 5. Persist in a single transaction
        document = Document(
            id=doc_id,
            filename=filename,
            content_type=content_type,
            minio_key=minio_key,
            chunk_count=len(chunks),
        )
        self._db.add(document)

        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = DocumentChunk(
                document_id=doc_id,
                chunk_index=idx,
                content=chunk_text,
                embedding=embedding,
            )
            self._db.add(chunk)

        await self._db.commit()
        await self._db.refresh(document)
        logger.info("document_persisted", doc_id=str(doc_id))

        return DocumentResponse.model_validate(document)

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _extract_text(data: bytes, content_type: str) -> str:
        """Extract plain text from raw file bytes.

        Currently handles text/plain, text/markdown, and treats
        application/pdf as raw text (placeholder for a real PDF parser).
        """
        # For text-based types, decode directly
        if content_type in (
            "text/plain",
            "text/markdown",
            "application/pdf",
            "application/octet-stream",
        ):
            return data.decode("utf-8", errors="replace")
        # Fallback: try UTF-8 decode
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def _chunk_text(
        text: str,
        chunk_size: int = 512,
        overlap: int = 50,
    ) -> list[str]:
        """Split *text* into overlapping chunks using character boundaries.

        Uses a simple recursive character splitter: tries to split on
        paragraph breaks, then newlines, then spaces, falling back to
        hard character slicing.
        """
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        separators = ["\n\n", "\n", " ", ""]
        return IngestPipeline._recursive_split(text, separators, chunk_size, overlap)

    @staticmethod
    def _recursive_split(
        text: str,
        separators: list[str],
        chunk_size: int,
        overlap: int,
    ) -> list[str]:
        """Recursively split text on the first working separator."""
        if not text.strip():
            return []

        sep = separators[0] if separators else ""
        remaining_seps = separators[1:] if len(separators) > 1 else []

        if sep == "":
            # Hard character split
            chunks: list[str] = []
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                start = end - overlap if end < len(text) else end
            return chunks

        parts = text.split(sep)
        current = ""
        chunks = []

        for part in parts:
            candidate = f"{current}{sep}{part}" if current else part
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current.strip():
                    if len(current) <= chunk_size:
                        chunks.append(current.strip())
                    else:
                        chunks.extend(
                            IngestPipeline._recursive_split(
                                current, remaining_seps, chunk_size, overlap
                            )
                        )
                current = part

        if current.strip():
            if len(current) <= chunk_size:
                chunks.append(current.strip())
            else:
                chunks.extend(
                    IngestPipeline._recursive_split(
                        current, remaining_seps, chunk_size, overlap
                    )
                )

        # Apply overlap between chunks
        if overlap > 0 and len(chunks) > 1:
            overlapped: list[str] = [chunks[0]]
            for i in range(1, len(chunks)):
                prev_tail = chunks[i - 1][-overlap:]
                merged = (prev_tail + " " + chunks[i]).strip()
                overlapped.append(merged)
            return overlapped

        return chunks
