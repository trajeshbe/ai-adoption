"""Shared fixtures for document-service tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from document_service.embeddings import EmbeddingClient


@pytest.fixture
def sample_uuid() -> uuid.UUID:
    """A deterministic UUID for test assertions."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_datetime() -> datetime:
    """A deterministic datetime for test assertions."""
    return datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_embedding_client() -> EmbeddingClient:
    """An EmbeddingClient with a mocked HTTP client (always falls back)."""
    client = EmbeddingClient.__new__(EmbeddingClient)
    client._model_url = "http://localhost:11434/api/embeddings"
    client._model_name = "all-minilm:l6-v2"
    client._http = AsyncMock()
    return client


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """A mocked SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_object_store() -> MagicMock:
    """A mocked ObjectStore."""
    store = MagicMock()
    store.upload_file = MagicMock(return_value="test-key")
    store.get_file = MagicMock(return_value=b"file content")
    store.delete_file = MagicMock()
    store.ensure_bucket = MagicMock()
    return store
