"""Fixtures for end-to-end tests."""

from __future__ import annotations

import os

import httpx
import pytest


@pytest.fixture(scope="session")
def gateway_url() -> str:
    """Return the gateway URL from environment or default to localhost."""
    return os.environ.get("GATEWAY_URL", "http://localhost:8000")


@pytest.fixture()
async def http_client(gateway_url: str) -> httpx.AsyncClient:
    """Yield an async HTTP client configured for the gateway."""
    async with httpx.AsyncClient(
        base_url=gateway_url,
        timeout=httpx.Timeout(30.0, connect=10.0),
        headers={"Content-Type": "application/json"},
    ) as client:
        yield client
