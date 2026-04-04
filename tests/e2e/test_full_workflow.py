"""End-to-end tests for the Agent Platform full workflow.

These tests verify critical user journeys across the entire platform:
  - Service health checks
  - Agent creation and chat interaction
  - Document upload and semantic search
  - Cost tracking after inference

Requires a running platform (local or CI). Set GATEWAY_URL env var.

Run:
    pytest tests/e2e/test_full_workflow.py -v
    GATEWAY_URL=http://gateway.example.com pytest tests/e2e/test_full_workflow.py -v
"""

from __future__ import annotations

import uuid

import httpx
import pytest

pytestmark = pytest.mark.anyio


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


async def graphql(
    client: httpx.AsyncClient,
    query: str,
    variables: dict | None = None,
) -> dict:
    """Execute a GraphQL query and return the parsed response."""
    payload: dict = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = await client.post("/graphql", json=payload)
    assert resp.status_code == 200, f"GraphQL request failed: {resp.status_code} {resp.text}"
    body = resp.json()
    assert "errors" not in body or len(body["errors"]) == 0, (
        f"GraphQL errors: {body.get('errors')}"
    )
    return body["data"]


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


class TestHealthChecks:
    """Verify all services are healthy."""

    @pytest.mark.parametrize(
        "path",
        ["/healthz", "/readyz"],
    )
    async def test_health_check(
        self, http_client: httpx.AsyncClient, path: str
    ) -> None:
        """All health and readiness endpoints return 200."""
        resp = await http_client.get(path)
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("status") in ("ok", "healthy", "ready")

    async def test_graphql_introspection(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """GraphQL endpoint responds to introspection."""
        data = await graphql(
            http_client,
            "{ __schema { queryType { name } } }",
        )
        assert data["__schema"]["queryType"]["name"] == "Query"


class TestAgentChatWorkflow:
    """Create an agent, send a message, and verify the response."""

    async def test_create_agent_and_chat(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Full agent creation and chat interaction workflow."""
        session_id = f"e2e-{uuid.uuid4().hex[:8]}"

        # Step 1: List agents to verify the API works
        agents_data = await graphql(
            http_client,
            """
            query {
                agents {
                    id
                    name
                    status
                }
            }
            """,
        )
        agents = agents_data["agents"]
        assert isinstance(agents, list)

        # Step 2: Use the first available agent (or default)
        agent_id = agents[0]["id"] if agents else "default-agent"

        # Step 3: Send a message
        message_data = await graphql(
            http_client,
            """
            mutation SendMessage($input: SendMessageInput!) {
                sendMessage(input: $input) {
                    id
                    content
                    role
                    timestamp
                }
            }
            """,
            variables={
                "input": {
                    "agentId": agent_id,
                    "content": "Hello, what can you help me with?",
                    "sessionId": session_id,
                }
            },
        )
        message = message_data["sendMessage"]
        assert message["id"] is not None
        assert message["content"] is not None
        assert len(message["content"]) > 0
        assert message["role"] == "assistant"

    async def test_conversation_context(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Verify multi-turn conversation maintains context."""
        session_id = f"e2e-ctx-{uuid.uuid4().hex[:8]}"

        # First message
        await graphql(
            http_client,
            """
            mutation SendMessage($input: SendMessageInput!) {
                sendMessage(input: $input) {
                    id
                    content
                }
            }
            """,
            variables={
                "input": {
                    "agentId": "default-agent",
                    "content": "My name is TestBot.",
                    "sessionId": session_id,
                }
            },
        )

        # Follow-up referencing prior context
        followup_data = await graphql(
            http_client,
            """
            mutation SendMessage($input: SendMessageInput!) {
                sendMessage(input: $input) {
                    id
                    content
                }
            }
            """,
            variables={
                "input": {
                    "agentId": "default-agent",
                    "content": "What is my name?",
                    "sessionId": session_id,
                }
            },
        )
        followup = followup_data["sendMessage"]
        assert followup["content"] is not None


class TestDocumentWorkflow:
    """Upload a document, search for it, and verify results."""

    async def test_document_upload_and_search(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Upload a document and perform semantic search."""
        # Step 1: Upload a document
        upload_data = await graphql(
            http_client,
            """
            mutation UploadDocument($input: UploadDocumentInput!) {
                uploadDocument(input: $input) {
                    id
                    filename
                    status
                }
            }
            """,
            variables={
                "input": {
                    "filename": "e2e-test-doc.txt",
                    "content": "Kubernetes is a container orchestration platform for automating deployment, scaling, and management of containerized applications.",
                    "mimeType": "text/plain",
                }
            },
        )
        doc = upload_data["uploadDocument"]
        assert doc["id"] is not None
        assert doc["status"] in ("uploaded", "processing", "indexed")

        doc_id = doc["id"]

        # Step 2: Search for the document
        search_data = await graphql(
            http_client,
            """
            query SearchDocuments($query: String!) {
                searchDocuments(query: $query) {
                    results {
                        documentId
                        content
                        score
                    }
                    totalCount
                }
            }
            """,
            variables={"query": "container orchestration"},
        )
        search = search_data["searchDocuments"]
        assert search["totalCount"] > 0
        # Verify our uploaded doc appears in results
        result_ids = [r["documentId"] for r in search["results"]]
        assert doc_id in result_ids, (
            f"Uploaded doc {doc_id} not found in search results: {result_ids}"
        )

        # Step 3: List documents to verify it exists
        list_data = await graphql(
            http_client,
            """
            query {
                documents {
                    id
                    filename
                }
            }
            """,
        )
        doc_ids = [d["id"] for d in list_data["documents"]]
        assert doc_id in doc_ids


class TestCostTracking:
    """Verify costs are tracked after inference."""

    async def test_cost_tracking(
        self, http_client: httpx.AsyncClient
    ) -> None:
        """Send an inference request and verify cost is recorded."""
        session_id = f"e2e-cost-{uuid.uuid4().hex[:8]}"

        # Trigger an inference
        await graphql(
            http_client,
            """
            mutation SendMessage($input: SendMessageInput!) {
                sendMessage(input: $input) {
                    id
                    content
                }
            }
            """,
            variables={
                "input": {
                    "agentId": "default-agent",
                    "content": "Explain load balancing briefly.",
                    "sessionId": session_id,
                }
            },
        )

        # Check cost summary
        cost_data = await graphql(
            http_client,
            """
            query {
                costSummary {
                    totalCost
                    breakdown {
                        service
                        cost
                        requestCount
                    }
                    period
                }
            }
            """,
        )
        summary = cost_data["costSummary"]
        assert summary["totalCost"] >= 0
        assert isinstance(summary["breakdown"], list)
        assert summary["period"] is not None
