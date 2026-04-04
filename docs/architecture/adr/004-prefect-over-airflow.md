# ADR-004: Prefect 3 over Airflow for Agent Orchestration

## Status: Accepted

## Date: 2026-04-04

## Context

AI agent execution in the KIAA platform involves multi-step workflows: retrieving
context from vector stores, calling LLM inference, executing tool actions, validating
outputs, and persisting results. These workflows require robust retry logic (with
exponential backoff for rate-limited APIs), per-step timeouts, real-time observability
into execution state, and scheduled batch runs. Agent workflows are inherently dynamic
-- the number of steps, tool calls, and branching paths depend on runtime LLM output,
making static DAG definitions impractical.

LangGraph state machines define the agent logic (nodes, edges, conditional routing),
but LangGraph alone lacks production orchestration features: no persistent scheduling,
no centralized monitoring dashboard, no built-in retry policies, and no distributed
task execution.

## Decision

We adopt Prefect 3 as the orchestration layer, wrapping LangGraph state machine
executions inside Prefect flows and tasks. Each agent type is a Prefect flow; each
LangGraph node execution is a Prefect task with independent retry and timeout
configuration. Prefect workers run on Kubernetes via the prefect-worker Helm chart,
with work pools scoped by resource requirements (GPU-requiring tasks vs CPU-only).

## Consequences

**Positive:**
- Prefect's Python-native API requires no DAG compilation or DSL translation -- flows
  are standard Python functions decorated with `@flow` and `@task`, enabling arbitrary
  control flow including loops, conditionals, and dynamic task generation.
- Built-in retry with configurable backoff (`retries=3, retry_delay_seconds=[10, 30, 60]`)
  handles transient LLM API failures without custom retry wrappers.
- Per-task timeouts (`timeout_seconds=120`) prevent runaway LLM calls from blocking
  worker capacity, with automatic cancellation and state reporting.
- The Prefect UI provides real-time flow run visualization, task-level logs, and
  failure alerting -- critical for debugging agent execution chains where failures
  may occur 5+ steps into a workflow.
- Prefect's artifact system captures intermediate agent outputs (retrieved documents,
  LLM responses, tool results) for post-hoc analysis and auditing.

**Negative:**
- Prefect 3 is a relatively recent major version; some ecosystem integrations are
  still maturing compared to the Airflow plugin ecosystem.
- The team must learn Prefect's concurrency model (async-native, concurrent task
  runners) and its interaction with LangGraph's own async execution.
- Prefect Cloud offers the best monitoring experience, but we self-host Prefect
  Server to maintain data sovereignty, accepting reduced polish in the UI.
- Wrapping LangGraph nodes as Prefect tasks adds a serialization boundary that
  requires careful handling of large state objects (conversation history, retrieved
  document chunks).

## Alternatives Considered

- **Apache Airflow:** Rejected due to its static DAG requirement -- agent workflows
  with runtime-determined branching cannot be expressed as Airflow DAGs without
  awkward workarounds (dynamic task mapping is limited). Airflow's scheduler
  architecture also introduces 10-30 second latency between tasks.
- **Dagster:** Strong contender with excellent asset-oriented design, but its
  op/graph/job abstraction adds conceptual overhead for our workflow-centric use
  case. Dagster's strength in data pipelines is less relevant for agent orchestration.
- **Raw LangGraph without orchestration:** Insufficient for production: no persistent
  scheduling, no centralized monitoring, no retry policies beyond manual implementation,
  and no distributed execution across worker pools.
