"""Tests for GraphQL resolvers."""



def _graphql(client, query: str, variables: dict | None = None) -> dict:
    """Helper to execute a GraphQL query via HTTP POST."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    response = client.post("/graphql", json=payload)
    assert response.status_code == 200
    return response.json()


# ── Agent Queries ──────────────────────────────────────────────────────


def test_list_agents(client):
    """Should return seeded mock agents."""
    result = _graphql(client, "{ agents { id name agentType } }")
    assert "errors" not in result
    agents = result["data"]["agents"]
    assert len(agents) >= 3
    agent_names = [a["name"] for a in agents]
    assert "Weather Bot" in agent_names
    assert "Movie Quiz Bot" in agent_names
    assert "Document Assistant" in agent_names


def test_get_agent_by_id(client):
    """Should return a specific agent when queried by ID."""
    # First get the list to find an ID
    result = _graphql(client, "{ agents { id name } }")
    agent_id = result["data"]["agents"][0]["id"]

    # Query by ID
    result = _graphql(
        client,
        "query ($id: UUID!) { agent(agentId: $id) { id name agentType instructions } }",
        variables={"id": agent_id},
    )
    assert "errors" not in result
    agent = result["data"]["agent"]
    assert agent is not None
    assert agent["id"] == agent_id


def test_get_nonexistent_agent(client):
    """Should return null for non-existent agent ID."""
    result = _graphql(
        client,
        'query { agent(agentId: "00000000-0000-0000-0000-000000000000") { id name } }',
    )
    assert "errors" not in result
    assert result["data"]["agent"] is None


# ── Agent Mutations ────────────────────────────────────────────────────


def test_create_agent(client):
    """Should create a new agent and return it."""
    result = _graphql(
        client,
        """
        mutation {
            createAgent(input: {
                name: "Test Bot",
                agentType: CUSTOM,
                instructions: "You are a test bot."
            }) {
                id name agentType instructions
            }
        }
        """,
    )
    assert "errors" not in result
    agent = result["data"]["createAgent"]
    assert agent["name"] == "Test Bot"
    assert agent["agentType"] == "CUSTOM"
    assert agent["instructions"] == "You are a test bot."


def test_delete_agent(client):
    """Should delete an agent and return true."""
    # Create an agent first
    create_result = _graphql(
        client,
        """
        mutation {
            createAgent(input: {
                name: "To Delete",
                agentType: WEATHER,
                instructions: "Temporary."
            }) { id }
        }
        """,
    )
    agent_id = create_result["data"]["createAgent"]["id"]

    # Delete it
    result = _graphql(
        client,
        f'mutation {{ deleteAgent(agentId: "{agent_id}") }}',
    )
    assert "errors" not in result
    assert result["data"]["deleteAgent"] is True


# ── Chat Queries ───────────────────────────────────────────────────────


def test_send_message(client):
    """Should send a message and get a mock response."""
    # Get an agent ID first
    agents = _graphql(client, "{ agents { id } }")
    agent_id = agents["data"]["agents"][0]["id"]

    result = _graphql(
        client,
        """
        mutation ($input: SendMessageInput!) {
            sendMessage(input: $input) {
                id role content costUsd latencyMs
            }
        }
        """,
        variables={
            "input": {
                "agentId": agent_id,
                "content": "What is the weather in Paris?",
            }
        },
    )
    assert "errors" not in result
    message = result["data"]["sendMessage"]
    assert message["role"] == "ASSISTANT"
    assert "Mock response" in message["content"]
    assert message["costUsd"] is not None


def test_list_chat_sessions(client):
    """Should return chat sessions (may be empty initially)."""
    result = _graphql(client, "{ chatSessions { id agentId } }")
    assert "errors" not in result
    assert isinstance(result["data"]["chatSessions"], list)


# ── Document Queries ───────────────────────────────────────────────────


def test_list_documents(client):
    """Should return mock documents."""
    result = _graphql(client, "{ documents { id filename contentType chunkCount } }")
    assert "errors" not in result
    docs = result["data"]["documents"]
    assert len(docs) >= 2


def test_upload_document(client):
    """Should create a new document entry."""
    result = _graphql(
        client,
        """
        mutation {
            uploadDocument(filename: "test.pdf", contentType: "application/pdf") {
                id filename contentType chunkCount
            }
        }
        """,
    )
    assert "errors" not in result
    doc = result["data"]["uploadDocument"]
    assert doc["filename"] == "test.pdf"
    assert doc["chunkCount"] == 0  # Not yet processed


# ── Cost Queries ───────────────────────────────────────────────────────


def test_inference_costs(client):
    """Should return mock inference costs."""
    result = _graphql(
        client,
        "{ inferenceCosts(limit: 5) { totalCostUsd promptTokens completionTokens model } }",
    )
    assert "errors" not in result
    costs = result["data"]["inferenceCosts"]
    assert len(costs) > 0
    assert costs[0]["totalCostUsd"] > 0


def test_cost_summary(client):
    """Should return aggregated cost summary."""
    result = _graphql(
        client,
        '{ costSummary(period: "24h") { totalCostUsd totalInferences avgCostPerInference period } }',
    )
    assert "errors" not in result
    summary = result["data"]["costSummary"]
    assert summary["period"] == "24h"
    assert summary["totalInferences"] > 0
