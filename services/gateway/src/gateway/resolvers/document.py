"""Document resolvers for upload and retrieval.

Stub implementation. Will be wired to document-service in Phase 3.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from gateway.schema import Document

# ── Mock document store ────────────────────────────────────────────────
_mock_documents: list[Document] = [
    Document(
        id=uuid4(),
        filename="sample-report.pdf",
        content_type="application/pdf",
        chunk_count=24,
        created_at=datetime.now(tz=timezone.utc),
    ),
    Document(
        id=uuid4(),
        filename="architecture-guide.md",
        content_type="text/markdown",
        chunk_count=12,
        created_at=datetime.now(tz=timezone.utc),
    ),
]


def resolve_documents() -> list[Document]:
    """List all uploaded documents."""
    return _mock_documents


def resolve_document(document_id: UUID) -> Document | None:
    """Get a single document by ID."""
    return next((d for d in _mock_documents if d.id == document_id), None)


def resolve_upload_document(filename: str, content_type: str) -> Document:
    """Upload a new document (stub -- real implementation in Phase 3)."""
    doc = Document(
        id=uuid4(),
        filename=filename,
        content_type=content_type,
        chunk_count=0,
        created_at=datetime.now(tz=timezone.utc),
    )
    _mock_documents.append(doc)
    return doc
