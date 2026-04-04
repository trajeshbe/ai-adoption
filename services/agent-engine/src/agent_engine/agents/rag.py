"""RAG agent -- answers questions from documents via the document-service."""

from __future__ import annotations

import json

import structlog

from agent_engine.agents.base import BaseAgent

logger = structlog.get_logger()


class RAGAgent(BaseAgent):
    """Agent that retrieves relevant document chunks before answering."""

    @property
    def agent_type(self) -> str:
        return "RAG"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a knowledgeable assistant that answers questions based on "
            "documents. When the user asks a question, use the search_documents "
            "tool to find relevant passages, then synthesise a concise answer "
            "citing the source material. If no relevant documents are found, "
            "say so honestly."
        )

    @property
    def available_tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_documents",
                    "description": "Search uploaded documents for passages relevant to a query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query.",
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return (default 5).",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

    async def execute_tool(self, tool_name: str, arguments: dict) -> str:
        if tool_name == "search_documents":
            return await self._search_documents(
                query=arguments.get("query", ""),
                top_k=arguments.get("top_k", 5),
            )
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    async def _search_documents(self, query: str, top_k: int = 5) -> str:
        """Call document-service /documents/search endpoint."""
        if self.http_client is None:
            return json.dumps({"error": "Document service client not configured"})

        try:
            resp = await self.http_client.post(
                "/documents/search",
                json={"query": query, "top_k": top_k},
            )
            resp.raise_for_status()
            return json.dumps(resp.json())
        except Exception as exc:
            await logger.awarning("document_search_failed", error=str(exc))
            return json.dumps({"error": f"Document search failed: {exc}", "results": []})
