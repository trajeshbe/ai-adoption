# Tech Stack Guide for Fresh Graduates

> **Audience:** You just graduated and joined the team. This document explains every
> piece of our application stack in plain language, why we chose it, and shows one
> concrete example of how it appears in our app.

---

## Table of Contents

1. [Front-end: Next.js + Tailwind CSS](#1-front-end--nextjs--tailwind-css)
2. [Ingress: Envoy (Contour)](#2-ingress--envoy-contour)
3. [Service Mesh: Istio Ambient](#3-service-mesh--istio-ambient)
4. [API Layer: FastAPI + GraphQL (Strawberry)](#4-api-layer--fastapi--graphql-strawberry)
5. [LLM Runtime: vLLM on KubeRay](#5-llm-runtime--vllm-on-kuberay)
6. [CPU Fallback: llama.cpp Server](#6-cpu-fallback--llamacpp-server)
7. [Vector DB: Postgres + pgvector](#7-vector-db--postgres--pgvector)
8. [Object Store: MinIO (Ozone-ready)](#8-object-store--minio-ozone-ready)
9. [Cache: Redis 7.2 with VSS Semantic Cache](#9-cache--redis-72-with-vss-semantic-cache)
10. [Agent DAG: Prefect 3 (LangGraph inside)](#10-agent-dag--prefect-3-langgraph-inside)
11. [Feature Store: Feast on Flink](#11-feature-store--feast-on-flink)
12. [Traces: OTEL to Grafana Tempo/Loki/Mimir](#12-traces--otel-to-grafana-tempolokimimir)
13. [Cost: OpenCost Real-time $/Inference](#13-cost--opencost-real-time-inference)
14. [GitOps: Argo CD + Tekton](#14-gitops--argo-cd--tekton)
15. [Policy: OPA Gatekeeper](#15-policy--opa-gatekeeper)
16. [Dev Loop: DevContainer + Skaffold + mirrord](#16-dev-loop--devcontainer--skaffold--mirrord)
17. [Bonus: Key Libraries You Will See Everywhere](#17-bonus--key-libraries-you-will-see-everywhere)

---

## 1. Front-end: Next.js + Tailwind CSS

### What are they?

**Next.js** is a React-based framework for building web applications. React by itself
only gives you a way to build UI components; Next.js adds routing (URL pages),
server-side rendering (SSR), and API routes so you can build a full website without
gluing together a dozen separate tools.

**Tailwind CSS** is a utility-first CSS framework. Instead of writing CSS classes like
`.btn-primary { background: blue; padding: 10px; }`, you write utility classes
directly in your HTML/JSX: `className="bg-blue-500 p-2"`. It sounds ugly at first
but turns out to be extremely fast to develop with and keeps styles consistent.

### Why do we need them?

- **Next.js** gives us fast page loads (SSR/SSG), file-based routing, and built-in
  API routes for lightweight backend endpoints.
- **Tailwind** keeps our design system consistent and removes the need for
  hand-written CSS files that grow out of control.

### Example in our app

```jsx
// app/chat/page.tsx  — the main chat page of our LLM app
"use client";

import { useState } from "react";

export default function ChatPage() {
  const [message, setMessage] = useState("");

  async function handleSend() {
    const res = await fetch("/api/chat", {
      method: "POST",
      body: JSON.stringify({ prompt: message }),
    });
    const data = await res.json();
    console.log(data.reply);
  }

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <header className="p-4 border-b border-gray-700 text-xl font-bold">
        AI Assistant
      </header>
      <main className="flex-1 overflow-y-auto p-6">
        {/* Chat messages render here */}
      </main>
      <footer className="p-4 border-t border-gray-700 flex gap-2">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="flex-1 rounded bg-gray-800 px-4 py-2 outline-none"
          placeholder="Ask something..."
        />
        <button
          onClick={handleSend}
          className="rounded bg-blue-600 px-6 py-2 hover:bg-blue-500"
        >
          Send
        </button>
      </footer>
    </div>
  );
}
```

**What is happening:** The user types a question, clicks Send, and Next.js calls our
FastAPI backend at `/api/chat`. Tailwind classes (`bg-gray-900`, `flex`, `rounded`)
handle all the styling without a single CSS file.

---

## 2. Ingress: Envoy (Contour)

### What is it?

When a user types `https://our-app.com` in their browser, the request has to enter
our Kubernetes cluster somehow. **Ingress** is the "front door."

**Envoy** is a high-performance proxy (think of it as a very smart traffic cop). It
sits at the edge of the cluster and routes incoming HTTP requests to the correct
internal service.

**Contour** is a Kubernetes Ingress controller that makes Envoy easy to configure. You
write a simple YAML file and Contour translates it into Envoy configuration
automatically.

### Why do we need it?

Without an ingress controller, external users cannot reach services inside Kubernetes.
Contour + Envoy give us:

- TLS termination (HTTPS)
- Path-based routing (`/api/*` goes to FastAPI, `/` goes to Next.js)
- Rate limiting and load balancing

### Example in our app

```yaml
# k8s/ingress.yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: app-ingress
spec:
  virtualhost:
    fqdn: our-app.example.com
    tls:
      secretName: tls-cert
  routes:
    - conditions:
        - prefix: /api
      services:
        - name: fastapi-service
          port: 8000
    - conditions:
        - prefix: /
      services:
        - name: nextjs-frontend
          port: 3000
```

**What is happening:** Any request to `our-app.example.com/api/*` is forwarded to our
FastAPI backend on port 8000. Everything else goes to the Next.js frontend on port
3000. Contour tells Envoy how to do this; you never configure Envoy directly.

---

## 3. Service Mesh: Istio Ambient

### What is it?

Imagine dozens of microservices talking to each other inside the cluster. A **service
mesh** is an invisible infrastructure layer that manages all that service-to-service
communication.

**Istio** is the most popular service mesh. Traditionally it injects a sidecar proxy
(a tiny Envoy container) next to every pod. **Istio Ambient mode** is the newer
approach where proxies run per-node instead of per-pod, which is lighter and simpler.

### Why do we need it?

- **Mutual TLS (mTLS):** Every internal call is automatically encrypted — even if a
  developer forgets to configure HTTPS.
- **Observability:** Istio generates metrics, logs, and traces for every request
  between services.
- **Traffic control:** Canary deployments, retries, circuit breaking — all without
  changing application code.

### Example in our app

```yaml
# k8s/istio-auth-policy.yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-api-to-vllm
spec:
  selector:
    matchLabels:
      app: vllm-inference
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/default/sa/fastapi-sa"]
      to:
        - operation:
            methods: ["POST"]
            paths: ["/v1/completions"]
```

**What is happening:** This policy says "only the FastAPI service (identified by its
service account) is allowed to call the vLLM inference endpoint." If any other service
tries, Istio blocks it. Zero code changes needed.

---

## 4. API Layer: FastAPI + GraphQL (Strawberry)

### What are they?

**FastAPI** is a modern Python web framework for building APIs. It is extremely fast
(built on top of Starlette and uvicorn), has automatic request validation, and
generates interactive API docs (Swagger UI) for free.

**Pydantic** (used heavily by FastAPI) is a data validation library. You define a
Python class with type hints, and Pydantic makes sure incoming data matches the shape
you expect. If someone sends `{"age": "not-a-number"}` and you expected an `int`,
Pydantic raises a clear error.

**GraphQL** is an alternative to REST. Instead of having dozens of endpoints
(`/users`, `/users/1/posts`, `/users/1/posts/5/comments`), you have a single
endpoint where the client specifies exactly what data it needs. No over-fetching, no
under-fetching.

**Strawberry** is a Python library that lets you write GraphQL schemas using Python
type hints — it feels natural alongside FastAPI and Pydantic.

### Why do we need them?

- **FastAPI + Pydantic** = validated, documented APIs with minimal boilerplate.
- **GraphQL (Strawberry)** = the frontend team fetches exactly the data they need in
  a single request instead of calling five REST endpoints.

### Example in our app

```python
# app/api/schema.py
import strawberry
from pydantic import BaseModel

# --- Pydantic model for validation ---
class ChatRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7

# --- Strawberry GraphQL types ---
@strawberry.type
class ChatResponse:
    reply: str
    tokens_used: int
    model: str

@strawberry.type
class Query:
    @strawberry.field
    def health(self) -> str:
        return "ok"

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def ask(self, prompt: str, max_tokens: int = 512) -> ChatResponse:
        # Calls the LLM service internally
        result = await call_llm(prompt, max_tokens)
        return ChatResponse(
            reply=result.text,
            tokens_used=result.usage,
            model=result.model_name,
        )

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

```python
# app/main.py
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from app.api.schema import schema

app = FastAPI(title="AI Assistant API")
app.include_router(GraphQLRouter(schema), prefix="/graphql")

@app.get("/health")
def health():
    return {"status": "ok"}
```

**What is happening:** The frontend sends a GraphQL mutation like
`mutation { ask(prompt: "Explain recursion") { reply tokensUsed } }` to `/graphql`.
FastAPI handles the HTTP layer, Strawberry resolves the GraphQL, and Pydantic
validates any REST payloads.

---

## 5. LLM Runtime: vLLM on KubeRay

### What are they?

**vLLM** is an open-source library for serving Large Language Models (LLMs) with very
high throughput. It uses a technique called **PagedAttention** that manages GPU memory
more efficiently, letting you serve more concurrent users with the same hardware.

**Ray** is a distributed computing framework — it lets you spread work across many
machines. **KubeRay** is the Kubernetes operator for Ray, meaning it creates and
manages Ray clusters inside Kubernetes automatically.

### Why do we need them?

- **vLLM** makes LLM inference 2-10x faster than a naive implementation.
- **KubeRay** auto-scales GPU workers. If traffic spikes, Kubernetes spins up more
  Ray workers with GPUs. When traffic drops, it scales down to save cost.

### Example in our app

```yaml
# k8s/vllm-ray-cluster.yaml
apiVersion: ray.io/v1
kind: RayService
metadata:
  name: vllm-service
spec:
  serveConfigV2: |
    applications:
      - name: llm
        import_path: serve_vllm:deployment
        runtime_env:
          pip: ["vllm==0.4.1"]
        deployments:
          - name: VLLMDeployment
            num_replicas: 2
            ray_actor_options:
              num_gpus: 1
  rayClusterConfig:
    headGroupSpec:
      template:
        spec:
          containers:
            - name: ray-head
              image: rayproject/ray-ml:2.11.0-gpu
              resources:
                limits:
                  nvidia.com/gpu: 1
    workerGroupSpecs:
      - replicas: 2
        template:
          spec:
            containers:
              - name: ray-worker
                image: rayproject/ray-ml:2.11.0-gpu
                resources:
                  limits:
                    nvidia.com/gpu: 1
```

```python
# serve_vllm.py  — the Ray Serve deployment
from vllm import LLM, SamplingParams
from ray import serve

@serve.deployment(num_replicas=2, ray_actor_options={"num_gpus": 1})
class VLLMDeployment:
    def __init__(self):
        self.llm = LLM(model="mistralai/Mistral-7B-Instruct-v0.2")

    async def __call__(self, request):
        data = await request.json()
        params = SamplingParams(
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 512),
        )
        outputs = self.llm.generate([data["prompt"]], params)
        return {"text": outputs[0].outputs[0].text}

deployment = VLLMDeployment.bind()
```

**What is happening:** KubeRay manages a cluster of GPU machines. vLLM loads the
Mistral-7B model on each GPU worker. When our FastAPI backend calls the inference
endpoint, Ray distributes the request to an available GPU worker, and vLLM generates
the response efficiently.

---

## 6. CPU Fallback: llama.cpp Server

### What is it?

**llama.cpp** is a C/C++ implementation for running LLMs on CPU (no GPU needed). It
uses quantization (reducing model precision from 32-bit to 4-bit) to make models small
enough to run on regular machines.

The **llama.cpp server** exposes an OpenAI-compatible HTTP API, so switching between
GPU and CPU inference requires zero code changes in the calling service.

### Why do we need it?

GPUs are expensive and sometimes unavailable. When:

- GPU nodes are fully loaded
- Running in a dev/test environment without GPUs
- The request is low-priority and latency is acceptable

...we fall back to llama.cpp on CPU nodes. The model is smaller (quantized), so
responses are slower but still functional.

### Example in our app

```yaml
# k8s/llama-cpp-fallback.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llama-cpp-fallback
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: llama-server
          image: ghcr.io/ggerganov/llama.cpp:server
          args:
            - "--model"
            - "/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
            - "--host"
            - "0.0.0.0"
            - "--port"
            - "8080"
            - "--ctx-size"
            - "4096"
          resources:
            requests:
              cpu: "4"
              memory: "8Gi"
          volumeMounts:
            - name: model-storage
              mountPath: /models
```

```python
# app/services/llm_router.py
import httpx

VLLM_URL = "http://vllm-service:8000/v1/completions"
LLAMA_CPP_URL = "http://llama-cpp-fallback:8080/v1/completions"

async def call_llm(prompt: str, max_tokens: int = 512) -> dict:
    """Try GPU inference first; fall back to CPU if unavailable."""
    payload = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(VLLM_URL, json=payload)
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPError, httpx.TimeoutException):
        # GPU unavailable — fall back to CPU
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(LLAMA_CPP_URL, json=payload)
            return resp.json()
```

**What is happening:** Our `call_llm` function first tries the fast GPU path (vLLM).
If that times out or errors, it automatically retries against the llama.cpp CPU
server. Both expose the same `/v1/completions` API shape, so the switch is seamless.

---

## 7. Vector DB: Postgres + pgvector

### What are they?

**PostgreSQL (Postgres)** is the world's most advanced open-source relational
database. You probably used MySQL in college — Postgres is similar but more powerful.

**pgvector** is a Postgres extension that adds support for **vector similarity
search**. In AI applications, we convert text into numerical vectors (embeddings). To
find "similar" documents, we need to search for vectors that are close together in
high-dimensional space. pgvector makes Postgres do this natively.

### Why do we need them?

Our app implements **Retrieval Augmented Generation (RAG)**. When a user asks a
question:

1. Convert the question to a vector embedding.
2. Search pgvector for the most similar document chunks.
3. Feed those chunks as context to the LLM.

Using Postgres (which we already have for relational data) instead of a separate
vector database like Pinecone means one fewer system to manage.

### Example in our app

```sql
-- migrations/001_create_documents.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id          BIGSERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector(1536),       -- 1536 dimensions (OpenAI ada-002 size)
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Create an index for fast approximate nearest neighbor search
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

```python
# app/services/retrieval.py
from sqlalchemy import text
from app.db import async_session

async def find_similar_docs(query_embedding: list[float], top_k: int = 5):
    """Find the top_k most similar documents to the query."""
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT id, title, content,
                       1 - (embedding <=> :embedding) AS similarity
                FROM documents
                ORDER BY embedding <=> :embedding
                LIMIT :top_k
            """),
            {"embedding": str(query_embedding), "top_k": top_k},
        )
        return result.fetchall()
```

**What is happening:** When a user asks "How do I reset my password?", we convert that
question into a 1536-dimensional vector and use the `<=>` operator (cosine distance)
to find the 5 most relevant knowledge-base articles. Those articles become context for
the LLM's answer.

> **What is SQLAlchemy?** It is Python's most popular ORM (Object-Relational Mapper).
> Instead of writing raw SQL strings everywhere, you define Python classes that
> represent database tables and SQLAlchemy translates your Python operations into SQL.
> Think of it as a translator between Python objects and database rows.

---

## 8. Object Store: MinIO (Ozone-ready)

### What is it?

**MinIO** is an open-source, S3-compatible object storage server. If you have used
Amazon S3 to store files (images, PDFs, model weights), MinIO is the same thing but
runs on your own servers.

"**Ozone-ready**" means our setup is designed to migrate to Apache Ozone (a
distributed object store for Hadoop ecosystems) if we scale to petabyte-level data in
the future.

**Object storage** stores data as "objects" (files + metadata) in flat "buckets"
rather than in a hierarchical file system. It is ideal for unstructured data like
documents, images, and ML model files.

### Why do we need it?

- Store uploaded documents (PDFs, CSVs) that users want the AI to analyze.
- Store trained model weights and GGUF files for llama.cpp.
- Store conversation logs and exported reports.
- S3-compatible API means any tool that works with AWS S3 works with MinIO.

### Example in our app

```python
# app/services/storage.py
from minio import Minio
from io import BytesIO

client = Minio(
    endpoint="minio.storage.svc:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False,
)

BUCKET = "user-uploads"

async def upload_document(user_id: str, filename: str, data: bytes) -> str:
    """Upload a user's document and return the object path."""
    object_name = f"{user_id}/{filename}"

    client.put_object(
        bucket_name=BUCKET,
        object_name=object_name,
        data=BytesIO(data),
        length=len(data),
        content_type="application/pdf",
    )
    return object_name


async def download_document(object_name: str) -> bytes:
    """Download a document from MinIO."""
    response = client.get_object(BUCKET, object_name)
    return response.read()
```

**What is happening:** When a user uploads a PDF for the AI to analyze, we store it in
MinIO under their user ID. Later, the RAG pipeline downloads the PDF, splits it into
chunks, generates embeddings, and stores them in pgvector. The original file stays in
MinIO as the source of truth.

---

## 9. Cache: Redis 7.2 with VSS Semantic Cache

### What is it?

**Redis** is an in-memory data store — think of it as a super-fast dictionary that
lives in RAM. It is commonly used for caching (storing frequently accessed data so you
don't hit the database every time).

**Redis VSS (Vector Similarity Search)** is a module in Redis 7.2+ that supports
vector search — similar to pgvector but entirely in memory, making it much faster.

**Semantic cache** means we cache LLM responses based on the *meaning* of the query,
not the exact text. "What is Python?" and "Tell me about the Python language" are
different strings but semantically similar — a semantic cache can return the same
cached answer for both.

### Why do we need it?

LLM inference is expensive (GPU time costs money). If 100 users ask roughly the same
question, we should generate the answer once and serve it from cache 99 times. Redis
semantic cache does this by comparing query embeddings instead of exact strings.

### Example in our app

```python
# app/services/semantic_cache.py
import redis
import numpy as np
import json

r = redis.Redis(host="redis.cache.svc", port=6379)

SIMILARITY_THRESHOLD = 0.92  # If similarity > 92%, use cached response

async def get_cached_response(query_embedding: list[float]) -> str | None:
    """Check if a semantically similar query was already answered."""
    results = r.execute_command(
        "FT.SEARCH", "idx:cache",
        f"(*)=>[KNN 1 @embedding $vec AS score]",
        "PARAMS", "2", "vec", np.array(query_embedding, dtype=np.float32).tobytes(),
        "RETURN", "2", "score", "response",
        "DIALECT", "2",
    )

    if results[0] > 0:
        score = float(results[2][1])  # cosine similarity
        if score >= SIMILARITY_THRESHOLD:
            return results[2][3].decode()  # cached response

    return None


async def cache_response(query_embedding: list[float], response: str):
    """Store a new query-response pair in the semantic cache."""
    cache_id = f"cache:{hash(response) & 0xFFFFFFFF}"
    r.hset(cache_id, mapping={
        "embedding": np.array(query_embedding, dtype=np.float32).tobytes(),
        "response": response,
    })
    r.expire(cache_id, 3600)  # TTL: 1 hour
```

**What is happening:** Before calling the LLM, we check Redis: "Has anyone asked
something similar in the past hour?" If yes (similarity > 92%), we return the cached
answer instantly — saving GPU cost and reducing latency from seconds to milliseconds.

---

## 10. Agent DAG: Prefect 3 (LangGraph inside)

### What are they?

**Prefect** is a workflow orchestration tool. Think of it as a scheduler that runs
tasks in the right order, handles retries on failure, and shows you a dashboard of
what ran and what broke. Version 3 is the latest with a cleaner Python-native API.

**LangGraph** is a library (from the LangChain ecosystem) for building stateful,
multi-step AI agents. An "agent" might need to: (1) search documents, (2) call an
API, (3) summarize results, (4) ask the user for clarification — LangGraph models
this as a directed acyclic graph (DAG) of steps.

**DAG (Directed Acyclic Graph):** Tasks have dependencies — Task B can only run after
Task A finishes. The "directed" means one-way arrows, and "acyclic" means no circular
dependencies.

### Why do we need them?

- **Prefect** handles the operational side: scheduling, retries, logging, alerting.
- **LangGraph** handles the AI logic: which tools to call, what to do with the
  results, when to loop back and try again.
- Together: Prefect orchestrates when and how LangGraph agents run; LangGraph decides
  what the agent does at each step.

### Example in our app

```python
# app/agents/research_agent.py
from prefect import flow, task
from langgraph.graph import StateGraph, END
from typing import TypedDict

# --- LangGraph agent definition ---
class AgentState(TypedDict):
    question: str
    documents: list[str]
    answer: str

def retrieve_docs(state: AgentState) -> AgentState:
    """Search vector DB for relevant documents."""
    docs = vector_search(state["question"])
    return {**state, "documents": docs}

def generate_answer(state: AgentState) -> AgentState:
    """Use LLM to answer based on retrieved docs."""
    context = "\n".join(state["documents"])
    answer = call_llm(f"Context: {context}\nQuestion: {state['question']}")
    return {**state, "answer": answer}

# Build the LangGraph DAG
graph = StateGraph(AgentState)
graph.add_node("retrieve", retrieve_docs)
graph.add_node("generate", generate_answer)
graph.add_edge("retrieve", "generate")
graph.add_edge("generate", END)
graph.set_entry_point("retrieve")
agent = graph.compile()

# --- Prefect orchestration ---
@task(retries=3, retry_delay_seconds=10)
def run_research_agent(question: str) -> str:
    result = agent.invoke({"question": question, "documents": [], "answer": ""})
    return result["answer"]

@flow(name="research-pipeline")
def research_pipeline(questions: list[str]):
    for q in questions:
        answer = run_research_agent(q)
        save_to_db(q, answer)
```

**What is happening:** Prefect schedules and monitors the research pipeline. For each
question, LangGraph runs a two-step agent: first retrieve documents, then generate an
answer. If the LLM call fails, Prefect automatically retries up to 3 times.

---

## 11. Feature Store: Feast on Flink

### What are they?

**Feast (Feature Store)** is an open-source tool for managing and serving ML features.
A "feature" is a computed value used as input to a model — for example, "number of
messages this user sent in the last hour" or "average response time."

**Apache Flink** is a stream-processing framework. It processes data in real-time as
it flows through the system (unlike batch processing, which waits to collect all data
first).

### Why do we need them?

- **Feast** ensures that the features used during training are the exact same features
  used during inference (this consistency is called "training-serving skew prevention").
- **Flink** computes features in real-time from event streams (user activity, system
  metrics) and pushes them to Feast's online store.
- Together, our LLM system can make decisions based on fresh, computed features rather
  than stale data.

### Example in our app

```python
# feature_repo/features.py
from feast import Entity, Feature, FeatureView, FileSource, ValueType
from datetime import timedelta

# Define the user entity
user = Entity(name="user_id", value_type=ValueType.STRING)

# Define where raw features come from
user_activity_source = FileSource(
    path="s3://minio/features/user_activity.parquet",
    timestamp_field="event_timestamp",
)

# Define the feature view
user_features = FeatureView(
    name="user_activity_features",
    entities=[user],
    ttl=timedelta(hours=1),
    features=[
        Feature(name="messages_last_hour", dtype=ValueType.INT64),
        Feature(name="avg_response_length", dtype=ValueType.FLOAT),
        Feature(name="topic_diversity_score", dtype=ValueType.FLOAT),
    ],
    source=user_activity_source,
)
```

```python
# app/services/personalization.py
from feast import FeatureStore

store = FeatureStore(repo_path="./feature_repo")

async def get_user_context(user_id: str) -> dict:
    """Fetch real-time user features to personalize LLM responses."""
    features = store.get_online_features(
        features=[
            "user_activity_features:messages_last_hour",
            "user_activity_features:avg_response_length",
            "user_activity_features:topic_diversity_score",
        ],
        entity_rows=[{"user_id": user_id}],
    ).to_dict()
    return features
```

**What is happening:** Flink continuously computes user activity features in real-time.
Feast stores them. Before generating an LLM response, we fetch the user's features to
personalize behavior — for example, a power user (high message count, diverse topics)
might get more concise, expert-level answers.

---

## 12. Traces: OTEL to Grafana Tempo/Loki/Mimir

### What are they?

**OpenTelemetry (OTEL)** is an open standard for collecting three types of telemetry
data:

1. **Traces** — the journey of a single request through all services.
2. **Logs** — text messages like "User 123 asked a question."
3. **Metrics** — numerical measurements like "requests per second" or "p99 latency."

The Grafana stack stores and visualizes this data:

- **Tempo** stores traces.
- **Loki** stores logs.
- **Mimir** stores metrics.

You view all of them in **Grafana** dashboards.

### Why do we need them?

When a user says "the app is slow," you need to know: Was it the API? The LLM? The
database? OTEL traces show you exactly where time was spent. Without observability,
debugging a distributed system is like finding a needle in a haystack, blindfolded.

### Example in our app

```python
# app/middleware/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Setup
provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="otel-collector:4317"))
)
trace.set_tracer_provider(provider)

# Auto-instrument FastAPI (every request gets a trace automatically)
FastAPIInstrumentor.instrument_app(app)

# Manual span for LLM calls
tracer = trace.get_tracer(__name__)

async def call_llm_with_tracing(prompt: str) -> str:
    with tracer.start_as_current_span("llm-inference") as span:
        span.set_attribute("prompt.length", len(prompt))
        span.set_attribute("model", "mistral-7b")

        result = await call_llm(prompt)

        span.set_attribute("response.tokens", result.tokens_used)
        span.set_attribute("inference.latency_ms", result.latency_ms)
        return result.text
```

**What is happening:** Every request that hits FastAPI is automatically traced. We
also add a custom span around LLM inference so we can see exactly how long the model
took. All this data flows through the OTEL collector to Tempo. In Grafana, you can
click on a slow request and see a waterfall diagram of every step.

---

## 13. Cost: OpenCost Real-time $/Inference

### What is it?

**OpenCost** is an open-source tool that monitors Kubernetes resource usage and
translates it into real dollar costs. It knows the price of your cloud instances and
maps CPU/GPU/memory usage per pod to actual cost.

### Why do we need it?

LLM inference on GPUs is expensive. We need to know:

- How much does each inference call cost?
- Which users/teams are consuming the most resources?
- Are we overpaying for idle GPU nodes?

OpenCost answers these questions in real-time, not at the end of the month when the
cloud bill arrives.

### Example in our app

```yaml
# k8s/opencost.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opencost
  namespace: monitoring
spec:
  template:
    spec:
      containers:
        - name: opencost
          image: ghcr.io/opencost/opencost:1.108
          env:
            - name: CLUSTER_ID
              value: "ai-platform-prod"
            - name: CLOUD_PROVIDER_API_KEY
              valueFrom:
                secretKeyRef:
                  name: cloud-creds
                  key: api-key
          ports:
            - containerPort: 9003  # cost API
```

```python
# app/services/cost_tracker.py
import httpx

OPENCOST_API = "http://opencost.monitoring.svc:9003/allocation/compute"

async def get_inference_cost(window: str = "1h") -> dict:
    """Get the cost of LLM inference in the last time window."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(OPENCOST_API, params={
            "window": window,
            "filterNamespaces": "inference",
            "aggregate": "pod",
        })
        data = resp.json()

    total_cost = sum(
        pod["totalCost"] for pod in data["data"][0].values()
    )
    return {
        "window": window,
        "total_cost_usd": round(total_cost, 4),
        "breakdown": {
            name: round(pod["totalCost"], 4)
            for name, pod in data["data"][0].items()
        },
    }
```

**What is happening:** We query OpenCost's API to get the dollar cost of every pod in
our `inference` namespace for the last hour. This data feeds into dashboards so the
team can see: "We spent $12.34 on GPU inference in the last hour, and 70% of that was
the Mistral-7B model."

---

## 14. GitOps: Argo CD + Tekton

### What are they?

**GitOps** is a practice where Git is the single source of truth for your
infrastructure. Instead of SSHing into a server and running commands, you commit a
YAML change to Git and the system automatically applies it.

**Argo CD** watches your Git repository and continuously synchronizes the cluster
state with what is defined in Git. If someone manually changes something in the
cluster, Argo CD detects the drift and reverts it.

**Tekton** is a Kubernetes-native CI/CD pipeline tool. It runs your build, test, and
deployment steps as Kubernetes pods. Think of it as GitHub Actions but running inside
your cluster.

### Why do we need them?

- **Argo CD** ensures the cluster always matches what is in Git — no "it works on my
  cluster" problems.
- **Tekton** runs our CI/CD pipelines (build Docker images, run tests, security
  scans) inside Kubernetes, close to where the code will actually run.
- Together: Tekton builds and tests; Argo CD deploys.

### Example in our app

```yaml
# tekton/pipeline.yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-and-test
spec:
  params:
    - name: git-url
    - name: image-tag
  tasks:
    - name: clone
      taskRef:
        name: git-clone
      params:
        - name: url
          value: $(params.git-url)

    - name: run-tests
      taskRef:
        name: pytest-runner
      runAfter: ["clone"]

    - name: build-image
      taskRef:
        name: kaniko-build
      runAfter: ["run-tests"]
      params:
        - name: IMAGE
          value: registry.example.com/ai-app:$(params.image-tag)
```

```yaml
# argocd/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ai-platform
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/our-org/ai-platform
    targetRevision: main
    path: k8s/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true      # Delete resources removed from Git
      selfHeal: true   # Revert manual cluster changes
```

**What is happening:** When you push code to `main`, Tekton runs: clone -> test ->
build Docker image. Once the image is pushed, you update the image tag in the k8s
manifests. Argo CD detects the change in Git and automatically rolls out the new
version to the cluster. If anything drifts, Argo self-heals.

---

## 15. Policy: OPA Gatekeeper

### What is it?

**OPA (Open Policy Agent)** is a general-purpose policy engine. You write rules in a
language called Rego, and OPA evaluates whether an action is allowed.

**Gatekeeper** is the Kubernetes-specific integration of OPA. It acts as an admission
controller — every time someone tries to create or modify a Kubernetes resource,
Gatekeeper checks it against your policies and blocks it if it violates any rule.

### Why do we need it?

Without policies, anyone with cluster access could:

- Deploy a container running as root (security risk).
- Create a pod without resource limits (could consume all memory).
- Pull images from untrusted registries (supply chain attack).

Gatekeeper prevents these mistakes automatically.

### Example in our app

```yaml
# policies/require-resource-limits.yaml
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
          not container.resources.limits.memory
          msg := sprintf(
            "Container '%v' must have memory limits set",
            [container.name]
          )
        }

        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not container.resources.limits.cpu
          msg := sprintf(
            "Container '%v' must have CPU limits set",
            [container.name]
          )
        }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredResources
metadata:
  name: must-have-resource-limits
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces: ["production", "inference"]
```

**What is happening:** If a developer tries to deploy a pod in `production` or
`inference` namespaces without CPU and memory limits, Gatekeeper rejects the
deployment immediately with a clear error message. This prevents a single runaway pod
from crashing the entire cluster.

---

## 16. Dev Loop: DevContainer + Skaffold + mirrord

### What are they?

**DevContainer** is a VS Code feature that runs your entire development environment
inside a Docker container. Every developer gets the same OS, same tools, same Python
version — no more "works on my machine."

**Skaffold** watches your source code and automatically rebuilds, pushes, and
redeploys to Kubernetes every time you save a file. It is `hot reload` for Kubernetes.

**mirrord** is a tool that lets your local process "pretend" it is running inside the
Kubernetes cluster. It mirrors network traffic and environment variables from a remote
pod to your local machine, so you can debug with real cluster data without deploying.

### Why do we need them?

Developing against Kubernetes is painful without these tools:

- Without DevContainer: "It works on my Mac but not on yours."
- Without Skaffold: Manually run `docker build`, `docker push`, `kubectl apply` on
  every code change.
- Without mirrord: You have to deploy to the cluster just to test if your service
  talks to Redis and Postgres correctly.

### Example in our app

```json
// .devcontainer/devcontainer.json
{
  "name": "AI Platform Dev",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {},
    "ghcr.io/devcontainers/features/docker-in-docker:2": {}
  },
  "postCreateCommand": "pip install -r requirements.txt && feast apply",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-azuretools.vscode-docker",
        "metalbear.mirrord"
      ]
    }
  },
  "forwardPorts": [8000, 3000, 9090]
}
```

```yaml
# skaffold.yaml
apiVersion: skaffold/v4beta6
kind: Config
build:
  artifacts:
    - image: ai-platform-api
      context: .
      docker:
        dockerfile: Dockerfile
  local:
    push: true
deploy:
  kubectl:
    manifests:
      - k8s/dev/*.yaml
portForward:
  - resourceType: service
    resourceName: fastapi-service
    port: 8000
    localPort: 8000
```

```json
// .mirrord/mirrord.json
{
  "target": {
    "path": "deployment/fastapi-service",
    "namespace": "development"
  },
  "feature": {
    "network": {
      "incoming": "mirror",
      "outgoing": true
    },
    "env": true,
    "fs": "local"
  }
}
```

**What is happening:**

1. Open the project in VS Code -> it launches inside the DevContainer with all tools
   pre-installed.
2. Run `skaffold dev` -> it watches your code, rebuilds the Docker image, and
   redeploys to the dev cluster on every save.
3. For debugging, run with mirrord -> your local FastAPI process can talk to the real
   Redis, Postgres, and vLLM in the cluster as if it were deployed there.

---

## 17. Bonus: Key Libraries You Will See Everywhere

### SQLAlchemy

**What:** Python ORM (Object-Relational Mapper) for database access.

```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(255), unique=True)

# Query: get all users named "Alice"
users = session.query(User).filter(User.name == "Alice").all()
```

Instead of writing `SELECT * FROM users WHERE name = 'Alice'`, you write Python. SQLAlchemy handles SQL generation, connection pooling, and migrations.

---

### Pydantic

**What:** Data validation using Python type hints.

```python
from pydantic import BaseModel, Field

class InferenceRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4096)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

# This works
req = InferenceRequest(prompt="Hello", max_tokens=100)

# This raises a validation error automatically
req = InferenceRequest(prompt="", max_tokens=-1)
# ValidationError: prompt must have at least 1 character; max_tokens >= 1
```

Every API request passes through Pydantic models. Invalid data never reaches your business logic.

---

### Microservices (the architecture pattern)

**What:** Instead of one giant application (monolith), you split the system into small, independent services that communicate over the network.

```
MONOLITH                          MICROSERVICES
┌─────────────────────┐           ┌──────────┐  ┌──────────┐
│  Auth + Chat + LLM  │    vs.    │   Auth   │  │   Chat   │
│  + Storage + Billing │           └──────────┘  └──────────┘
│  (all in one app)    │           ┌──────────┐  ┌──────────┐
└─────────────────────┘           │   LLM    │  │ Storage  │
                                  └──────────┘  └──────────┘
```

**Why microservices?**

- **Scale independently:** The LLM service needs GPUs; the auth service does not. Scale them separately.
- **Deploy independently:** Fix a bug in auth without redeploying the LLM service.
- **Tech flexibility:** The LLM service can be in Python; the auth service could be in Go.
- **Fault isolation:** If the billing service crashes, chat still works.

**The tradeoff:** More operational complexity — which is exactly why we need Kubernetes, Istio, OTEL, Argo CD, and all the other tools in this document.

---

## Quick Reference Cheat Sheet

| Layer | Tool | One-liner |
|-------|------|-----------|
| Frontend | Next.js + Tailwind | React framework with utility CSS |
| Ingress | Contour (Envoy) | Front door that routes external traffic in |
| Mesh | Istio Ambient | Encrypts and controls service-to-service calls |
| API | FastAPI + Strawberry | Python API with GraphQL support |
| GPU inference | vLLM + KubeRay | Fast LLM serving on auto-scaling GPU cluster |
| CPU fallback | llama.cpp | Quantized LLM on CPU when GPUs are busy |
| Vector DB | Postgres + pgvector | Similarity search for RAG inside Postgres |
| Object store | MinIO | Self-hosted S3 for files and model weights |
| Cache | Redis 7.2 VSS | Semantic caching to avoid redundant LLM calls |
| Orchestration | Prefect + LangGraph | Workflow scheduling + AI agent logic |
| Features | Feast + Flink | Real-time ML features for personalization |
| Observability | OTEL + Grafana stack | Traces, logs, and metrics in one place |
| Cost | OpenCost | Real-time dollar cost per inference call |
| GitOps | Argo CD + Tekton | Git-driven deployments + CI/CD pipelines |
| Policy | OPA Gatekeeper | Blocks unsafe Kubernetes configurations |
| Dev loop | DevContainer + Skaffold + mirrord | Consistent dev env + hot reload + local-to-cluster debugging |

---

*Last updated: 2026-04-05*
