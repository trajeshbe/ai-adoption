"""Unit tests for cache-service embedding client."""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from cache_service.embeddings import EMBEDDING_DIM, EmbeddingClient


class TestFallbackEmbed:
    """Tests for the deterministic hash-based fallback embedding."""

    def test_fallback_returns_correct_dimension(self) -> None:
        """Fallback embedding returns exactly 384 dimensions."""
        result = EmbeddingClient._fallback_embed("hello world")
        assert len(result) == EMBEDDING_DIM

    def test_fallback_returns_floats(self) -> None:
        """All elements in the fallback embedding are floats."""
        result = EmbeddingClient._fallback_embed("test input")
        assert all(isinstance(v, float) for v in result)

    def test_fallback_deterministic(self) -> None:
        """Same input always produces the exact same embedding."""
        text = "deterministic test"
        result1 = EmbeddingClient._fallback_embed(text)
        result2 = EmbeddingClient._fallback_embed(text)
        assert result1 == result2

    def test_fallback_different_inputs_differ(self) -> None:
        """Different inputs produce different embeddings."""
        result1 = EmbeddingClient._fallback_embed("input A")
        result2 = EmbeddingClient._fallback_embed("input B")
        assert result1 != result2

    def test_fallback_is_unit_vector(self) -> None:
        """Fallback embedding is normalized to unit length."""
        result = EmbeddingClient._fallback_embed("unit vector test")
        norm = math.sqrt(sum(v * v for v in result))
        assert abs(norm - 1.0) < 1e-6

    def test_fallback_values_in_range(self) -> None:
        """Fallback values are in [-1, 1] range (unit vector components)."""
        result = EmbeddingClient._fallback_embed("range test")
        for v in result:
            assert -1.0 <= v <= 1.0

    def test_fallback_empty_string(self) -> None:
        """Fallback works with empty string input."""
        result = EmbeddingClient._fallback_embed("")
        assert len(result) == EMBEDDING_DIM

    def test_fallback_unicode_input(self) -> None:
        """Fallback handles unicode input."""
        result = EmbeddingClient._fallback_embed("Unicode text here.")
        assert len(result) == EMBEDDING_DIM

    def test_fallback_no_nan_values(self) -> None:
        """Fallback never produces NaN values."""
        result = EmbeddingClient._fallback_embed("nan check")
        assert all(not math.isnan(v) for v in result)


class TestEmbedMethod:
    """Tests for the async embed() method."""

    @pytest.mark.asyncio
    async def test_embed_calls_http_endpoint(self) -> None:
        """embed() calls the HTTP endpoint and returns the embedding."""
        client = EmbeddingClient(model_url="http://test:11434/api/embeddings")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1] * EMBEDDING_DIM}

        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.embed("test text")

        assert len(result) == EMBEDDING_DIM
        assert result == [0.1] * EMBEDDING_DIM
        client._client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_embed_truncates_long_embeddings(self) -> None:
        """embed() truncates embeddings longer than EMBEDDING_DIM."""
        client = EmbeddingClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"embedding": [0.5] * 512}

        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.embed("test")
        assert len(result) == EMBEDDING_DIM

    @pytest.mark.asyncio
    async def test_embed_pads_short_embeddings(self) -> None:
        """embed() pads embeddings shorter than EMBEDDING_DIM with zeros."""
        client = EmbeddingClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"embedding": [0.5] * 100}

        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.embed("test")
        assert len(result) == EMBEDDING_DIM
        # Last values should be zero (padding)
        assert result[-1] == 0.0

    @pytest.mark.asyncio
    async def test_embed_falls_back_on_connection_error(self) -> None:
        """embed() uses fallback when HTTP endpoint is unreachable."""
        client = EmbeddingClient()

        client._client = AsyncMock()
        client._client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        result = await client.embed("test text")
        assert len(result) == EMBEDDING_DIM

    @pytest.mark.asyncio
    async def test_embed_falls_back_on_http_status_error(self) -> None:
        """embed() uses fallback on HTTP 500 error."""
        client = EmbeddingClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "500", request=MagicMock(), response=MagicMock()
            )
        )

        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.embed("test text")
        assert len(result) == EMBEDDING_DIM


class TestClose:
    """Tests for the close() method."""

    @pytest.mark.asyncio
    async def test_close_calls_aclose(self) -> None:
        """close() calls aclose on the underlying HTTP client."""
        client = EmbeddingClient()
        client._client = AsyncMock()
        client._client.aclose = AsyncMock()

        await client.close()
        client._client.aclose.assert_awaited_once()
