# The Complete Tech Stack Guide: Building an Enterprise AI Agent Platform

> **Audience:** Fresh graduates and early-career engineers who want to understand how
> production AI applications are built at scale.
>
> **What you will learn:** Every layer of a modern AI platform -- from the pixels on
> screen to the GPU crunching matrix multiplications -- explained in plain language
> with real code from this repository.
>
> **How to read this:** Start with the architecture overview, then read each component
> in order. Each section is self-contained, but they build on each other. The
> "How It All Connects" section at the end ties everything together.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component 1: Frontend -- Next.js 14 + Tailwind CSS](#2-frontend----nextjs-14--tailwind-css)
3. [Component 2: Ingress -- Envoy (via Contour)](#3-ingress----envoy-via-contour)
4. [Component 3: Service Mesh -- Istio Ambient Mode](#4-service-mesh----istio-ambient-mode)
5. [Component 4: API Gateway -- FastAPI + GraphQL (Strawberry)](#5-api-gateway----fastapi--graphql-strawberry)
6. [Component 5: LLM Runtime -- vLLM on KubeRay](#6-llm-runtime----vllm-on-kuberay)
7. [Component 6: CPU Fallback -- llama.cpp Server](#7-cpu-fallback----llamacpp-server)
8. [Component 7: Vector DB -- PostgreSQL + pgvector](#8-vector-db----postgresql--pgvector)
9. [Component 8: Object Store -- MinIO (S3-compatible)](#9-object-store----minio-s3-compatible)
10. [Component 9: Cache -- Redis 7.2 with VSS Semantic Cache](#10-cache----redis-72-with-vss-semantic-cache)
11. [Component 10: Agent DAG -- Prefect 3 + LangGraph](#11-agent-dag----prefect-3--langgraph)
12. [Component 11: Feature Store -- Feast on Flink](#12-feature-store----feast-on-flink)
13. [Component 12: Observability -- OpenTelemetry to Grafana](#13-observability----opentelemetry-to-grafana)
14. [Component 13: Cost Tracking -- OpenCost](#14-cost-tracking----opencost)
15. [Component 14: GitOps -- Argo CD + Tekton](#15-gitops----argo-cd--tekton)
16. [Component 15: Policy -- OPA Gatekeeper](#16-policy----opa-gatekeeper)
17. [Component 16: Dev Loop -- DevContainer + Skaffold + mirrord](#17-dev-loop----devcontainer--skaffold--mirrord)
18. [How It All Connects: The Request Flow](#18-how-it-all-connects-the-request-flow)
19. [Glossary](#19-glossary)

---

## 1. Architecture Overview

Before diving into individual components, here is how they all fit together.
Every box below is a real piece of software running in our Kubernetes cluster.

```
                            USERS (Browser / Mobile / API Client)
                                          |
                                          v
                    +---------------------------------------------+
                    |         Contour / Envoy  (INGRESS)          |
                    |   TLS termination, routing, rate limiting   |
                    +---------------------------------------------+
                                  |               |
                   +--------------+               +--------------+
                   v                                             v
    +----------------------------+              +----------------------------+
    |   Next.js 14  (FRONTEND)   |              |   FastAPI + Strawberry     |
    |   Tailwind CSS + React     |              |   (API GATEWAY / GraphQL)  |
    |   Server Components        |              |   Schema-first API         |
    +----------------------------+              +----------------------------+
                                                     |          |
                   +---------------------------------+          |
                   |              |           |                 |
                   v              v           v                 v
    +-------------+  +---------+  +--------+  +------------------+
    | Agent Engine|  | Document|  | Cache  |  | Cost Tracker     |
    | Prefect +   |  | Service |  | Service|  | (OpenCost)       |
    | LangGraph   |  | (MinIO +|  | Redis  |  | $/inference      |
    |             |  | pgvector)|  | 7.2 VSS|  +------------------+
    +------+------+  +---------+  +--------+
           |
           |  (LLM inference calls)
           |
    +------v---------------------------+
    |  Circuit Breaker                 |
    |  +------------+  +------------+  |
    |  | vLLM on    |  | llama.cpp  |  |
    |  | KubeRay    |  | (CPU       |  |
    |  | (GPU,      |  |  fallback) |  |
    |  |  primary)  |  |            |  |
    |  +------------+  +------------+  |
    +----------------------------------+

    Cross-cutting concerns (present everywhere, not shown above for clarity):

    +------------------+  +------------------+  +------------------+
    | Istio Ambient    |  | OpenTelemetry    |  | OPA Gatekeeper   |
    | (Service Mesh)   |  | -> Grafana Stack |  | (Policy Engine)  |
    | mTLS, traffic    |  | Tempo (traces)   |  | Enforce rules on |
    | management       |  | Loki  (logs)     |  | all K8s objects  |
    +------------------+  | Mimir (metrics)  |  +------------------+
                          +------------------+

    Developer workflow:

    +------------------+  +------------------+  +------------------+
    | DevContainer     |  | Skaffold         |  | Argo CD + Tekton |
    | (local env)      |  | (K8s dev loop)   |  | (GitOps CI/CD)   |
    +------------------+  +------------------+  +------------------+
```

**Think of it like a restaurant:**

| Restaurant Analogy       | Our Platform            | Component              |
|--------------------------|-------------------------|------------------------|
| The front door & host    | Ingress                 | Contour / Envoy        |
| The dining room decor    | User Interface          | Next.js + Tailwind     |
| The menu                 | API schema              | GraphQL (Strawberry)   |
| The kitchen              | Agent Engine            | Prefect + LangGraph    |
| The head chef            | LLM (primary)           | vLLM on KubeRay       |
| The sous chef (backup)   | LLM (fallback)          | llama.cpp              |
| The recipe book          | Documents & embeddings  | pgvector + MinIO       |
| The fridge (quick access)| Cache                   | Redis VSS              |
| The ingredient prep area | Feature preparation     | Feast on Flink         |
| The security cameras     | Observability           | OTEL + Grafana         |
| The cash register        | Cost tracking           | OpenCost               |
| The supply chain         | Deployment pipeline     | Argo CD + Tekton       |
| The health inspector     | Policy enforcement      | OPA Gatekeeper         |
| The staff-only hallways  | Service-to-service sec  | Istio ambient mesh     |
| The kitchen workstation  | Developer environment   | DevContainer+Skaffold  |

Now let us go deep on each one.

---

## 2. Frontend -- Next.js 14 + Tailwind CSS

**Location in repo:** `frontend/`

### What Is It?

**Next.js** is a React framework created by Vercel. If React is the engine,
Next.js is the car -- it adds routing, server-side rendering, API routes, and
many optimizations that React alone does not provide.

Think of it like this: React lets you build interactive UI components (buttons,
forms, chat bubbles). Next.js wraps React and says "I will also handle how pages
are organized, how data is fetched, how the app is deployed, and how to make
it fast."

**Tailwind CSS** is a utility-first CSS framework. Instead of writing separate
CSS files with class names like `.chat-bubble { background: blue; padding: 8px; }`,
you write classes directly in your HTML: `className="bg-blue-500 p-2"`. It sounds
messy at first, but it is extremely productive once you learn the pattern.

### Why We Chose It

| Requirement                  | Next.js Advantage                | Alternative We Considered |
|------------------------------|----------------------------------|---------------------------|
| Server-side rendering (SEO)  | Built-in with App Router         | Create React App (no SSR) |
| File-based routing           | `/app/chat/page.tsx` = `/chat`   | React Router (manual)     |
| TypeScript-first             | Zero-config TS support           | Vite (also good, but less opinionated) |
| React Server Components      | First-class support (Next 14)    | Remix (partial support)   |
| Streaming responses          | Native streaming with Suspense   | Vue.js (possible but harder) |
| Production-grade             | Used by Netflix, TikTok, Hulu   | -                         |

For CSS, we chose Tailwind over alternatives because:

- **vs. plain CSS:** Tailwind eliminates the "naming problem" (what do I call this class?)
  and co-locates styles with markup, making components self-contained.
- **vs. CSS Modules:** Tailwind is faster to write and produces smaller CSS bundles
  (unused classes are automatically removed via PurgeCSS).
- **vs. styled-components:** No runtime CSS-in-JS overhead. Tailwind generates styles
  at build time, not in the browser.

### How It Works in Our App

Our frontend is a chat interface for interacting with AI agents. The key flow:

1. User types a message in the chat input.
2. Frontend sends a GraphQL mutation to the gateway.
3. Gateway processes the request through the agent engine.
4. Response streams back and renders in the chat window.

Here is the core chat interaction code:

```typescript
// frontend/src/app/chat/page.tsx  (simplified)

const res = await fetch(GRAPHQL_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        query: `mutation SendMessage($input: SendMessageInput!) {
            sendMessage(input: $input) {
                id role content costUsd latencyMs
                toolCalls { toolName arguments result }
            }
        }`,
        variables: { input: { agentId: agent.id, sessionId, content: text } },
    }),
});
```

**What is happening here, line by line:**

- `fetch(GRAPHQL_URL, ...)` -- We use the browser's built-in `fetch` API to make
  an HTTP POST request to our GraphQL API gateway.
- `query: \`mutation SendMessage...\`` -- This is a GraphQL mutation (a write
  operation). It tells the server "run the `sendMessage` operation."
- `variables: { input: ... }` -- GraphQL separates the query structure from the
  data. Variables are the data. This prevents injection attacks (similar to
  parameterized SQL queries).
- The response includes `costUsd` and `latencyMs` -- our platform tracks the
  cost and speed of every LLM call, which we display to the user.
- `toolCalls` -- when the AI agent uses a tool (like checking the weather), the
  tool name, arguments, and result are included in the response.

**Project structure:**

```
frontend/
  src/
    app/                    # Next.js App Router -- each folder = a route
      layout.tsx            # Root layout (shared header, sidebar)
      page.tsx              # Home page (/)
      chat/
        page.tsx            # Chat page (/chat)
    components/
      ChatMessage.tsx       # Single message bubble
      ChatInput.tsx         # Text input + send button
      AgentPicker.tsx       # Dropdown to select which agent to talk to
    lib/
      graphql.ts            # GraphQL client utilities
  tailwind.config.ts        # Tailwind configuration
  next.config.js            # Next.js configuration
```

**Tailwind in action:**

```tsx
// A chat message component
function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`
          max-w-[70%] rounded-2xl px-4 py-2 text-sm
          ${isUser
            ? "bg-blue-600 text-white rounded-br-sm"
            : "bg-gray-100 text-gray-900 rounded-bl-sm"
          }
        `}
      >
        {message.content}
        {message.costUsd && (
          <span className="block mt-1 text-xs opacity-60">
            Cost: ${message.costUsd.toFixed(4)} | {message.latencyMs}ms
          </span>
        )}
      </div>
    </div>
  );
}
```

Notice how `className` contains all the styling. `max-w-[70%]` means maximum
width 70%. `rounded-2xl` means large border radius. `px-4 py-2` means
horizontal padding 1rem and vertical padding 0.5rem. You can read Tailwind
classes left to right like a sentence describing the element's appearance.

### Key Concepts for the Interview

- **Server Components vs. Client Components:** Server Components render on the
  server and send HTML to the browser (faster initial load, better SEO). Client
  Components run in the browser and handle interactivity (clicks, typing).
  In Next.js 14, components are Server Components by default; add `"use client"`
  at the top to make them Client Components.

- **App Router:** Next.js 14's routing system. Each folder inside `app/` becomes
  a URL path. `app/chat/page.tsx` becomes `/chat`. This is called file-based
  routing.

- **Streaming:** Next.js can stream HTML to the browser as it is generated,
  instead of waiting for the entire page to render. This is critical for our
  chat app because LLM responses can take several seconds.

- **Utility-first CSS:** Tailwind's approach of using small, composable utility
  classes instead of writing custom CSS. The tradeoff is longer class attributes
  but faster development and smaller production bundles.

---

## 3. Ingress -- Envoy (via Contour)

**Location in repo:** `infra/k8s/` and `infra/helm/`

### What Is It?

When a user types `https://your-app.com` in their browser, that request needs
to reach the correct service inside your Kubernetes cluster. The **ingress
controller** is the component that receives external traffic and routes it to
the right place.

Think of it like the reception desk in a large office building. Visitors
(HTTP requests) arrive at the front door (the load balancer's public IP), and
the receptionist (ingress controller) checks their destination and directs them
to the correct floor and office (backend service).

**Envoy** is a high-performance proxy originally built at Lyft. It handles
connection management, load balancing, TLS termination, and observability at
the network edge.

**Contour** is a Kubernetes ingress controller that uses Envoy under the hood.
Contour translates Kubernetes ingress resources (YAML you write) into Envoy
configuration (complex JSON that you do not want to write by hand).

```
User's Browser
       |
       v
  [Cloud Load Balancer]   <-- Provided by your cloud (AWS ALB, GCP LB, etc.)
       |
       v
  [Contour]                <-- Reads K8s Ingress/HTTPProxy resources
       |
       v
  [Envoy Proxy Pods]       <-- Actually handles the traffic
       |
       +---> frontend (Next.js)       if path starts with /
       +---> gateway (FastAPI)        if path starts with /graphql
       +---> gateway (FastAPI)        if path starts with /api/
```

### Why We Chose It

| Requirement                 | Contour/Envoy Advantage              | Alternative              |
|-----------------------------|--------------------------------------|--------------------------|
| HTTP/2 and gRPC support     | Native in Envoy                      | nginx (requires modules) |
| Dynamic configuration       | Hot reload, no restarts              | nginx (requires reload)  |
| Observability               | Built-in metrics, tracing headers    | HAProxy (limited)        |
| Rate limiting               | Native with global rate limit service| nginx (basic module)     |
| HTTPProxy CRD               | More expressive than Ingress API     | Istio Gateway (heavier)  |
| CNCF graduated project      | Production-proven, well-maintained   | Traefik (also good)      |

The key reason: Envoy gives us fine-grained traffic control (weighted routing,
retries, circuit breaking at the edge) and deep observability (every request
gets metrics and trace headers), which are essential for a platform that needs
to be reliable and debuggable.

### How It Works in Our App

We define an HTTPProxy resource that tells Contour how to route traffic:

```yaml
# infra/k8s/base/ingress/httpproxy.yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: agent-platform
  namespace: agent-platform
spec:
  virtualhost:
    fqdn: agent-platform.local
    tls:
      secretName: agent-platform-tls
  routes:
    # GraphQL API traffic -> gateway service
    - conditions:
        - prefix: /graphql
      services:
        - name: gateway
          port: 8000
      timeoutPolicy:
        response: 60s        # LLM calls can be slow
    # Health check endpoint (used by load balancers)
    - conditions:
        - prefix: /healthz
      services:
        - name: gateway
          port: 8000
    # Everything else -> frontend
    - conditions:
        - prefix: /
      services:
        - name: frontend
          port: 3000
```

**What this means:**

- Requests to `https://agent-platform.local/graphql` go to the FastAPI gateway
  on port 8000.
- Requests to `https://agent-platform.local/` (and all other paths) go to the
  Next.js frontend on port 3000.
- TLS is terminated at the ingress layer -- Envoy handles HTTPS, and traffic
  inside the cluster is plain HTTP (Istio handles internal encryption separately).
- The `timeoutPolicy` of 60 seconds accounts for slow LLM inference calls.

**Rate limiting example:**

```yaml
# infra/k8s/base/ingress/ratelimit.yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: agent-platform
spec:
  routes:
    - conditions:
        - prefix: /graphql
      rateLimitPolicy:
        local:
          requests: 100
          unit: minute
      services:
        - name: gateway
          port: 8000
```

This limits each client to 100 GraphQL requests per minute, preventing a single
user from overwhelming the system or running up GPU costs.

### Key Concepts for the Interview

- **Ingress vs. Load Balancer:** A load balancer distributes traffic across
  multiple servers. An ingress controller is a specialized load balancer that
  understands HTTP -- it can route based on URL paths, hostnames, and headers.

- **TLS Termination:** Decrypting HTTPS at the edge so internal services do not
  need to handle certificates. The ingress proxy holds the TLS certificate and
  forwards plain HTTP internally.

- **L4 vs. L7 Proxy:** L4 (transport layer) proxies forward TCP connections
  without understanding the content. L7 (application layer) proxies understand
  HTTP and can make routing decisions based on URLs, headers, and cookies.
  Envoy is an L7 proxy.

- **Hot Reload:** Envoy can update its routing configuration without restarting.
  This means you can deploy new services or change routes without dropping any
  active connections.

---

## 4. Service Mesh -- Istio Ambient Mode

**Location in repo:** `infra/k8s/base/istio/`, `infra/helm/istio/`

### What Is It?

A service mesh is an infrastructure layer that manages communication between
your microservices. It handles encryption, retries, timeouts, load balancing,
and traffic policies -- all without changing your application code.

Think of it like the postal system in a city. Your services are buildings that
need to send letters (requests) to each other. Without a postal system, each
building would need to figure out routes, handle lost mail, and verify
identities on its own. The service mesh is the postal system: it picks up mail,
routes it, retries failed deliveries, and ensures only authorized buildings can
communicate.

**Istio** is the most widely adopted service mesh. Traditionally, it works by
injecting a "sidecar" proxy container (Envoy) into every pod. This sidecar
intercepts all network traffic and applies policies.

**Ambient mode** is Istio's newer, sidecar-less architecture. Instead of adding
a proxy to every pod, it uses:

- A **ztunnel** (zero-trust tunnel) DaemonSet on each node for L4 encryption
  (mTLS).
- Optional **waypoint proxies** for L7 features (retries, traffic splitting).

```
Traditional Istio (sidecar):          Istio Ambient (sidecar-less):

+------------------+                  +------------------+
| Pod              |                  | Pod              |
| +------+ +-----+|                  | +------+         |
| | App  | |Envoy||                  | | App  |         |
| +------+ +-----+|                  | +------+         |
+------------------+                  +------------------+
                                            |
                                      +-----v-----+
                                      | ztunnel   |  (shared per node)
                                      | (DaemonSet)|
                                      +-----------+
```

### Why We Chose It

| Requirement                    | Istio Ambient Advantage           | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| Zero-trust networking (mTLS)   | Automatic, no code changes        | Manual cert management   |
| No sidecar overhead            | Ambient mode = no extra containers| Linkerd (lighter but less features) |
| Traffic management             | Canary deployments, fault injection| App-level retries (fragile) |
| Authorization policies         | Declarative YAML                  | Custom middleware         |
| Industry standard              | Most adopted mesh, huge community | Cilium mesh (newer)      |

**Why ambient mode specifically:** In a platform that runs GPU workloads,
memory matters. Traditional Istio sidecars add ~50MB of memory per pod. With
50 pods, that is 2.5GB wasted on proxies. Ambient mode eliminates this
overhead by sharing a single ztunnel per node.

### How It Works in Our App

**Enabling ambient mode for our namespace:**

```yaml
# infra/k8s/base/istio/namespace-label.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: agent-platform
  labels:
    istio.io/dataplane-mode: ambient    # This single label enables the mesh
```

That is it. One label, and all pods in the namespace get automatic mTLS
encryption. No sidecars, no code changes.

**Authorization policy (who can talk to whom):**

```yaml
# infra/k8s/base/istio/auth-policy.yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: gateway-to-agent-engine
  namespace: agent-platform
spec:
  selector:
    matchLabels:
      app: agent-engine
  action: ALLOW
  rules:
    - from:
        - source:
            principals:
              - "cluster.local/ns/agent-platform/sa/gateway"
      to:
        - operation:
            methods: ["POST"]
            paths: ["/api/*"]
```

**In plain English:** Only the gateway service account is allowed to make POST
requests to the agent-engine's `/api/*` endpoints. If the cache-service or any
other service tries to call the agent-engine directly, Istio blocks it.

**Traffic splitting for canary deployments:**

```yaml
# infra/k8s/overlays/canary/virtual-service.yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: gateway
spec:
  hosts:
    - gateway
  http:
    - route:
        - destination:
            host: gateway
            subset: stable
          weight: 90
        - destination:
            host: gateway
            subset: canary
          weight: 10
```

This sends 90% of traffic to the stable version and 10% to the canary (new
version). If the canary has errors, you shift traffic back to 100% stable
without any downtime.

### Key Concepts for the Interview

- **mTLS (Mutual TLS):** Both sides of a connection verify each other's
  identity using certificates. In a service mesh, this happens automatically.
  Every service gets a certificate, and all traffic is encrypted.

- **Zero-trust networking:** Never trust, always verify. Even inside your
  cluster, services must prove their identity before communicating. This
  prevents lateral movement if an attacker compromises one service.

- **Sidecar vs. Ambient:** Sidecar = one proxy per pod (more isolation, more
  overhead). Ambient = shared proxy per node (less overhead, slightly less
  isolation). Ambient is the future of Istio.

- **Canary deployment:** Gradually rolling out a new version to a small
  percentage of users before rolling it out to everyone. The service mesh
  makes this trivial with traffic splitting.

---

## 5. API Gateway -- FastAPI + GraphQL (Strawberry)

**Location in repo:** `services/gateway/`

### What Is It?

The API gateway is the single entry point for all client requests to your
backend services. Instead of the frontend talking to 5 different microservices
directly, it talks to one gateway that routes requests to the right service.

**FastAPI** is a modern Python web framework that is both fast (built on ASGI,
comparable to Node.js and Go performance) and fast to develop with (automatic
OpenAPI docs, type validation via Pydantic).

**GraphQL** is a query language for APIs (invented at Facebook in 2012, open-
sourced in 2015). Unlike REST, where the server decides what data to return,
GraphQL lets the client specify exactly which fields it needs.

**Strawberry** is a Python library for building GraphQL APIs using Python type
hints. It is the GraphQL equivalent of what FastAPI did for REST APIs -- making
Python's type system the source of truth.

Think of it like ordering at a restaurant:

- **REST API** = a fixed menu. You order "Combo #3" and get a burger, fries,
  and a drink, even if you only wanted the burger. Each combo is a different
  endpoint (`/api/users`, `/api/orders`).

- **GraphQL** = an a-la-carte menu. You say exactly what you want: "I want the
  user's name and their last 3 orders, but only the order totals." One endpoint,
  flexible queries.

### Why We Chose It

| Requirement                     | Our Choice Advantage              | Alternative               |
|---------------------------------|-----------------------------------|---------------------------|
| Python ecosystem (LLM libs)     | FastAPI is Python-native          | Express.js (Node.js)      |
| Type safety                     | Pydantic + Strawberry types       | Flask (untyped)           |
| Flexible data fetching          | GraphQL (client picks fields)     | REST (over/under-fetching)|
| Auto-generated docs             | FastAPI + GraphQL Playground       | Manual Swagger/OpenAPI    |
| Async support                   | FastAPI is async-first (ASGI)     | Django (WSGI, sync)       |
| Schema-first design             | Strawberry code = the schema      | graphene (verbose)        |

**Why GraphQL over REST for an AI platform:**

Our chat responses include many optional fields: `content`, `toolCalls`,
`costUsd`, `latencyMs`, `modelUsed`, etc. With REST, you would either:
1. Return everything always (wasteful on mobile), or
2. Create multiple endpoints like `/api/messages?fields=content,cost` (ugly).

With GraphQL, the frontend asks for exactly what it needs. The chat list view
might request only `id`, `role`, and `content`. The admin dashboard might
request `costUsd`, `latencyMs`, and `modelUsed`. Same endpoint, different queries.

### How It Works in Our App

**The GraphQL schema (the contract between frontend and backend):**

```python
# services/gateway/src/gateway/schema.py

import strawberry
from uuid import UUID
from datetime import datetime
from enum import Enum

@strawberry.enum
class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

@strawberry.type
class ToolCall:
    tool_name: str
    arguments: str        # JSON string of the arguments
    result: str | None    # JSON string of the tool's response

@strawberry.type
class ChatMessage:
    id: UUID
    role: MessageRole
    content: str
    tool_calls: list[ToolCall] | None = None
    cost_usd: float | None = None
    latency_ms: float | None = None
    created_at: datetime

@strawberry.input
class SendMessageInput:
    agent_id: UUID
    session_id: UUID | None = None
    content: str
```

**Why this matters:** Each `@strawberry.type` class becomes a GraphQL type.
Each `@strawberry.input` becomes a GraphQL input type. The Python type hints
(`str`, `UUID`, `float | None`) are automatically converted to GraphQL types
(`String!`, `ID!`, `Float`). The schema is your Python code -- there is no
separate `.graphql` file to keep in sync.

**The mutation resolver (what happens when a message is sent):**

```python
# services/gateway/src/gateway/schema.py (continued)

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def send_message(self, input: SendMessageInput) -> ChatMessage:
        """Send a message to an agent and get a response."""
        # 1. Create or retrieve the session
        session = await get_or_create_session(input.agent_id, input.session_id)

        # 2. Forward to the agent engine service
        response = await agent_engine_client.send_message(
            agent_id=input.agent_id,
            session_id=session.id,
            content=input.content,
        )

        # 3. Return the structured response
        return ChatMessage(
            id=response.id,
            role=MessageRole.ASSISTANT,
            content=response.content,
            tool_calls=[
                ToolCall(
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    result=tc.result,
                )
                for tc in response.tool_calls
            ] if response.tool_calls else None,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
            created_at=response.created_at,
        )
```

**The FastAPI application (wiring it all together):**

```python
# services/gateway/src/gateway/main.py

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from gateway.schema import schema

app = FastAPI(title="Agent Platform Gateway")
graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")

@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}

@app.get("/readyz")
async def readyz():
    # Check dependencies (database, redis, etc.)
    return {"status": "ready"}
```

**The 12-factor configuration (environment-driven settings):**

```python
# libs/py-common/src/agent_platform_common/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "agent-platform"
    database_url: str = "postgresql://..."
    redis_url: str = "redis://localhost:6379/0"
    llm_primary_url: str = "http://localhost:11434/v1"
    llm_fallback_url: str = "http://localhost:8080/v1"
    llm_model: str = "llama3.1:8b"
```

**What is "12-factor"?** The [Twelve-Factor App](https://12factor.net/) is a
methodology for building software-as-a-service. Factor #3 says "store config
in the environment." Pydantic Settings reads environment variables
automatically: set `DATABASE_URL=postgresql://prod-server:5432/mydb` as an
environment variable, and `settings.database_url` picks it up. This means the
same code runs in dev, staging, and production with zero changes -- only the
environment variables change.

### Key Concepts for the Interview

- **Schema-first vs. code-first:** Schema-first means you define the GraphQL
  schema in a `.graphql` file and generate code. Code-first (our approach with
  Strawberry) means you write Python code and the schema is generated from it.
  Code-first is better for Python teams because you get type checking for free.

- **Resolvers:** Functions that "resolve" (compute) the value of a GraphQL
  field. When a client queries `{ chatMessage { content toolCalls } }`, two
  resolvers run: one for `content` and one for `toolCalls`.

- **N+1 problem:** A common GraphQL pitfall. If you query 50 messages and each
  message has a `user` field, a naive implementation makes 1 query for messages
  + 50 queries for users = 51 queries. The fix is **DataLoader** (batching).

- **ASGI vs. WSGI:** WSGI is synchronous (one request at a time per worker).
  ASGI is asynchronous (handles many concurrent requests in one process). FastAPI
  uses ASGI, which is essential for an AI platform where LLM calls take seconds.

---

## 6. LLM Runtime -- vLLM on KubeRay

**Location in repo:** `infra/k8s/base/vllm/`, `infra/helm/kuberay/`

### What Is It?

An **LLM runtime** is the software that loads a large language model into memory
(usually GPU memory) and serves inference requests (you send text in, it sends
text out).

**vLLM** (pronounced "v-L-L-M") is an open-source LLM serving engine developed
at UC Berkeley. Its key innovation is **PagedAttention**, which manages GPU
memory like an operating system manages RAM pages. This allows vLLM to serve
2-4x more concurrent requests than naive implementations.

Think of GPU memory like seats in a movie theater. Naive serving reserves an
entire row for each viewer, even if they only need one seat. vLLM says "sit
wherever there is an empty seat" and dynamically manages the seating chart.

**KubeRay** is the Kubernetes operator for Ray, a distributed computing
framework. It lets you run Ray clusters on Kubernetes, which enables:
- Auto-scaling GPU workers based on request queue depth.
- Distributed inference across multiple GPUs.
- Fault tolerance (if a GPU node dies, Ray reschedules work).

```
                   +---------------------------+
                   |       KubeRay Cluster      |
                   |                           |
                   |  +-------+   +-------+    |
  Inference   ---->|  | vLLM  |   | vLLM  |    |
  Requests         |  | GPU 0 |   | GPU 1 |    |
                   |  +-------+   +-------+    |
                   |                           |
                   |  Ray Head (coordination)  |
                   +---------------------------+
```

### Why We Chose It

| Requirement                    | vLLM Advantage                    | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| Throughput (tokens/second)     | PagedAttention = 2-4x better      | HuggingFace TGI          |
| OpenAI-compatible API          | Drop-in replacement for OpenAI    | Ollama (simpler but slower)|
| Continuous batching            | Serves new requests without waiting| TensorRT-LLM (NVIDIA-only)|
| Multi-GPU support              | Tensor parallelism built-in       | llama.cpp (single GPU)   |
| Kubernetes-native scaling      | KubeRay handles auto-scaling      | Manual scaling           |

### How It Works in Our App

**KubeRay cluster definition:**

```yaml
# infra/k8s/base/vllm/ray-cluster.yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: vllm-cluster
  namespace: agent-platform
spec:
  headGroupSpec:
    replicas: 1
    template:
      spec:
        containers:
          - name: ray-head
            image: vllm/vllm-openai:latest
            command: ["/bin/bash", "-c"]
            args:
              - |
                vllm serve meta-llama/Llama-3.1-8B-Instruct \
                  --host 0.0.0.0 \
                  --port 8000 \
                  --max-model-len 4096 \
                  --gpu-memory-utilization 0.9 \
                  --enable-auto-tool-choice \
                  --tool-call-parser llama3_json
            resources:
              limits:
                nvidia.com/gpu: 1
                memory: "16Gi"
              requests:
                nvidia.com/gpu: 1
                memory: "16Gi"
```

**What the flags mean:**

- `--max-model-len 4096`: Maximum sequence length (input + output tokens).
  Longer = more memory. 4096 tokens is about 3000 words.
- `--gpu-memory-utilization 0.9`: Use 90% of GPU memory for model weights
  and KV cache. The remaining 10% is a safety buffer.
- `--enable-auto-tool-choice`: Enable the model to use function calling
  (tools), which is how our agents invoke tools like `get_weather`.
- `--tool-call-parser llama3_json`: Parse tool calls in Llama 3's JSON format.

**Exposing vLLM as a Kubernetes Service:**

```yaml
# infra/k8s/base/vllm/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm
  namespace: agent-platform
spec:
  selector:
    app: vllm
  ports:
    - port: 8000
      targetPort: 8000
      name: http
```

Now any service in the cluster can call `http://vllm:8000/v1/chat/completions`
-- exactly the same API as OpenAI. This is why our `LLMClient` uses the
`openai` Python library to talk to vLLM:

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="http://vllm:8000/v1",   # vLLM, not OpenAI
    api_key="not-needed",              # Local model, no API key
)

response = await client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[{"role": "user", "content": "What is the weather in Tokyo?"}],
    tools=weather_agent.available_tools,
    temperature=0.7,
)
```

### Key Concepts for the Interview

- **PagedAttention:** The key innovation in vLLM. It breaks the KV cache
  (attention key-value pairs) into fixed-size "pages" that can be allocated
  non-contiguously in GPU memory. This eliminates memory fragmentation and
  allows more concurrent sequences.

- **KV Cache:** During inference, the model caches attention keys and values
  for previously generated tokens so it does not recompute them. This cache
  grows linearly with sequence length and is the main GPU memory consumer.

- **Continuous Batching:** Traditional batching waits for a batch of requests
  to finish before starting new ones. Continuous batching starts new requests
  as soon as any request in the current batch finishes, improving GPU
  utilization from ~50% to ~90%.

- **Tensor Parallelism:** Splitting a model across multiple GPUs. If a model
  needs 32GB and each GPU has 16GB, tensor parallelism splits the model weights
  across 2 GPUs and coordinates the computation.

---

## 7. CPU Fallback -- llama.cpp Server

**Location in repo:** `infra/k8s/base/llamacpp/`

### What Is It?

**llama.cpp** is a C/C++ implementation of LLM inference that runs efficiently
on CPUs. It was created by Georgi Gerganov and has become the standard for
running language models without GPUs.

Think of vLLM as a Formula 1 car (fast, needs specialized fuel/track) and
llama.cpp as a reliable Toyota (slower, but runs on any road with any fuel).
In production, you want both: the F1 car for normal operation and the Toyota
as a backup when the F1 car is in the pit.

### Why We Chose It

| Requirement                    | llama.cpp Advantage               | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| No GPU required                | Pure CPU inference                | Ollama (uses llama.cpp internally) |
| Low memory footprint           | Quantized models (Q4_K_M = ~5GB) | vLLM (needs full precision) |
| OpenAI-compatible API          | Built-in `/v1/chat/completions`   | Custom wrapper           |
| Fast startup                   | Seconds vs. minutes for vLLM      | TensorRT-LLM (slow init) |
| Quantization support           | GGUF format, many quant levels    | GPTQ (GPU-only)          |

**Why a CPU fallback matters in production:**

GPUs fail. GPU nodes get preempted (in cloud environments). GPU drivers crash.
GPU memory runs out. When any of these happen, your AI platform should degrade
gracefully (slower responses) rather than fail completely (no responses). The
CPU fallback ensures users always get an answer, even if it takes 10 seconds
instead of 1 second.

### How It Works in Our App

The magic is in the **Circuit Breaker pattern**, which automatically switches
between vLLM (primary/GPU) and llama.cpp (fallback/CPU):

```python
# services/agent-engine/src/agent_engine/llm_client.py

class CircuitBreaker:
    """
    Three states:
      CLOSED   -> Primary works normally, all traffic goes to primary.
      OPEN     -> After 3 consecutive failures, ALL traffic goes to fallback
                  for 30 seconds (giving primary time to recover).
      HALF_OPEN -> After 30s, send ONE request to primary to test if it
                   recovered. If it succeeds -> CLOSED. If it fails -> OPEN.
    """

    def __init__(self, failure_threshold=3, recovery_timeout=30):
        self._state = "CLOSED"
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._last_failure_time = None

    @property
    def should_use_primary(self) -> bool:
        if self._state == "CLOSED":
            return True
        if self._state == "OPEN":
            if time.time() - self._last_failure_time > self._recovery_timeout:
                self._state = "HALF_OPEN"
                return True
            return False
        if self._state == "HALF_OPEN":
            return True
        return False

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._failure_threshold:
            self._state = "OPEN"

    def record_success(self):
        self._state = "CLOSED"
        self._failure_count = 0


class LLMClient:
    def __init__(self, primary_url, fallback_url, model):
        self._primary = AsyncOpenAI(base_url=primary_url, api_key="not-needed")
        self._fallback = AsyncOpenAI(base_url=fallback_url, api_key="not-needed")
        self._circuit = CircuitBreaker()

    async def chat(self, messages, temperature=0.7, max_tokens=1024, tools=None):
        if self._circuit.should_use_primary:
            try:
                result = await self._call(self._primary, messages,
                                          temperature, max_tokens, tools)
                self._circuit.record_success()
                return result
            except Exception:
                self._circuit.record_failure()

        # Fallback attempt (CPU)
        return await self._call(self._fallback, messages,
                                temperature, max_tokens, tools)
```

**The state machine visualized:**

```
                  success
            +<--------------+
            |                |
            v                |
  +--------+------+   +-----------+
  |    CLOSED     |   | HALF_OPEN |
  | (use primary) |   | (test 1   |
  +-------+-------+   |  request) |
          |            +-----+-----+
          | 3 failures       ^
          v                  | 30s elapsed
  +-------+-------+         |
  |     OPEN      +---------+
  | (use fallback)|
  +---------------+
          failure -> stays OPEN, resets 30s timer
```

**llama.cpp Kubernetes deployment:**

```yaml
# infra/k8s/base/llamacpp/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llamacpp
  namespace: agent-platform
spec:
  replicas: 2          # Always have 2 replicas ready
  selector:
    matchLabels:
      app: llamacpp
  template:
    spec:
      containers:
        - name: llamacpp
          image: ghcr.io/ggerganov/llama.cpp:server
          args:
            - "--model"
            - "/models/llama-3.1-8b-instruct-q4_k_m.gguf"
            - "--host"
            - "0.0.0.0"
            - "--port"
            - "8080"
            - "--ctx-size"
            - "4096"
            - "--n-gpu-layers"
            - "0"          # 0 = pure CPU
            - "--threads"
            - "4"
          resources:
            limits:
              memory: "8Gi"
              cpu: "4"
            requests:
              memory: "6Gi"
              cpu: "2"
```

**Key differences from the vLLM deployment:**

- No `nvidia.com/gpu` resource requests -- this runs on any CPU node.
- Uses a quantized model (`q4_k_m` = 4-bit quantization with k-means, medium
  quality). The original 16GB model fits in ~5GB.
- `--n-gpu-layers 0` explicitly disables GPU offloading.
- `--threads 4` uses 4 CPU threads for matrix multiplication.

### Key Concepts for the Interview

- **Circuit Breaker Pattern:** Borrowed from electrical engineering. When a
  circuit detects a fault, it "opens" to prevent further damage. In software,
  when a service fails repeatedly, the circuit breaker stops sending traffic
  to it and uses a fallback. After a timeout, it sends one test request to
  check if the service recovered.

- **Quantization:** Reducing the precision of model weights from 16-bit
  floats to 4-bit integers. This makes the model ~4x smaller and faster,
  with a small quality loss. `Q4_K_M` is a popular choice that balances size
  and quality.

- **GGUF format:** The file format used by llama.cpp for quantized models.
  It contains the model weights, tokenizer, and metadata in a single file.

- **Graceful Degradation:** A system design principle where the system
  continues to function (possibly with reduced quality) when a component
  fails, rather than failing completely.

---

## 8. Vector DB -- PostgreSQL + pgvector

**Location in repo:** `services/document-service/`, `infra/k8s/base/postgres/`

### What Is It?

A **vector database** stores and searches high-dimensional vectors (lists of
numbers). In AI applications, text is converted into vectors (called
**embeddings**) that capture semantic meaning. Similar texts have vectors that
are close together in space.

Think of it like a library, but instead of organizing books by the Dewey
Decimal System (categories), you organize them by meaning. If someone asks
"How do I make pasta?", the vector search finds documents about pasta recipes,
Italian cooking, and noodle preparation -- even if they do not contain the
exact word "pasta."

**PostgreSQL** is the world's most advanced open-source relational database.
It has been around since 1986 and is trusted by virtually every Fortune 500
company.

**pgvector** is a PostgreSQL extension that adds vector data types and
similarity search operations. It turns PostgreSQL into a vector database
without needing a separate system.

### Why We Chose It

| Requirement                    | pgvector Advantage                | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| Operational simplicity         | One database for everything       | Pinecone (separate service) |
| SQL + vectors together         | JOIN vectors with metadata        | Weaviate (separate query lang) |
| ACID transactions              | PostgreSQL's guarantees           | Milvus (eventual consistency) |
| Cost                           | Free, open-source, self-hosted    | Pinecone ($70/month minimum) |
| Existing tooling               | pgAdmin, pg_dump, replication     | Qdrant (new tooling to learn) |
| Production proven              | PostgreSQL is battle-tested       | ChromaDB (not production-ready) |

**The key insight:** Most AI applications also need relational data (users,
sessions, billing). By using pgvector, you get vectors AND relational data
in one database. No need to sync data between two systems.

### How It Works in Our App

**Schema for document embeddings:**

```sql
-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table with vector embeddings
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),     -- 1536-dimensional vector (OpenAI ada-002 size)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create an index for fast similarity search
-- IVFFlat = Inverted File with Flat compression
-- lists = 100 means 100 clusters (sqrt of expected row count)
CREATE INDEX ON documents
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

**What `vector(1536)` means:** Each document is represented by a list of
1536 floating-point numbers. These numbers are computed by an embedding model
(like OpenAI's text-embedding-ada-002) and capture the semantic meaning of
the text. Two documents about similar topics will have similar vectors.

**Similarity search in Python:**

```python
# services/document-service/src/document_service/search.py

async def search_similar_documents(
    query_embedding: list[float],
    limit: int = 5,
    similarity_threshold: float = 0.7,
) -> list[Document]:
    """Find documents similar to the query embedding."""
    result = await db.fetch_all(
        """
        SELECT id, title, content, metadata,
               1 - (embedding <=> :query_embedding::vector) AS similarity
        FROM documents
        WHERE 1 - (embedding <=> :query_embedding::vector) > :threshold
        ORDER BY embedding <=> :query_embedding::vector
        LIMIT :limit
        """,
        {
            "query_embedding": str(query_embedding),
            "threshold": similarity_threshold,
            "limit": limit,
        },
    )
    return [Document(**row) for row in result]
```

**What the `<=>` operator does:** This is the cosine distance operator from
pgvector. Cosine distance measures the angle between two vectors:
- Distance 0 = identical direction (same meaning).
- Distance 1 = perpendicular (unrelated meaning).
- Distance 2 = opposite direction (opposite meaning).

We compute similarity as `1 - distance`, so:
- Similarity 1.0 = identical.
- Similarity 0.7 = somewhat related (our threshold).
- Similarity 0.0 = unrelated.

**The RAG (Retrieval-Augmented Generation) flow:**

```
User asks: "How do I deploy to Kubernetes?"
    |
    v
1. Convert question to embedding vector (1536 floats)
    |
    v
2. Search pgvector for similar documents
   (finds: "K8s deployment guide", "kubectl tutorial", "pod scheduling docs")
    |
    v
3. Include retrieved documents as context in the LLM prompt:
   "Based on these documents: [K8s deployment guide...], answer: How do I
    deploy to Kubernetes?"
    |
    v
4. LLM generates an answer grounded in your actual documentation
```

### Key Concepts for the Interview

- **Embeddings:** Dense vector representations of text that capture semantic
  meaning. Created by embedding models (neural networks trained on billions of
  text pairs). Similar concepts have similar embeddings.

- **Cosine Similarity:** Measures the angle between two vectors, ignoring
  magnitude. Used because document length should not affect similarity -- a
  short paragraph about cooking and a long essay about cooking should still be
  "similar."

- **IVFFlat Index:** An approximate nearest neighbor (ANN) index. It clusters
  vectors into groups (the "lists" parameter) and only searches the most
  relevant clusters during a query. This trades a small amount of accuracy
  for a large speed improvement (exact search is O(n); IVFFlat is O(sqrt(n))).

- **RAG (Retrieval-Augmented Generation):** A pattern where you retrieve
  relevant documents from a vector database and include them in the LLM
  prompt. This gives the LLM access to current, domain-specific knowledge
  without retraining.

- **HNSW vs. IVFFlat:** Two indexing strategies. IVFFlat is faster to build
  but slower to query. HNSW (Hierarchical Navigable Small World) is slower to
  build but faster to query. For our workload (more reads than writes), HNSW
  would be slightly better in production.

---

## 9. Object Store -- MinIO (S3-compatible)

**Location in repo:** `services/document-service/`, `infra/k8s/base/minio/`

### What Is It?

An **object store** is a storage system designed for unstructured data: files,
images, PDFs, model weights, backups. Unlike a file system (which organizes
data in directories) or a database (which organizes data in rows and columns),
an object store organizes data as flat objects in buckets.

**Amazon S3** (Simple Storage Service) is the standard for object storage in
the cloud. It stores trillions of objects for millions of applications.

**MinIO** is an open-source, S3-compatible object store that you can run
anywhere: on your laptop, in your data center, or in Kubernetes. It speaks the
same API as S3, so any code written for S3 works with MinIO (and vice versa).

Think of it like a warehouse with numbered lockers. Each locker (object) has a
unique key (name), and lockers are organized into sections (buckets). You do
not care which physical shelf the locker is on -- you just need the key to
retrieve it.

### Why We Chose It

| Requirement                    | MinIO Advantage                   | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| S3 compatibility               | Drop-in, use `boto3` / AWS SDK    | Ceph (heavier, more complex) |
| Run anywhere                   | Laptop, VM, or Kubernetes         | AWS S3 (cloud-only)      |
| No cloud dependency            | Self-hosted, no vendor lock-in    | Google Cloud Storage     |
| Simple deployment              | Single binary or container        | Ceph (needs 3+ nodes)   |
| Performance                    | Optimized for modern hardware     | GlusterFS (slower for small files) |

### How It Works in Our App

We use MinIO to store:

1. **Uploaded documents** (PDFs, text files) before they are processed and
   embedded.
2. **Model artifacts** (quantized model files, tokenizer configs).
3. **Agent conversation exports** (for compliance and debugging).

```python
# services/document-service/src/document_service/storage.py

import boto3
from botocore.config import Config

class ObjectStorage:
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str):
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,       # http://minio:9000
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
        )

    async def upload_document(self, bucket: str, key: str, data: bytes) -> str:
        """Upload a document and return its URL."""
        self._client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType="application/pdf",
        )
        return f"s3://{bucket}/{key}"

    async def download_document(self, bucket: str, key: str) -> bytes:
        """Download a document by bucket and key."""
        response = self._client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    async def list_documents(self, bucket: str, prefix: str = "") -> list[str]:
        """List all document keys in a bucket with optional prefix filter."""
        response = self._client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return [obj["Key"] for obj in response.get("Contents", [])]
```

**Notice:** We use `boto3`, the standard AWS SDK for Python. The only
difference from using real S3 is the `endpoint_url` parameter -- instead of
pointing to `https://s3.amazonaws.com`, it points to our local MinIO instance.
If we ever migrate to AWS, we just change one URL.

**MinIO Kubernetes deployment:**

```yaml
# infra/k8s/base/minio/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
  namespace: agent-platform
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: minio
          image: minio/minio:latest
          command: ["minio", "server", "/data", "--console-address", ":9001"]
          ports:
            - containerPort: 9000    # S3 API
              name: api
            - containerPort: 9001    # Web console (admin UI)
              name: console
          env:
            - name: MINIO_ROOT_USER
              valueFrom:
                secretKeyRef:
                  name: minio-credentials
                  key: root-user
            - name: MINIO_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: minio-credentials
                  key: root-password
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: minio-data    # 50Gi persistent volume
```

### Key Concepts for the Interview

- **Object Store vs. File System vs. Database:** File systems are hierarchical
  (directories inside directories). Databases store structured data (rows and
  columns). Object stores are flat (buckets and objects) and optimized for large
  blobs of unstructured data.

- **S3 API Compatibility:** S3's API has become a de facto standard. If a
  storage system is "S3-compatible," it means any tool built for AWS S3 works
  with it. This prevents vendor lock-in.

- **Buckets and Keys:** A bucket is a top-level container (like a folder). A
  key is the unique name of an object within a bucket. Together,
  `s3://my-bucket/documents/report.pdf` uniquely identifies an object.

- **Presigned URLs:** A temporary, signed URL that grants time-limited access
  to a private object. Used when you want the browser to download a file
  directly from MinIO without routing through your application server.

---

## 10. Cache -- Redis 7.2 with VSS Semantic Cache

**Location in repo:** `services/cache-service/`, `infra/k8s/base/redis/`

### What Is It?

A **cache** is a fast, temporary storage layer that sits between your
application and slower storage (database, LLM inference). It stores frequently
accessed data so you do not have to recompute or re-fetch it.

**Redis** (Remote Dictionary Server) is an in-memory data structure store. It
keeps all data in RAM, making reads/writes sub-millisecond. It is the most
popular caching solution in the world.

**VSS (Vector Similarity Search)** is a Redis module (available since Redis
7.2 via RediSearch) that enables similarity search on vectors, just like
pgvector but in memory. This lets us build a **semantic cache**.

Think of it like this: A regular cache is a dictionary. You look up "What is
the capital of France?" and get "Paris." But if someone asks "What's France's
capital city?" -- a slightly different wording -- the cache misses.

A **semantic cache** understands meaning. It converts questions to vectors
and checks if any cached question is semantically similar. "What is the
capital of France?" and "What's France's capital city?" have nearly identical
vectors, so the cache hits, and you skip the expensive LLM call entirely.

```
Regular Cache:                          Semantic Cache:

"capital of France?" -> "Paris"  HIT    "capital of France?" -> "Paris"  HIT
"France's capital?"  -> ???     MISS    "France's capital?"  -> "Paris"  HIT
                                        (vectors are similar = cache hit!)
```

### Why We Chose It

| Requirement                    | Redis VSS Advantage               | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| Sub-millisecond latency        | In-memory, single-digit us        | Memcached (no vectors)   |
| Semantic similarity search     | Built-in VSS module               | Separate vector DB       |
| Data structures                | Lists, sets, hashes, sorted sets  | Memcached (key-value only) |
| Pub/sub messaging              | Built-in for real-time updates    | RabbitMQ (separate system) |
| Session storage                | TTL support, atomic operations    | DynamoDB (cloud-only)    |

**Why semantic caching matters for cost:**

Each LLM inference call costs time (1-10 seconds) and money (compute costs).
If 30% of questions are semantically similar to previous questions, the semantic
cache eliminates 30% of LLM calls. At scale, this saves thousands of dollars
per month.

### How It Works in Our App

```python
# services/cache-service/src/cache_service/semantic_cache.py

import redis
import numpy as np
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query

class SemanticCache:
    def __init__(self, redis_url: str, similarity_threshold: float = 0.92):
        self._redis = redis.from_url(redis_url)
        self._threshold = similarity_threshold
        self._index_name = "semantic_cache_idx"
        self._ensure_index()

    def _ensure_index(self):
        """Create the vector search index if it doesn't exist."""
        try:
            self._redis.ft(self._index_name).info()
        except redis.ResponseError:
            schema = (
                TextField("$.prompt", as_name="prompt"),
                TextField("$.response", as_name="response"),
                VectorField(
                    "$.embedding",
                    "FLAT",                 # FLAT = brute force (fast for <100k vectors)
                    {
                        "TYPE": "FLOAT32",
                        "DIM": 1536,        # Embedding dimension
                        "DISTANCE_METRIC": "COSINE",
                    },
                    as_name="embedding",
                ),
            )
            self._redis.ft(self._index_name).create_index(
                schema,
                definition=IndexDefinition(
                    prefix=["cache:"],
                    index_type=IndexType.JSON,
                ),
            )

    async def get(self, query_embedding: list[float]) -> str | None:
        """Check if a semantically similar prompt was cached."""
        query_vector = np.array(query_embedding, dtype=np.float32).tobytes()

        q = (
            Query("*=>[KNN 1 @embedding $vec AS score]")
            .return_fields("prompt", "response", "score")
            .dialect(2)
        )
        results = self._redis.ft(self._index_name).search(
            q, query_params={"vec": query_vector}
        )

        if results.total > 0:
            best = results.docs[0]
            similarity = 1 - float(best.score)  # Convert distance to similarity
            if similarity >= self._threshold:
                return best.response    # Cache HIT

        return None  # Cache MISS

    async def put(self, prompt: str, response: str, embedding: list[float]):
        """Store a prompt-response pair with its embedding."""
        import uuid
        key = f"cache:{uuid.uuid4()}"
        self._redis.json().set(key, "$", {
            "prompt": prompt,
            "response": response,
            "embedding": embedding,
        })
        # Auto-expire after 1 hour
        self._redis.expire(key, 3600)
```

**The flow in the agent engine:**

```python
# Pseudocode showing how semantic cache integrates with LLM calls

async def handle_user_message(prompt: str) -> str:
    # 1. Convert prompt to embedding
    embedding = await embed(prompt)

    # 2. Check semantic cache
    cached = await semantic_cache.get(embedding)
    if cached:
        logger.info("Semantic cache HIT -- skipping LLM call")
        return cached

    # 3. Cache miss -- call the LLM
    response = await llm_client.chat(messages=[{"role": "user", "content": prompt}])

    # 4. Store in cache for future similar queries
    await semantic_cache.put(prompt, response.content, embedding)

    return response.content
```

### Key Concepts for the Interview

- **Cache Hit vs. Cache Miss:** A hit means the data was found in the cache
  (fast). A miss means it was not found and must be fetched from the source
  (slow). Cache hit rate is a key metric -- above 80% is good.

- **TTL (Time to Live):** How long a cache entry exists before being
  automatically deleted. We use 1 hour for semantic cache entries because LLM
  knowledge does not change frequently, but we want entries to eventually expire
  to avoid serving stale information.

- **Semantic Cache vs. Exact Cache:** Exact cache requires the exact same key.
  Semantic cache uses vector similarity, so slightly different phrasings of the
  same question can hit the cache. This dramatically improves hit rates for
  natural language queries.

- **Cosine Similarity Threshold:** We use 0.92, meaning the cached prompt must
  be at least 92% similar to the new prompt. Too low (e.g., 0.7) and you get
  false hits (returning irrelevant cached responses). Too high (e.g., 0.99) and
  you barely get any hits.

---

## 11. Agent DAG -- Prefect 3 + LangGraph

**Location in repo:** `services/agent-engine/`

### What Is It?

An **AI agent** is an LLM that can take actions. Instead of just generating
text, an agent can call tools (APIs, databases, calculators), observe the
results, and decide what to do next. An agent's behavior is defined as a
**directed acyclic graph (DAG)** -- a flowchart of steps.

**Prefect** is a workflow orchestration framework. Think of it as a
sophisticated cron job manager that handles retries, scheduling, caching, and
observability for your data pipelines and AI workflows.

**LangGraph** is a library for building stateful, multi-step agent applications.
It lets you define the agent's reasoning as a graph:

```
          START
            |
            v
     +------+------+
     |  Call LLM   |
     +------+------+
            |
       +----+----+
       |         |
       v         v
  [Use Tool]  [Respond to User]
       |
       v
  [Observe Tool Result]
       |
       v
  [Call LLM Again]  ---> (loop until done)
```

Think of an agent like a chess player. The LLM is the player's brain (it
decides what move to make). Tools are the pieces on the board (they execute
the moves). LangGraph is the rulebook (it defines what moves are legal and
in what order). Prefect is the tournament organizer (it schedules games,
handles timeouts, and records results).

### Why We Chose It

| Requirement                    | Our Choice Advantage              | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| Visual DAG definition          | LangGraph's graph API             | Raw LangChain (spaghetti) |
| State management               | LangGraph's state checkpointing   | Custom (error-prone)    |
| Workflow orchestration          | Prefect's task/flow model         | Airflow (heavier, XML-based) |
| Human-in-the-loop              | LangGraph's interrupt nodes       | Custom (complex)        |
| Retry and error handling        | Prefect's built-in retries        | Celery (less observable) |
| Observability                   | Prefect UI + OTEL integration     | Temporal (steeper learning curve) |

### How It Works in Our App

**Defining an agent with tools (the Weather Agent):**

```python
# services/agent-engine/src/agent_engine/agents/weather.py

class WeatherAgent(BaseAgent):
    """An agent that can check weather conditions."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are a helpful weather assistant. When asked about weather, "
            "use the get_weather tool to look up current conditions. "
            "Always provide temperatures in both Celsius and Fahrenheit."
        )

    @property
    def available_tools(self):
        return [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather conditions for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name"}
                    },
                    "required": ["city"],
                },
            },
        }]

    async def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool call and return the result as a string."""
        if tool_name == "get_weather":
            return await self._get_weather(arguments["city"])
        raise ValueError(f"Unknown tool: {tool_name}")

    async def _get_weather(self, city: str) -> str:
        """Call weather API and return formatted result."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://wttr.in/{city}?format=j1"
            )
            data = response.json()
            current = data["current_condition"][0]
            return json.dumps({
                "city": city,
                "temp_c": current["temp_C"],
                "temp_f": current["temp_F"],
                "condition": current["weatherDesc"][0]["value"],
                "humidity": current["humidity"],
            })
```

**The LangGraph agent loop:**

```python
# services/agent-engine/src/agent_engine/graph.py

from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    messages: list[dict]
    tool_calls: list[ToolCall]
    final_response: str | None

def build_agent_graph(agent: BaseAgent, llm_client: LLMClient) -> StateGraph:
    """Build the agent's reasoning graph."""

    graph = StateGraph(AgentState)

    # Node 1: Call the LLM
    async def call_llm(state: AgentState) -> AgentState:
        response = await llm_client.chat(
            messages=state["messages"],
            tools=agent.available_tools,
        )
        # Add assistant response to message history
        state["messages"].append({
            "role": "assistant",
            "content": response.content,
            "tool_calls": response.tool_calls,
        })
        return state

    # Node 2: Execute tool calls
    async def execute_tools(state: AgentState) -> AgentState:
        last_message = state["messages"][-1]
        for tool_call in last_message.get("tool_calls", []):
            result = await agent.execute_tool(
                tool_call["function"]["name"],
                json.loads(tool_call["function"]["arguments"]),
            )
            state["messages"].append({
                "role": "tool",
                "name": tool_call["function"]["name"],
                "content": result,
            })
            state["tool_calls"].append(ToolCall(
                tool_name=tool_call["function"]["name"],
                arguments=tool_call["function"]["arguments"],
                result=result,
            ))
        return state

    # Conditional edge: does the LLM want to use tools or respond?
    def should_use_tools(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if last_message.get("tool_calls"):
            return "execute_tools"
        return "respond"

    # Node 3: Format the final response
    async def respond(state: AgentState) -> AgentState:
        state["final_response"] = state["messages"][-1]["content"]
        return state

    # Wire up the graph
    graph.add_node("call_llm", call_llm)
    graph.add_node("execute_tools", execute_tools)
    graph.add_node("respond", respond)

    graph.set_entry_point("call_llm")
    graph.add_conditional_edges("call_llm", should_use_tools, {
        "execute_tools": "execute_tools",
        "respond": "respond",
    })
    graph.add_edge("execute_tools", "call_llm")  # Loop back after tool use
    graph.add_edge("respond", END)

    return graph.compile()
```

**The graph visualized:**

```
  START
    |
    v
+--------+     has tool calls     +---------------+
|Call LLM| ------------------->  | Execute Tools  |
+--------+                       +-------+--------+
    ^   |                                |
    |   | no tool calls                  | (loop back with tool results)
    |   v                                |
    | +--------+                         |
    | |Respond | --> END                 |
    | +--------+                         |
    +----------------------------------- +
```

**Wrapping it with Prefect for orchestration:**

```python
# services/agent-engine/src/agent_engine/flows.py

from prefect import flow, task
from prefect.tasks import task_input_hash

@task(retries=2, retry_delay_seconds=5, cache_key_fn=task_input_hash)
async def embed_query(text: str) -> list[float]:
    """Convert text to embedding vector. Cached and retried."""
    return await embedding_model.embed(text)

@task(retries=1)
async def check_semantic_cache(embedding: list[float]) -> str | None:
    """Check Redis semantic cache for similar queries."""
    return await semantic_cache.get(embedding)

@task(retries=2, retry_delay_seconds=10)
async def run_agent(agent_id: UUID, messages: list[dict]) -> AgentResponse:
    """Run the agent graph. Retries on transient LLM failures."""
    agent = agent_registry.get(agent_id)
    graph = build_agent_graph(agent, llm_client)
    result = await graph.ainvoke({"messages": messages, "tool_calls": []})
    return AgentResponse(
        content=result["final_response"],
        tool_calls=result["tool_calls"],
    )

@flow(name="handle-message", log_prints=True)
async def handle_message_flow(agent_id: UUID, session_id: UUID, content: str):
    """Main flow: cache check -> agent execution -> cache store."""
    # Step 1: Embed the query
    embedding = await embed_query(content)

    # Step 2: Check cache
    cached = await check_semantic_cache(embedding)
    if cached:
        print(f"Cache hit for session {session_id}")
        return cached

    # Step 3: Run the agent
    response = await run_agent(agent_id, [{"role": "user", "content": content}])

    # Step 4: Store in cache
    await semantic_cache.put(content, response.content, embedding)

    return response
```

### Key Concepts for the Interview

- **Agent vs. Chatbot:** A chatbot just generates text. An agent can take
  actions (call APIs, query databases, execute code) and reason about the
  results. Agents use a loop: think -> act -> observe -> think again.

- **Tool Calling (Function Calling):** The LLM generates a structured JSON
  object specifying which tool to call and with what arguments. The application
  executes the tool and sends the result back to the LLM. This is how agents
  interact with the real world.

- **DAG (Directed Acyclic Graph):** A flowchart where arrows only go forward
  (no infinite loops). In our agent graph, the LLM can loop between "call LLM"
  and "execute tools" but eventually reaches "respond" and stops.

- **State Checkpointing:** LangGraph saves the state (message history, tool
  results) at each node, so if a failure occurs, execution can resume from the
  last checkpoint instead of starting over.

- **Prefect Flow vs. Task:** A flow is a function that orchestrates tasks. A
  task is a unit of work that can be retried, cached, and observed independently.
  Flows define the "what order"; tasks define the "what."

---

## 12. Feature Store -- Feast on Flink

**Location in repo:** `infra/k8s/base/feast/`, `services/agent-engine/`

### What Is It?

A **feature store** is a centralized system for managing, storing, and serving
machine learning features. Features are the input variables that ML models use
to make predictions.

Think of it like a prep kitchen in a restaurant. Raw ingredients (raw data)
arrive from suppliers (data sources). The prep kitchen (feature store) washes,
chops, and portions them (feature engineering) so the chefs (ML models) can
grab pre-prepared ingredients instantly during service instead of prepping from
scratch for every order.

**Feast** (Feature Store) is an open-source feature store that:
- Defines features as code (version controlled).
- Serves features with low latency for online inference.
- Stores feature history for offline training.

**Apache Flink** is a stream processing engine that computes features in
real-time from event streams. Flink processes data as it arrives (streaming),
rather than in periodic batches.

```
Data Sources (databases, APIs, events)
        |
        v
  +-----+------+
  | Apache     |   <-- Computes features in real-time
  | Flink      |       (e.g., "user's request count in last 5 min")
  +-----+------+
        |
        v
  +-----+------+
  | Feast      |   <-- Stores and serves computed features
  | Feature    |       Online store: Redis (low latency serving)
  | Store      |       Offline store: Postgres (training data)
  +-----+------+
        |
        v
  Model / Agent (consumes features for decisions)
```

### Why We Chose It

| Requirement                    | Feast + Flink Advantage           | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| Feature consistency            | Same features for training & serving | Manual (train/serve skew) |
| Real-time features             | Flink streaming computation       | Spark (batch, higher latency) |
| Open source                    | No vendor lock-in                 | Tecton (SaaS, expensive) |
| Point-in-time correctness      | Feast handles time-travel queries | Custom (error-prone)     |
| Feature reuse                  | Central registry, shared across models | Duplicated code per team |

### How It Works in Our App

We use features for:
1. **Rate limiting intelligence:** A user's request count in the last 5 minutes
   determines whether to apply strict limits.
2. **Cost prediction:** Historical token usage per user helps predict costs.
3. **Agent selection:** User behavior features help route to the best agent.

**Feature definition:**

```python
# services/agent-engine/src/agent_engine/features/definitions.py

from feast import Entity, Feature, FeatureView, FileSource
from feast.types import Float32, Int64, String
from datetime import timedelta

# Entity = the thing you are computing features for
user = Entity(
    name="user",
    join_keys=["user_id"],
    description="A platform user",
)

# Feature View = a group of related features from the same source
user_activity_features = FeatureView(
    name="user_activity",
    entities=[user],
    ttl=timedelta(hours=1),    # Features older than 1 hour are stale
    schema=[
        Feature(name="request_count_5min", dtype=Int64),
        Feature(name="avg_tokens_per_request", dtype=Float32),
        Feature(name="total_cost_24h", dtype=Float32),
        Feature(name="preferred_agent", dtype=String),
    ],
    online=True,     # Serve from Redis for low-latency lookups
    source=user_activity_source,
)
```

**Serving features at inference time:**

```python
# services/agent-engine/src/agent_engine/features/serving.py

from feast import FeatureStore

store = FeatureStore(repo_path=".")

async def get_user_features(user_id: str) -> dict:
    """Fetch pre-computed features for a user."""
    features = store.get_online_features(
        features=[
            "user_activity:request_count_5min",
            "user_activity:avg_tokens_per_request",
            "user_activity:total_cost_24h",
            "user_activity:preferred_agent",
        ],
        entity_rows=[{"user_id": user_id}],
    )
    return features.to_dict()
```

### Key Concepts for the Interview

- **Online vs. Offline Store:** Online store (Redis) serves features in
  milliseconds for real-time inference. Offline store (Postgres/S3) stores
  historical features for model training. Feast keeps both in sync.

- **Feature Engineering:** Transforming raw data into useful inputs for ML
  models. Example: raw data = list of API requests. Feature = "number of
  requests in the last 5 minutes." The feature is more useful than the raw data.

- **Train-Serve Skew:** When features computed during training differ from
  features computed during serving. This causes models to perform worse in
  production than in experiments. Feature stores eliminate this by using the
  same computation for both.

- **Point-in-Time Join:** When training a model, you need features as they
  were at the time of each training example -- not as they are now. Feast
  handles this automatically by timestamping all feature values.

---

## 13. Observability -- OpenTelemetry to Grafana

**Location in repo:** `libs/py-common/src/agent_platform_common/telemetry.py`,
`infra/k8s/base/grafana/`, `infra/helm/grafana/`

### What Is It?

**Observability** is the ability to understand what your system is doing by
looking at its external outputs: logs, metrics, and traces. It answers the
question "Why is the system behaving this way?"

Think of it like a doctor examining a patient. Logs are the patient's symptom
diary ("headache at 3pm, nausea at 4pm"). Metrics are vital signs (heart rate,
blood pressure). Traces are medical imaging (X-ray showing the exact path of
an injury through the body).

**OpenTelemetry (OTEL)** is a vendor-neutral standard for collecting logs,
metrics, and traces. It is the "USB" of observability: write instrumentation
once, send data to any backend.

**Grafana** is a visualization platform. We use three Grafana backends:

| Backend          | What It Stores | Example                        |
|------------------|----------------|--------------------------------|
| **Tempo**        | Traces         | "Request took 2.3s: 0.1s gateway + 0.2s cache + 2s LLM" |
| **Loki**         | Logs           | "ERROR: LLM timeout after 30s for session abc123"        |
| **Mimir**        | Metrics        | "gateway_requests_total = 45,231, p99_latency = 890ms"   |

### Why We Chose It

| Requirement                    | OTEL + Grafana Advantage          | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| Vendor neutrality              | Switch backends without code change| Datadog (proprietary SDK) |
| Cost                           | Open-source, self-hosted          | Datadog (~$15/host/month) |
| Unified telemetry              | Logs + metrics + traces in one SDK| Prometheus + ELK (separate) |
| Kubernetes-native              | Helm charts, auto-instrumentation | Splunk (heavier)         |
| Community standard             | CNCF graduated, wide adoption     | New Relic (proprietary)  |

### How It Works in Our App

**The telemetry library (shared across all services):**

```python
# libs/py-common/src/agent_platform_common/telemetry.py

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_telemetry(service_name: str, otlp_endpoint: str = "otel-collector:4317"):
    """Initialize OpenTelemetry for a service."""

    # Traces: track request flow across services
    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
    )

    # Metrics: counters, histograms, gauges
    metrics.set_meter_provider(MeterProvider(
        metric_readers=[PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=otlp_endpoint),
            export_interval_millis=10000,  # Export every 10 seconds
        )]
    ))

    return trace.get_tracer(service_name), metrics.get_meter(service_name)
```

**Using telemetry in the gateway:**

```python
# services/gateway/src/gateway/main.py

from agent_platform_common.telemetry import setup_telemetry

tracer, meter = setup_telemetry("gateway")

# Define custom metrics
request_counter = meter.create_counter(
    "gateway.requests.total",
    description="Total number of requests",
)
llm_latency = meter.create_histogram(
    "gateway.llm.latency_ms",
    description="LLM call latency in milliseconds",
)

@app.middleware("http")
async def telemetry_middleware(request, call_next):
    """Add tracing and metrics to every request."""
    with tracer.start_as_current_span(
        f"{request.method} {request.url.path}",
        attributes={
            "http.method": request.method,
            "http.url": str(request.url),
        },
    ) as span:
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        # Record metrics
        request_counter.add(1, {"path": request.url.path, "status": response.status_code})
        span.set_attribute("http.status_code", response.status_code)

        return response
```

**The metrics collector (lightweight, in-process):**

```python
# services/gateway/src/gateway/metrics.py

class MetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self._total_requests = 0
        self._request_latencies = deque(maxlen=100)

    def record_request(self, path, status, latency_ms):
        with self._lock:
            self._total_requests += 1
            if status >= 400:
                self._total_errors += 1
            self._request_latencies.append(latency_ms)
```

**A distributed trace looks like this:**

```
Trace ID: abc-123-def-456
|
|-- [gateway] POST /graphql                    (2350ms total)
|   |
|   |-- [gateway] parse_graphql_query          (2ms)
|   |
|   |-- [cache-service] semantic_cache.get     (5ms)
|   |   Result: MISS
|   |
|   |-- [agent-engine] run_agent               (2300ms)
|   |   |
|   |   |-- [agent-engine] call_llm            (1800ms)
|   |   |   |
|   |   |   |-- [vllm] /v1/chat/completions   (1795ms)
|   |   |       Model: llama3.1-8b
|   |   |       Tokens: 150 input, 85 output
|   |   |
|   |   |-- [agent-engine] execute_tools       (450ms)
|   |   |   |
|   |   |   |-- [weather-api] get_weather      (445ms)
|   |   |       City: Tokyo
|   |   |
|   |   |-- [agent-engine] call_llm            (50ms)
|   |       (Final response with tool results)
|   |
|   |-- [cache-service] semantic_cache.put     (3ms)
|   |
|   |-- [gateway] format_response              (1ms)
```

This trace tells you exactly where time is spent. The LLM call took 1795ms
(76% of total time), and the weather API took 445ms (19%). If you want to make
the system faster, optimize those two things.

### Key Concepts for the Interview

- **Three Pillars of Observability:**
  - **Logs:** Text records of events ("User X logged in at time T").
  - **Metrics:** Numeric measurements over time (request count, error rate, latency percentiles).
  - **Traces:** The path of a request through multiple services, with timing for each step.

- **Span:** A single operation within a trace. Each service creates a span for
  the work it does. Spans are nested: a parent span (gateway) contains child
  spans (agent-engine, cache-service).

- **Trace Context Propagation:** When service A calls service B, OTEL
  automatically adds trace headers (`traceparent`) to the HTTP request. Service
  B reads these headers and links its spans to the same trace. This is how you
  get end-to-end traces across microservices.

- **p50, p95, p99 Latency:** Percentile latencies. p99 = 890ms means 99% of
  requests finish in under 890ms. The remaining 1% are slower. p99 is more
  useful than average because averages hide outliers.

- **Cardinality:** The number of unique values for a metric label. High
  cardinality (e.g., labeling by `user_id` with millions of users) causes
  metric storage to explode. Use labels with bounded cardinality (e.g.,
  `http_method` has only a few values).

---

## 14. Cost Tracking -- OpenCost

**Location in repo:** `services/cost-tracker/`, `infra/k8s/base/opencost/`

### What Is It?

**OpenCost** is a CNCF project that provides real-time cost monitoring for
Kubernetes clusters. It tracks how much each namespace, deployment, and pod
costs in terms of CPU, memory, GPU, and network resources.

In an AI platform, cost tracking is critical because GPU compute is expensive.
A single NVIDIA A100 GPU costs ~$3/hour in the cloud. If your LLM is running
24/7, that is $2,190/month for one GPU. You need to know:
- How much does each inference call cost?
- Which users/agents are consuming the most resources?
- Are we within budget?

Think of it like the electricity meter in your house, but for cloud computing.
Without it, you get a surprise bill at the end of the month. With it, you can
see in real-time that "the weather agent costs $0.002 per request, and it has
handled 5,000 requests today, so it will cost $10 today."

### Why We Chose It

| Requirement                    | OpenCost Advantage                | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| Real-time cost visibility      | Per-pod cost, updated minutely    | Cloud billing (24h delay) |
| Kubernetes-native              | Understands pods, namespaces      | Kubecost (commercial fork) |
| Open source (CNCF)             | Free, no vendor lock-in           | Kubecost (paid enterprise) |
| GPU cost tracking              | Tracks nvidia.com/gpu allocations | Custom (complex)         |
| API access                     | REST API for programmatic access  | Cloud console (manual)   |

### How It Works in Our App

**Per-inference cost calculation:**

```python
# services/cost-tracker/src/cost_tracker/calculator.py

class CostCalculator:
    """Calculate the cost of each LLM inference call."""

    # Costs per token (approximate, based on GPU amortization)
    GPU_COST_PER_HOUR = 3.00          # A100 cloud cost
    TOKENS_PER_SECOND = 40            # vLLM throughput for 8B model
    TOKENS_PER_HOUR = TOKENS_PER_SECOND * 3600

    @property
    def cost_per_token(self) -> float:
        return self.GPU_COST_PER_HOUR / self.TOKENS_PER_HOUR  # ~$0.0000208

    def calculate_inference_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
        backend: str,     # "vllm" or "llamacpp"
    ) -> float:
        """Calculate cost in USD for a single inference call."""
        total_tokens = input_tokens + output_tokens

        if backend == "llamacpp":
            # CPU inference is ~10x cheaper (no GPU cost)
            return total_tokens * self.cost_per_token * 0.1

        return total_tokens * self.cost_per_token

    def calculate_monthly_projection(
        self,
        daily_requests: int,
        avg_tokens_per_request: int,
    ) -> float:
        """Project monthly cost based on current usage."""
        daily_cost = daily_requests * avg_tokens_per_request * self.cost_per_token
        return daily_cost * 30
```

**Exposing cost data to the frontend:**

The `costUsd` field in the GraphQL response is calculated by the cost tracker
and included in every chat message. This lets users see exactly how much each
AI response costs -- building trust and awareness.

**OpenCost Kubernetes integration:**

```yaml
# infra/k8s/base/opencost/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opencost
  namespace: opencost
spec:
  template:
    spec:
      containers:
        - name: opencost
          image: ghcr.io/opencost/opencost:latest
          env:
            - name: PROMETHEUS_SERVER_ENDPOINT
              value: "http://mimir:9009"    # Read metrics from Grafana Mimir
            - name: CLUSTER_ID
              value: "agent-platform-dev"
          ports:
            - containerPort: 9003    # OpenCost API
              name: http
```

### Key Concepts for the Interview

- **Unit Economics:** The cost to serve a single request. In AI platforms, this
  is typically measured in $/request or $/1000 tokens. Understanding unit
  economics tells you if your pricing model is sustainable.

- **Showback vs. Chargeback:** Showback = showing teams how much they cost
  (informational). Chargeback = actually billing teams for their usage
  (financial). OpenCost enables both.

- **GPU Amortization:** Spreading the cost of a GPU over its total usage. If
  a GPU costs $3/hour and processes 144,000 tokens per hour, each token costs
  ~$0.00002. This is how we calculate per-inference cost.

---

## 15. GitOps -- Argo CD + Tekton

**Location in repo:** `infra/argocd/`, `infra/tekton/`

### What Is It?

**GitOps** is a way of managing infrastructure where Git is the single source
of truth. Instead of running `kubectl apply` manually or clicking buttons in a
dashboard, you commit YAML to Git, and an automated system applies it to your
cluster.

Think of it like Google Docs for your infrastructure. Everyone edits the same
document (Git repo). Changes are tracked (commit history). You can see who
changed what and when (git blame). If something breaks, you revert to a
previous version (git revert).

**Argo CD** is the "sync engine." It continuously watches your Git repository
and ensures your Kubernetes cluster matches what is in Git. If someone manually
changes the cluster, Argo CD detects the drift and reverts it.

**Tekton** is the CI pipeline engine. It runs your build steps (lint, test,
build container image, push image) as Kubernetes-native tasks. Think of Tekton
as GitHub Actions, but running inside your cluster.

```
Developer pushes code to Git
        |
        v
  +-----+------+
  | Tekton CI  |   <-- Runs tests, builds container image, pushes to registry
  +-----+------+
        |
        v
  Git repo updated with new image tag
        |
        v
  +-----+------+
  | Argo CD    |   <-- Detects change in Git, syncs to cluster
  +-----+------+
        |
        v
  Kubernetes cluster updated with new version
```

### Why We Chose It

| Requirement                    | Our Choice Advantage              | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| Git as single source of truth  | Argo CD's declarative model       | Jenkins (imperative scripts) |
| Kubernetes-native CI           | Tekton runs as K8s resources      | GitHub Actions (external) |
| Drift detection                | Argo CD alerts on manual changes  | Flux (also good)         |
| Visual pipeline UI             | Argo CD dashboard shows sync state| Flux (CLI-focused)       |
| Multi-cluster support          | Argo CD manages multiple clusters | Jenkins X (deprecated)   |
| RBAC integration               | K8s RBAC for pipeline permissions | Jenkins (own auth system) |

### How It Works in Our App

**Argo CD Application definition:**

```yaml
# infra/argocd/applications/gateway.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: gateway
  namespace: argocd
spec:
  project: agent-platform
  source:
    repoURL: https://github.com/your-org/agent-platform.git
    targetRevision: main
    path: infra/k8s/overlays/production    # Kustomize overlay for prod
  destination:
    server: https://kubernetes.default.svc
    namespace: agent-platform
  syncPolicy:
    automated:
      prune: true          # Delete resources removed from Git
      selfHeal: true       # Revert manual cluster changes
    syncOptions:
      - CreateNamespace=true
```

**What `selfHeal: true` means:** If someone runs `kubectl edit deployment gateway`
and changes the replica count from 3 to 1, Argo CD detects this within seconds
and reverts it back to 3 (the value in Git). This prevents "snowflake clusters"
where the running state diverges from the declared state.

**Tekton CI pipeline:**

```yaml
# infra/tekton/pipelines/build-and-test.yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-and-test
spec:
  params:
    - name: git-url
    - name: git-revision
    - name: image-name
  tasks:
    # Step 1: Clone the repo
    - name: clone
      taskRef:
        name: git-clone
      params:
        - name: url
          value: $(params.git-url)
        - name: revision
          value: $(params.git-revision)

    # Step 2: Run linting
    - name: lint
      runAfter: [clone]
      taskRef:
        name: ruff-lint
      workspaces:
        - name: source
          workspace: shared-workspace

    # Step 3: Run unit tests
    - name: test
      runAfter: [clone]     # Runs in PARALLEL with lint
      taskRef:
        name: pytest
      workspaces:
        - name: source
          workspace: shared-workspace

    # Step 4: Build container image (after lint and test pass)
    - name: build
      runAfter: [lint, test]
      taskRef:
        name: kaniko-build
      params:
        - name: IMAGE
          value: $(params.image-name):$(params.git-revision)

    # Step 5: Security scan
    - name: scan
      runAfter: [build]
      taskRef:
        name: trivy-scan
      params:
        - name: IMAGE
          value: $(params.image-name):$(params.git-revision)
```

**Notice:** Steps 2 (lint) and 3 (test) both `runAfter: [clone]` -- they run
in parallel. Step 4 (build) runs after both finish. This is a DAG, just like
the agent graph, but for CI/CD.

### Key Concepts for the Interview

- **Declarative vs. Imperative:** Imperative = "run these commands in this
  order" (Jenkins scripts). Declarative = "here is what the end state should
  look like" (Argo CD YAML). Declarative is more reliable because the system
  continuously reconciles toward the desired state.

- **Reconciliation Loop:** Argo CD runs a loop: (1) read desired state from
  Git, (2) read actual state from cluster, (3) if different, apply changes.
  This loop runs every 3 minutes by default, or immediately on Git webhook.

- **Drift Detection:** When the cluster state differs from Git. Causes include
  manual `kubectl` commands, failing controllers, or resource limit changes.
  Argo CD shows drift in its UI with a yellow "OutOfSync" status.

- **Kustomize Overlays:** A way to customize Kubernetes YAML for different
  environments without duplicating files. Base = common config. Overlay =
  environment-specific patches (dev uses 1 replica, prod uses 3).

---

## 16. Policy -- OPA Gatekeeper

**Location in repo:** `infra/policy/`

### What Is It?

**OPA (Open Policy Agent)** is a general-purpose policy engine. You write
policies in a language called Rego, and OPA evaluates them against data.

**Gatekeeper** is the Kubernetes-native integration for OPA. It acts as an
admission controller -- a gatekeeper (literally) that checks every Kubernetes
resource before it is created or modified. If a resource violates a policy,
Gatekeeper rejects it.

Think of it like a building code inspector. Before any construction (resource
creation) is approved, the inspector (Gatekeeper) checks it against the
building codes (policies). No structure gets built without passing inspection.

```
Developer submits: "Create a pod with image: latest"
        |
        v
  +-----+------+
  | Kubernetes |
  | API Server |
  +-----+------+
        |
        v
  +-----+------+
  | Gatekeeper |   <-- "REJECTED: All images must have a specific version tag.
  | (Admission |       'latest' is not allowed."
  | Controller)|
  +-----------+
```

### Why We Chose It

| Requirement                    | OPA Gatekeeper Advantage          | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| Kubernetes-native              | Admission controller integration  | OPA standalone (manual)  |
| Policy as code                 | Rego policies in Git, version-controlled | Manual review (slow) |
| Audit mode                     | Report violations without blocking| Kyverno (also good)      |
| Constraint templates           | Reusable policy templates         | Custom webhooks          |
| CNCF graduated                 | Production-proven, well-maintained| Kyverno (CNCF sandbox)  |

### How It Works in Our App

**Policy: All containers must have resource limits:**

```yaml
# infra/policy/templates/require-resource-limits.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredresources
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredResources
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredresources

        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not container.resources.limits
          msg := sprintf(
            "Container '%s' must have resource limits defined. "
            "This prevents a single pod from consuming all node resources.",
            [container.name]
          )
        }

        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not container.resources.limits.memory
          msg := sprintf(
            "Container '%s' must have a memory limit. "
            "Without it, OOM kills can cascade to other pods.",
            [container.name]
          )
        }
```

**Applying the policy:**

```yaml
# infra/policy/constraints/require-resource-limits.yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredResources
metadata:
  name: require-resource-limits
spec:
  enforcementAction: deny     # Block non-compliant resources
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment", "StatefulSet"]
    namespaces: ["agent-platform"]
```

**Policy: No 'latest' image tags:**

```yaml
# infra/policy/templates/require-image-tag.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredimagetag
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredImageTag
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredimagetag

        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          endswith(container.image, ":latest")
          msg := sprintf(
            "Container '%s' uses ':latest' tag. "
            "Use a specific version tag (e.g., ':v1.2.3' or ':sha-abc123') "
            "for reproducible deployments.",
            [container.name]
          )
        }

        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not contains(container.image, ":")
          msg := sprintf(
            "Container '%s' has no image tag. "
            "This defaults to ':latest'. Specify a version tag.",
            [container.name]
          )
        }
```

**Policy: GPU pods must have cost labels:**

```yaml
# infra/policy/templates/require-cost-labels.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredcostlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredCostLabels
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredcostlabels

        violation[{"msg": msg}] {
          # Only check pods requesting GPUs
          container := input.review.object.spec.containers[_]
          container.resources.limits["nvidia.com/gpu"]

          # Must have cost-center label
          not input.review.object.metadata.labels["cost-center"]
          msg := "GPU pods must have a 'cost-center' label for cost tracking."
        }
```

### Key Concepts for the Interview

- **Admission Controller:** A webhook that intercepts Kubernetes API requests
  before they are persisted. There are two types: validating (accept/reject)
  and mutating (modify the resource). Gatekeeper is a validating admission
  controller.

- **Rego:** The policy language used by OPA. It is declarative (you describe
  what violations look like, not how to check for them). Rego is inspired by
  Datalog.

- **Constraint Template vs. Constraint:** A template defines the policy logic
  (Rego code). A constraint applies the template to specific resources with
  specific parameters. This separation lets you reuse one template across
  many constraints.

- **Audit Mode vs. Enforce Mode:** `enforcementAction: deny` blocks violations.
  `enforcementAction: warn` allows but logs. `enforcementAction: dryrun`
  silently records. Start with dryrun, then warn, then deny.

- **Shift Left:** Catching problems as early as possible. With Gatekeeper,
  policy violations are caught at deployment time (before the bad resource
  runs), not at incident time (after it caused a problem).

---

## 17. Dev Loop -- DevContainer + Skaffold + mirrord

**Location in repo:** `.devcontainer/`, `skaffold.yaml`

### What Is It?

The "dev loop" is how quickly a developer can make a code change and see it
running. A fast dev loop means high productivity. A slow dev loop means
frustration and context switching.

**DevContainer** is a VS Code feature that defines your development environment
as a Docker container. Every developer gets the same tools, versions, and
configuration, regardless of their host OS.

Think of it like a chemistry lab. Instead of each student bringing their own
beakers and chemicals (installing Python, Node, Docker manually), the school
provides a fully equipped lab bench (DevContainer) with everything pre-installed
and labeled.

**Skaffold** is a tool by Google that automates the inner dev loop for
Kubernetes: detect code change -> build container -> deploy to cluster ->
stream logs. It does this in seconds, not minutes.

**mirrord** is a tool that lets you run a local process as if it were inside
the Kubernetes cluster. Instead of deploying your code to K8s every time you
change a line, mirrord intercepts the cluster traffic and routes it to your
local process. You get instant feedback without any build/deploy step.

```
Without mirrord:                     With mirrord:

  Edit code                            Edit code
    |                                    |
    v                                    v
  Build container (30s)                Run locally (instant)
    |                                    |
    v                                    v
  Push to registry (15s)               mirrord intercepts cluster traffic
    |                                   and routes it to your local process
    v
  Deploy to K8s (20s)
    |
    v
  See result (~65s total)              See result (~1s total)
```

### Why We Chose It

| Requirement                    | Our Choice Advantage              | Alternative              |
|--------------------------------|-----------------------------------|--------------------------|
| Reproducible environment       | DevContainer = same env for all   | README.md "install these tools" |
| Fast iteration                 | mirrord = sub-second dev loop     | Docker Compose (slower)  |
| K8s-realistic testing          | Skaffold deploys to real K8s      | Docker Compose (no K8s)  |
| File watching                  | Skaffold detects changes, auto-builds | Manual `docker build`  |
| Multi-service debugging        | mirrord connects to real cluster  | Telepresence (heavier)   |

### How It Works in Our App

**DevContainer configuration:**

```json
// .devcontainer/devcontainer.json
{
  "name": "Agent Platform Dev",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/node:1": {"version": "20"},
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {},
    "ghcr.io/devcontainers-contrib/features/skaffold:1": {}
  },
  "postCreateCommand": "make dev-setup",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "charliermarsh.ruff",
        "ms-python.mypy-type-checker",
        "dbaeumer.vscode-eslint",
        "bradlc.vscode-tailwindcss",
        "graphql.vscode-graphql"
      ]
    }
  },
  "forwardPorts": [3000, 8000, 9000, 6379, 5432]
}
```

**What happens when you open this in VS Code:**

1. VS Code builds (or pulls) the Docker image with Python 3.11.
2. It installs Node.js 20, Docker-in-Docker, kubectl, Helm, and Skaffold.
3. It runs `make dev-setup` (installs project dependencies).
4. It installs VS Code extensions for Python, Ruff, mypy, ESLint, Tailwind, and
   GraphQL.
5. It forwards ports so you can access the frontend (3000), gateway (8000),
   MinIO (9000), Redis (6379), and Postgres (5432) from your browser.

**Every developer, on any OS, gets this exact setup in ~3 minutes.**

**Skaffold configuration:**

```yaml
# skaffold.yaml
apiVersion: skaffold/v4beta6
kind: Config
metadata:
  name: agent-platform
build:
  artifacts:
    - image: agent-platform/gateway
      context: services/gateway
      docker:
        dockerfile: Dockerfile
    - image: agent-platform/agent-engine
      context: services/agent-engine
      docker:
        dockerfile: Dockerfile
    - image: agent-platform/frontend
      context: frontend
      docker:
        dockerfile: Dockerfile
  local:
    push: false            # Don't push to registry in dev
    useBuildkit: true       # Faster builds with BuildKit
deploy:
  kustomize:
    paths: ["infra/k8s/overlays/dev"]
portForward:
  - resourceType: service
    resourceName: frontend
    port: 3000
  - resourceType: service
    resourceName: gateway
    port: 8000
```

**Run `skaffold dev` and:**

1. It builds container images for all services.
2. Deploys them to your local Kubernetes cluster using Kustomize.
3. Forwards ports so you can access services from localhost.
4. Watches for file changes. When you edit code, it rebuilds only the changed
   service and redeploys it automatically.
5. Streams logs from all services to your terminal.

**Horizontal Pod Autoscaler (for production, but tested in dev):**

```yaml
# infra/k8s/demo/gateway.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gateway
  minReplicas: 1
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 10
      policies:
        - type: Pods
          value: 2
          periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 30
```

**What this means in plain English:**

- Keep between 1 and 5 gateway pods running.
- If average CPU usage across all pods exceeds 50%, add more pods.
- When scaling up, add at most 2 pods every 15 seconds. Wait at least 10
  seconds before deciding to scale up again (stabilization window).
- When scaling down, wait 30 seconds before removing pods (to avoid flapping:
  scale down -> traffic increases -> scale up -> repeat).

### Key Concepts for the Interview

- **Inner Loop vs. Outer Loop:** Inner loop = code -> build -> test -> debug
  (what a developer does repeatedly). Outer loop = commit -> CI -> deploy ->
  monitor (what the pipeline does). Skaffold and mirrord accelerate the inner
  loop.

- **DevContainer:** A standardized, shareable development environment defined
  in JSON. It eliminates "works on my machine" problems by ensuring every
  developer uses identical tooling.

- **HPA (Horizontal Pod Autoscaler):** Automatically adjusts the number of
  pod replicas based on metrics (CPU, memory, custom metrics). Horizontal
  scaling = adding more instances. Vertical scaling = giving one instance more
  resources.

- **Hot Reload:** Automatically restarting (or replacing) the running service
  when code changes, without manual intervention. Skaffold's file watcher
  enables this for Kubernetes deployments.

---

## 18. How It All Connects: The Request Flow

Let us trace a single user request through the entire system, from keystroke
to response.

### Scenario: User asks "What's the weather in Tokyo?"

```
Step 1: FRONTEND (Next.js)
==============================
User types "What's the weather in Tokyo?" and clicks Send.
Next.js client component sends a GraphQL mutation via fetch().

     Browser
       |
       | POST /graphql
       | Content-Type: application/json
       | Body: { query: "mutation SendMessage...", variables: { ... } }
       v

Step 2: INGRESS (Contour/Envoy)
==============================
Envoy receives the HTTPS request.
  - Terminates TLS (decrypts HTTPS -> HTTP)
  - Adds trace headers (X-Request-ID, traceparent)
  - Checks rate limit (100 req/min per client)
  - Routes /graphql -> gateway service (port 8000)

       |
       | HTTP (plain, inside cluster)
       | + traceparent header for distributed tracing
       v

Step 3: SERVICE MESH (Istio Ambient)
==============================
ztunnel encrypts the request with mTLS before it leaves the node.
Checks authorization policy: is the source allowed to reach the gateway?

       |
       | mTLS encrypted
       v

Step 4: API GATEWAY (FastAPI + Strawberry)
==============================
FastAPI receives the request.
  - Telemetry middleware starts a trace span
  - MetricsCollector records the request
  - Strawberry parses the GraphQL query
  - Resolves the sendMessage mutation
  - Calls the agent-engine service

       |
       | Internal HTTP call to agent-engine
       v

Step 5: SEMANTIC CACHE (Redis VSS)
==============================
Agent engine first checks the semantic cache:
  - Embeds the query: "What's the weather in Tokyo?" -> [0.123, -0.456, ...]
  - Searches Redis for vectors with cosine similarity > 0.92
  - MISS: No similar query found in cache

       |
       | Cache miss -> proceed to agent
       v

Step 6: FEATURE STORE (Feast)
==============================
Agent engine fetches user features:
  - request_count_5min: 3 (under limit)
  - total_cost_24h: $0.15 (under budget)
  - preferred_agent: "weather" (matches current agent)

       |
       | Features inform agent behavior
       v

Step 7: AGENT DAG (LangGraph)
==============================
The Weather Agent graph executes:

  Node 1: call_llm
    -> LLM sees the user message and available tools
    -> LLM decides to call get_weather(city="Tokyo")
    -> Returns tool_call: { name: "get_weather", arguments: { "city": "Tokyo" } }

       |
       v

  Node 2: execute_tools
    -> Calls the weather API: https://wttr.in/Tokyo?format=j1
    -> Result: { temp_c: 22, temp_f: 72, condition: "Partly cloudy" }

       |
       v

  Node 3: call_llm (again, with tool result)
    -> LLM now has the weather data
    -> Generates: "The weather in Tokyo is 22C (72F) and partly cloudy."

       |
       v

  Node 4: respond
    -> Final response ready

Step 8: LLM RUNTIME (vLLM or llama.cpp)
==============================
The LLM calls in Step 7 go through the Circuit Breaker:
  - Circuit is CLOSED (healthy) -> try vLLM (GPU)
  - vLLM processes the request with PagedAttention
  - 150 input tokens + 85 output tokens = 235 tokens
  - Latency: 1.8 seconds
  - SUCCESS -> circuit stays CLOSED

       |
       | If vLLM had failed 3 times, circuit would OPEN
       | and requests would go to llama.cpp (CPU fallback)
       v

Step 9: COST TRACKING (OpenCost)
==============================
Cost calculator computes:
  - 235 tokens * $0.0000208/token = $0.00489
  - Backend: vLLM (GPU rate)
  - Added to the response as costUsd: 0.00489

       |
       v

Step 10: CACHE STORE (Redis VSS)
==============================
Store the response in the semantic cache:
  - Key: embedding of "What's the weather in Tokyo?"
  - Value: the full response
  - TTL: 3600 seconds (1 hour)
  - Next time someone asks "Tokyo weather?" -> cache HIT

       |
       v

Step 11: OBSERVABILITY (OTEL -> Grafana)
==============================
The trace is complete:
  - 12 spans across 4 services
  - Total latency: 2350ms
  - LLM latency: 1800ms (76%)
  - Tool call latency: 445ms (19%)
  - Everything else: 105ms (5%)
  - Exported to Grafana Tempo for visualization

       |
       v

Step 12: RESPONSE (back through the stack)
==============================
The response travels back:
  agent-engine -> gateway -> Istio (mTLS) -> Envoy -> browser

The frontend renders the chat message:
  +------------------------------------------+
  | What's the weather in Tokyo?        [You] |
  +------------------------------------------+
  | The weather in Tokyo is 22C (72F)        |
  | and partly cloudy.                       |
  |                                          |
  | Tool used: get_weather(city: "Tokyo")    |
  | Cost: $0.005 | Latency: 2350ms     [AI] |
  +------------------------------------------+

Step 13: POLICY (OPA Gatekeeper) -- Background
==============================
Throughout all of this, Gatekeeper ensures:
  - All deployments have resource limits
  - No containers use :latest tags
  - GPU pods have cost-center labels
  - Network policies restrict service-to-service communication

Step 14: GITOPS (Argo CD + Tekton) -- Background
==============================
  - All the infrastructure that made this possible was deployed via GitOps
  - Every YAML file is in Git, version controlled
  - Argo CD ensures the cluster matches Git
  - Tekton built and tested the container images
```

### Latency Breakdown

```
+------------------------------------------------------+
|                     Total: 2350ms                     |
+------------------------------------------------------+
| Envoy    | Gateway | Cache | Agent Engine              |
| (5ms)    | (10ms)  | (5ms) |                           |
|          |         |       | LLM #1     | Tool | LLM#2|
|          |         |       | (1800ms)   |(445ms)|(50ms)|
+------------------------------------------------------+
```

---

## 19. Glossary

This glossary covers terms used throughout this guide, organized alphabetically.

| Term | Definition |
|------|-----------|
| **ACID** | Atomicity, Consistency, Isolation, Durability. Four properties that guarantee database transactions are reliable. PostgreSQL provides ACID guarantees. |
| **Admission Controller** | A Kubernetes webhook that intercepts API requests before resources are created. Gatekeeper is a validating admission controller. |
| **Agent** | An LLM-powered program that can take actions (call tools, query databases) and reason about the results, not just generate text. |
| **ANN (Approximate Nearest Neighbor)** | An algorithm that finds "close enough" vectors without checking every single one. Trades small accuracy loss for large speed gain. Used by pgvector (IVFFlat, HNSW) and Redis VSS. |
| **ASGI** | Asynchronous Server Gateway Interface. The async version of WSGI. FastAPI runs on ASGI, enabling concurrent request handling. |
| **Canary Deployment** | Releasing a new version to a small percentage of traffic before full rollout. If errors increase, roll back without affecting most users. |
| **Circuit Breaker** | A design pattern that stops calling a failing service after repeated failures. After a timeout, it tests with one request to see if the service recovered. States: CLOSED (normal), OPEN (failing, use fallback), HALF_OPEN (testing recovery). |
| **Continuous Batching** | Processing new inference requests as soon as any current request finishes, rather than waiting for an entire batch to complete. Improves GPU utilization. |
| **Cosine Similarity** | A measure of similarity between two vectors, based on the angle between them. Range: -1 (opposite) to 1 (identical). Used for semantic search. |
| **CRD (Custom Resource Definition)** | A Kubernetes extension that lets you define your own resource types (like HTTPProxy or ConstraintTemplate). |
| **DAG (Directed Acyclic Graph)** | A graph where edges have direction and there are no cycles (you cannot follow edges back to where you started). Used to model workflows and agent reasoning. |
| **DevContainer** | A Docker-based development environment defined in JSON. Ensures all developers use identical tools and configurations. |
| **Drift** | When the actual state of a Kubernetes cluster differs from the desired state in Git. Argo CD detects and corrects drift. |
| **Embedding** | A dense vector representation of data (text, images, audio) that captures semantic meaning. Similar items have similar embeddings. |
| **Feature (ML)** | An input variable used by a machine learning model. Example: "number of requests in the last 5 minutes" is a feature derived from raw log data. |
| **Feature Store** | A centralized system for computing, storing, and serving ML features. Ensures consistency between training and serving. Feast is our feature store. |
| **GGUF** | A file format for quantized language models used by llama.cpp. Contains model weights, tokenizer, and metadata in a single file. |
| **GitOps** | Managing infrastructure and applications declaratively through Git. Changes are applied by automated tools (Argo CD), not manual commands. |
| **GraphQL** | A query language for APIs where the client specifies exactly which fields it needs. One endpoint, flexible queries. Alternative to REST. |
| **gRPC** | Google Remote Procedure Call. A high-performance RPC framework using Protocol Buffers and HTTP/2. Used for service-to-service communication. |
| **HNSW** | Hierarchical Navigable Small World. An approximate nearest neighbor algorithm that builds a multi-layer graph for fast similarity search. |
| **HPA** | Horizontal Pod Autoscaler. A Kubernetes resource that automatically scales the number of pod replicas based on CPU, memory, or custom metrics. |
| **Ingress** | A Kubernetes resource that manages external access to services in a cluster, typically HTTP/HTTPS routing. Contour/Envoy is our ingress controller. |
| **IVFFlat** | Inverted File with Flat compression. A pgvector index type that clusters vectors and searches only relevant clusters. Fast to build, good for moderate-size datasets. |
| **KubeRay** | The Kubernetes operator for Ray, enabling distributed computing workloads (including LLM inference) on Kubernetes. |
| **Kustomize** | A Kubernetes configuration management tool that allows customization of YAML without templating. Uses overlays to patch base configurations. |
| **KV Cache** | Key-Value cache used during LLM inference. Stores attention keys and values for previously generated tokens to avoid recomputation. Grows with sequence length. |
| **L4 / L7** | OSI network model layers. L4 = Transport (TCP/UDP), understands ports. L7 = Application (HTTP), understands URLs, headers, cookies. Envoy is an L7 proxy. |
| **mTLS** | Mutual TLS. Both client and server present certificates and verify each other's identity. Istio automates mTLS between all services. |
| **OTEL** | OpenTelemetry. A CNCF standard for collecting logs, metrics, and traces. Vendor-neutral instrumentation. |
| **PagedAttention** | vLLM's key innovation. Manages GPU memory for the KV cache using virtual memory pages, eliminating fragmentation and enabling more concurrent sequences. |
| **Pydantic** | A Python library for data validation using type hints. Pydantic Settings reads configuration from environment variables. |
| **Quantization** | Reducing the precision of model weights (e.g., from 16-bit to 4-bit) to decrease model size and increase speed, with a small quality tradeoff. |
| **RAG** | Retrieval-Augmented Generation. A pattern where relevant documents are retrieved from a vector database and included in the LLM prompt to ground responses in factual data. |
| **Rego** | The policy language used by OPA. Declarative, inspired by Datalog. Used to define rules that Gatekeeper enforces on Kubernetes resources. |
| **Resolver** | In GraphQL, a function that computes the value of a field. Each field in the schema has a resolver (even if it is the default "return the attribute" resolver). |
| **Semantic Cache** | A cache that uses vector similarity instead of exact key matching. Two semantically similar queries (different wording, same meaning) can share a cache entry. |
| **Service Mesh** | An infrastructure layer that manages service-to-service communication. Handles mTLS, retries, load balancing, and traffic policies without application code changes. |
| **Sidecar** | A container that runs alongside your application container in the same pod. Traditional Istio injects Envoy as a sidecar. Ambient mode eliminates sidecars. |
| **Span** | A single operation within a distributed trace. Spans are nested (parent-child) and include timing, attributes, and status. |
| **Strawberry** | A Python GraphQL library that uses type hints to define schemas. Code-first approach: your Python classes are the schema. |
| **Tensor Parallelism** | Splitting a model's weight matrices across multiple GPUs. Each GPU computes a portion of each layer and they synchronize. Enables running models that do not fit on a single GPU. |
| **TLS Termination** | Decrypting HTTPS at the edge (ingress) so internal traffic is plain HTTP. The ingress proxy holds the TLS certificate. |
| **Tool Calling** | An LLM capability where the model outputs structured JSON to invoke external functions (tools). The application executes the tool and returns the result to the model. |
| **Trace** | A record of a request's path through a distributed system. Contains multiple spans, one per service/operation. Visualized as a waterfall diagram. |
| **TTL (Time to Live)** | The duration a cache entry exists before automatic expiration. Prevents serving stale data. |
| **Twelve-Factor App** | A methodology for building SaaS applications. Key factors include: store config in environment variables, treat logs as event streams, maximize robustness with fast startup and graceful shutdown. |
| **Vector Database** | A database optimized for storing and searching high-dimensional vectors (embeddings). Supports similarity search. pgvector adds this capability to PostgreSQL. |
| **vLLM** | A high-throughput LLM serving engine with PagedAttention. OpenAI API compatible. Runs on GPUs. |
| **VSS** | Vector Similarity Search. The Redis module that enables approximate nearest neighbor search on vectors stored in Redis. |
| **WSGI** | Web Server Gateway Interface. The traditional Python web server interface (synchronous). Flask and Django use WSGI. Replaced by ASGI for async workloads. |
| **Zero-Trust** | A security model where no entity (user, service, device) is trusted by default, even inside the network perimeter. Every request must be authenticated and authorized. |
| **ztunnel** | Zero-Trust Tunnel. The per-node DaemonSet in Istio ambient mode that provides L4 mTLS encryption without sidecars. |

---

## What to Read Next

Now that you understand all 16 components, explore the tutorial phases to build
each one step by step:

1. [Phase 0: Environment Setup](./phase-00-environment.md) -- DevContainer, toolchain
2. [Phase 1: API Layer](./phase-01-api-layer.md) -- FastAPI + Strawberry GraphQL
3. [Phase 2: Frontend](./phase-02-frontend.md) -- Next.js + Tailwind
4. [Phase 3: Data Layer](./phase-03-data-layer.md) -- Postgres, Redis, MinIO
5. [Phase 4: Agent Orchestration](./phase-04-agent-orchestration.md) -- Prefect + LangGraph
6. [Phase 5: LLM Runtime](./phase-05-llm-runtime.md) -- vLLM + llama.cpp
7. [Phase 6: Observability](./phase-06-observability.md) -- OTEL + Grafana
8. [Phase 7: Service Mesh](./phase-07-service-mesh.md) -- Istio ambient
9. [Phase 8: GitOps & CI/CD](./phase-08-gitops-cicd.md) -- Argo CD + Tekton
10. [Phase 9: Policy & Governance](./phase-09-policy-governance.md) -- OPA Gatekeeper
11. [Phase 10: Production Hardening](./phase-10-production-hardening.md) -- Load, chaos, security

---

*This guide is part of the Agent Platform tutorial series. It was written to
help fresh graduates understand enterprise AI application architecture. If you
find errors or have suggestions, please open an issue or pull request.*
