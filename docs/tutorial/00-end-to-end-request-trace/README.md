# End-to-End Request Trace: "Tell me about Artificial Intelligence"

> **Objective:** Follow a single user query through every layer of the platform — from browser keystroke to rendered response — showing exactly what happens at each service, what logs are generated, how to trace the flow, and how to debug when things go wrong.

---

## Table of Contents

1. [The Query](#1-the-query)
2. [Architecture Flow Diagram](#2-architecture-flow-diagram)
3. [Step-by-Step Trace](#3-step-by-step-trace)
   - [Step 1: Frontend (Next.js + Tailwind)](#step-1-frontend--nextjs--tailwind)
   - [Step 2: Ingress (Envoy / Contour)](#step-2-ingress--envoy--contour)
   - [Step 3: Service Mesh (Istio Ambient)](#step-3-service-mesh--istio-ambient)
   - [Step 4: API Gateway (FastAPI + GraphQL)](#step-4-api-gateway--fastapi--graphql)
   - [Step 5: Semantic Cache (Redis VSS)](#step-5-semantic-cache--redis-vss)
   - [Step 6: Feature Store (Feast on Flink)](#step-6-feature-store--feast-on-flink)
   - [Step 7: Agent Engine (Prefect + LangGraph)](#step-7-agent-engine--prefect--langgraph)
   - [Step 8: Document Retrieval — RAG (pgvector + MinIO)](#step-8-document-retrieval--rag-pgvector--minio)
   - [Step 9: LLM Inference (vLLM on KubeRay)](#step-9-llm-inference--vllm-on-kuberay)
   - [Step 9b: CPU Fallback (llama.cpp)](#step-9b-cpu-fallback--llamacpp)
   - [Step 10: Response Flows Back](#step-10-response-flows-back)
4. [Cross-Cutting Concerns](#4-cross-cutting-concerns)
   - [Observability (OTEL → Grafana Tempo/Loki/Mimir)](#41-observability--otel--grafana)
   - [Cost Tracking (OpenCost)](#42-cost-tracking--opencost)
   - [Policy Enforcement (OPA Gatekeeper)](#43-policy-enforcement--opa-gatekeeper)
   - [GitOps & CI/CD (Argo CD + Tekton)](#44-gitops--cicd--argo-cd--tekton)
   - [Developer Experience (DevContainer + Skaffold + mirrord)](#45-developer-experience)
5. [Complete Trace ID Journey](#5-complete-trace-id-journey)
6. [How to Debug Each Layer](#6-how-to-debug-each-layer)
7. [Live Debugging Walkthrough](#7-live-debugging-walkthrough)
8. [Common Failure Scenarios](#8-common-failure-scenarios)

---

## 1. The Query

A user opens the chat UI in their browser and types:

```
Tell me about Artificial Intelligence
```

They press **Send**. What follows is a journey across 16 services, 3 networks, and roughly 50 internal operations — all completing in under 3 seconds.

Here is every single thing that happens.

---

## 2. Architecture Flow Diagram

```
                                    USER BROWSER
                                         │
                              ① Types "Tell me about AI"
                              ② Clicks Send
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ① NEXT.JS FRONTEND (Client Component)                                      │
│  • React state updates with user message                                     │
│  • Renders user bubble in chat UI                                            │
│  • POST /graphql with mutation { chat(prompt: "...") }                       │
│  • Opens SSE/streaming connection for response tokens                        │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │ HTTPS request
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ② ENVOY / CONTOUR (Ingress)                                                │
│  • TLS termination (HTTPS → HTTP)                                            │
│  • Rate limiting check (100 req/min per IP)                                  │
│  • Route: /graphql → fastapi-service:8000                                    │
│  • Adds: X-Request-ID, X-Envoy-Upstream-Service-Time headers                │
│  • Access log entry written                                                  │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │ HTTP (plain, inside cluster)
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ③ ISTIO AMBIENT (ztunnel — L4)                                              │
│  • Intercepts TCP connection                                                 │
│  • Establishes mTLS tunnel to destination node's ztunnel                     │
│  • Verifies SPIFFE identity: spiffe://cluster.local/ns/default/sa/frontend   │
│  • TCP metrics recorded (bytes in/out, connection duration)                   │
│  • If waypoint exists: routes through waypoint for L7 auth policies          │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │ mTLS encrypted
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ④ FASTAPI + GRAPHQL (Strawberry)                                            │
│  • Receives POST /graphql                                                    │
│  • OTEL auto-instrumentation creates root span: "POST /graphql"              │
│  • Strawberry resolves mutation: chat(prompt: "Tell me about AI")            │
│  • Extracts trace context, propagates to all downstream calls                │
│  • Dependency injection: get_cache(), get_agent(), get_features()            │
│  │                                                                           │
│  │  ┌──────────────────────────────────────────────────────────────────┐     │
│  │  │  ⑤ SEMANTIC CACHE CHECK (Redis 7.2 VSS)                         │     │
│  │  │  • Embed the prompt → 384-dim vector                             │     │
│  │  │  • FT.SEARCH cache_idx KNN 1 @embedding $vec                    │     │
│  │  │  • Compare cosine similarity: 0.92 < 0.95 threshold             │     │
│  │  │  • Result: CACHE MISS                                            │     │
│  │  │  • Span: "semantic_cache_lookup" (2ms, cache.hit=false)          │     │
│  │  └──────────────────────────────────────────────────────────────────┘     │
│  │                                                                           │
│  │  ┌──────────────────────────────────────────────────────────────────┐     │
│  │  │  ⑥ FEATURE STORE (Feast on Flink)                                │     │
│  │  │  • Fetch user features: user_activity:queries_last_hour = 5      │     │
│  │  │  • Fetch user features: user_activity:preferred_model = llama-3  │     │
│  │  │  • Fetch model features: model_perf:p99_latency = 1200ms         │     │
│  │  │  • Features used for: model routing, context enrichment          │     │
│  │  │  • Span: "feast_feature_lookup" (3ms)                            │     │
│  │  └──────────────────────────────────────────────────────────────────┘     │
│  │                                                                           │
│  ▼  Calls agent engine                                                       │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │ gRPC/HTTP with trace context
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ⑦ AGENT ENGINE (Prefect 3 + LangGraph)                                     │
│                                                                              │
│  Prefect Flow: "chat-agent-flow" (run_id: abc-123)                           │
│  │                                                                           │
│  ├── Task: "validate_input"                                                  │
│  │   • Check prompt length, content policy                                   │
│  │   • Span: "validate_input" (1ms)                                          │
│  │                                                                           │
│  ├── Task: "run_langgraph_agent"                                             │
│  │   │                                                                       │
│  │   │  LangGraph State Machine:                                             │
│  │   │  ┌─────────────────────────────────────────────────────────────┐      │
│  │   │  │ State: { messages: [...], documents: [], answer: "" }       │      │
│  │   │  │                                                             │      │
│  │   │  │ Node: "classify_intent"                                     │      │
│  │   │  │   → intent = "knowledge_question"                           │      │
│  │   │  │   → needs_rag = true                                        │      │
│  │   │  │                                                             │      │
│  │   │  │ Node: "retrieve_documents" (conditional: needs_rag=true)    │      │
│  │   │  │   → Calls pgvector for similar documents                    │      │
│  │   │  │   → 3 chunks retrieved (similarity > 0.8)                   │      │
│  │   │  │                                                             │      │
│  │   │  │ Node: "generate_response"                                   │      │
│  │   │  │   → Calls vLLM with prompt + context                        │      │
│  │   │  │   → Streams tokens back                                     │      │
│  │   │  │                                                             │      │
│  │   │  │ Node: "quality_check"                                       │      │
│  │   │  │   → Checks response coherence                               │      │
│  │   │  │   → PASS → END                                              │      │
│  │   │  └─────────────────────────────────────────────────────────────┘      │
│  │   │                                                                       │
│  │   ▼                                                                       │
│  │                                                                           │
│  │  ┌──────────────────────────────────────────────────────────────────┐     │
│  │  │  ⑧ RAG: DOCUMENT RETRIEVAL                                      │     │
│  │  │                                                                  │     │
│  │  │  pgvector (PostgreSQL):                                          │     │
│  │  │  • Embed query → 384-dim vector                                  │     │
│  │  │  • SQL: SELECT content, 1-(embedding <=> $1) AS similarity       │     │
│  │  │         FROM documents                                           │     │
│  │  │         WHERE metadata->>'category' = 'technology'               │     │
│  │  │         ORDER BY embedding <=> $1 LIMIT 3                        │     │
│  │  │  • HNSW index scan (ef_search=100)                               │     │
│  │  │  • Returns 3 chunks:                                             │     │
│  │  │    [0.94] "AI is a branch of computer science..."                │     │
│  │  │    [0.91] "Machine learning, a subset of AI..."                  │     │
│  │  │    [0.87] "Deep learning uses neural networks..."                │     │
│  │  │  • Span: "pgvector_search" (8ms, docs.count=3)                   │     │
│  │  │                                                                  │     │
│  │  │  MinIO (source documents):                                       │     │
│  │  │  • Original PDFs stored at: documents/raw/<hash>/ai-guide.pdf    │     │
│  │  │  • Chunks were created during ingestion pipeline                 │     │
│  │  │  • Not accessed during query (already in pgvector)               │     │
│  │  └──────────────────────────────────────────────────────────────────┘     │
│  │                                                                           │
│  ▼  Calls LLM                                                                │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │ HTTP with trace context
                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ⑨ LLM INFERENCE (vLLM on KubeRay)                                          │
│                                                                              │
│  Circuit Breaker: state=CLOSED (healthy)                                     │
│  → Route to primary: vLLM                                                    │
│                                                                              │
│  vLLM Server receives POST /v1/chat/completions:                             │
│  {                                                                           │
│    "model": "meta-llama/Meta-Llama-3-70B-Instruct",                         │
│    "messages": [                                                             │
│      {"role": "system", "content": "Answer based on context:\n              │
│        AI is a branch of computer science...\n                               │
│        Machine learning, a subset of AI...\n                                 │
│        Deep learning uses neural networks..."},                              │
│      {"role": "user", "content": "Tell me about Artificial Intelligence"}    │
│    ],                                                                        │
│    "stream": true,                                                           │
│    "temperature": 0.7,                                                       │
│    "max_tokens": 1024                                                        │
│  }                                                                           │
│                                                                              │
│  vLLM internals:                                                             │
│  1. Tokenize prompt → 847 tokens                                             │
│  2. Check prefix cache → partial hit (system prompt cached)                  │
│  3. PagedAttention allocates KV cache pages                                  │
│  4. Continuous batching: joins batch with 12 other requests                  │
│  5. Forward pass on 2x A100-80GB (tensor parallel=2)                         │
│  6. Generate tokens one-by-one (auto-regressive):                            │
│     "Artificial" → "Intelligence" → "(" → "AI" → ")" → "is" → ...          │
│  7. Each token streamed via SSE as generated                                 │
│  8. Total: 312 tokens generated in 1.8 seconds                              │
│                                                                              │
│  Metrics emitted:                                                            │
│  • vllm:num_requests_running = 13                                            │
│  • vllm:gpu_cache_usage_perc = 0.72                                          │
│  • vllm:avg_generation_throughput_toks_per_s = 173                           │
│  • vllm:time_to_first_token_seconds = 0.089                                 │
│                                                                              │
│  Span: "vllm_inference" (1800ms, model=llama-3-70b, tokens.prompt=847,       │
│         tokens.completion=312, gpu_cache_pct=0.72)                           │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │ SSE token stream
                           │
        ┌──────────────────┘
        │
        │  IF vLLM FAILS (circuit breaker opens):
        │  ┌──────────────────────────────────────────────────────────────┐
        │  │  ⑨b CPU FALLBACK (llama.cpp)                                │
        │  │  • Circuit breaker: 5 consecutive failures → OPEN           │
        │  │  • Route to: llama-cpp-svc:8080                             │
        │  │  • Model: llama-3-8b-q4_k_m.gguf (smaller, quantized)      │
        │  │  • Same OpenAI-compatible API                               │
        │  │  • Slower: ~30 tok/s vs ~173 tok/s on GPU                   │
        │  │  • Response tagged: { "_fallback": true }                   │
        │  │  • After 30s recovery_timeout: try vLLM again (HALF_OPEN)   │
        │  └──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ⑩ RESPONSE FLOWS BACK                                                       │
│                                                                              │
│  Agent Engine:                                                               │
│  • LangGraph "generate_response" node streams tokens                         │
│  • Quality check node validates coherence → PASS                             │
│  • Prefect task "run_langgraph_agent" completes (status: COMPLETED)          │
│  • Background task: store response in semantic cache (Redis)                 │
│  • Background task: log inference metrics                                    │
│  • Background task: calculate cost ($0.0034 for this query)                  │
│                                                                              │
│  FastAPI:                                                                    │
│  • GraphQL subscription streams tokens to client                             │
│  • Adds response headers: X-Trace-ID, X-Model-Used, X-Cache-Status          │
│  • OTEL span completes: "POST /graphql" (total: 2,847ms)                    │
│                                                                              │
│  Istio (ztunnel):                                                            │
│  • mTLS tunnel carries response back                                         │
│  • TCP metrics: bytes_sent=4,821, connection_duration=2.9s                   │
│                                                                              │
│  Envoy (Contour):                                                            │
│  • Streams SSE response to client                                            │
│  • Access log: 200, 2847ms, upstream=fastapi-service:8000                    │
│                                                                              │
│  Next.js Frontend:                                                           │
│  • ReadableStream reader processes each chunk                                │
│  • Each token appended to assistant message bubble                           │
│  • UI updates in real-time (token-by-token)                                  │
│  • Auto-scroll to bottom of chat                                             │
│  • "Send" button re-enabled when stream completes                            │
│  • Total user-perceived time: ~2.9 seconds                                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Step-by-Step Trace

### Step 1: Frontend — Next.js + Tailwind

**What happens:**

The user types "Tell me about Artificial Intelligence" in the chat input and presses Send (or hits Enter).

```tsx
// app/chat/page.tsx — simplified flow
"use client";

async function handleSend() {
  // 1. Add user message to UI immediately
  setMessages(prev => [...prev, { role: "user", content: input }]);
  setInput("");
  setIsStreaming(true);

  // 2. Add empty assistant bubble (will fill with streamed tokens)
  setMessages(prev => [...prev, { role: "assistant", content: "" }]);

  // 3. Send GraphQL mutation
  const res = await fetch("/graphql", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": crypto.randomUUID(),  // Client-generated trace seed
    },
    body: JSON.stringify({
      query: `mutation { chat(prompt: "Tell me about Artificial Intelligence") { text tokens model } }`,
    }),
  });

  // 4. Read streaming response
  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    // 5. Append each token to the assistant message
    setMessages(prev => {
      const updated = [...prev];
      updated[updated.length - 1].content += chunk;
      return updated;
    });
  }
  setIsStreaming(false);
}
```

**Logs (Browser Console):**

```
[14:23:01.001] User sent: "Tell me about Artificial Intelligence"
[14:23:01.002] POST /graphql — request sent
[14:23:01.089] First byte received (TTFB: 87ms — this is the network + cache check time)
[14:23:01.102] Token 1: "Artificial"
[14:23:01.115] Token 2: "Intelligence"
...
[14:23:03.891] Token 312: "applications."
[14:23:03.892] Stream complete. Total tokens: 312, Duration: 2890ms
```

**How to debug:**

```bash
# Browser DevTools → Network tab
# Look for the POST /graphql request
# Headers tab: check X-Request-ID, response headers
# Response tab: see streamed chunks
# Timing tab: see TTFB, content download time

# React DevTools → Components tab
# Check ChatPage state: messages array, isStreaming boolean
```

---

### Step 2: Ingress — Envoy (Contour)

**What happens:**

The HTTPS request from the browser hits the Envoy proxy (managed by Contour).

```
Client (browser) ──[HTTPS/TLS 1.3]──► Envoy (:443)
                                         │
                                         ├── TLS termination
                                         ├── Rate limit check (token bucket)
                                         ├── Route match: /graphql → fastapi-service:8000
                                         ├── Add headers
                                         └── Forward as HTTP/1.1
```

**Envoy access log:**

```json
{
  "timestamp": "2026-04-06T14:23:01.005Z",
  "method": "POST",
  "path": "/graphql",
  "protocol": "HTTP/2",
  "response_code": 200,
  "response_flags": "-",
  "bytes_received": 312,
  "bytes_sent": 4821,
  "duration_ms": 2847,
  "upstream_host": "10.244.1.15:8000",
  "upstream_cluster": "default/fastapi-service/8000",
  "upstream_service_time": 2841,
  "x_request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_agent": "Mozilla/5.0...",
  "x_forwarded_for": "203.0.113.42",
  "rate_limit_status": "ok"
}
```

**How to debug:**

```bash
# View Envoy access logs
kubectl logs -n projectcontour -l app=envoy -f | jq '.'

# Check rate limiting
kubectl logs -n projectcontour -l app=envoy -f | jq 'select(.rate_limit_status != "ok")'

# Envoy admin interface
kubectl port-forward -n projectcontour deploy/envoy 9901:9901

# View all routes
curl http://localhost:9901/config_dump | jq '.configs[] | select(.["@type"] | contains("route"))'

# Check upstream health
curl http://localhost:9901/clusters | grep -A5 fastapi-service

# Key metrics
curl http://localhost:9901/stats | grep "downstream_rq_2xx\|downstream_rq_5xx\|upstream_rq_time"
```

**What to look for:**

| Log Field | Healthy | Problem |
|-----------|---------|---------|
| `response_code` | 200 | 429 (rate limited), 503 (backend down) |
| `upstream_service_time` | <3000ms | >5000ms (slow backend) |
| `response_flags` | `-` | `UO` (upstream overflow), `UF` (upstream failure) |
| `rate_limit_status` | `ok` | `over_limit` |

---

### Step 3: Service Mesh — Istio Ambient

**What happens:**

The ztunnel (per-node proxy) intercepts the TCP connection and wraps it in mTLS.

```
Envoy Pod (Node A)                           FastAPI Pod (Node B)
     │                                            │
     ▼                                            ▼
[ztunnel-A]  ──── mTLS tunnel ────  [ztunnel-B]
     │                                            │
     ├── Verify SPIFFE ID of source              ├── Deliver to FastAPI
     ├── Encrypt with mTLS                        ├── Record TCP metrics
     └── Forward to Node B ztunnel                └── Check AuthorizationPolicy
```

**ztunnel logs:**

```
[2026-04-06T14:23:01.008Z] inbound: src=10.244.0.12 (envoy/projectcontour)
  dst=10.244.1.15:8000 (fastapi/ai-platform)
  identity=spiffe://cluster.local/ns/projectcontour/sa/envoy
  bytes_sent=312 bytes_recv=4821 duration=2.84s
```

**How to debug:**

```bash
# Check ztunnel logs
kubectl logs -n istio-system -l app=ztunnel --tail=50

# Verify mTLS is active
kubectl exec -n ai-platform deploy/fastapi -- curl -s localhost:15020/healthz/ready

# Check authorization policies
kubectl get authorizationpolicy -n ai-platform -o yaml

# Analyze mesh config
istioctl analyze -n ai-platform

# Check which workloads are enrolled
istioctl ztunnel-config workloads

# View waypoint proxy logs (if L7 policies active)
kubectl logs -n ai-platform -l istio.io/gateway-name -f
```

**What to look for:**

| Issue | Symptom | Debug Command |
|-------|---------|---------------|
| mTLS not active | No `X-Forwarded-Client-Cert` header | `istioctl authn tls-check` |
| AuthZ denied | 403 from mesh | `kubectl logs ztunnel` |
| Waypoint routing | Unexpected L7 behavior | `istioctl proxy-config routes` |

---

### Step 4: API Gateway — FastAPI + GraphQL (Strawberry)

**What happens:**

FastAPI receives the GraphQL mutation, creates an OTEL trace, and orchestrates the downstream calls.

```python
# Simplified flow inside FastAPI

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def chat(self, info: Info, prompt: str) -> ChatResponse:
        tracer = trace.get_tracer("ai-api")

        with tracer.start_as_current_span("graphql.chat") as span:
            span.set_attribute("prompt.length", len(prompt))
            span.set_attribute("prompt.text", prompt[:200])

            # Step 5: Check semantic cache
            cached = await cache_service.get(prompt)
            if cached:
                span.set_attribute("cache.hit", True)
                return cached

            # Step 6: Get user features
            features = await feast_service.get_features(user_id, model_id)

            # Step 7: Run agent
            result = await agent_service.run(prompt, features, context)

            # Background: cache the result
            background_tasks.add_task(cache_service.set, prompt, result)
            background_tasks.add_task(cost_service.record, result)

            return result
```

**Application logs (structured JSON):**

```json
{
  "timestamp": "2026-04-06T14:23:01.012Z",
  "level": "INFO",
  "service": "ai-api",
  "trace_id": "a1b2c3d4e5f67890abcdef1234567890",
  "span_id": "1234567890abcdef",
  "message": "GraphQL mutation: chat",
  "prompt_length": 40,
  "user_id": "user-42"
}

{
  "timestamp": "2026-04-06T14:23:01.014Z",
  "level": "INFO",
  "service": "ai-api",
  "trace_id": "a1b2c3d4e5f67890abcdef1234567890",
  "span_id": "abcdef1234567890",
  "message": "Cache lookup",
  "cache_hit": false,
  "similarity": 0.92,
  "threshold": 0.95
}

{
  "timestamp": "2026-04-06T14:23:03.859Z",
  "level": "INFO",
  "service": "ai-api",
  "trace_id": "a1b2c3d4e5f67890abcdef1234567890",
  "span_id": "1234567890abcdef",
  "message": "Chat mutation completed",
  "total_duration_ms": 2847,
  "tokens_prompt": 847,
  "tokens_completion": 312,
  "model": "llama-3-70b",
  "cache_hit": false,
  "cost_usd": 0.0034
}
```

**How to debug:**

```bash
# Application logs
kubectl logs -n ai-platform deploy/fastapi -f | jq '.'

# Filter by trace ID
kubectl logs -n ai-platform deploy/fastapi | jq 'select(.trace_id == "a1b2c3...")'

# Filter errors
kubectl logs -n ai-platform deploy/fastapi | jq 'select(.level == "ERROR")'

# GraphQL playground (for testing)
kubectl port-forward -n ai-platform svc/fastapi 8000:8000
# Open http://localhost:8000/graphql

# Test the mutation manually
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { chat(prompt: \"test\") { text tokens model } }"}'

# Check OTEL spans
# Open Grafana → Explore → Tempo → Search by trace_id
```

---

### Step 5: Semantic Cache — Redis VSS

**What happens:**

Before calling the expensive LLM, we check if a similar question has been asked recently.

```
1. Embed prompt: "Tell me about Artificial Intelligence" → [0.12, -0.34, 0.56, ...]
2. Search Redis vector index:
   FT.SEARCH cache_idx "*=>[KNN 1 @embedding $vec AS score]"
3. Best match: "What is AI and machine learning?" (similarity: 0.92)
4. Threshold: 0.95
5. 0.92 < 0.95 → CACHE MISS → proceed to LLM
```

**Redis commands executed:**

```redis
# Embedding lookup (via Python redis-py)
FT.SEARCH sem_cache "*=>[KNN 1 @embedding $vec AS score]" PARAMS 2 vec <binary> SORTBY score LIMIT 0 1 RETURN 3 prompt response score DIALECT 2

# Result:
# 1) (integer) 1
# 2) "semcache:8a3f..."
# 3) 1) "prompt"  2) "What is AI and machine learning?"
#    3) "response" 4) "AI is a field of computer science..."
#    5) "score"   6) "0.078"  (cosine distance; similarity = 1 - 0.078 = 0.922)
```

**After response is generated (background task):**

```redis
# Store new entry in cache
HSET semcache:b7e2... prompt "Tell me about Artificial Intelligence" response "Artificial Intelligence (AI) is..." embedding <binary> created_at 1712412181
EXPIRE semcache:b7e2... 3600
```

**How to debug:**

```bash
# Connect to Redis
kubectl exec -it -n ai-platform deploy/redis -- redis-cli

# Check cache index info
FT.INFO sem_cache

# Check cache entries
SCAN 0 MATCH semcache:* COUNT 100

# Check a specific entry
HGETALL semcache:b7e2...

# Check memory usage
INFO memory

# Monitor commands in real-time
MONITOR

# Check slow queries
SLOWLOG GET 10
```

---

### Step 6: Feature Store — Feast on Flink

**What happens:**

Feast provides real-time features about the user and model to inform routing decisions.

```python
features = feast_store.get_online_features(
    features=[
        "user_activity:queries_last_hour",        # → 5
        "user_activity:preferred_model",           # → "llama-3-70b"
        "user_activity:cache_hit_rate",            # → 0.65
        "model_performance:p99_latency_ms",        # → 1200
        "model_performance:error_rate",            # → 0.002
        "model_performance:gpu_utilization",       # → 0.72
    ],
    entity_rows=[{"user_id": "user-42", "model_id": "llama-3-70b"}],
)

# Decision: p99_latency < 2000ms and error_rate < 0.05 → use llama-3-70b
# If p99 > 2000ms → route to llama-3-8b (smaller, faster)
```

**How to debug:**

```bash
# Check Feast registry
feast feature-views list
feast entities list

# Query features directly
feast materialize-incremental $(date -u +%Y-%m-%dT%H:%M:%S)

# Check Flink jobs (if using Flink for feature computation)
kubectl port-forward -n flink svc/flink-jobmanager 8081:8081
# Open http://localhost:8081 — Flink dashboard

# Check feature freshness
feast feature-views describe user_activity
```

---

### Step 7: Agent Engine — Prefect + LangGraph

**What happens:**

The agent engine runs a LangGraph state machine inside a Prefect flow.

```
Prefect Flow: chat-agent-flow (run_id: flow-abc-123)
│
├── Task: validate_input → COMPLETED (1ms)
│   └── Input valid, no policy violations
│
├── Task: run_langgraph_agent → RUNNING
│   │
│   │  LangGraph execution:
│   │  ┌─────────────────────────────────────────────────┐
│   │  │ State: {messages: [user: "Tell me about AI"],   │
│   │  │         documents: [], answer: ""}              │
│   │  │                                                 │
│   │  │ → classify_intent                               │
│   │  │   intent="knowledge_question", needs_rag=true   │
│   │  │                                                 │
│   │  │ → retrieve_documents (conditional: needs_rag)   │
│   │  │   Called pgvector → 3 documents retrieved        │
│   │  │   State.documents = [doc1, doc2, doc3]          │
│   │  │                                                 │
│   │  │ → generate_response                             │
│   │  │   Built prompt with context                     │
│   │  │   Called vLLM → streaming 312 tokens             │
│   │  │   State.answer = "Artificial Intelligence..."    │
│   │  │                                                 │
│   │  │ → quality_check                                 │
│   │  │   Coherence check: PASS                         │
│   │  │   → END                                         │
│   │  └─────────────────────────────────────────────────┘
│   │
│   └── COMPLETED (2820ms)
│
├── Task: cache_result (background) → COMPLETED (5ms)
│   └── Stored in Redis semantic cache
│
└── Task: record_cost (background) → COMPLETED (2ms)
    └── $0.0034 recorded for this inference
```

**Prefect logs:**

```
14:23:01.020 | INFO  | Flow run 'chat-agent-flow/flow-abc-123' - Started
14:23:01.021 | INFO  | Task run 'validate_input' - Started
14:23:01.022 | INFO  | Task run 'validate_input' - Completed (1ms)
14:23:01.023 | INFO  | Task run 'run_langgraph_agent' - Started
14:23:01.025 | INFO  | LangGraph node 'classify_intent' - intent=knowledge_question
14:23:01.026 | INFO  | LangGraph node 'retrieve_documents' - Starting RAG retrieval
14:23:01.034 | INFO  | LangGraph node 'retrieve_documents' - Retrieved 3 documents
14:23:01.035 | INFO  | LangGraph node 'generate_response' - Calling vLLM
14:23:02.835 | INFO  | LangGraph node 'generate_response' - 312 tokens generated
14:23:02.840 | INFO  | LangGraph node 'quality_check' - PASS
14:23:02.841 | INFO  | Task run 'run_langgraph_agent' - Completed (2820ms)
14:23:02.843 | INFO  | Flow run 'chat-agent-flow/flow-abc-123' - Completed (2823ms)
```

**How to debug:**

```bash
# Prefect UI
kubectl port-forward -n ai-platform svc/prefect-server 4200:4200
# Open http://localhost:4200
# Navigate to: Flows → chat-agent-flow → select run → see task timeline

# Prefect CLI
prefect flow-run ls --flow-name chat-agent-flow --limit 10
prefect flow-run inspect flow-abc-123

# Application logs for agent service
kubectl logs -n ai-platform deploy/agent-engine -f | jq '.'

# Filter by flow run
kubectl logs -n ai-platform deploy/agent-engine | jq 'select(.flow_run_id == "flow-abc-123")'
```

---

### Step 8: Document Retrieval — RAG (pgvector + MinIO)

**What happens:**

The agent's `retrieve_documents` node queries pgvector for semantically similar content.

**SQL executed:**

```sql
-- Embed query: "Tell me about Artificial Intelligence" → vector
-- Search with HNSW index

EXPLAIN ANALYZE
SELECT
    id,
    content,
    source,
    metadata,
    1 - (embedding <=> $1::vector) AS similarity
FROM documents
WHERE metadata->>'category' IN ('technology', 'general')
ORDER BY embedding <=> $1::vector
LIMIT 3;

-- Output:
-- Index Scan using documents_embedding_hnsw_idx on documents
--   Index Cond: (embedding <=> '[0.12,-0.34,0.56,...]'::vector)
--   Rows Removed by Filter: 0
--   Planning Time: 0.2ms
--   Execution Time: 7.8ms
--
-- Results:
-- id=142 | similarity=0.94 | "AI is a branch of computer science that..."
-- id=89  | similarity=0.91 | "Machine learning, a subset of AI, enables..."
-- id=203 | similarity=0.87 | "Deep learning uses multi-layered neural..."
```

**How to debug:**

```bash
# Connect to PostgreSQL
kubectl exec -it -n ai-platform deploy/postgres -- psql -U admin -d aiplatform

# Check index status
SELECT * FROM pg_indexes WHERE tablename = 'documents';

# Check table size
SELECT count(*) FROM documents;
SELECT pg_size_pretty(pg_total_relation_size('documents'));

# Run the search manually
SET hnsw.ef_search = 100;
SELECT id, content, 1-(embedding <=> '[...]'::vector) AS sim
FROM documents ORDER BY embedding <=> '[...]'::vector LIMIT 5;

# Check slow queries
SELECT * FROM pg_stat_activity WHERE state = 'active';

# MinIO — check original documents
kubectl exec -it -n ai-platform deploy/minio -- mc ls local/documents/raw/
```

---

### Step 9: LLM Inference — vLLM on KubeRay

**What happens:**

vLLM receives the chat completion request with the RAG context and streams tokens back.

**Request received:**

```json
{
  "model": "meta-llama/Meta-Llama-3-70B-Instruct",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant. Answer based on the following context:\n\nAI is a branch of computer science that aims to create intelligent machines...\n\nMachine learning, a subset of AI, enables systems to learn from data...\n\nDeep learning uses multi-layered neural networks to model complex patterns..."
    },
    {
      "role": "user",
      "content": "Tell me about Artificial Intelligence"
    }
  ],
  "stream": true,
  "temperature": 0.7,
  "max_tokens": 1024
}
```

**vLLM server logs:**

```
INFO:     Received request abc123: prompt_tokens=847
INFO:     Prefix cache: 124 tokens cached (system prompt prefix)
INFO:     Scheduled request abc123 in batch (batch_size=13)
INFO:     GPU 0 KV cache: 72.3% utilized (14,832/20,480 pages)
INFO:     GPU 1 KV cache: 71.8% utilized
INFO:     Generated 312 tokens in 1.803s (173 tok/s)
INFO:     Request abc123 completed: prompt=847, completion=312, total=1159 tokens
```

**vLLM Prometheus metrics during this request:**

```
vllm:num_requests_running 13
vllm:num_requests_waiting 0
vllm:gpu_cache_usage_perc{gpu="0"} 0.723
vllm:gpu_cache_usage_perc{gpu="1"} 0.718
vllm:avg_prompt_throughput_toks_per_s 2340
vllm:avg_generation_throughput_toks_per_s 173
vllm:time_to_first_token_seconds{quantile="0.5"} 0.089
vllm:time_to_first_token_seconds{quantile="0.99"} 0.234
```

**How to debug:**

```bash
# vLLM logs
kubectl logs -n ai-platform deploy/vllm -f

# vLLM metrics
kubectl port-forward -n ai-platform svc/vllm 8000:8000
curl http://localhost:8000/metrics | grep vllm

# GPU status
kubectl exec -it -n ai-platform deploy/vllm -- nvidia-smi

# Test inference directly
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"meta-llama/Meta-Llama-3-70B-Instruct","messages":[{"role":"user","content":"test"}],"max_tokens":10}'

# Ray dashboard (KubeRay)
kubectl port-forward -n ai-platform svc/vllm-cluster-head-svc 8265:8265
# Open http://localhost:8265

# Check KubeRay cluster status
kubectl get raycluster -n ai-platform
kubectl get rayservice -n ai-platform
```

---

### Step 9b: CPU Fallback — llama.cpp

**When this activates:**

```python
# Circuit breaker logic
if circuit_breaker.state == CircuitState.OPEN:
    # vLLM has failed 5+ times → route to llama.cpp
    response = await call_llamacpp(messages)
    response["_fallback"] = True
```

**How to debug fallback:**

```bash
# Check circuit breaker state (in agent logs)
kubectl logs -n ai-platform deploy/agent-engine | jq 'select(.circuit_breaker)'

# llama.cpp logs
kubectl logs -n ai-platform deploy/llama-cpp -f

# llama.cpp health
kubectl exec -n ai-platform deploy/llama-cpp -- curl -s localhost:8080/health

# Test llama.cpp directly
kubectl port-forward -n ai-platform svc/llama-cpp-svc 8080:8080
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}],"max_tokens":10}'
```

---

### Step 10: Response Flows Back

The 312 generated tokens stream back through every layer in reverse:

```
vLLM → Agent Engine → FastAPI → Istio mTLS → Envoy → Browser

Timeline:
  0ms      — vLLM starts generating
  89ms     — First token generated (TTFT)
  90ms     — Token 1 arrives at browser (user sees "Artificial")
  103ms    — Token 2 ("Intelligence")
  ...every ~5.8ms another token...
  1803ms   — Token 312 ("applications.")
  1810ms   — vLLM signals stream complete
  1815ms   — Agent quality check (5ms)
  1820ms   — FastAPI closes SSE stream
  1825ms   — Background: cache store (Redis)
  1827ms   — Background: cost recording
  ~2850ms  — User sees complete response, Send button re-enabled
```

---

## 4. Cross-Cutting Concerns

### 4.1 Observability — OTEL → Grafana

**Every service produces telemetry via OpenTelemetry:**

#### The Complete Trace (as seen in Grafana Tempo)

```
Trace ID: a1b2c3d4e5f67890abcdef1234567890
Duration: 2847ms

├── [ai-api] POST /graphql                         0ms ─────────────────────── 2847ms
│   ├── [ai-api] graphql.chat                      5ms ─────────────────────── 2845ms
│   │   ├── [ai-api] semantic_cache_lookup         7ms ── 9ms (2ms)
│   │   ├── [ai-api] feast_feature_lookup          10ms ── 13ms (3ms)
│   │   ├── [agent] prefect.chat_agent_flow        15ms ────────────────────── 2838ms
│   │   │   ├── [agent] validate_input             16ms ── 17ms (1ms)
│   │   │   ├── [agent] langgraph.classify         18ms ── 20ms (2ms)
│   │   │   ├── [agent] langgraph.retrieve_docs    21ms ──── 30ms (9ms)
│   │   │   │   ├── [pgvector] embed_query         21ms ── 24ms (3ms)
│   │   │   │   └── [pgvector] hnsw_search         24ms ── 30ms (6ms)
│   │   │   ├── [agent] langgraph.generate         31ms ─────────────────── 2833ms
│   │   │   │   └── [vllm] chat.completions        35ms ─────────────────── 1838ms
│   │   │   │       ├── [vllm] tokenize            35ms ── 37ms (2ms)
│   │   │   │       ├── [vllm] prefix_cache        37ms ── 38ms (1ms)
│   │   │   │       ├── [vllm] inference           38ms ────────────────── 1835ms
│   │   │   │       └── [vllm] detokenize          1835ms ── 1838ms (3ms)
│   │   │   └── [agent] langgraph.quality_check    2833ms ── 2838ms (5ms)
│   │   └── [ai-api] cache_store (async)           2840ms ── 2845ms (5ms)
```

#### How to view this trace:

```bash
# 1. Open Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000
# Open http://localhost:3000

# 2. Go to Explore → Select "Tempo" data source

# 3. Search by trace ID:
#    Paste: a1b2c3d4e5f67890abcdef1234567890

# 4. Or search by attributes:
#    service.name = "ai-api" AND http.method = "POST"

# 5. Click on a trace to see the waterfall diagram
```

#### Logs correlated with trace (Loki):

```bash
# In Grafana → Explore → Loki
# Query:
{service_name="ai-api"} |= "a1b2c3d4e5f67890abcdef1234567890"

# Or from the Tempo trace view, click "Logs for this span" button
# This automatically queries Loki with the trace ID
```

#### Metrics dashboard (Mimir/Prometheus):

```promql
# Request rate for the chat endpoint
rate(http_server_request_duration_seconds_count{http_route="/graphql"}[5m])

# P99 latency
histogram_quantile(0.99, rate(http_server_request_duration_seconds_bucket{http_route="/graphql"}[5m]))

# LLM tokens per second
vllm:avg_generation_throughput_toks_per_s

# Cache hit rate
rate(semantic_cache_hits_total[5m]) / rate(semantic_cache_lookups_total[5m])

# Error rate
rate(http_server_request_duration_seconds_count{http_status_code=~"5.."}[5m])
/ rate(http_server_request_duration_seconds_count[5m])
```

---

### 4.2 Cost Tracking — OpenCost

**For this specific query:**

```
Cost breakdown:
├── GPU time: 1.8s on A100 ($3.00/hr) = $0.0015
├── CPU time: 2.8s across services     = $0.0002
├── Memory: ~4GB for 2.8s              = $0.0001
├── Network: ~5KB transferred           = $0.0000
└── Total: $0.0018 (actual compute)
    + Amortized overhead: $0.0016
    = $0.0034 per query
```

```bash
# Query OpenCost for this namespace
kubectl port-forward -n opencost svc/opencost 9003:9003
curl "http://localhost:9003/allocation/compute?window=1h&aggregate=pod&namespace=ai-platform" | jq '.'
```

---

### 4.3 Policy Enforcement — OPA Gatekeeper

**Policies active during this request's deployment:**

```bash
# These policies were evaluated when the pods were deployed (not per-request):
kubectl get constraints

# Active policies:
# ✓ require-team-env-labels    — All deployments have team/env labels
# ✓ deny-root-containers       — No containers run as root
# ✓ require-resource-limits    — All containers have CPU/memory limits
# ✓ approved-models-only       — Only approved LLM models deployed
# ✓ only-trusted-registries    — Images from approved registries only

# Check violations
kubectl get constraints -o custom-columns='NAME:.metadata.name,VIOLATIONS:.status.totalViolations'
```

---

### 4.4 GitOps & CI/CD — Argo CD + Tekton

**How these services got deployed:**

```
1. Developer pushed code to source repo
2. Tekton Pipeline ran: lint → test → build → push image
3. Tekton updated the deploy repo with new image tag
4. Argo CD detected the change (auto-sync)
5. Argo CD deployed updated manifests to cluster
6. Gatekeeper validated the manifests (policies passed)
7. Pods rolled out with zero downtime
```

```bash
# Check Argo CD sync status
argocd app list
argocd app get ai-api

# Check recent Tekton pipeline runs
tkn pipelinerun list --limit 5

# Check deployment history
kubectl rollout history deployment/fastapi -n ai-platform
```

---

### 4.5 Developer Experience

**How a developer would debug this flow locally:**

```bash
# Option 1: mirrord — run locally against K8s
mirrord exec --target deployment/fastapi -- uvicorn main:app --port 8000
# Now local FastAPI connects to K8s Redis, PostgreSQL, vLLM
# Set breakpoints in VS Code, step through the code

# Option 2: Skaffold — deploy changes instantly
skaffold dev -p dev
# Edit code → Skaffold syncs files → uvicorn reloads → test in ~2 seconds

# Option 3: DevContainer — full isolated env
# Open in VS Code → Reopen in Container → all tools ready
```

---

## 5. Complete Trace ID Journey

The trace ID (`a1b2c3d4e5f67890abcdef1234567890`) appears in:

| Location | How to Find |
|----------|-------------|
| **Browser** | DevTools → Network → Response Headers → `X-Trace-ID` |
| **Envoy** | Access log → `x_request_id` field |
| **Istio** | ztunnel log → `trace_id` in OTEL context |
| **FastAPI** | Application log → `trace_id` field |
| **Redis** | MONITOR output (trace in key or command context) |
| **Feast** | Python SDK logs with trace context |
| **Prefect** | Flow run metadata → OTEL trace ID |
| **LangGraph** | Embedded in agent state |
| **pgvector** | PostgreSQL logs with `application_name` containing trace |
| **vLLM** | Server logs → `request_id` (mapped to trace) |
| **Grafana Tempo** | Search by trace ID → full waterfall view |
| **Grafana Loki** | `{trace_id="a1b2c3..."}` → all logs for this request |
| **OpenCost** | Correlated via pod/timestamp with Prometheus labels |

**Searching across everything:**

```bash
# One command to find this request everywhere
TRACE_ID="a1b2c3d4e5f67890abcdef1234567890"

# Grafana Tempo (traces)
# URL: http://grafana:3000/explore?left={"datasource":"Tempo","queries":[{"queryType":"traceql","query":"${TRACE_ID}"}]}

# Grafana Loki (logs)
# Query: {namespace="ai-platform"} |= "$TRACE_ID"

# Kubernetes logs (all pods)
kubectl logs -n ai-platform --all-containers --prefix -l app.kubernetes.io/part-of=ai-platform --since=5m | grep "$TRACE_ID"
```

---

## 6. How to Debug Each Layer

### Quick Reference: Debug Commands

| Layer | Health Check | Logs | Metrics | Interactive |
|-------|-------------|------|---------|-------------|
| **Next.js** | `curl /health` | Browser DevTools | Lighthouse | React DevTools |
| **Envoy** | `:9901/ready` | `kubectl logs envoy` | `:9901/stats` | `:9901/` admin |
| **Istio** | `istioctl analyze` | `kubectl logs ztunnel` | Kiali dashboard | `istioctl proxy-config` |
| **FastAPI** | `curl /health` | `kubectl logs fastapi` | `/metrics` | `/graphql` playground |
| **Redis** | `redis-cli PING` | `redis-cli MONITOR` | `INFO` command | `redis-cli` |
| **Feast** | `feast feature-views list` | Python logging | Registry metrics | Feast SDK |
| **Prefect** | Prefect UI | Prefect UI + logs | Prefect UI | `prefect flow-run inspect` |
| **pgvector** | `pg_isready` | PostgreSQL logs | `pg_stat_*` views | `psql` |
| **MinIO** | `/minio/health/ready` | `mc admin trace` | MinIO console | `mc` CLI |
| **vLLM** | `curl /health` | `kubectl logs vllm` | `/metrics` endpoint | OpenAI client |
| **llama.cpp** | `curl /health` | `kubectl logs llama-cpp` | `/slots` endpoint | `curl` |
| **OTEL** | Collector health | Collector logs | Pipeline metrics | Grafana |
| **OpenCost** | API endpoint | Pod logs | `/allocation` API | UI |
| **Argo CD** | `argocd app get` | UI + pod logs | Sync status | Argo CD UI |
| **Tekton** | `tkn pipelinerun list` | `tkn pipelinerun logs` | Dashboard | Tekton Dashboard |
| **Gatekeeper** | `kubectl get constraints` | Pod logs | Violation count | `opa eval` |

---

## 7. Live Debugging Walkthrough

### Scenario: "The chat response is slow (>5 seconds)"

**Step 1: Check the trace in Grafana Tempo**

```
Open Grafana → Explore → Tempo → Search for recent slow traces:
  duration > 5s AND service.name = "ai-api"
```

**Step 2: Identify the bottleneck from the waterfall**

```
Example trace (slow):
├── POST /graphql                              0ms ────────────────── 6200ms
│   ├── semantic_cache_lookup                  5ms ── 7ms (2ms)        ✓ fast
│   ├── feast_feature_lookup                   8ms ── 12ms (4ms)       ✓ fast
│   ├── prefect.chat_agent_flow                13ms ───────────────── 6195ms
│   │   ├── validate_input                     14ms ── 15ms            ✓ fast
│   │   ├── langgraph.retrieve_docs            16ms ──── 2025ms (2009ms) ← SLOW!
│   │   │   ├── embed_query                    16ms ── 19ms (3ms)      ✓ fast
│   │   │   └── hnsw_search                    20ms ──── 2025ms        ← pgvector is slow
│   │   └── langgraph.generate                 2026ms ─── 6190ms       ← vLLM also slow
│   │       └── vllm chat.completions          2030ms ─── 6188ms       ← confirm vLLM
```

**Step 3: Investigate pgvector (2 seconds for a search!)**

```bash
# Check PostgreSQL
kubectl exec -it -n ai-platform deploy/postgres -- psql -U admin -d aiplatform

# Check if HNSW index exists
SELECT * FROM pg_indexes WHERE tablename = 'documents';

# Check if index is being used
EXPLAIN ANALYZE
SELECT id, 1-(embedding <=> '[0.1,...]'::vector) AS sim
FROM documents ORDER BY embedding <=> '[0.1,...]'::vector LIMIT 3;

# If Seq Scan instead of Index Scan → index missing or disabled!
# Fix: CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);

# Check table bloat
SELECT pg_size_pretty(pg_total_relation_size('documents'));
VACUUM ANALYZE documents;
```

**Step 4: Investigate vLLM (4 seconds for inference)**

```bash
# Check GPU utilization
kubectl exec -it -n ai-platform deploy/vllm -- nvidia-smi
# If GPU utilization = 100% → overloaded

# Check request queue
curl http://vllm:8000/metrics | grep "num_requests_waiting"
# If > 0 → requests are queuing → need more replicas

# Check KV cache
curl http://vllm:8000/metrics | grep "gpu_cache_usage"
# If > 0.95 → KV cache full → requests are being delayed

# Solution: scale up
kubectl scale deployment vllm --replicas=3 -n ai-platform
```

---

## 8. Common Failure Scenarios

### Scenario 1: Complete failure — user sees error

```
Symptom:  User gets "Something went wrong" error
Browser:  POST /graphql → 502 Bad Gateway

Debug path:
1. Envoy logs → upstream_connect_failure
2. → FastAPI pod is crashlooping
3. kubectl logs fastapi → OOMKilled
4. → Increase memory limit in deployment.yaml
5. → Commit, push → Argo CD auto-deploys fix
```

### Scenario 2: Slow first response, subsequent responses fast

```
Symptom:  First query takes 10s, next similar ones take 200ms
Reason:   Semantic cache warming

Debug path:
1. Check cache: first query is always a MISS
2. Check vLLM: cold start (model loading on first request)
3. Solution: pre-warm cache with common queries
4. Solution: keep minimum 1 vLLM replica always running
```

### Scenario 3: Responses are wrong/hallucinated

```
Symptom:  AI gives incorrect information about the company

Debug path:
1. Check Tempo trace → look at RAG retrieval step
2. pgvector returned irrelevant documents (similarity < 0.7)
3. → Embedding model quality issue or missing documents
4. → Check MinIO: documents/raw/ — are source docs up to date?
5. → Re-run ingestion pipeline with updated documents
```

### Scenario 4: GPU failure, automatic fallback

```
Symptom:  Responses are slower but still working

Debug path:
1. Agent logs → circuit_breaker.state = "OPEN"
2. vLLM logs → CUDA out of memory / GPU driver error
3. llama.cpp serving requests (CPU fallback active)
4. → Check GPU node: kubectl describe node gpu-node-1
5. → Restart vLLM pod: kubectl delete pod vllm-xxx
6. → Circuit breaker auto-recovers after 30s (HALF_OPEN → test → CLOSED)
```

### Scenario 5: Rate limited

```
Symptom:  User gets 429 Too Many Requests

Debug path:
1. Envoy access log → rate_limit_status = "over_limit"
2. Check rate limit config: 100 req/min per IP
3. User is power user making >100 requests/minute
4. → Increase limit for authenticated users
5. → Or implement per-user rate limiting in FastAPI
```

---

## Summary

Every user query touches all 16 components. The key insight is that **observability ties everything together**:

- **Trace ID** propagates through every service
- **Grafana Tempo** shows the complete request waterfall
- **Grafana Loki** shows all logs correlated with the trace
- **Grafana Mimir** shows the metrics during the request
- **OpenCost** shows what the request cost

When something goes wrong, start with the trace in Tempo, identify the slow/failed span, then drill into that specific service's logs and metrics. The trace ID is your thread through the maze.
