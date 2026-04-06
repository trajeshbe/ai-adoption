# Tutorial 06: llama.cpp — CPU Fallback Inference

> **Objective:** Learn how llama.cpp enables LLM inference on CPUs, serving as our fallback when GPU resources are unavailable.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [Architecture](#3-architecture)
4. [Installation & Setup](#4-installation--setup)
5. [llama.cpp Server](#5-llamacpp-server)
6. [Exercises](#6-exercises)
7. [Performance Tuning](#7-performance-tuning)
8. [How It's Used in Our Project](#8-how-its-used-in-our-project)
9. [vLLM vs llama.cpp Comparison](#9-vllm-vs-llamacpp-comparison)
10. [Further Reading](#10-further-reading)

---

## 1. Introduction

### What is llama.cpp?

**llama.cpp** is a C/C++ implementation of LLM inference that runs efficiently on CPUs. Created by Georgi Gerganov, it enables running large language models on consumer hardware without GPUs.

### Why CPU Inference?

- **Cost** — CPU servers are 10-50x cheaper than GPU servers
- **Availability** — GPUs can be scarce; CPUs are always available
- **Fallback** — When GPU pods fail, CPU keeps the platform running
- **Edge deployment** — Run models on laptops, Raspberry Pi, etc.

### When to Use It

| Scenario | Use vLLM (GPU) | Use llama.cpp (CPU) |
|----------|---------------|---------------------|
| High throughput | Yes | No |
| Low latency | Yes | Acceptable |
| GPU available | Yes | — |
| GPU unavailable | — | Yes |
| Cost-sensitive | — | Yes |
| Small models (<7B) | Either | Great |
| Large models (>70B) | Required | Very slow |

---

## 2. Core Concepts

### 2.1 GGUF Model Format

GGUF (GPT-Generated Unified Format) is llama.cpp's model format. It stores:
- Model weights (quantized)
- Tokenizer
- Model metadata

```
Original model (FP16):     ~14 GB  (7B model)
GGUF Q4_K_M quantized:    ~4.1 GB  (same model, ~95% quality)
```

### 2.2 Quantization Levels

| Format | Bits/Weight | Size (7B) | Quality | Speed |
|--------|------------|-----------|---------|-------|
| F16 | 16 | 14 GB | 100% | Slowest |
| Q8_0 | 8 | 7.2 GB | ~99.5% | Good |
| Q6_K | 6 | 5.5 GB | ~99% | Better |
| Q5_K_M | 5 | 4.8 GB | ~98% | Better |
| **Q4_K_M** | **4** | **4.1 GB** | **~95%** | **Fast** |
| Q3_K_M | 3 | 3.3 GB | ~90% | Fastest |
| Q2_K | 2 | 2.7 GB | ~80% | Fastest |

**Recommendation:** Q4_K_M is the sweet spot — good quality with significant size reduction.

### 2.3 Memory Mapping (mmap)

llama.cpp uses memory-mapped files to load models:
- Model stays on disk, pages loaded on demand
- Multiple processes can share the same mapped file
- Startup is near-instant (no full load into RAM)

### 2.4 KV Cache

The Key-Value cache stores intermediate attention computations:

```
Context length × Layers × Hidden size × 2 (K and V) × Precision = KV cache size

For a 7B model with 4096 context:
4096 × 32 × 128 × 2 × FP16 ≈ 512 MB per request
```

---

## 3. Architecture

```
┌─────────────────────────────────────────┐
│            llama.cpp Server              │
│                                          │
│  HTTP API (:8080)                        │
│  ├── /v1/chat/completions  (OpenAI)     │
│  ├── /v1/completions       (OpenAI)     │
│  ├── /v1/embeddings        (OpenAI)     │
│  ├── /completion           (native)     │
│  └── /health                             │
│                                          │
│  Inference Engine                        │
│  ├── GGUF Model Loader (mmap)           │
│  ├── Tokenizer                           │
│  ├── Attention (CPU optimized)           │
│  │   ├── AVX2 / AVX-512 (x86)          │
│  │   └── NEON (ARM)                      │
│  ├── KV Cache Manager                    │
│  └── Sampling (top_k, top_p, temp)      │
│                                          │
│  Thread Pool (configurable)              │
│  └── -t 8  (8 threads for inference)    │
└─────────────────────────────────────────┘
```

---

## 4. Installation & Setup

### Build from Source

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make -j$(nproc)

# With specific optimizations
make -j$(nproc) LLAMA_AVX2=1 LLAMA_F16C=1
```

### Docker

```bash
docker run -p 8080:8080 \
  -v /path/to/models:/models \
  ghcr.io/ggerganov/llama.cpp:server \
  --model /models/llama-3-8b-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --threads 8
```

### Download a GGUF Model

```bash
# From HuggingFace (using huggingface-cli)
pip install huggingface-hub
huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF \
  tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
  --local-dir ./models
```

---

## 5. llama.cpp Server

### Server Parameters

```bash
./llama-server \
  --model ./models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --threads 8 \              # CPU threads for inference
  --ctx-size 4096 \           # Context window size
  --batch-size 512 \          # Prompt processing batch size
  --parallel 4 \              # Concurrent request slots
  --cont-batching \           # Enable continuous batching
  --mlock \                   # Lock model in RAM (no swap)
  --flash-attn                # Enable flash attention
```

### API Endpoints

```bash
# Health check
curl http://localhost:8080/health

# OpenAI-compatible chat completion
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7,
    "max_tokens": 100
  }'

# Native completion endpoint
curl http://localhost:8080/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "The meaning of life is",
    "n_predict": 50,
    "temperature": 0.7
  }'

# Embeddings
curl http://localhost:8080/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What is machine learning?"
  }'

# Server status/metrics
curl http://localhost:8080/slots
```

---

## 6. Exercises

### Exercise 1: Download and Run a Model

```bash
# Download a small model for testing
mkdir -p models
huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF \
  tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
  --local-dir ./models

# Start the server
./llama-server \
  --model ./models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
  --port 8080 \
  --threads 4 \
  --ctx-size 2048

# Verify it's running
curl http://localhost:8080/health
```

---

### Exercise 2: Chat Completions

```bash
# Single turn
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a helpful DevOps engineer."},
      {"role": "user", "content": "What is a container?"}
    ],
    "temperature": 0.7,
    "max_tokens": 200
  }' | python -m json.tool

# Multi-turn conversation
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is Docker?"},
      {"role": "assistant", "content": "Docker is a platform for containerization..."},
      {"role": "user", "content": "How is it different from a VM?"}
    ],
    "temperature": 0.5,
    "max_tokens": 300
  }'
```

---

### Exercise 3: Python Client

```python
# client.py
from openai import OpenAI

# Point to llama.cpp server
client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed",
)

# Chat completion
response = client.chat.completions.create(
    model="local-model",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain Kubernetes in 3 sentences."},
    ],
    temperature=0.7,
    max_tokens=150,
)

print(response.choices[0].message.content)
print(f"\nTokens: prompt={response.usage.prompt_tokens}, "
      f"completion={response.usage.completion_tokens}")
```

---

### Exercise 4: Streaming with Server-Sent Events

```python
# streaming.py
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8080/v1", api_key="not-needed")

stream = client.chat.completions.create(
    model="local-model",
    messages=[{"role": "user", "content": "Write a short poem about coding."}],
    stream=True,
    max_tokens=200,
)

print("Streaming response:")
for chunk in stream:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="", flush=True)
print("\n--- Done ---")
```

Raw SSE with `httpx`:

```python
# raw_sse.py
import httpx
import json

url = "http://localhost:8080/v1/chat/completions"
payload = {
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": True,
    "max_tokens": 100,
}

with httpx.stream("POST", url, json=payload) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            content = chunk["choices"][0]["delta"].get("content", "")
            print(content, end="", flush=True)
print()
```

---

### Exercise 5: Embeddings for RAG

```python
# embeddings.py
import httpx
import numpy as np

def get_embedding(text: str) -> list[float]:
    response = httpx.post(
        "http://localhost:8080/v1/embeddings",
        json={"input": text},
    )
    return response.json()["data"][0]["embedding"]

def cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# Create embeddings
docs = [
    "Kubernetes is a container orchestration platform",
    "Python is a programming language",
    "Docker packages applications in containers",
    "Machine learning uses data to learn patterns",
]

query = "How do containers work?"
query_emb = get_embedding(query)

# Find most similar document
similarities = []
for doc in docs:
    doc_emb = get_embedding(doc)
    sim = cosine_similarity(query_emb, doc_emb)
    similarities.append((doc, sim))

similarities.sort(key=lambda x: x[1], reverse=True)

print(f"Query: {query}\n")
for doc, sim in similarities:
    print(f"  [{sim:.4f}] {doc}")
```

---

### Exercise 6: Kubernetes Deployment

```yaml
# llama-cpp-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llama-cpp
  namespace: ai-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: llama-cpp
  template:
    metadata:
      labels:
        app: llama-cpp
    spec:
      containers:
        - name: llama-cpp
          image: ghcr.io/ggerganov/llama.cpp:server
          args:
            - "--model"
            - "/models/llama-3-8b-q4_k_m.gguf"
            - "--host"
            - "0.0.0.0"
            - "--port"
            - "8080"
            - "--threads"
            - "8"
            - "--ctx-size"
            - "4096"
            - "--parallel"
            - "4"
            - "--cont-batching"
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: "8"
              memory: "8Gi"
            limits:
              cpu: "16"
              memory: "16Gi"
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 60
            periodSeconds: 30
          volumeMounts:
            - name: models
              mountPath: /models
      volumes:
        - name: models
          persistentVolumeClaim:
            claimName: model-storage
---
apiVersion: v1
kind: Service
metadata:
  name: llama-cpp-svc
  namespace: ai-platform
spec:
  selector:
    app: llama-cpp
  ports:
    - port: 8080
      targetPort: 8080
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: llama-cpp-hpa
  namespace: ai-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: llama-cpp
  minReplicas: 1
  maxReplicas: 8
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

### Exercise 7: Circuit Breaker Pattern

```python
# circuit_breaker.py
import httpx
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"       # Normal — requests go to primary (vLLM)
    OPEN = "open"           # Failed — requests go to fallback (llama.cpp)
    HALF_OPEN = "half_open" # Testing — try primary again

class CircuitBreaker:
    def __init__(
        self,
        primary_url: str = "http://vllm-service:8000",
        fallback_url: str = "http://llama-cpp-svc:8080",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self.primary_url = primary_url
        self.fallback_url = fallback_url
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    async def call(self, messages: list[dict], **kwargs) -> dict:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                return await self._call_fallback(messages, **kwargs)

        if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
            try:
                result = await self._call_primary(messages, **kwargs)
                if self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                return await self._call_fallback(messages, **kwargs)

    async def _call_primary(self, messages, **kwargs):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.primary_url}/v1/chat/completions",
                json={"messages": messages, **kwargs},
            )
            response.raise_for_status()
            return response.json()

    async def _call_fallback(self, messages, **kwargs):
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.fallback_url}/v1/chat/completions",
                json={"messages": messages, **kwargs},
            )
            response.raise_for_status()
            result = response.json()
            result["_fallback"] = True
            return result

# Usage
breaker = CircuitBreaker()
result = await breaker.call(
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.7,
    max_tokens=100,
)
```

---

## 7. Performance Tuning

| Parameter | Effect | Recommendation |
|-----------|--------|----------------|
| `--threads` | CPU threads for inference | Set to physical core count |
| `--batch-size` | Prompt processing batch | 512-2048 |
| `--ctx-size` | Context window | As needed (affects memory) |
| `--parallel` | Concurrent slots | 2-8 depending on RAM |
| `--mlock` | Lock in RAM | Enable if enough RAM |
| `--flash-attn` | Flash attention | Enable for speed |
| Quantization | Model precision | Q4_K_M for balance |

### Memory Formula

```
RAM needed ≈ Model size + (ctx_size × parallel × ~2MB)

Example: 7B Q4_K_M, 4096 ctx, 4 parallel
= 4.1 GB + (4096 × 4 × 2 MB) ≈ 4.1 + 0.032 GB ≈ 4.2 GB
```

---

## 8. How It's Used in Our Project

- **CPU fallback** — When vLLM GPU pods are down or overloaded
- **Circuit breaker** — Automatic failover from vLLM → llama.cpp
- **Cost savings** — CPU inference for low-priority/batch requests
- **Development** — Developers run models locally without GPU access
- **Embedding generation** — CPU-based embeddings for document ingestion

---

## 9. vLLM vs llama.cpp Comparison

| Feature | vLLM (GPU) | llama.cpp (CPU) |
|---------|-----------|-----------------|
| Throughput | ~1000 tok/s | ~30 tok/s |
| Latency (TTFT) | ~50ms | ~500ms |
| Hardware | GPU required | CPU only |
| Cost/hour | $1-3 (GPU instance) | $0.05-0.10 (CPU) |
| Max model size | 70B+ (multi-GPU) | 13B practical limit |
| Batching | Continuous | Basic |
| Memory format | FP16/INT8 | GGUF (Q2-Q8) |
| API | OpenAI-compatible | OpenAI-compatible |

---

## 10. Further Reading

- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- [GGUF Specification](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md)
- [llama.cpp Server Documentation](https://github.com/ggerganov/llama.cpp/tree/master/examples/server)
- [Quantization Methods Explained](https://huggingface.co/docs/transformers/quantization)
- [TheBloke's Quantized Models](https://huggingface.co/TheBloke)
