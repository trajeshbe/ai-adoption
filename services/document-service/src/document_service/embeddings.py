"""Embedding client -- calls an HTTP model endpoint or falls back to hash-based vectors."""

from __future__ import annotations

import hashlib
import struct

import httpx

from agent_platform_common.logging import get_logger

logger = get_logger(__name__)

EMBEDDING_DIM = 384


class EmbeddingClient:
    """Generate text embeddings via an HTTP embedding endpoint.

    Falls back to deterministic hash-based vectors when the endpoint is
    unreachable (development / testing only).
    """

    def __init__(
        self,
        model_url: str = "http://localhost:11434/api/embeddings",
        model_name: str = "all-minilm:l6-v2",
    ) -> None:
        self._model_url = model_url
        self._model_name = model_name
        self._http = httpx.AsyncClient(timeout=30.0)

    # ── Public API ───────────────────────────────────────────────────────

    async def embed(self, text: str) -> list[float]:
        """Return a 384-dimensional embedding for *text*."""
        try:
            response = await self._http.post(
                self._model_url,
                json={"model": self._model_name, "prompt": text},
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except (httpx.HTTPError, KeyError) as exc:
            logger.warning(
                "embedding_endpoint_unreachable_using_fallback",
                url=self._model_url,
                error=str(exc),
            )
            return self._fallback_embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts. Calls embed() for each (serial for now)."""
        return [await self.embed(t) for t in texts]

    # ── Fallback ─────────────────────────────────────────────────────────

    @staticmethod
    def _fallback_embed(text: str) -> list[float]:
        """Deterministic hash-based 384-dim vector (dev/testing only).

        Uses SHA-512 to generate reproducible floats in [-1, 1].
        """
        digest = hashlib.sha512(text.encode("utf-8")).digest()
        # SHA-512 = 64 bytes = 16 floats from struct; repeat to fill 384 dims
        base_floats: list[float] = []
        while len(base_floats) < EMBEDDING_DIM:
            # Re-hash to expand
            digest = hashlib.sha512(digest).digest()
            # Unpack 64 bytes as 8 doubles (8 bytes each)
            doubles = struct.unpack("8d", digest)
            for d in doubles:
                # Normalise into [-1, 1]
                base_floats.append((d % 2.0) - 1.0)
        return base_floats[:EMBEDDING_DIM]

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
