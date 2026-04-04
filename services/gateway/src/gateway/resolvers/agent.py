"""Agent CRUD resolvers.

Stub implementation returning mock data. Will be wired to agent-engine
service via httpx in Phase 4.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import strawberry

from gateway.schema import Agent, AgentType, CreateAgentInput

# ── Mock data store (replaced by agent-engine in Phase 4) ──────────────
_mock_agents: dict[UUID, Agent] = {}


def _seed_mock_agents() -> None:
    """Seed mock agents for development."""
    if _mock_agents:
        return
    seeds = [
        ("Weather Bot", AgentType.WEATHER, "You are a helpful weather assistant."),
        ("Movie Quiz Bot", AgentType.QUIZ, "You are a movie quiz master specializing in South Indian cinema."),
        ("Document Assistant", AgentType.RAG, "You answer questions based on uploaded documents."),
    ]
    for name, agent_type, instructions in seeds:
        agent_id = uuid4()
        _mock_agents[agent_id] = Agent(
            id=agent_id,
            name=name,
            agent_type=agent_type,
            instructions=instructions,
            created_at=datetime.now(tz=timezone.utc),
        )


_seed_mock_agents()


def resolve_agents() -> list[Agent]:
    """List all agents."""
    return list(_mock_agents.values())


def resolve_agent(agent_id: UUID) -> Agent | None:
    """Get a single agent by ID."""
    return _mock_agents.get(agent_id)


def resolve_create_agent(input: CreateAgentInput) -> Agent:
    """Create a new agent."""
    agent_id = uuid4()
    agent = Agent(
        id=agent_id,
        name=input.name,
        agent_type=input.agent_type,
        instructions=input.instructions,
        created_at=datetime.now(tz=timezone.utc),
    )
    _mock_agents[agent_id] = agent
    return agent


def resolve_delete_agent(agent_id: UUID) -> bool:
    """Delete an agent by ID."""
    if agent_id in _mock_agents:
        del _mock_agents[agent_id]
        return True
    return False
