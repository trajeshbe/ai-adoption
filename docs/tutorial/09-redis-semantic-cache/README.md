# Tutorial 09: Redis 7.2 — Semantic Cache with Vector Similarity Search

> **Objective:** Learn Redis and build a semantic cache that saves LLM inference costs by matching similar (not just identical) queries.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [Semantic Cache Concept](#3-semantic-cache-concept)
4. [Installation & Setup](#4-installation--setup)
5. [Exercises](#5-exercises)
6. [How It's Used in Our Project](#6-how-its-used-in-our-project)
7. [Monitoring](#7-monitoring)
8. [Further Reading](#8-further-reading)

---

## 1. Introduction

### What is Redis?

**Redis** (Remote Dictionary Server) is an in-memory data structure store. It's blazing fast because everything lives in RAM:

- **Reads:** <1ms latency
- **Writes:** <1ms latency
- **Throughput:** 100K+ operations/second

### What is Semantic Caching?

Traditional caching uses **exact key matching**:
```
"What is K8s?" → cache MISS
"What is Kubernetes?" → cache MISS (different string!)
```

Semantic caching uses **vector similarity**:
```
"What is K8s?" → embeddings → search → MATCH with "What is Kubernetes?" → cache HIT!
```

### Why Cache LLM Responses?

| Metric | Without Cache | With Semantic Cache |
|--------|---------------|-------------------|
| Latency | 2-10 seconds | <100ms (cache hit) |
| Cost per query | $0.01-0.10 | $0.00 (cache hit) |
| GPU utilization | Always high | Reduced 30-60% |

---

## 2. Core Concepts

### 2.1 Data Structures

```bash
# Strings — simplest key-value
SET greeting "hello"
GET greeting          # → "hello"

# Hashes — like a Python dict
HSET user:1 name "Alice" role "admin" age 30
HGET user:1 name     # → "Alice"
HGETALL user:1       # → {name: "Alice", role: "admin", age: "30"}

# Lists — ordered collection
LPUSH queue "task1" "task2" "task3"
RPOP queue           # → "task1" (FIFO with LPUSH/RPOP)
LRANGE queue 0 -1    # → ["task3", "task2"]

# Sets — unique values
SADD tags "ml" "python" "kubernetes"
SISMEMBER tags "ml"  # → 1 (true)
SMEMBERS tags        # → {"ml", "python", "kubernetes"}

# Sorted Sets — unique values with scores
ZADD leaderboard 100 "model-a" 95 "model-b" 88 "model-c"
ZRANGE leaderboard 0 -1 WITHSCORES  # → ordered by score

# Streams — append-only event log
XADD events * type "inference" model "llama-3" latency_ms 245
XREAD COUNT 10 STREAMS events 0     # → read events
```

### 2.2 TTL (Time To Live)

```bash
SET cache:response "Hello!" EX 300   # Expire in 300 seconds
TTL cache:response                    # → 298 (seconds remaining)
EXPIRE cache:response 600             # Reset TTL to 600s
PERSIST cache:response                # Remove expiration
```

### 2.3 Pub/Sub

```bash
# Terminal 1 — subscribe
SUBSCRIBE notifications

# Terminal 2 — publish
PUBLISH notifications "New model deployed: llama-3.1"
# Terminal 1 sees the message instantly
```

### 2.4 Persistence

| Mode | How | Recovery | Performance |
|------|-----|----------|-------------|
| **RDB** | Periodic snapshots | Up to last snapshot | Fastest |
| **AOF** | Append every write | Up to last write | Slower |
| **RDB+AOF** | Both | Best of both | Balanced |

---

## 3. Semantic Cache Concept

### How It Works

```
1. User asks: "How does K8s scheduling work?"
2. Generate embedding: [0.12, -0.34, 0.56, ...]
3. Search Redis for similar embeddings (cosine similarity > 0.95)
4. IF FOUND (cache hit):
   └─ Return cached response instantly
5. IF NOT FOUND (cache miss):
   ├─ Send to LLM for inference
   ├─ Store embedding + response in Redis
   └─ Return response
```

### Similarity Threshold

| Threshold | Effect |
|-----------|--------|
| 0.99 | Very strict — almost exact matches only |
| **0.95** | **Recommended — similar questions** |
| 0.90 | Loose — may return unrelated answers |
| 0.85 | Too loose — likely wrong answers |

---

## 4. Installation & Setup

```bash
# Docker with Redis Stack (includes RediSearch for vectors)
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis/redis-stack:latest

# Connect with redis-cli
docker exec -it redis redis-cli

# Verify modules loaded
MODULE LIST
# Should show: search, ReJSON, etc.
```

---

## 5. Exercises

### Exercise 1: Basic Redis Operations

```bash
# Connect
redis-cli

# Strings
SET model:name "llama-3-70b"
GET model:name
SET model:requests 0
INCR model:requests           # → 1
INCRBY model:requests 10      # → 11

# Hashes (perfect for structured data)
HSET model:llama3 name "LLaMA 3" version "3.1" params_b 70 status "active"
HGET model:llama3 status
HGETALL model:llama3
HINCRBY model:llama3 request_count 1

# Lists (request queue)
LPUSH inference:queue '{"prompt": "Hello", "model": "llama-3"}'
LPUSH inference:queue '{"prompt": "Hi", "model": "llama-3"}'
RPOP inference:queue          # Dequeue oldest
LLEN inference:queue          # Queue length

# Sets (unique users)
SADD active:users "user:1" "user:2" "user:3"
SCARD active:users            # → 3
SRANDMEMBER active:users      # Random user

# Sorted Sets (model latency leaderboard)
ZADD model:latency 245 "llama-3-70b" 89 "llama-3-8b" 312 "mixtral-8x7b"
ZRANGE model:latency 0 -1 WITHSCORES   # Sorted by latency
ZRANGEBYSCORE model:latency 0 100       # Models under 100ms

# TTL
SET cache:response "cached data" EX 300
TTL cache:response
```

---

### Exercise 2: Python redis-py Client

```python
# redis_basics.py
import redis
import json

# Connect with connection pool
pool = redis.ConnectionPool(host="localhost", port=6379, decode_responses=True)
r = redis.Redis(connection_pool=pool)

# Store model config
r.hset("config:llama3", mapping={
    "name": "llama-3-70b",
    "endpoint": "http://vllm-service:8000",
    "max_tokens": "4096",
    "temperature": "0.7",
})

# Read config
config = r.hgetall("config:llama3")
print(f"Model config: {config}")

# Increment request counter
r.incr("metrics:total_requests")
r.incr("metrics:total_requests")
print(f"Total requests: {r.get('metrics:total_requests')}")

# Store with TTL
r.setex("cache:query:abc123", 300, json.dumps({
    "response": "Kubernetes is an orchestration platform...",
    "tokens": 150,
}))

# Check TTL
ttl = r.ttl("cache:query:abc123")
print(f"Cache TTL: {ttl}s")

# Pipeline (batch commands — much faster)
pipe = r.pipeline()
for i in range(100):
    pipe.incr("metrics:batch_counter")
pipe.execute()  # All 100 commands in one round trip
print(f"Batch counter: {r.get('metrics:batch_counter')}")
```

---

### Exercise 3: Create Vector Index (FT.CREATE)

```python
# vector_index.py
import redis
import numpy as np
from redis.commands.search.field import VectorField, TextField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

r = redis.Redis(host="localhost", port=6379, decode_responses=False)

# Define vector index schema
schema = (
    TextField("prompt"),
    TextField("response"),
    NumericField("tokens"),
    NumericField("timestamp"),
    VectorField(
        "embedding",
        "HNSW",                    # Index algorithm
        {
            "TYPE": "FLOAT32",
            "DIM": 384,            # Embedding dimensions
            "DISTANCE_METRIC": "COSINE",
            "M": 16,
            "EF_CONSTRUCTION": 200,
        },
    ),
)

# Create index
try:
    r.ft("cache_idx").dropindex(delete_documents=True)
except:
    pass

r.ft("cache_idx").create_index(
    schema,
    definition=IndexDefinition(prefix=["cache:"], index_type=IndexType.HASH),
)

print("Vector index created!")
print(r.ft("cache_idx").info())
```

---

### Exercise 4: Store and Search Vectors

```python
# vector_search.py
import redis
import numpy as np
from redis.commands.search.query import Query

r = redis.Redis(host="localhost", port=6379, decode_responses=False)

# Store some cached queries with embeddings
entries = [
    {"prompt": "What is Kubernetes?", "response": "Kubernetes is a container orchestration platform..."},
    {"prompt": "How does Docker work?", "response": "Docker uses containerization to package apps..."},
    {"prompt": "Explain machine learning", "response": "ML is a subset of AI that learns from data..."},
    {"prompt": "What is a neural network?", "response": "A neural network is a computing model inspired by the brain..."},
    {"prompt": "How to deploy to K8s?", "response": "To deploy to Kubernetes, create a Deployment manifest..."},
]

for i, entry in enumerate(entries):
    # In production, use a real embedding model
    embedding = np.random.randn(384).astype(np.float32).tobytes()
    r.hset(f"cache:{i}", mapping={
        "prompt": entry["prompt"],
        "response": entry["response"],
        "tokens": 100,
        "timestamp": 1700000000 + i,
        "embedding": embedding,
    })

# Search for similar vectors
query_embedding = np.random.randn(384).astype(np.float32).tobytes()

q = (
    Query("*=>[KNN 3 @embedding $vec AS score]")
    .sort_by("score")
    .return_fields("prompt", "response", "score")
    .dialect(2)
)

results = r.ft("cache_idx").search(q, query_params={"vec": query_embedding})

print(f"Found {results.total} results:")
for doc in results.docs:
    print(f"  [{doc.score}] {doc.prompt}")
```

---

### Exercise 5: Full Semantic Cache Implementation

```python
# semantic_cache.py
import redis
import numpy as np
import json
import time
import hashlib
import httpx
from redis.commands.search.query import Query
from redis.commands.search.field import VectorField, TextField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

class SemanticCache:
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        embed_url: str = "http://localhost:8080/v1/embeddings",
        llm_url: str = "http://localhost:8080/v1/chat/completions",
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 3600,
        dim: int = 384,
    ):
        self.r = redis.from_url(redis_url, decode_responses=False)
        self.embed_url = embed_url
        self.llm_url = llm_url
        self.threshold = similarity_threshold
        self.ttl = ttl_seconds
        self.dim = dim
        self._ensure_index()

    def _ensure_index(self):
        try:
            self.r.ft("sem_cache").info()
        except:
            schema = (
                TextField("prompt"),
                TextField("response"),
                NumericField("created_at"),
                VectorField("embedding", "HNSW", {
                    "TYPE": "FLOAT32",
                    "DIM": self.dim,
                    "DISTANCE_METRIC": "COSINE",
                }),
            )
            self.r.ft("sem_cache").create_index(
                schema,
                definition=IndexDefinition(prefix=["semcache:"], index_type=IndexType.HASH),
            )

    def _get_embedding(self, text: str) -> np.ndarray:
        response = httpx.post(self.embed_url, json={"input": text})
        data = response.json()["data"][0]["embedding"]
        return np.array(data, dtype=np.float32)

    def get(self, prompt: str) -> dict | None:
        """Search cache for semantically similar query."""
        embedding = self._get_embedding(prompt)
        vec_bytes = embedding.tobytes()

        q = (
            Query("*=>[KNN 1 @embedding $vec AS score]")
            .sort_by("score")
            .return_fields("prompt", "response", "score")
            .dialect(2)
        )

        results = self.r.ft("sem_cache").search(q, query_params={"vec": vec_bytes})

        if results.total > 0:
            doc = results.docs[0]
            similarity = 1 - float(doc.score)
            if similarity >= self.threshold:
                return {
                    "response": doc.response.decode() if isinstance(doc.response, bytes) else doc.response,
                    "cached_prompt": doc.prompt.decode() if isinstance(doc.prompt, bytes) else doc.prompt,
                    "similarity": similarity,
                    "source": "cache",
                }
        return None

    def set(self, prompt: str, response: str):
        """Store response in semantic cache."""
        embedding = self._get_embedding(prompt)
        key = f"semcache:{hashlib.md5(prompt.encode()).hexdigest()}"
        self.r.hset(key, mapping={
            "prompt": prompt,
            "response": response,
            "created_at": int(time.time()),
            "embedding": embedding.tobytes(),
        })
        self.r.expire(key, self.ttl)

    def query(self, prompt: str) -> dict:
        """Full query: check cache, fallback to LLM."""
        # Check cache first
        cached = self.get(prompt)
        if cached:
            return cached

        # Cache miss — call LLM
        response = httpx.post(self.llm_url, json={
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
        }, timeout=60)

        llm_response = response.json()["choices"][0]["message"]["content"]

        # Store in cache
        self.set(prompt, llm_response)

        return {
            "response": llm_response,
            "source": "llm",
            "similarity": 0.0,
        }

# Usage
cache = SemanticCache()

# First query — cache miss, calls LLM
result = cache.query("What is Kubernetes?")
print(f"[{result['source']}] {result['response'][:100]}...")

# Similar query — cache hit!
result = cache.query("Can you explain K8s?")
print(f"[{result['source']}] similarity={result.get('similarity', 0):.3f}")
```

---

### Exercise 6: Cache Invalidation

```python
# cache_invalidation.py
import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Strategy 1: TTL-based (automatic)
r.setex("cache:query:123", 3600, "response data")  # Expires in 1 hour

# Strategy 2: Manual invalidation (when model is updated)
def invalidate_model_cache(model_name: str):
    """Delete all cache entries for a specific model."""
    cursor = 0
    deleted = 0
    while True:
        cursor, keys = r.scan(cursor, match=f"semcache:*", count=100)
        for key in keys:
            r.delete(key)
            deleted += 1
        if cursor == 0:
            break
    print(f"Invalidated {deleted} cache entries")

# Strategy 3: Version-based
def set_with_version(key: str, value: str, version: int):
    r.hset(f"versioned:{key}", mapping={
        "value": value,
        "version": str(version),
    })

def get_with_version(key: str, current_version: int) -> str | None:
    data = r.hgetall(f"versioned:{key}")
    if data and int(data.get("version", 0)) == current_version:
        return data["value"]
    return None  # Stale, treat as miss
```

---

### Exercise 7: Pub/Sub for Real-time Notifications

```python
# pubsub.py
import redis
import json
import threading
import time

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Publisher — send events
def publish_event(channel: str, event: dict):
    r.publish(channel, json.dumps(event))

# Subscriber — listen for events
def event_listener():
    pubsub = r.pubsub()
    pubsub.subscribe("model:events", "inference:events")

    for message in pubsub.listen():
        if message["type"] == "message":
            event = json.loads(message["data"])
            channel = message["channel"]
            print(f"[{channel}] {event}")

# Start listener in background
listener_thread = threading.Thread(target=event_listener, daemon=True)
listener_thread.start()

# Publish some events
time.sleep(0.5)
publish_event("model:events", {"type": "deployed", "model": "llama-3.1", "version": "v2"})
publish_event("inference:events", {"type": "completed", "tokens": 150, "latency_ms": 234})
publish_event("model:events", {"type": "scaled", "replicas": 4})

time.sleep(1)
```

---

### Exercise 8: Redis Streams for Event Processing

```python
# streams.py
import redis
import time

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Produce events
def log_inference(model: str, prompt: str, latency_ms: int, tokens: int):
    r.xadd("inference:log", {
        "model": model,
        "prompt": prompt[:100],
        "latency_ms": str(latency_ms),
        "tokens": str(tokens),
        "timestamp": str(int(time.time())),
    }, maxlen=10000)  # Keep last 10K events

# Log some events
log_inference("llama-3-70b", "What is K8s?", 245, 150)
log_inference("llama-3-8b", "Hello world", 89, 20)
log_inference("llama-3-70b", "Explain ML", 312, 200)

# Read all events
events = r.xrange("inference:log", "-", "+", count=10)
for event_id, data in events:
    print(f"[{event_id}] model={data['model']} latency={data['latency_ms']}ms")

# Consumer group (for distributed processing)
try:
    r.xgroup_create("inference:log", "analytics", "$", mkstream=True)
except redis.ResponseError:
    pass  # Group already exists

# Read new events as consumer
events = r.xreadgroup("analytics", "worker-1", {"inference:log": ">"}, count=5, block=1000)
for stream, messages in events:
    for msg_id, data in messages:
        print(f"Processing: {data}")
        r.xack("inference:log", "analytics", msg_id)
```

---

## 6. How It's Used in Our Project

- **Semantic cache** — Cache LLM responses with vector similarity matching
- **Session store** — User chat sessions with TTL
- **Rate limiting** — Track request counts per user/minute
- **Pub/Sub** — Notify services when models are updated
- **Streams** — Inference event log for analytics
- **Feature cache** — Cache Feast features for fast retrieval

---

## 7. Monitoring

```bash
# Redis INFO command
redis-cli INFO

# Key metrics:
# used_memory — RAM usage
# connected_clients — Active connections
# ops_per_sec — Operations per second
# hit_rate — keyspace_hits / (keyspace_hits + keyspace_misses)

# Monitor commands in real-time
redis-cli MONITOR

# Slow log
redis-cli SLOWLOG GET 10
```

---

## 8. Further Reading

- [Redis Documentation](https://redis.io/docs/)
- [Redis Stack (RediSearch + Vector)](https://redis.io/docs/stack/)
- [redis-py Documentation](https://redis-py.readthedocs.io/)
- [Redis Vector Similarity Search](https://redis.io/docs/stack/search/reference/vectors/)
