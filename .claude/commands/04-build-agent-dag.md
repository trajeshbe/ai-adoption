# Phase 4: Agent Orchestration -- Build LangGraph Agents with Prefect Flows

## What You Will Learn
- LangGraph state machines for AI agent logic
- Prefect 3 flows for operational reliability (retry, timeout, observability)
- Agent registry pattern (factory + strategy)
- Tool-use pattern for function calling agents
- Circuit breaker pattern for LLM client resilience
- Why Prefect over Airflow for ML workflows

## Prerequisites
- Phase 3 complete (Postgres/pgvector, Redis VSS, MinIO operational)
- Understanding of LLM concepts (prompts, tokens, function calling)

## Background: Why Prefect Wrapping LangGraph?
LangGraph excels at defining agent state machines (nodes = actions, edges = transitions).
But it lacks production workflow features: retry with backoff, timeout enforcement,
flow-level observability, artifact storage, and scheduling. Prefect provides all of
these. Each agent execution is a Prefect flow containing a task that runs the LangGraph
state machine. This gives us LangGraph for agent logic + Prefect for operational reliability.

A production AI system must handle LLM API timeouts, rate limits, and transient failures.
Raw LangGraph has no built-in retry. Prefect retries with exponential backoff are
the difference between "our agent is down" and "the agent recovered automatically."

See: docs/architecture/adr/004-prefect-over-airflow.md

## Step-by-Step Instructions

### Step 1: Create the Agent Engine Service

Create `services/agent-engine/pyproject.toml` with:
- fastapi, uvicorn, httpx
- langgraph>=0.2, langchain-core
- prefect>=3.0
- openai (for LLM API compatibility)
- agent-platform-common

### Step 2: Define the Agent Base Interface

Create `services/agent-engine/src/agent_engine/agents/base.py`:
```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from pydantic import BaseModel

class AgentInput(BaseModel):
    session_id: str
    message: str
    context: dict | None = None

class AgentOutput(BaseModel):
    response: str
    tool_calls: list[dict] | None = None
    tokens_used: int = 0
    cost_usd: float = 0.0

class BaseAgent(ABC):
    @abstractmethod
    async def run(self, input: AgentInput) -> AgentOutput: ...

    @abstractmethod
    async def stream(self, input: AgentInput) -> AsyncIterator[str]: ...
```

**Why an abstract base?** It defines the contract every agent must fulfill. The gateway
doesn't care if it's a weather agent or RAG agent -- it calls `agent.run(input)`.
This is the Strategy Pattern from design patterns.

### Step 3: Implement the Weather Agent (LangGraph)

Create `services/agent-engine/src/agent_engine/graphs/weather_graph.py`:
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class WeatherState(TypedDict):
    messages: list[dict]
    city: str | None
    weather_data: dict | None
    response: str | None

def parse_city(state: WeatherState) -> WeatherState:
    # Extract city name from user message using LLM
    ...

def fetch_weather(state: WeatherState) -> WeatherState:
    # Call weather API tool
    ...

def generate_response(state: WeatherState) -> WeatherState:
    # Generate natural language response using LLM
    ...

def build_weather_graph() -> StateGraph:
    graph = StateGraph(WeatherState)
    graph.add_node("parse_city", parse_city)
    graph.add_node("fetch_weather", fetch_weather)
    graph.add_node("generate_response", generate_response)
    graph.add_edge("parse_city", "fetch_weather")
    graph.add_edge("fetch_weather", "generate_response")
    graph.add_edge("generate_response", END)
    graph.set_entry_point("parse_city")
    return graph.compile()
```

**Key insight:** Each node is a pure function that transforms state. The graph
defines the execution order. This makes agents testable (test each node independently)
and observable (trace each node as a span).

### Step 4: Implement the RAG Agent

Create `services/agent-engine/src/agent_engine/graphs/rag_graph.py`:
- Node 1: Embed the query
- Node 2: Retrieve similar chunks from document-service
- Node 3: Build prompt with retrieved context
- Node 4: Generate response with LLM
- Conditional edge: If no relevant chunks found, respond with "I don't have info on that"

### Step 5: Implement Tools

Create tool implementations in `services/agent-engine/src/agent_engine/tools/`:
- `weather_api.py` -- Calls OpenWeatherMap or similar API
- `web_search.py` -- Web search integration
- `calculator.py` -- Math expression evaluation

### Step 6: Wrap in Prefect Flows

Create `services/agent-engine/src/agent_engine/flows/agent_flow.py`:
```python
from prefect import flow, task
from prefect.tasks import task_input_hash

@task(retries=3, retry_delay_seconds=[1, 10, 60], timeout_seconds=120,
      cache_key_fn=task_input_hash)
async def execute_graph(agent_type: str, input: AgentInput) -> AgentOutput:
    graph = registry.get_graph(agent_type)
    result = await graph.ainvoke({"messages": [{"role": "user", "content": input.message}]})
    return AgentOutput(response=result["response"], ...)

@flow(name="agent-execution", log_prints=True)
async def run_agent(agent_type: str, input: AgentInput) -> AgentOutput:
    return await execute_graph(agent_type, input)
```

**What Prefect adds:**
- `retries=3` with exponential backoff (1s, 10s, 60s) for LLM API failures
- `timeout_seconds=120` kills runaway LLM calls
- `cache_key_fn` deduplicates identical requests
- Flow-level observability in Prefect UI
- Artifact storage for debugging agent responses

### Step 7: Build the Agent Registry

Create `services/agent-engine/src/agent_engine/registry.py`:
```python
class AgentRegistry:
    _agents: dict[str, type[BaseAgent]] = {}
    _graphs: dict[str, StateGraph] = {}

    @classmethod
    def register(cls, agent_type: str, agent_cls: type[BaseAgent], graph_builder):
        cls._agents[agent_type] = agent_cls
        cls._graphs[agent_type] = graph_builder()

    @classmethod
    def get(cls, agent_type: str) -> BaseAgent:
        return cls._agents[agent_type]()
```

### Step 8: Build the LLM Client with Fallback

Create `services/agent-engine/src/agent_engine/llm_client.py`:
```python
class LLMClient:
    def __init__(self, primary_url: str, fallback_url: str):
        self.primary = AsyncOpenAI(base_url=primary_url)   # vLLM
        self.fallback = AsyncOpenAI(base_url=fallback_url)  # llama.cpp

    async def chat(self, messages, **kwargs):
        try:
            if await self._is_healthy(self.primary):
                return await self.primary.chat.completions.create(messages=messages, **kwargs)
        except Exception:
            pass  # Circuit breaker trips
        return await self.fallback.chat.completions.create(messages=messages, **kwargs)
```

### Step 9: Wire to Gateway

Update gateway resolvers to call agent-engine via httpx for real agent execution.

### Step 10: Write Unit Tests

Test each graph node independently with mocked LLM responses.

## Verification
```bash
# Start agent-engine
cd services/agent-engine && uv run uvicorn agent_engine.main:create_app --factory --port 8003

# Test via GraphQL
# mutation { sendMessage(agentId: "weather-1", content: "Weather in Paris?") { response } }

# Check Prefect UI (if running)
# prefect server start  # http://localhost:4200

uv run pytest services/agent-engine/tests/ -v
```

## Key Concepts Taught
1. **LangGraph state machines** -- Nodes as pure functions, edges as transitions
2. **Prefect for reliability** -- Retry, timeout, caching for production ML workflows
3. **Strategy pattern** -- Agent registry decouples gateway from agent implementations
4. **Circuit breaker** -- Graceful LLM fallback (vLLM -> llama.cpp)
5. **Tool-use pattern** -- Agents that call external APIs via function calling

## What's Next
Phase 5 (`/05-setup-llm-runtime`) deploys the actual LLM inference infrastructure:
vLLM on KubeRay for GPU-accelerated inference and llama.cpp for CPU fallback.
