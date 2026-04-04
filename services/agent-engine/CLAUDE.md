# Agent Engine Service

## Purpose
AI agent orchestration. Executes LangGraph state machines for different agent types
(weather, quiz, RAG) wrapped in Prefect flows for operational reliability.

## Tech
FastAPI, LangGraph 0.2+, Prefect 3.x, OpenAI SDK (vLLM/llama.cpp compatible)

## Key Files
- `src/agent_engine/agents/base.py` -- Abstract agent interface
- `src/agent_engine/agents/weather.py` -- Weather agent implementation
- `src/agent_engine/agents/quiz.py` -- Quiz bot implementation
- `src/agent_engine/agents/rag.py` -- RAG agent (uses document-service)
- `src/agent_engine/graphs/` -- LangGraph StateGraph definitions per agent
- `src/agent_engine/flows/agent_flow.py` -- Prefect flow wrapping LangGraph
- `src/agent_engine/llm_client.py` -- Unified LLM client (vLLM + llama.cpp fallback)
- `src/agent_engine/registry.py` -- Agent type registry (factory pattern)
- `src/agent_engine/tools/` -- Tool implementations (weather_api, web_search, calculator)

## Patterns
- Each agent is a LangGraph StateGraph with typed state
- Prefect wraps execution for retry (3x with backoff), timeout (120s), caching
- LLM client uses circuit breaker: vLLM primary -> llama.cpp fallback
- Agent registry maps agent_type string to agent class + graph builder

## Run
`uv run uvicorn agent_engine.main:create_app --factory --reload --port 8003`

## Test
`uv run pytest tests/ -v`
