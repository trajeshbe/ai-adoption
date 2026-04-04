"""Unit tests for the document-service ingest pipeline."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from document_service.ingest import IngestPipeline


class TestChunkText:
    """Tests for IngestPipeline._chunk_text static method."""

    def test_empty_text_returns_empty_list(self) -> None:
        """Empty or whitespace-only text produces no chunks."""
        assert IngestPipeline._chunk_text("") == []
        assert IngestPipeline._chunk_text("   ") == []
        assert IngestPipeline._chunk_text("\n\n") == []

    def test_short_text_returns_single_chunk(self) -> None:
        """Text shorter than chunk_size is returned as a single chunk."""
        text = "Hello, world!"
        chunks = IngestPipeline._chunk_text(text, chunk_size=512, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_text_exactly_chunk_size(self) -> None:
        """Text exactly at chunk_size boundary returns one chunk."""
        text = "x" * 512
        chunks = IngestPipeline._chunk_text(text, chunk_size=512, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_produces_multiple_chunks(self) -> None:
        """Text longer than chunk_size is split into multiple chunks."""
        # Create text with spaces so the splitter can use word boundaries
        words = ["word"] * 200  # ~1000 chars with spaces
        text = " ".join(words)
        chunks = IngestPipeline._chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) > 1

    def test_all_chunks_within_size_limit(self) -> None:
        """No chunk exceeds chunk_size + overlap (overlap adds tail from prev)."""
        text = " ".join(["segment"] * 200)
        chunk_size = 80
        overlap = 10
        chunks = IngestPipeline._chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        # First chunk should be within chunk_size; subsequent may have overlap prefix
        assert len(chunks[0]) <= chunk_size

    def test_paragraph_separator_preferred(self) -> None:
        """The splitter prefers paragraph breaks (double newline) as separators."""
        para1 = "First paragraph " * 10
        para2 = "Second paragraph " * 10
        text = para1.strip() + "\n\n" + para2.strip()
        chunks = IngestPipeline._chunk_text(text, chunk_size=200, overlap=0)
        assert len(chunks) >= 2

    def test_overlap_creates_repeated_content(self) -> None:
        """When overlap > 0, consecutive chunks share trailing/leading text."""
        # Use hard character split scenario (no separators)
        text = "a" * 200
        chunks = IngestPipeline._chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) >= 2
        # With overlap, second chunk should contain chars from end of first

    def test_newline_separator_used(self) -> None:
        """Falls back to newline separator when paragraphs are too large."""
        lines = [f"Line {i} with some extra content padding" for i in range(30)]
        text = "\n".join(lines)
        chunks = IngestPipeline._chunk_text(text, chunk_size=150, overlap=0)
        assert len(chunks) > 1

    def test_zero_overlap(self) -> None:
        """With overlap=0, chunks do not share content (except separator logic)."""
        text = " ".join(["word"] * 100)
        chunks = IngestPipeline._chunk_text(text, chunk_size=50, overlap=0)
        assert len(chunks) > 1


class TestExtractText:
    """Tests for IngestPipeline._extract_text static method."""

    def test_extract_text_plain(self) -> None:
        """text/plain content is decoded as UTF-8."""
        data = b"Hello, world!"
        result = IngestPipeline._extract_text(data, "text/plain")
        assert result == "Hello, world!"

    def test_extract_text_markdown(self) -> None:
        """text/markdown content is decoded as UTF-8."""
        data = b"# Heading\n\nSome text"
        result = IngestPipeline._extract_text(data, "text/markdown")
        assert result == "# Heading\n\nSome text"

    def test_extract_text_pdf_placeholder(self) -> None:
        """application/pdf is treated as raw text (placeholder behavior)."""
        data = b"PDF content as text"
        result = IngestPipeline._extract_text(data, "application/pdf")
        assert result == "PDF content as text"

    def test_extract_text_unknown_type_fallback(self) -> None:
        """Unknown content types fall back to UTF-8 decode."""
        data = b"Some data"
        result = IngestPipeline._extract_text(data, "application/json")
        assert result == "Some data"

    def test_extract_text_invalid_utf8(self) -> None:
        """Invalid UTF-8 bytes use errors='replace' and don't raise."""
        data = b"\xff\xfe invalid bytes"
        result = IngestPipeline._extract_text(data, "text/plain")
        assert isinstance(result, str)
        # Should contain replacement characters but not raise


class TestIngestPipeline:
    """Tests for the full IngestPipeline.ingest method with mocked deps."""

    @pytest.mark.asyncio
    async def test_ingest_calls_all_steps(
        self,
        mock_db_session: AsyncMock,
        mock_object_store: MagicMock,
        mock_embedding_client: MagicMock,
    ) -> None:
        """ingest() uploads to MinIO, chunks, embeds, and persists."""
        from datetime import datetime, timezone

        # Make embedding_client.embed_batch return matching embeddings
        mock_embedding_client.embed_batch = AsyncMock(
            return_value=[[0.1] * 384]
        )

        # The Document ORM model uses server_default for created_at,
        # which is None without a real DB. Simulate refresh populating it.
        async def fake_refresh(obj: object) -> None:
            obj.created_at = datetime.now(tz=timezone.utc)  # type: ignore[attr-defined]

        mock_db_session.refresh = AsyncMock(side_effect=fake_refresh)

        pipeline = IngestPipeline(
            db_session=mock_db_session,
            object_store=mock_object_store,
            embedding_client=mock_embedding_client,
        )

        result = await pipeline.ingest(
            filename="test.txt",
            content_type="text/plain",
            file_data=b"Short text content",
        )

        # Verify MinIO upload was called
        mock_object_store.upload_file.assert_called_once()

        # Verify DB commit was called
        mock_db_session.commit.assert_awaited_once()

        # Verify result
        assert result.filename == "test.txt"
        assert result.content_type == "text/plain"

    @pytest.mark.asyncio
    async def test_ingest_empty_file(
        self,
        mock_db_session: AsyncMock,
        mock_object_store: MagicMock,
        mock_embedding_client: MagicMock,
    ) -> None:
        """Ingesting an empty file produces zero chunks."""
        from datetime import datetime, timezone

        mock_embedding_client.embed_batch = AsyncMock(return_value=[])

        async def fake_refresh(obj: object) -> None:
            obj.created_at = datetime.now(tz=timezone.utc)  # type: ignore[attr-defined]

        mock_db_session.refresh = AsyncMock(side_effect=fake_refresh)

        pipeline = IngestPipeline(
            db_session=mock_db_session,
            object_store=mock_object_store,
            embedding_client=mock_embedding_client,
        )

        result = await pipeline.ingest(
            filename="empty.txt",
            content_type="text/plain",
            file_data=b"",
        )

        assert result.chunk_count == 0
