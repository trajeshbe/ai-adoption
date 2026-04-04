"""Tests for the weather API tool with mocked httpx."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_engine.tools.weather_api import get_weather


@pytest.mark.asyncio
async def test_get_weather_api_success() -> None:
    """When wttr.in returns valid data, parse it correctly."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "current_condition": [
            {
                "temp_C": "18",
                "weatherDesc": [{"value": "Sunny"}],
                "humidity": "55",
                "windspeedKmph": "15",
                "winddir16Point": "NE",
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("agent_engine.tools.weather_api.httpx.AsyncClient", return_value=mock_client):
        result = await get_weather("Paris")

    assert result["city"] == "Paris"
    assert result["temperature"] == "18°C"
    assert result["condition"] == "Sunny"
    assert result["humidity"] == "55%"
    assert result["wind"] == "15 km/h NE"


@pytest.mark.asyncio
async def test_get_weather_api_failure_falls_back_known_city() -> None:
    """When the API fails for a known city, return mock data."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Connection error"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("agent_engine.tools.weather_api.httpx.AsyncClient", return_value=mock_client):
        result = await get_weather("London")

    assert result["city"] == "London"
    assert result["temperature"] == "15°C"
    assert result["condition"] == "Partly cloudy"


@pytest.mark.asyncio
async def test_get_weather_api_failure_falls_back_unknown_city() -> None:
    """When the API fails for an unknown city, return default mock data."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("agent_engine.tools.weather_api.httpx.AsyncClient", return_value=mock_client):
        result = await get_weather("Atlantis")

    assert result["city"] == "Atlantis"
    assert result["temperature"] == "20°C"
    assert result["condition"] == "Clear"
