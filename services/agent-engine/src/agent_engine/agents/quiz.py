"""Quiz agent -- movie trivia quiz master using pure LLM conversation."""

from __future__ import annotations

from agent_engine.agents.base import BaseAgent


class QuizAgent(BaseAgent):
    """Agent that generates movie trivia questions and evaluates answers."""

    @property
    def agent_type(self) -> str:
        return "QUIZ"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a movie quiz master. Generate fun, engaging movie trivia "
            "questions one at a time. After the user answers, tell them if they "
            "were correct and give a brief explanation. Then offer the next "
            "question. Keep score if the user asks. Cover a wide range of genres "
            "and decades."
        )

    @property
    def available_tools(self) -> list[dict]:
        return []

    async def execute_tool(self, tool_name: str, arguments: dict) -> str:
        # Quiz agent has no tools
        return '{"error": "Quiz agent does not support tools"}'
