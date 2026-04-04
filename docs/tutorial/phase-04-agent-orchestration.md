# Phase 4: Agent Orchestration

## Summary

Wire up agent orchestration using Prefect for workflow scheduling and LangGraph for stateful, multi-step agent graphs. This phase builds the Weather Bot, Quiz Bot, and RAG Assistant as composable agent graphs with tool-calling, memory, and retry logic.

## Learning Objectives

- Define LangGraph state machines for each bot persona
- Register Prefect flows for scheduled and event-driven tasks
- Implement tool nodes (API calls, vector search, document retrieval)
- Add conversation memory and context window management

## Key Commands

```bash
# Start the Prefect server
prefect server start

# Run an agent graph locally
python -m agents.weather_bot --query "Weather in Tokyo"

# View Prefect flow runs
open http://localhost:4200
```

## Slash Command

Run `/04-agent-orchestration` in Claude Code to begin this phase.

## Next Phase

[Phase 5: LLM Runtime](phase-05-llm-runtime.md)
