"""FastAPI application factory for the Document Service."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from agent_platform_common.config import Settings
from agent_platform_common.logging import setup_logging
from agent_platform_common.middleware import RequestIdMiddleware, RequestLoggingMiddleware
from agent_platform_common.telemetry import setup_telemetry

from document_service.embeddings import EmbeddingClient
from document_service.ingest import DOCUMENTS_BUCKET, IngestPipeline
from document_service.models import ChunkResponse, Document, DocumentResponse
from document_service.retriever import Retriever
from document_service.store import ObjectStore

# ── Settings ─────────────────────────────────────────────────────────────────

settings = Settings(service_name="document-service")


# ── Request / response schemas ───────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=100)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown hook: build shared resources and attach to app.state."""
    # Database
    db_url = settings.database_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    engine = create_async_engine(db_url, echo=settings.debug, pool_size=10)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Object storage
    object_store = ObjectStore(settings)
    object_store.ensure_bucket(DOCUMENTS_BUCKET)

    # Embedding client
    embedding_client = EmbeddingClient()

    # Attach to app.state for dependency injection
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.object_store = object_store
    app.state.embedding_client = embedding_client

    yield

    # Shutdown
    await embedding_client.close()
    await engine.dispose()


# ── App factory ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    setup_logging(
        service_name=settings.service_name,
        log_level=settings.log_level,
        debug=settings.debug,
    )
    setup_telemetry(
        service_name=settings.service_name,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
        enabled=settings.otel_enabled,
    )

    app = FastAPI(
        title="Document Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware (order matters -- outermost first)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # ── Dependency helpers ───────────────────────────────────────────────

    async def get_db(
    ) -> AsyncGenerator[AsyncSession, None]:
        async with app.state.session_factory() as session:
            yield session

    # ── Routes ───────────────────────────────────────────────────────────

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "healthy"}

    @app.get("/readyz")
    async def readyz(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
        try:
            await db.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception:
            raise HTTPException(status_code=503, detail="Database not ready")

    @app.post("/documents/upload", response_model=DocumentResponse)
    async def upload_document(
        file: UploadFile,
        db: AsyncSession = Depends(get_db),
    ) -> DocumentResponse:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        file_data = await file.read()
        content_type = file.content_type or "application/octet-stream"

        pipeline = IngestPipeline(
            db_session=db,
            object_store=app.state.object_store,
            embedding_client=app.state.embedding_client,
        )
        return await pipeline.ingest(
            filename=file.filename,
            content_type=content_type,
            file_data=file_data,
        )

    @app.get("/documents", response_model=list[DocumentResponse])
    async def list_documents(
        db: AsyncSession = Depends(get_db),
    ) -> list[DocumentResponse]:
        from sqlalchemy import select as sa_select

        result = await db.execute(
            sa_select(Document).order_by(Document.created_at.desc())
        )
        documents = result.scalars().all()
        return [DocumentResponse.model_validate(d) for d in documents]

    @app.get("/documents/{document_id}", response_model=DocumentResponse)
    async def get_document(
        document_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
    ) -> DocumentResponse:
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentResponse.model_validate(document)

    @app.delete("/documents/{document_id}")
    async def delete_document(
        document_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, bool]:
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete from MinIO
        try:
            app.state.object_store.delete_file(DOCUMENTS_BUCKET, document.minio_key)
        except Exception:
            pass  # Best-effort MinIO cleanup

        await db.delete(document)
        await db.commit()
        return {"deleted": True}

    @app.post("/documents/search", response_model=list[ChunkResponse])
    async def search_documents(
        body: SearchRequest,
        db: AsyncSession = Depends(get_db),
    ) -> list[ChunkResponse]:
        retriever = Retriever(
            db_session=db,
            embedding_client=app.state.embedding_client,
        )
        return await retriever.search(query=body.query, top_k=body.top_k)

    return app
