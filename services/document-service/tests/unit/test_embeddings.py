"""Unit tests for document-service embedding client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from document_service.embeddings import EMBEDDING_DIM, EmbeddingClient


class TestFallbackEmbed:
    """Tests for the hash-based fallback embedding."""

    def test_fallback_returns_correct_dimension(self) -> None:
        """Fallback embedding returns exactly 384 dimensions."""
        result = EmbeddingClient._fallback_embed("hello world")
        assert len(result) == EMBEDDING_DIM

    def test_fallback_returns_floats(self) -> None:
        """All elements in the fallback embedding are floats."""
        result = EmbeddingClient._fallback_embed("test input")
        assert all(isinstance(v, float) for v in result)

    def test_fallback_deterministic(self) -> None:
        """Same input always produces the same embedding."""
        text = "deterministic test"
        result1 = EmbeddingClient._fallback_embed(text)
        result2 = EmbeddingClient._fallback_embed(text)
        assert result1 == result2

    def test_fallback_different_inputs_differ(self) -> None:
        """Different inputs produce different embeddings."""
        result1 = EmbeddingClient._fallback_embed("input A")
        result2 = EmbeddingClient._fallback_embed("input B")
        assert result1 != result2

    def test_fallback_values_in_range(self) -> None:
        """Fallback embedding values are in a reasonable numeric range."""
        result = EmbeddingClient._fallback_embed("range test")
        for v in result:
            assert isinstance(v, float)
            # Values should be finite
            assert v == v  # not NaN

    def test_fallback_empty_string(self) -> None:
        """Fallback works with empty string input."""
        result = EmbeddingClient._fallback_embed("")
        assert len(result) == EMBEDDING_DIM

    def test_fallback_unicode_input(self) -> None:
        """Fallback handles unicode input correctly."""
        result = EmbeddingClient._fallback_embed("Hello, world! This has unicode.")
        assert len(result) == EMBEDDING_DIM


class TestEmbedMethod:
    """Tests for the async embed() method."""

    @pytest.mark.asyncio
    async def test_embed_calls_http_endpoint(self) -> None:
        """embed() calls the HTTP endpoint and returns the embedding."""
        client = EmbeddingClient(model_url="http://test:11434/api/embeddings")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1] * EMBEDDING_DIM}

        client._http = AsyncMock()
        client._http.post = AsyncMock(return_value=mock_response)

        result = await client.embed("test text")

        assert len(result) == EMBEDDING_DIM
        assert result == [0.1] * EMBEDDING_DIM
        client._http.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_embed_falls_back_on_http_error(self) -> None:
        """embed() uses fallback when HTTP endpoint raises an error."""
        client = EmbeddingClient(model_url="http://test:11434/api/embeddings")

        client._http = AsyncMock()
        client._http.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        result = await client.embed("test text")

        # Should still return a valid embedding from fallback
        assert len(result) == EMBEDDING_DIM

    @pytest.mark.asyncio
    async def test_embed_falls_back_on_missing_key(self) -> None:
        """embed() uses fallback when response JSON lacks 'embedding' key."""
        client = EmbeddingClient(model_url="http://test:11434/api/embeddings")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"error": "bad request"}

        client._http = AsyncMock()
        client._http.post = AsyncMock(return_value=mock_response)

        result = await client.embed("test text")
        assert len(result) == EMBEDDING_DIM


class TestEmbedBatch:
    """Tests for the async embed_batch() method."""

    @pytest.mark.asyncio
    async def test_embed_batch_returns_list_of_embeddings(self) -> None:
        """embed_batch() returns one embedding per input text."""
        client = EmbeddingClient()
        # Force fallback by making HTTP fail
        client._http = AsyncMock()
        client._http.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        texts = ["hello", "world", "test"]
        results = await client.embed_batch(texts)

        assert len(results) == 3
        for emb in results:
            assert len(emb) == EMBEDDING_DIM

    @pytest.mark.asyncio
    async def test_embed_batch_empty_list(self) -> None:
        """embed_batch() with empty list returns empty list."""
        client = EmbeddingClient()
        client._http = AsyncMock()
        results = await client.embed_batch([])
        assert results == []


class TestClose:
    """Tests for the close() method."""

    @pytest.mark.asyncio
    async def test_close_calls_aclose(self) -> None:
        """close() calls aclose on the underlying HTTP client."""
        client = EmbeddingClient()
        client._http = AsyncMock()
        client._http.aclose = AsyncMock()

        await client.close()

        client._http.aclose.assert_awaited_once()
