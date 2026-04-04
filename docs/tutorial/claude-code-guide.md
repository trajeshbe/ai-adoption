# How This Platform Was Built with Claude Code

A comprehensive guide for fresh graduates on AI-assisted software development.

---

## Table of Contents

1. [What is Claude Code?](#1-what-is-claude-code)
2. [CLAUDE.md -- The Project Brain](#2-claudemd----the-project-brain)
3. [Slash Commands -- Tutorial Phases](#3-slash-commands----tutorial-phases)
4. [How This App Was Built with Claude Code](#4-how-this-app-was-built-with-claude-code)
5. [The AI-Assisted Development Workflow](#5-the-ai-assisted-development-workflow)
6. [Architecture Decision Records (ADRs)](#6-architecture-decision-records-adrs)
7. [Best Practices for AI-Assisted Development](#7-best-practices-for-ai-assisted-development)
8. [What Claude Code Can and Cannot Do](#8-what-claude-code-can-and-cannot-do)

---

## 1. What is Claude Code?

### The Tool

Claude Code is Anthropic's command-line interface for AI-assisted software development.
It is not a chatbot with a coding hobby. It is a full development partner that lives
inside your terminal, reads your codebase, generates production-quality code, debugs
errors in real time, and explains its reasoning every step of the way.

You install it, open a terminal in your project directory, and start describing what
you want to build in plain English. Claude Code reads your files, understands your
project structure, and writes code that fits your existing patterns. It is like pair
programming with a senior engineer who has read every file in your repository and
never forgets a convention.

### How It Works

The core loop is straightforward:

1. **You describe intent in natural language.** "Create a FastAPI service with a
   GraphQL endpoint that returns a list of AI agents."
2. **Claude Code reads your project context.** It examines CLAUDE.md files, existing
   code, configuration, and directory structure to understand conventions.
3. **It generates code that follows your patterns.** If your project uses the app
   factory pattern, it generates an app factory. If you use Pydantic Settings for
   config, it uses Pydantic Settings.
4. **You review, test, and iterate.** Paste an error message, and Claude Code
   analyzes the stack trace and produces a fix.

This is not copy-pasting from Stack Overflow. Claude Code generates code that is
aware of your specific project -- your imports, your directory structure, your naming
conventions, your dependencies.

### Vibe Coding and AI Pair Programming

"Vibe coding" is a term that has emerged to describe the experience of building
software by describing your intent and letting an AI generate the implementation.
You focus on the *what* and the *why* while the AI handles the *how*.

But here is the important nuance: vibe coding does not mean abdicating responsibility.
It means operating at a higher level of abstraction. Instead of typing
`async def create_app() -> FastAPI:` character by character, you say "create a FastAPI
app factory with GraphQL, health endpoints, and CORS middleware." You still need to
understand what an app factory is, why health endpoints matter, and what CORS does.
The AI accelerates your output; it does not replace your understanding.

Think of it as the difference between writing assembly code and writing Python. Python
did not make understanding computation unnecessary -- it raised the abstraction level
so you could think about problems instead of registers. Claude Code raises the
abstraction level again so you can think about architecture instead of syntax.

---

## 2. CLAUDE.md -- The Project Brain

### What is CLAUDE.md?

Every time you start a conversation with Claude Code in a directory, it looks for a
file named `CLAUDE.md`. This file is the project's memory. It tells Claude Code what
this project is, how it is structured, what conventions to follow, and what commands
are available. Without it, Claude Code is a brilliant engineer who just walked into
your codebase with zero context. With it, Claude Code is a team member who has read
the onboarding documentation.

### The Hierarchical Strategy

This project uses **12 CLAUDE.md files** organized in a hierarchy. This is not
accidental -- it is a deliberate strategy to give Claude Code the right amount of
context at the right scope.

```
ai_adoption/
  CLAUDE.md                          # Root: project overview, all conventions
  services/
    CLAUDE.md                        # All services: shared patterns, ports, commands
    gateway/
      CLAUDE.md                      # Gateway: schema-first, resolvers, middleware
    agent-engine/
      CLAUDE.md                      # Agent engine: LangGraph, Prefect, registry
    document-service/
      CLAUDE.md                      # Document service: MinIO, pgvector, chunking
    cache-service/
      CLAUDE.md                      # Cache service: Redis VSS, semantic cache
    cost-tracker/
      CLAUDE.md                      # Cost tracker: OpenCost, per-inference cost
  frontend/
    CLAUDE.md                        # Frontend: Next.js, Tailwind, urql, hooks
  libs/
    CLAUDE.md                        # Shared libraries: py-common, ts-common
  infra/
    CLAUDE.md                        # Infrastructure: Kustomize, Helm, Argo CD, OPA
  tests/
    CLAUDE.md                        # Cross-cutting tests: e2e, load, chaos, security
  docs/
    CLAUDE.md                        # Documentation: ADRs, tutorials, runbooks
```

**Why a hierarchy?** When you are working on the gateway service and ask Claude Code
to add a new resolver, it reads:

1. The **root CLAUDE.md** -- knows the overall architecture and conventions
2. The **services/CLAUDE.md** -- knows all services use the app factory pattern and
   expose `/healthz` endpoints
3. The **services/gateway/CLAUDE.md** -- knows the gateway uses schema-first design,
   resolvers live in `resolvers/`, and the run command is `uv run uvicorn ...`

This layered context means Claude Code generates a resolver that fits the project
perfectly -- correct imports, correct patterns, correct directory placement.

### What Goes in Each CLAUDE.md

**Root CLAUDE.md (under 200 lines):** The big picture. Project overview, architecture
diagram, monorepo layout, coding conventions, build commands, testing strategy, and
the list of tutorial phases. This is what every Claude Code conversation starts with.

Here is the conventions section from our root CLAUDE.md:

```
## Conventions
- Python: 3.11+, uv for deps, ruff lint+format, mypy strict, pytest
- TypeScript: strict mode, ESLint+Prettier, Vitest+Playwright
- Services: /healthz and /readyz endpoints, OTEL traces via libs/py-common/telemetry.py
- Config: Environment variables via Pydantic Settings (12-factor)
- API: GraphQL schema-first -- edit services/gateway/src/gateway/schema.py first
- K8s: Kustomize base/overlays. Never raw kubectl apply. Helm for third-party only.
- GitOps: All changes via Argo CD sync. Git is the single source of truth.
```

These six lines save hundreds of corrections. Without them, Claude Code might generate
a REST endpoint instead of GraphQL, use pip instead of uv, or create a raw Kubernetes
manifest instead of a Kustomize overlay.

**Directory-level CLAUDE.md (services/, infra/, libs/):** Scope-specific patterns.
The services CLAUDE.md documents the port assignments, the shared app factory pattern,
and the standard test/run commands for every Python service. The infra CLAUDE.md
documents the Kustomize rules and the prohibition on raw `kubectl apply`.

**Service-level CLAUDE.md (gateway/, agent-engine/):** Deep technical context. The
gateway CLAUDE.md lists key files (main.py, schema.py, resolvers/), patterns
(schema-first, dependency injection, circuit breaker), and the exact run command.

### Why This Matters

CLAUDE.md files are the single most important thing you can write for AI-assisted
development. They are the difference between Claude Code generating generic code and
generating code that belongs in your project. They are cheap to write (each one is
10-30 lines), and they pay for themselves immediately.

A well-written CLAUDE.md is more valuable than a README. A README is for humans who
browse GitHub. A CLAUDE.md is for an AI that is about to write code in your project.
It needs to be precise, not narrative. Conventions, not explanations. Commands, not
prose.

---

## 3. Slash Commands -- Tutorial Phases

### What Are Slash Commands?

Claude Code supports custom slash commands -- predefined prompts stored in
`.claude/commands/` that you invoke by typing a command like `/01-scaffold-api`.
Each command is a Markdown file containing detailed, step-by-step instructions for
Claude Code to follow.

This project has **11 custom slash commands**, one for each tutorial phase:

| Command                | Phase | What It Builds                                    |
|------------------------|-------|---------------------------------------------------|
| `/00-setup-env`        | 0     | DevContainer, Docker Compose, toolchain bootstrap |
| `/01-scaffold-api`     | 1     | FastAPI + Strawberry GraphQL gateway               |
| `/02-scaffold-frontend`| 2     | Next.js 14 + Tailwind + Shadcn/ui frontend        |
| `/03-setup-data-layer` | 3     | Postgres/pgvector, Redis VSS, MinIO               |
| `/04-build-agent-dag`  | 4     | Prefect + LangGraph agent orchestration            |
| `/05-setup-llm-runtime`| 5     | vLLM on KubeRay + llama.cpp CPU fallback          |
| `/06-add-observability`| 6     | OpenTelemetry, Grafana Tempo/Loki/Mimir           |
| `/07-setup-mesh`       | 7     | Istio ambient mesh + Contour/Envoy ingress        |
| `/08-setup-gitops`     | 8     | Argo CD + Tekton CI/CD pipelines                   |
| `/09-add-policy`       | 9     | OPA Gatekeeper + OpenCost governance               |
| `/10-harden`           | 10    | Load tests, chaos tests, security scans, SLOs     |

### How They Guide Complex Builds

Each slash command is a detailed blueprint. Take `/01-scaffold-api` as an example.
It contains:

- **What You Will Learn** -- Lists the concepts (schema-first design, app factory
  pattern, dependency injection)
- **Prerequisites** -- What must be done before this phase
- **Background** -- Why the technology choices were made (with links to ADRs)
- **Step-by-Step Instructions** -- 8-10 numbered steps, each with code templates,
  file paths, and explanations of *why* each step matters
- **Verification** -- Commands to confirm everything works
- **Key Concepts Taught** -- Summary of engineering principles covered

When you type `/01-scaffold-api` in Claude Code, it reads this entire document and
executes each step: creating files, writing code, setting up configurations. But
because it also reads the CLAUDE.md hierarchy, the code it generates follows all
project conventions automatically.

### The Power of Composable Phases

Each phase builds on the previous one. Phase 1 creates the API with mock data.
Phase 3 replaces the mocks with real databases. Phase 4 adds agent intelligence.
Phase 6 adds observability. This composability means you can:

- **Learn incrementally.** Each phase teaches 3-5 new concepts without overwhelming
  you.
- **Debug in isolation.** If Phase 4 breaks, you know Phases 1-3 work. The problem
  is in agent orchestration, not in your API or database layer.
- **Understand the architecture.** By building layer by layer, you see why each
  service exists and how they connect.

---

## 4. How This App Was Built with Claude Code

This section walks through how Claude Code was actually used to build this platform.
These are not hypothetical examples -- this is the real process.

### Phase 1 -- API Layer: The Gateway Service

**What we told Claude Code:** "Build a FastAPI gateway service with Strawberry GraphQL.
Schema-first approach. App factory pattern. Mock data for now."

**What Claude Code generated:**

The FastAPI app factory in `services/gateway/src/gateway/main.py`:
```python
def create_app() -> FastAPI:
    app = FastAPI(title="Agent Platform Gateway", version="0.1.0")
    schema = strawberry.Schema(query=Query, mutation=Mutation)
    graphql_app = GraphQLRouter(schema)
    app.include_router(graphql_app, prefix="/graphql")

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz():
        return {"status": "ready"}

    return app
```

Claude Code did not just write a hello-world FastAPI app. It:

- Used the **app factory pattern** (`create_app()` function) because CLAUDE.md
  specified it -- this makes the service testable by creating fresh app instances
  in each test.
- Added **`/healthz` and `/readyz` endpoints** because CLAUDE.md requires every
  service to have them -- Kubernetes uses these for liveness and readiness probes.
- Mounted **Strawberry GraphQL** on `/graphql` because the conventions specify
  schema-first GraphQL.
- Created the **full GraphQL schema** with types for Agent, ChatMessage, ChatSession,
  Document, and InferenceCost -- all with proper Strawberry decorators and Python
  type hints.
- Generated **stub resolvers** organized in `resolvers/agent.py`, `resolvers/chat.py`,
  `resolvers/document.py`, and `resolvers/cost.py` -- returning mock data so the
  frontend team could start building immediately.
- Added **middleware** for telemetry, auth (stub), and rate limiting.
- Created the **Dockerfile** with multi-stage builds.
- Wrote **unit tests** using Strawberry's test client.

All of this from a single natural-language prompt, guided by the slash command and
CLAUDE.md context.

### Phase 2 -- Frontend: The Next.js Chat Interface

**What we told Claude Code:** "Build the Next.js frontend with Tailwind and Shadcn/ui.
Chat interface with streaming. Agent management. GraphQL client."

**What Claude Code generated:**

- **Next.js 14 App Router** with the full page structure:
  - `src/app/layout.tsx` -- Root layout with GraphQL provider, sidebar, navbar
  - `src/app/agents/page.tsx` -- Agent grid with cards
  - `src/app/agents/[id]/page.tsx` -- Agent detail with dynamic routing
  - `src/app/agents/new/page.tsx` -- Agent creation form
  - `src/app/documents/page.tsx` -- Document upload and listing
  - Placeholder pages for workflows, costs, and observability

- **Tailwind + Shadcn/ui component library** -- Button, Card, Dialog, Input, Textarea,
  DropdownMenu, Avatar, Badge, Separator, ScrollArea. All installed and configured
  with the project's design tokens.

- **Chat interface components:**
  - `ChatWindow.tsx` -- The main container with message list, input bar, and streaming
    indicator
  - `MessageBubble.tsx` -- Renders user and assistant messages with markdown support
  - `StreamingIndicator.tsx` -- Animated typing dots during LLM generation
  - `ToolCallCard.tsx` -- Visual display when an agent invokes an external tool

- **GraphQL client integration** with urql:
  - `src/lib/graphql/client.ts` -- urql client with cache, fetch, and subscription
    exchanges
  - `src/lib/graphql/queries.ts` -- All query documents
  - `src/lib/graphql/mutations.ts` -- All mutation documents
  - `src/lib/graphql/subscriptions.ts` -- WebSocket subscription for chat streaming

- **Custom hooks** that encapsulate data fetching:
  - `useAgents()` -- Agent listing with loading and error states
  - `useChat()` -- Chat state management, message sending, response subscription
  - `useCosts()` -- Cost data fetching
  - `useDocuments()` -- Document upload and listing

Claude Code understood the distinction between server components (agent list, document
list -- static data, fast initial load) and client components (chat interface --
interactive, real-time streaming). It applied the correct `"use client"` directives
only where needed.

### Phase 4 -- Agent Engine: Intelligence Layer

**What we told Claude Code:** "Build the agent orchestration service. LangGraph state
machines for weather, quiz, and RAG agents. Wrap everything in Prefect flows for
retry and timeout. Circuit breaker for LLM failover."

**What Claude Code generated:**

- **Abstract base agent class** (`agents/base.py`) defining the contract:
  - `AgentInput` and `AgentOutput` Pydantic models
  - `BaseAgent` ABC with `run()` and `stream()` methods
  - This is the Strategy Pattern -- the gateway calls `agent.run(input)` without
    knowing or caring what type of agent it is

- **LangGraph state machines** for each agent type:
  - Weather agent: `parse_city` -> `fetch_weather` -> `generate_response`
  - Quiz agent: `generate_question` -> `evaluate_answer` -> `provide_feedback`
  - RAG agent: `embed_query` -> `retrieve_chunks` -> `build_prompt` -> `generate_response`
  - Each node is a pure function that transforms typed state, making agents testable
    and observable

- **LLM client with circuit breaker** (`llm_client.py`):
  ```python
  class LLMClient:
      def __init__(self, primary_url, fallback_url):
          self.primary = AsyncOpenAI(base_url=primary_url)   # vLLM (GPU)
          self.fallback = AsyncOpenAI(base_url=fallback_url)  # Ollama (CPU)

      async def chat(self, messages, **kwargs):
          try:
              if await self._is_healthy(self.primary):
                  return await self.primary.chat.completions.create(...)
          except Exception:
              pass  # Circuit breaker trips to fallback
          return await self.fallback.chat.completions.create(...)
  ```
  This pattern ensures the platform stays operational even when the GPU inference
  server goes down. The fallback to CPU-based Ollama is slower but keeps users
  unblocked.

- **Prefect flow wrapping** (`flows/agent_flow.py`) adding production reliability:
  - `retries=3` with exponential backoff (1s, 10s, 60s)
  - `timeout_seconds=120` to kill runaway LLM calls
  - `cache_key_fn` for deduplicating identical requests
  - Flow-level observability in the Prefect UI

- **Agent registry** (`registry.py`) using the Factory Pattern to map agent type
  strings to agent classes and graph builders.

- **Tool implementations** in `tools/` for weather API calls, web search, and
  calculator operations.

### Live Debugging Sessions

Building a platform with 5 microservices, a frontend, and Kubernetes infrastructure
means encountering real bugs. Here is where Claude Code truly earns its keep -- not
in the initial generation, but in the debugging.

**CORS issues:** The frontend at `localhost:3000` could not call the gateway at
`localhost:8000`. Claude Code diagnosed the missing `allow_origins` configuration
in the FastAPI CORS middleware and added the correct origins, methods, and headers.

**Next.js 14 vs 15 API differences:** The initial code used `use(params)` for
accessing route parameters (a Next.js 15 pattern). Claude Code identified the version
mismatch and refactored to `useParams()`, the correct hook for Next.js 14.

**Async/sync mutation mismatch:** GraphQL mutations were defined as synchronous
functions but called async service methods. Claude Code traced the stack to the
Strawberry resolver layer, identified that Strawberry supports async resolvers
natively, and converted the mutation resolvers to `async def`.

**UUID validation errors:** The browser was sending agent IDs in a format that
failed server-side UUID validation. Claude Code added proper UUID parsing with a
clear error message instead of an opaque 500 error.

**Prefect version conflicts:** The codebase was written against Prefect 3.x, but
some patterns from Prefect 2.x documentation had leaked in. Claude Code identified
the API differences (task decorator changes, flow runner changes) and updated all
usages to Prefect 3.x.

**GraphQL schema type mismatches:** The `latency_ms` field was defined as `int` in
the schema but the agent engine was returning `float` values. Claude Code identified
the mismatch, assessed the trade-offs (precision vs. schema clarity), and updated the
schema to use `float` with a renamed field `latency_ms` to maintain semantic clarity.

In each case, the debugging workflow was identical: paste the error, Claude Code reads
the stack trace, identifies the root cause, and produces a targeted fix. No searching
Stack Overflow. No reading documentation for 30 minutes. Paste, diagnose, fix, move on.

### Infrastructure: Kubernetes and Beyond

**What we told Claude Code:** "Create Kubernetes manifests for all services. HPA
auto-scaling. Minikube-compatible. Load test scripts."

**What Claude Code generated:**

- **Kustomize manifests** in `infra/k8s/base/` for every service: Deployment,
  Service, ConfigMap, resource limits, liveness/readiness probes using the `/healthz`
  and `/readyz` endpoints from each service.

- **HPA (Horizontal Pod Autoscaler)** configurations that scale services based on
  CPU and memory utilization, with sensible min/max replica counts.

- **Kustomize overlays** for different environments (dev, staging, prod) that patch
  the base manifests with environment-specific resource limits and replica counts.

- **Minikube setup scripts** for local Kubernetes development.

- **Load test scripts** using Locust to hammer the GraphQL endpoint and verify
  auto-scaling behavior.

- **A scaling dashboard** (React + polling) that visualizes pod counts, CPU usage,
  and request rates in real time during load tests.

- **An in-memory metrics collector** for development environments where a full
  Prometheus stack is overkill.

---

## 5. The AI-Assisted Development Workflow

Here is the workflow that was used to build this platform. If you adopt it, you will
be dramatically faster than traditional development while producing code of equal or
higher quality.

### Step 1: Describe What You Want in Natural Language

Be specific about the outcome, not the implementation. Good prompts:

- "Create a new GraphQL resolver that returns the total inference cost grouped by
  model name for the last 7 days."
- "Add a circuit breaker to the LLM client that falls back to Ollama after 3
  consecutive failures to the vLLM endpoint."
- "Write a Kustomize overlay for the staging environment that sets memory limits
  to 512Mi and replica count to 2."

Bad prompts:

- "Write some code." (Too vague)
- "Create a function called `get_costs` that takes a `start_date` parameter and
  queries the database using SQL." (Too prescriptive -- you are writing the code in
  English instead of letting Claude Code choose the right approach for your project)

### Step 2: Claude Code Reads Existing Context

Before generating a single line, Claude Code reads:

- Every CLAUDE.md file in the hierarchy from the root to your current directory
- The files you are currently editing or have recently mentioned
- Any code, errors, or context you paste into the conversation

This is why CLAUDE.md files are critical. They are the difference between a generic
answer and a project-specific answer.

### Step 3: Code Generation Following Project Conventions

Claude Code generates code that matches your project. In this platform:

- Python code uses type hints, Pydantic models, and async/await
- Services use the app factory pattern with FastAPI
- Configuration comes from environment variables via Pydantic Settings
- GraphQL types are defined in `schema.py` before resolvers are implemented
- Kubernetes manifests use Kustomize, never raw `kubectl apply`
- Tests live in `tests/unit/` and `tests/integration/` within each service

Claude Code does not need to be told these things every time. It reads them from
CLAUDE.md and applies them automatically.

### Step 4: Test and Iterate

After Claude Code generates code, you run it. Sometimes it works on the first try.
Sometimes there are errors. When there are errors, the workflow is:

1. Run the code
2. Copy the error message or stack trace
3. Paste it to Claude Code
4. Claude Code analyzes the error, identifies the root cause, and produces a fix
5. Apply the fix, run again
6. Repeat until it works

This iterative loop is fast -- typically 1-3 cycles for most issues. Claude Code
is particularly good at reading Python tracebacks, JavaScript error messages, and
Kubernetes event logs.

### Step 5: Fix Bugs in Real Time

The debugging experience with Claude Code is qualitatively different from traditional
debugging. Instead of:

1. Read the error message
2. Google the error message
3. Read 5 Stack Overflow answers
4. Try the highest-voted answer
5. It does not work because your context is different
6. Try the second answer
7. Eventually figure it out

You do:

1. Paste the error message
2. Get a fix that is specific to your codebase
3. Apply it
4. Move on

Claude Code has the advantage of seeing your actual code, your actual configuration,
and your actual error. It does not give you a generic answer. It gives you your answer.

### Step 6: Understand the Decisions

Claude Code does not just write code -- it explains why. When it chooses the factory
pattern over a module-level app instance, it explains that factory patterns make
testing easier. When it uses a circuit breaker for LLM calls, it explains that LLM
APIs are unreliable and you need graceful degradation.

This is valuable for learning. You are not just getting code -- you are getting a
running commentary on software engineering decisions from a system that has absorbed
a vast amount of engineering knowledge.

---

## 6. Architecture Decision Records (ADRs)

### How Claude Code Helped Write ADRs

This project has **7 Architecture Decision Records** in `docs/architecture/adr/`.
Each one documents a significant technical decision using a structured format:
Context, Decision, Consequences (positive and negative), and Alternatives Considered.

Claude Code helped write these ADRs by:

1. **Analyzing the actual codebase** to understand what decisions had been made
2. **Articulating the trade-offs** that led to each decision
3. **Documenting alternatives** that were considered and rejected, with clear
   reasoning for the rejection

The 7 ADRs in this project:

| ADR | Decision | Key Trade-off |
|-----|----------|---------------|
| 001 | Monorepo structure | Atomic changes vs. repo size complexity |
| 002 | GraphQL over REST | Flexible queries vs. caching complexity |
| 003 | vLLM with CPU fallback | GPU performance vs. availability |
| 004 | Prefect over Airflow | ML-native workflows vs. ecosystem size |
| 005 | Istio ambient mesh | No sidecars vs. maturity of ambient mode |
| 006 | pgvector over dedicated vector DB | Operational simplicity vs. scale limits |
| 007 | Redis semantic cache | Low-latency caching vs. cache invalidation complexity |

### Example: ADR-002 (GraphQL over REST)

Here is the reasoning Claude Code helped articulate for choosing GraphQL:

**Context:** The frontend presents composite views aggregating data from 4 different
backend services. A REST approach would require N parallel requests or a dedicated
Backend-for-Frontend service. The chat interface also requires streaming over
WebSocket regardless of the API paradigm.

**Decision:** Strawberry GraphQL on FastAPI. Strawberry's code-first, type-annotation
approach aligns with the Pydantic model ecosystem. Subscriptions over WebSocket handle
real-time chat streaming.

**Consequences:**
- Positive: Single round-trip for composite views, unified real-time mechanism,
  auto-generated TypeScript types for the frontend
- Negative: HTTP caching is harder (single POST endpoint), N+1 queries require
  DataLoaders, partial error handling differs from REST

**Alternatives rejected:**
- REST with BFF: Solves aggregation but adds a service to maintain
- gRPC-web: Excellent performance but requires Envoy proxy for browsers
- tRPC: TypeScript-native but incompatible with Python backends

This is the kind of documentation that engineering teams often skip because it takes
time. With Claude Code, writing an ADR takes minutes instead of hours.

---

## 7. Best Practices for AI-Assisted Development

These practices were learned by building this platform. They apply to any project
using Claude Code or similar AI development tools.

### Write Good CLAUDE.md Files

This is the single highest-leverage thing you can do. A good CLAUDE.md is:

- **Specific, not generic.** "Python 3.11+, uv for deps, ruff lint+format" is useful.
  "Follow best practices" is useless.
- **Actionable.** Include exact commands: `uv run uvicorn gateway.main:create_app --factory --port 8000`
- **Convention-focused.** Document what patterns to use and what to avoid: "Kustomize
  base/overlays. Never raw kubectl apply."
- **Short.** The root CLAUDE.md should be under 200 lines. If it is longer, split
  context into directory-level CLAUDE.md files.

### Use Schema-First Design

Define your data contracts before implementing them. In this project, we defined
GraphQL types (Agent, ChatMessage, Document) before writing resolvers. This:

- Lets the frontend team start building against the schema immediately
- Gives Claude Code a clear target when generating resolver implementations
- Prevents the common failure mode of "the backend returns slightly different data
  than the frontend expects"

### Let AI Handle Boilerplate, Review the Patterns

Claude Code excels at generating repetitive code: CRUD resolvers, Kubernetes manifests,
test boilerplate, Dockerfile multi-stage builds, middleware setup. Let it handle these.

But **review the architectural patterns**. When Claude Code generates a circuit breaker,
verify that the failure thresholds make sense for your use case. When it generates HPA
configurations, verify that the CPU targets and replica ranges match your expected load.

The rule of thumb: trust the syntax, verify the semantics.

### Always Test AI-Generated Code

Claude Code generates code that is syntactically correct and follows patterns well.
But it can make logical errors, especially in:

- Edge cases in business logic
- Concurrency and race conditions
- Security-sensitive code (auth, input validation)
- Performance-critical paths

Run the tests. Write new tests for generated code. This project has a five-layer
testing strategy (unit, integration, e2e, load, chaos) precisely because every layer
of code -- human-written or AI-generated -- needs verification.

### Use AI for Debugging

This is arguably where Claude Code provides the most value per minute spent. The
workflow is simple:

1. Run your code
2. It fails with an error
3. Paste the error to Claude Code
4. Get a fix that is specific to your codebase
5. Apply it

Claude Code is particularly strong at:
- Python tracebacks (it identifies the root cause, not just the symptom)
- TypeScript type errors (it understands complex generic types)
- Kubernetes event logs (it maps pod events to configuration issues)
- Docker build failures (it traces layer dependencies)

### Trust but Verify

Claude Code is fast, knowledgeable, and consistent. It is also not infallible. It can:

- Hallucinate API methods that do not exist in the library version you are using
- Apply patterns from one framework to another where they do not fit
- Miss subtle security implications
- Generate code that works but is not the best approach for your scale

The correct mental model is: Claude Code is a very fast, very knowledgeable junior
engineer. It produces excellent first drafts that an experienced engineer should review.
As you gain experience, your ability to review effectively improves, and the
human-AI collaboration becomes more powerful.

---

## 8. What Claude Code Can and Cannot Do

### What Claude Code CAN Do

**Generate entire services from a description.** This platform has 5 Python
microservices and a Next.js frontend. Each one was initially generated by Claude Code
from a natural-language description guided by a slash command. The gateway service --
app factory, GraphQL schema, resolvers, middleware, Dockerfile, tests -- was generated
in a single session.

**Debug errors from stack traces.** Paste a Python traceback, a JavaScript error, or
a Kubernetes event log, and Claude Code identifies the root cause and produces a fix.
During this project's development, CORS issues, version mismatches, async/sync
conflicts, and schema type errors were all resolved this way.

**Write tests at every level.** Unit tests with pytest and Vitest, integration tests
with testcontainers, end-to-end tests with Playwright, load tests with Locust. Claude
Code generates tests that follow the existing test patterns in your project.

**Create Kubernetes manifests.** Deployments, Services, ConfigMaps, HPA configurations,
Kustomize overlays, Helm values files. Claude Code understands the Kubernetes resource
model and generates manifests with correct API versions, proper resource limits, and
working health probes.

**Follow project conventions consistently.** Once conventions are documented in
CLAUDE.md, Claude Code applies them across every file it generates. Every service
gets `/healthz` and `/readyz`. Every Python service uses the app factory pattern.
Every Kubernetes manifest uses Kustomize. Consistency is maintained across thousands
of lines of code without human vigilance.

**Explain code and architecture decisions.** Claude Code does not just write code. It
explains why it chose a particular pattern, what trade-offs exist, and what alternatives
were considered. This is invaluable for learning and for writing ADRs.

**Refactor across multiple files.** Rename a type, change an API contract, update a
pattern -- Claude Code can trace the implications across files and make coordinated
changes.

### What Claude Code CANNOT Do

**Access production systems or deploy code.** Claude Code operates on your local
filesystem. It cannot SSH into servers, access databases, or run deployment pipelines.
Deployment is handled by GitOps (Argo CD) -- you commit code, push to git, and the
deployment pipeline takes over.

**Replace understanding of fundamentals.** If you do not understand what a circuit
breaker is, you cannot evaluate whether Claude Code's circuit breaker implementation
is correct for your use case. If you do not understand Kubernetes resource limits,
you cannot judge whether the generated HPA configuration will work under your expected
load.

Claude Code accelerates engineers who understand the fundamentals. It does not
substitute for understanding the fundamentals.

**Make product decisions.** Claude Code does not know your users, your business
constraints, your performance requirements, or your budget. It can generate a service
that handles 10 requests per second or 10,000 requests per second -- but you need
to tell it which one you need and why.

**Guarantee security.** Claude Code can generate auth middleware, input validation,
and CORS configuration. But security requires threat modeling, penetration testing,
and domain-specific knowledge of attack vectors. Always have security-sensitive code
reviewed by a human with security expertise.

**Think about your system holistically across time.** Claude Code sees your codebase
at a point in time. It does not know your deployment history, your incident history,
or your team's operational strengths and weaknesses. Operational wisdom comes from
experience, not from code generation.

### The Goal: Amplify, Not Replace

The purpose of AI-assisted development is not to replace software engineers. It is to
amplify them. A junior engineer with Claude Code can produce code at the speed of a
mid-level engineer. A mid-level engineer with Claude Code can produce code at the
speed of a senior engineer. A senior engineer with Claude Code can build systems
that would normally require a team.

But in every case, the human brings something the AI cannot: judgment about what
to build, understanding of user needs, awareness of organizational context, and
accountability for the result.

The engineers who will thrive in the AI era are not those who memorize syntax or
type the fastest. They are those who:

1. **Understand systems deeply** -- so they can evaluate AI-generated architecture
2. **Communicate intent clearly** -- so they can guide AI effectively
3. **Think critically** -- so they can catch AI mistakes
4. **Learn continuously** -- so they can leverage each new AI capability

This platform was built to teach you all four of these skills. The code is real.
The architecture is production-grade. And every line was generated through a
collaboration between human intent and AI capability.

Welcome to the future of software engineering. It is not about coding less. It is
about building more.

---

## Appendix: Project File Reference

| Path | Description |
|------|-------------|
| `CLAUDE.md` | Root project context (83 lines) |
| `.claude/commands/*.md` | 11 slash commands for tutorial phases |
| `services/gateway/` | FastAPI + Strawberry GraphQL gateway |
| `services/agent-engine/` | Prefect + LangGraph agent orchestration |
| `services/document-service/` | MinIO + pgvector document service |
| `services/cache-service/` | Redis VSS semantic cache |
| `services/cost-tracker/` | OpenCost aggregation |
| `frontend/` | Next.js 14 + Tailwind + Shadcn/ui |
| `libs/py-common/` | Shared Python library (config, logging, telemetry) |
| `libs/ts-common/` | Shared TypeScript library (types, utils) |
| `infra/k8s/` | Kustomize base + overlays |
| `infra/argocd/` | Argo CD app-of-apps |
| `infra/tekton/` | Tekton CI/CD pipelines |
| `infra/policy/` | OPA Gatekeeper constraints |
| `docs/architecture/adr/` | 7 Architecture Decision Records |
| `docs/tutorial/` | Phase 0-10 tutorial documents |
| `tests/` | e2e, integration, load, chaos, security tests |
