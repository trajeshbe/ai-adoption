"""Embedding client for generating query vectors.

Uses an Ollama-compatible endpoint for production embeddings, with a
deterministic hash-based fallback for dev/testing environments.
"""

import hashlib
import struct

import httpx
import structlog

logger = structlog.get_logger()

EMBEDDING_DIM = 384


class EmbeddingClient:
    """Generates text embeddings via an HTTP embedding service."""

    def __init__(
        self,
        model_url: str = "http://localhost:11434/api/embeddings",
        model_name: str = "all-minilm:l6-v2",
    ) -> None:
        self.model_url = model_url
        self.model_name = model_name
        self._client = httpx.AsyncClient(timeout=30.0)

    async def embed(self, text: str) -> list[float]:
        """Generate a 384-dimensional embedding for the given text.

        Attempts to call the remote embedding service. Falls back to a
        deterministic hash-based vector if the service is unavailable.
        """
        try:
            response = await self._client.post(
                self.model_url,
                json={"model": self.model_name, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            embedding = data["embedding"]
            # Truncate or pad to EMBEDDING_DIM
            if len(embedding) >= EMBEDDING_DIM:
                return embedding[:EMBEDDING_DIM]
            return embedding + [0.0] * (EMBEDDING_DIM - len(embedding))
        except Exception as exc:
            await logger.awarning(
                "embedding_service_unavailable_using_fallback",
                error=str(exc),
            )
            return self._fallback_embed(text)

    @staticmethod
    def _fallback_embed(text: str) -> list[float]:
        """Deterministic hash-based embedding for dev/testing.

        Produces a consistent 384-dim unit vector from the input text,
        ensuring identical inputs always yield identical vectors.
        """
        # Generate enough hash bytes for 384 floats
        vectors: list[float] = []
        for i in range(EMBEDDING_DIM):
            h = hashlib.sha256(f"{text}:{i}".encode()).digest()
            # Unpack first 4 bytes as unsigned int, normalize to [-1, 1]
            val = struct.unpack("!I", h[:4])[0]
            vectors.append((val / (2**32 - 1)) * 2.0 - 1.0)

        # Normalize to unit vector
        norm = sum(v * v for v in vectors) ** 0.5
        if norm > 0:
            vectors = [v / norm for v in vectors]
        return vectors

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
