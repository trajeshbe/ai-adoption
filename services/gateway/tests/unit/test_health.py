"""Tests for health endpoints."""


def test_healthz(client):
    """Liveness probe returns 200."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz(client):
    """Readiness probe returns 200."""
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
