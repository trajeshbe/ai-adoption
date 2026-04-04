"""Shared test fixtures for gateway tests."""

import pytest
from fastapi.testclient import TestClient

from agent_platform_common.config import Settings
from gateway.main import create_app


@pytest.fixture
def settings() -> Settings:
    """Test settings with debug mode enabled."""
    return Settings(
        service_name="gateway-test",
        environment="test",
        debug=True,
        log_level="DEBUG",
    )


@pytest.fixture
def app(settings: Settings):
    """Create a test FastAPI application."""
    return create_app(settings=settings)


@pytest.fixture
def client(app) -> TestClient:
    """HTTP test client for REST and GraphQL endpoints."""
    return TestClient(app)
