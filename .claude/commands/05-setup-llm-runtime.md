# Phase 5: LLM Runtime -- Deploy vLLM on KubeRay with CPU Fallback

## What You Will Learn
- vLLM continuous batching for high-throughput LLM inference
- KubeRay for elastic GPU worker scaling on Kubernetes
- llama.cpp for CPU-based inference as availability fallback
- Token counting and cost estimation per inference
- Kubernetes NetworkPolicy for service isolation
- Health-check-based routing (not load balancing -- circuit breaker)

## Prerequisites
- Phase 4 complete (Agent engine with LLM client stub)
- Kubernetes cluster with GPU nodes (or Ollama for local dev)
- Understanding of LLM inference concepts (tokens, batching, KV cache)

## Background: Why Self-Hosted LLM Inference?
Cloud LLM APIs (OpenAI, Anthropic) are convenient but have drawbacks at scale:
per-token cost scales linearly, data leaves your network, rate limits constrain
throughput, and you depend on external availability. Self-hosted inference via vLLM
gives you: fixed GPU cost regardless of token volume, data sovereignty, no rate limits,
and control over model selection. The tradeoff is operational complexity -- which this
phase teaches you to manage.

vLLM's continuous batching achieves 2-4x higher throughput than naive HuggingFace
`model.generate()` by dynamically batching requests and managing the KV cache efficiently.

See: docs/architecture/adr/003-vllm-with-cpu-fallback.md

## Step-by-Step Instructions

### Step 1: Create KubeRay Helm Values

Create `infra/helm/values/kuberay.yaml`:
```yaml
operator:
  image:
    repository: rayproject/ray
    tag: 2.38.0-py311
  resources:
    limits:
      cpu: "1"
      memory: "1Gi"
```

### Step 2: Create vLLM Deployment on KubeRay

Create `infra/helm/values/vllm.yaml`:
```yaml
rayCluster:
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
    resources:
      limits:
        cpu: "4"
        memory: "8Gi"
  workerGroupSpecs:
    - replicas: 1
      minReplicas: 1
      maxReplicas: 4
      rayStartParams: {}
      resources:
        limits:
          cpu: "4"
          memory: "16Gi"
          nvidia.com/gpu: "1"

vllm:
  model: "meta-llama/Llama-3.1-8B-Instruct"
  maxModelLen: 4096
  tensorParallelSize: 1
  gpu_memory_utilization: 0.9
  port: 8000
```

**Key parameters explained:**
- `maxReplicas: 4` -- KubeRay auto-scales GPU workers based on queue depth
- `gpu_memory_utilization: 0.9` -- Use 90% of GPU VRAM for KV cache
- `tensorParallelSize: 1` -- Shard model across N GPUs (1 = single GPU)

### Step 3: Create llama.cpp CPU Fallback

Create `infra/k8s/base/llm-runtime/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llama-cpp-server
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: llama-cpp
          image: ghcr.io/ggerganov/llama.cpp:server
          args:
            - "--model"
            - "/models/llama-3.1-8b-instruct.Q4_K_M.gguf"
            - "--port"
            - "8080"
            - "--ctx-size"
            - "4096"
            - "--threads"
            - "4"
          resources:
            requests:
              cpu: "4"
              memory: "8Gi"
            limits:
              cpu: "8"
              memory: "16Gi"
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            periodSeconds: 10
```

**Why Q4_K_M quantization?** It's the sweet spot of quality vs size for CPU inference.
4-bit quantization reduces a 16GB FP16 model to ~4.5GB while retaining 95%+ quality.

### Step 4: Create Model Init Container

Models need to be downloaded before inference starts. Create an init container
that pulls from MinIO or HuggingFace:

```yaml
initContainers:
  - name: model-downloader
    image: python:3.11-slim
    command: ["python", "-c"]
    args:
      - |
        from huggingface_hub import hf_hub_download
        hf_hub_download(repo_id="meta-llama/Llama-3.1-8B-Instruct",
                        filename="*", local_dir="/models")
    volumeMounts:
      - name: model-storage
        mountPath: /models
```

### Step 5: Enrich the LLM Client

Update `services/agent-engine/src/agent_engine/llm_client.py`:

Add health-check-based routing:
```python
async def _is_healthy(self, client: AsyncOpenAI) -> bool:
    try:
        resp = await httpx.get(f"{client.base_url}/health", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False
```

Add token counting:
```python
def count_tokens(self, text: str, model: str) -> int:
    # Use tiktoken for OpenAI-compatible tokenization
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))
```

Add cost estimation:
```python
def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
    # Self-hosted cost = GPU-hour cost / tokens processed per hour
    gpu_cost_per_hour = 2.50  # A100 spot price
    tokens_per_hour = 50_000  # Measured throughput
    total_tokens = prompt_tokens + completion_tokens
    return (total_tokens / tokens_per_hour) * gpu_cost_per_hour
```

### Step 6: Create NetworkPolicy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: llm-runtime-access
spec:
  podSelector:
    matchLabels:
      app: vllm
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: agent-engine
      ports:
        - port: 8000
```

**Principle:** Only agent-engine can talk to LLM runtime. Zero-trust: deny all, allow explicitly.

### Step 7: Local Development with Ollama

For local dev without GPUs, use Ollama (already in docker-compose):
```bash
# Pull a model
docker exec ollama ollama pull llama3.1:8b

# Test
curl http://localhost:11434/api/generate -d '{"model":"llama3.1:8b","prompt":"Hello"}'
```

Update llm_client.py to support Ollama as a third fallback for local dev.

## Verification
```bash
# Local dev (Ollama)
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.1:8b","messages":[{"role":"user","content":"Hello"}]}'

# K8s (vLLM)
kubectl port-forward svc/vllm 8000:8000
curl http://localhost:8000/v1/models  # Should list the loaded model

# Test fallback: kill vLLM, verify agent-engine falls back to llama.cpp
kubectl scale deployment vllm --replicas=0
# Send a chat message -- should still work (slower, CPU inference)

# Tests
uv run pytest services/agent-engine/tests/unit/test_llm_client.py -v
```

## Key Concepts Taught
1. **vLLM continuous batching** -- Dynamic request batching for 2-4x throughput
2. **KubeRay** -- Elastic GPU scaling based on inference queue depth
3. **Circuit breaker** -- Health-check routing, not load balancing
4. **Quantization** -- Q4_K_M tradeoff between quality and resource usage
5. **NetworkPolicy** -- Zero-trust: only authorized services reach LLM runtime
6. **Cost modeling** -- GPU-hour amortization per token for self-hosted inference

## What's Next
Phase 6 (`/06-add-observability`) adds full observability: OpenTelemetry traces from
every service, Grafana dashboards for latency, cache hits, and cost per inference.
You'll finally see the full request flow from frontend click to LLM response.
