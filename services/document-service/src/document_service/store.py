"""MinIO object-storage wrapper for raw document files."""

from __future__ import annotations

import io

from minio import Minio

from agent_platform_common.config import Settings
from agent_platform_common.logging import get_logger

logger = get_logger(__name__)


class ObjectStore:
    """Thin wrapper around the MinIO Python SDK."""

    def __init__(self, settings: Settings) -> None:
        self._client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    # ── Bucket management ────────────────────────────────────────────────

    def ensure_bucket(self, bucket_name: str) -> None:
        """Create the bucket if it does not already exist."""
        if not self._client.bucket_exists(bucket_name):
            self._client.make_bucket(bucket_name)
            logger.info("minio_bucket_created", bucket=bucket_name)

    # ── CRUD operations ──────────────────────────────────────────────────

    def upload_file(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload bytes to MinIO and return the object key."""
        self._client.put_object(
            bucket_name=bucket,
            object_name=key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info("minio_file_uploaded", bucket=bucket, key=key, size=len(data))
        return key

    def get_file(self, bucket: str, key: str) -> bytes:
        """Download an object from MinIO and return its bytes."""
        try:
            response = self._client.get_object(bucket, key)
            return response.read()
        finally:
            try:
                response.close()  # type: ignore[possibly-undefined]
                response.release_conn()  # type: ignore[possibly-undefined]
            except Exception:
                pass

    def delete_file(self, bucket: str, key: str) -> None:
        """Remove an object from MinIO."""
        self._client.remove_object(bucket, key)
        logger.info("minio_file_deleted", bucket=bucket, key=key)
