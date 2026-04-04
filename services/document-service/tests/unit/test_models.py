"""Unit tests for document-service Pydantic response models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from document_service.models import ChunkResponse, DocumentResponse


class TestDocumentResponse:
    """Tests for the DocumentResponse Pydantic model."""

    def test_create_document_response(self) -> None:
        """DocumentResponse can be created with all required fields."""
        doc_id = uuid.uuid4()
        now = datetime.now(tz=timezone.utc)

        resp = DocumentResponse(
            id=doc_id,
            filename="test.txt",
            content_type="text/plain",
            chunk_count=5,
            created_at=now,
        )

        assert resp.id == doc_id
        assert resp.filename == "test.txt"
        assert resp.content_type == "text/plain"
        assert resp.chunk_count == 5
        assert resp.created_at == now

    def test_document_response_serialization(self) -> None:
        """DocumentResponse serializes to dict correctly."""
        doc_id = uuid.UUID("abcdef12-3456-7890-abcd-ef1234567890")
        now = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        resp = DocumentResponse(
            id=doc_id,
            filename="report.pdf",
            content_type="application/pdf",
            chunk_count=10,
            created_at=now,
        )
        data = resp.model_dump()

        assert data["id"] == doc_id
        assert data["filename"] == "report.pdf"
        assert data["content_type"] == "application/pdf"
        assert data["chunk_count"] == 10

    def test_document_response_json_roundtrip(self) -> None:
        """DocumentResponse can be serialized to JSON and back."""
        doc_id = uuid.uuid4()
        now = datetime.now(tz=timezone.utc)

        original = DocumentResponse(
            id=doc_id,
            filename="data.csv",
            content_type="text/csv",
            chunk_count=3,
            created_at=now,
        )
        json_str = original.model_dump_json()
        restored = DocumentResponse.model_validate_json(json_str)

        assert restored.id == original.id
        assert restored.filename == original.filename
        assert restored.chunk_count == original.chunk_count

    def test_document_response_from_attributes(self) -> None:
        """DocumentResponse can be created from an ORM-like object via from_attributes."""

        class FakeORM:
            id = uuid.uuid4()
            filename = "orm_test.txt"
            content_type = "text/plain"
            chunk_count = 2
            created_at = datetime.now(tz=timezone.utc)

        resp = DocumentResponse.model_validate(FakeORM(), from_attributes=True)
        assert resp.filename == "orm_test.txt"
        assert resp.chunk_count == 2


class TestChunkResponse:
    """Tests for the ChunkResponse Pydantic model."""

    def test_create_chunk_response_without_score(self) -> None:
        """ChunkResponse can be created without a score (defaults to None)."""
        chunk_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        now = datetime.now(tz=timezone.utc)

        resp = ChunkResponse(
            id=chunk_id,
            document_id=doc_id,
            chunk_index=0,
            content="Hello world",
            created_at=now,
        )

        assert resp.id == chunk_id
        assert resp.document_id == doc_id
        assert resp.chunk_index == 0
        assert resp.content == "Hello world"
        assert resp.score is None

    def test_create_chunk_response_with_score(self) -> None:
        """ChunkResponse can be created with a similarity score."""
        resp = ChunkResponse(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            chunk_index=2,
            content="Some chunk",
            score=0.95,
            created_at=datetime.now(tz=timezone.utc),
        )

        assert resp.score == 0.95

    def test_chunk_response_serialization(self) -> None:
        """ChunkResponse serializes score=None correctly."""
        resp = ChunkResponse(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            chunk_index=0,
            content="test",
            created_at=datetime.now(tz=timezone.utc),
        )
        data = resp.model_dump()
        assert data["score"] is None

    def test_chunk_response_json_roundtrip(self) -> None:
        """ChunkResponse survives JSON serialization roundtrip."""
        original = ChunkResponse(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            chunk_index=1,
            content="roundtrip test",
            score=0.87,
            created_at=datetime.now(tz=timezone.utc),
        )
        json_str = original.model_dump_json()
        restored = ChunkResponse.model_validate_json(json_str)

        assert restored.content == original.content
        assert restored.score == original.score
        assert restored.chunk_index == original.chunk_index
