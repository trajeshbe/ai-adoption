"""Weather tool using wttr.in API with fallback mock data."""

from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger()

_MOCK_WEATHER: dict[str, dict] = {
    "london": {"city": "London", "temperature": "15°C", "condition": "Partly cloudy", "humidity": "72%", "wind": "12 km/h SW"},
    "new york": {"city": "New York", "temperature": "22°C", "condition": "Clear", "humidity": "58%", "wind": "8 km/h NW"},
    "tokyo": {"city": "Tokyo", "temperature": "26°C", "condition": "Sunny", "humidity": "65%", "wind": "10 km/h E"},
}

_DEFAULT_MOCK = {"temperature": "20°C", "condition": "Clear", "humidity": "60%", "wind": "10 km/h N"}


async def get_weather(city: str) -> dict:
    """Fetch current weather for *city* via wttr.in.

    Falls back to mock data if the API is unreachable.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"https://wttr.in/{city}",
                params={"format": "j1"},
                headers={"User-Agent": "agent-platform/0.1"},
            )
            resp.raise_for_status()
            data = resp.json()

            current = data["current_condition"][0]
            return {
                "city": city,
                "temperature": f"{current['temp_C']}°C",
                "condition": current["weatherDesc"][0]["value"],
                "humidity": f"{current['humidity']}%",
                "wind": f"{current['windspeedKmph']} km/h {current['winddir16Point']}",
            }
    except Exception as exc:
        await logger.awarning("weather_api_fallback", city=city, error=str(exc))
        mock = _MOCK_WEATHER.get(city.lower(), {**_DEFAULT_MOCK, "city": city})
        if "city" not in mock:
            mock["city"] = city
        return mock
