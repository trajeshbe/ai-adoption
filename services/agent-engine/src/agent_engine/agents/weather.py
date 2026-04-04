"""Weather agent -- uses the get_weather tool to answer weather questions."""

from __future__ import annotations

import json

from agent_engine.agents.base import BaseAgent
from agent_engine.tools.weather_api import get_weather


class WeatherAgent(BaseAgent):
    """Agent specialised in answering weather-related questions."""

    @property
    def agent_type(self) -> str:
        return "WEATHER"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a helpful weather assistant. When the user asks about "
            "weather in a city, use the get_weather tool to fetch real-time "
            "data and present it in a clear, friendly format. If the user "
            "asks about something other than weather, politely redirect them."
        )

    @property
    def available_tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather conditions for a city.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "The city name to get weather for.",
                            },
                        },
                        "required": ["city"],
                    },
                },
            }
        ]

    async def execute_tool(self, tool_name: str, arguments: dict) -> str:
        if tool_name == "get_weather":
            result = await get_weather(arguments.get("city", "Unknown"))
            return json.dumps(result)
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
