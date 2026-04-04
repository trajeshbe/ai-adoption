"""Locust load test for the GraphQL gateway."""

from __future__ import annotations

import json

from locust import HttpUser, between, task


class GatewayUser(HttpUser):
    """Simulates a user interacting with the Agent Platform GraphQL API."""

    wait_time = between(1, 3)
    default_headers = {"Content-Type": "application/json"}

    def _graphql(self, query: str, variables: dict | None = None, name: str = "") -> None:
        """Send a GraphQL POST request to /graphql."""
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables
        self.client.post(
            "/graphql",
            data=json.dumps(payload),
            headers=self.default_headers,
            name=name or "/graphql",
        )

    @task(3)
    def list_agents(self) -> None:
        """List all available agents."""
        query = """
        query ListAgents {
            agents {
                id
                name
                description
                status
            }
        }
        """
        self._graphql(query, name="ListAgents")

    @task(1)
    def get_agent(self) -> None:
        """Fetch a single agent by ID."""
        query = """
        query GetAgent($id: ID!) {
            agent(id: $id) {
                id
                name
                description
                status
                capabilities
            }
        }
        """
        self._graphql(query, variables={"id": "default-agent"}, name="GetAgent")

    @task(5)
    def send_message(self) -> None:
        """Send a chat message to an agent."""
        query = """
        mutation SendMessage($input: SendMessageInput!) {
            sendMessage(input: $input) {
                id
                content
                role
                timestamp
            }
        }
        """
        variables = {
            "input": {
                "agentId": "default-agent",
                "content": "What is the capital of France?",
                "sessionId": "load-test-session",
            }
        }
        self._graphql(query, variables=variables, name="SendMessage")

    @task(1)
    def list_documents(self) -> None:
        """List uploaded documents."""
        query = """
        query ListDocuments {
            documents {
                id
                filename
                mimeType
                uploadedAt
            }
        }
        """
        self._graphql(query, name="ListDocuments")

    @task(1)
    def cost_summary(self) -> None:
        """Retrieve cost summary."""
        query = """
        query CostSummary {
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
        """
        self._graphql(query, name="CostSummary")
