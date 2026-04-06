# Tutorial 05: vLLM on KubeRay

> **Objective:** Learn how to serve LLMs at scale using vLLM for inference and KubeRay for Kubernetes-native GPU orchestration.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [vLLM Deep Dive](#3-vllm-deep-dive)
4. [KubeRay](#4-kuberay)
5. [Installation & Setup](#5-installation--setup)
6. [Exercises](#6-exercises)
7. [Monitoring](#7-monitoring)
8. [How It's Used in Our Project](#8-how-its-used-in-our-project)
9. [Cost Optimization](#9-cost-optimization)
10. [Further Reading](#10-further-reading)

---

## 1. Introduction

### What is vLLM?

**vLLM** (Virtual Large Language Model) is a high-throughput LLM inference engine. It's 10-24x faster than naive HuggingFace inference thanks to:

- **PagedAttention** — Manages GPU memory like an OS manages virtual memory
- **Continuous batching** — Groups requests together dynamically
- **OpenAI-compatible API** — Drop-in replacement for OpenAI's API

### What is Ray?

**Ray** is a distributed computing framework that makes it easy to scale Python code across multiple machines. Ray Serve is its model-serving library.

### What is KubeRay?

**KubeRay** is a Kubernetes operator that manages Ray clusters as native K8s resources. It handles:

- Cluster lifecycle (create, scale, delete)
- GPU scheduling
- Auto-scaling based on demand
- Health monitoring and recovery

### Why vLLM?

| Engine | Throughput | Latency | GPU Memory | API Compat |
|--------|-----------|---------|------------|------------|
| HuggingFace | Low | High | Wasteful | Custom |
| **vLLM** | **Very High** | **Low** | **Efficient** | **OpenAI** |
| TGI | High | Low | Good | Custom |
| llama.cpp | Medium (CPU) | Medium | N/A (CPU) | OpenAI |

---

## 2. Core Concepts

### 2.1 LLM Inference Pipeline

```
Input Text → Tokenizer → Token IDs → Model → Logits → Sampler → Output Tokens → Detokenizer → Output Text
```

1. **Tokenize** — Convert text to numbers ("Hello" → [15496])
2. **Forward pass** — Run through the neural network
3. **Sample** — Pick the next token based on probabilities
4. **Repeat** — Generate tokens one at a time (auto-regressive)

### 2.2 PagedAttention

Traditional attention stores KV cache in contiguous GPU memory — wasteful for variable-length sequences.

PagedAttention stores KV cache in **non-contiguous pages** (like virtual memory):

```
Traditional:  [Request 1 KV cache ~~~~~~~~ WASTED SPACE]
              [Request 2 KV cache ~~~~ WASTED SPACE ~~~]

PagedAttention: [Page1-R1][Page1-R2][Page2-R1][Page2-R2][Page3-R1]
                No wasted space! Pages allocated as needed.
```

This allows **2-4x more concurrent requests** in the same GPU memory.

### 2.3 Continuous Batching

Traditional batching waits for a batch to fill, processes it, then waits again.

Continuous batching adds new requests to the running batch immediately:

```
Traditional:  [Batch 1: R1,R2,R3] → process → [Batch 2: R4,R5,R6] → process
Continuous:   [R1,R2,R3] → R1 done, add R4 → [R4,R2,R3] → R3 done, add R5 → ...
```

### 2.4 Sampling Parameters

| Parameter | Range | Effect |
|-----------|-------|--------|
| `temperature` | 0-2 | Higher = more random, lower = more deterministic |
| `top_p` | 0-1 | Nucleus sampling — consider tokens summing to this probability |
| `top_k` | 1-100 | Only consider top K most likely tokens |
| `max_tokens` | 1-8192+ | Maximum output length |
| `frequency_penalty` | -2 to 2 | Penalize repeated tokens |
| `presence_penalty` | -2 to 2 | Penalize tokens that appeared at all |

### 2.5 Quantization

Reduce model size by using lower-precision numbers:

| Precision | Memory per param | Quality | Speed |
|-----------|-----------------|---------|-------|
| FP16 | 2 bytes | Baseline | Baseline |
| INT8 | 1 byte | ~99% | 1.5x faster |
| INT4 (GPTQ) | 0.5 bytes | ~95% | 2x faster |
| INT4 (AWQ) | 0.5 bytes | ~97% | 2x faster |

```
Llama-3-70B at FP16: ~140 GB VRAM (needs 2x A100-80GB)
Llama-3-70B at INT4:  ~35 GB VRAM (fits on 1x A100-80GB)
```

---

## 3. vLLM Deep Dive

### 3.1 Supported Models

vLLM supports most popular architectures:
- LLaMA, LLaMA-2, LLaMA-3
- Mistral, Mixtral
- Qwen, Qwen2
- Phi-3
- Falcon
- GPT-NeoX
- And many more...

### 3.2 OpenAI-Compatible API

vLLM provides endpoints identical to OpenAI's API:

```
POST /v1/chat/completions    → Chat (messages format)
POST /v1/completions         → Text completion
POST /v1/embeddings          → Text embeddings
GET  /v1/models              → List loaded models
```

### 3.3 Server Parameters

```bash
vllm serve meta-llama/Meta-Llama-3-70B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 2 \        # Split across 2 GPUs
  --max-model-len 4096 \            # Max context length
  --gpu-memory-utilization 0.9 \    # Use 90% of GPU memory
  --max-num-seqs 256 \              # Max concurrent sequences
  --quantization awq \              # Use AWQ quantization
  --enforce-eager \                 # Disable CUDA graphs (debugging)
  --enable-prefix-caching            # Cache common prefixes
```

---

## 4. KubeRay

### 4.1 RayCluster CRD

```yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: llm-cluster
spec:
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
    template:
      spec:
        containers:
          - name: ray-head
            image: rayproject/ray:2.9.0-py310-gpu
            resources:
              limits:
                cpu: "4"
                memory: "16Gi"
  workerGroupSpecs:
    - replicas: 2
      groupName: gpu-workers
      rayStartParams: {}
      template:
        spec:
          containers:
            - name: ray-worker
              image: rayproject/ray:2.9.0-py310-gpu
              resources:
                limits:
                  cpu: "8"
                  memory: "32Gi"
                  nvidia.com/gpu: "1"
```

### 4.2 RayService CRD

RayService combines Ray Cluster + Ray Serve deployment:

```yaml
apiVersion: ray.io/v1
kind: RayService
metadata:
  name: vllm-service
spec:
  serveConfigV2: |
    applications:
      - name: llm
        import_path: serve_llm:deployment
        runtime_env:
          pip: ["vllm>=0.4.0"]
  rayClusterConfig:
    headGroupSpec:
      # ... (same as RayCluster)
    workerGroupSpecs:
      # ... (same as RayCluster)
```

### 4.3 Autoscaling

```yaml
workerGroupSpecs:
  - replicas: 1
    minReplicas: 1
    maxReplicas: 4
    groupName: gpu-workers
    # KubeRay scales workers based on Ray's autoscaler
    # which monitors GPU utilization and pending requests
```

---

## 5. Installation & Setup

### Local vLLM Setup

```bash
# Install vLLM
pip install vllm

# Run with a small model for testing
vllm serve TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --host 0.0.0.0 --port 8000

# Or use Docker
docker run --gpus all \
  -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

### KubeRay on Kubernetes

```bash
# Install KubeRay operator
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update

helm install kuberay-operator kuberay/kuberay-operator \
  --namespace ray-system \
  --create-namespace

# Verify
kubectl get pods -n ray-system
```

---

## 6. Exercises

### Exercise 1: Run vLLM Locally

```bash
# Install
pip install vllm

# Start with TinyLlama (small enough for testing)
vllm serve TinyLlama/TinyLlama-1.1B-Chat-v1.0 --port 8000

# Test health
curl http://localhost:8000/health

# List models
curl http://localhost:8000/v1/models | python -m json.tool
```

---

### Exercise 2: Use the OpenAI-Compatible API

```bash
# Chat completion
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is Kubernetes in one sentence?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'

# Text completion
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "prompt": "The capital of France is",
    "max_tokens": 20,
    "temperature": 0
  }'
```

---

### Exercise 3: Python Client with Streaming

```python
# streaming_client.py
from openai import OpenAI

# Point to local vLLM server
client = OpenAI(
    api_url="http://localhost:8000/v1",
    api_key="not-needed",  # vLLM doesn't require auth by default
)

# Non-streaming
response = client.chat.completions.create(
    model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain Docker in simple terms."},
    ],
    temperature=0.7,
    max_tokens=200,
)
print(response.choices[0].message.content)

# Streaming
print("\n--- Streaming ---")
stream = client.chat.completions.create(
    model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    messages=[
        {"role": "user", "content": "Write a haiku about Kubernetes."},
    ],
    stream=True,
    max_tokens=50,
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()
```

---

### Exercise 4: Batch Inference (Offline Mode)

```python
# batch_inference.py
from vllm import LLM, SamplingParams

# Initialize model
llm = LLM(model="TinyLlama/TinyLlama-1.1B-Chat-v1.0")

# Define sampling parameters
sampling_params = SamplingParams(
    temperature=0.7,
    top_p=0.95,
    max_tokens=100,
)

# Batch of prompts
prompts = [
    "What is machine learning?",
    "Explain containerization.",
    "What is a service mesh?",
    "How does load balancing work?",
    "What is GitOps?",
]

# Process all at once (much faster than one-by-one)
outputs = llm.generate(prompts, sampling_params)

for output in outputs:
    prompt = output.prompt
    generated = output.outputs[0].text
    print(f"Prompt: {prompt}")
    print(f"Response: {generated}")
    print(f"Tokens: {len(output.outputs[0].token_ids)}")
    print("---")
```

---

### Exercise 5: Deploy RayCluster on Kubernetes

```yaml
# ray-cluster.yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: vllm-cluster
  namespace: ai-platform
spec:
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
      num-cpus: "0"   # Head doesn't run workloads
    template:
      spec:
        containers:
          - name: ray-head
            image: rayproject/ray:2.9.0-py310-gpu
            ports:
              - containerPort: 6379  # GCS
              - containerPort: 8265  # Dashboard
              - containerPort: 10001 # Client
            resources:
              limits:
                cpu: "4"
                memory: "8Gi"
  workerGroupSpecs:
    - replicas: 2
      minReplicas: 1
      maxReplicas: 4
      groupName: gpu-group
      rayStartParams:
        num-gpus: "1"
      template:
        spec:
          containers:
            - name: ray-worker
              image: rayproject/ray:2.9.0-py310-gpu
              resources:
                limits:
                  cpu: "8"
                  memory: "32Gi"
                  nvidia.com/gpu: "1"
          tolerations:
            - key: nvidia.com/gpu
              operator: Exists
              effect: NoSchedule
```

```bash
kubectl apply -f ray-cluster.yaml

# Check status
kubectl get raycluster -n ai-platform
kubectl get pods -n ai-platform -l ray.io/cluster=vllm-cluster

# Access Ray dashboard
kubectl port-forward svc/vllm-cluster-head-svc -n ai-platform 8265:8265
# Open http://localhost:8265
```

---

### Exercise 6: RayService with vLLM and Autoscaling

```python
# serve_vllm.py — Ray Serve deployment for vLLM
from ray import serve
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.sampling_params import SamplingParams

@serve.deployment(
    num_replicas=1,
    ray_actor_options={"num_gpus": 1},
    max_ongoing_requests=100,
    autoscaling_config={
        "min_replicas": 1,
        "max_replicas": 4,
        "target_ongoing_requests": 10,
    },
)
class VLLMDeployment:
    def __init__(self):
        args = AsyncEngineArgs(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            gpu_memory_utilization=0.9,
            max_model_len=4096,
        )
        self.engine = AsyncLLMEngine.from_engine_args(args)

    async def __call__(self, request):
        data = await request.json()
        prompt = data["prompt"]
        params = SamplingParams(
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 256),
        )

        results = []
        async for output in self.engine.generate(prompt, params, request_id=str(id(request))):
            results.append(output)

        final = results[-1]
        return {"text": final.outputs[0].text, "tokens": len(final.outputs[0].token_ids)}

deployment = VLLMDeployment.bind()
```

```yaml
# ray-service.yaml
apiVersion: ray.io/v1
kind: RayService
metadata:
  name: vllm-serve
  namespace: ai-platform
spec:
  serveConfigV2: |
    applications:
      - name: vllm-app
        import_path: serve_vllm:deployment
        runtime_env:
          pip: ["vllm>=0.4.0", "transformers"]
        deployments:
          - name: VLLMDeployment
            num_replicas: 1
            ray_actor_options:
              num_gpus: 1
  rayClusterConfig:
    headGroupSpec:
      rayStartParams:
        dashboard-host: "0.0.0.0"
      template:
        spec:
          containers:
            - name: ray-head
              image: rayproject/ray:2.9.0-py310-gpu
              resources:
                limits:
                  cpu: "4"
                  memory: "16Gi"
    workerGroupSpecs:
      - replicas: 1
        minReplicas: 1
        maxReplicas: 4
        groupName: gpu-workers
        rayStartParams:
          num-gpus: "1"
        template:
          spec:
            containers:
              - name: worker
                image: rayproject/ray:2.9.0-py310-gpu
                resources:
                  limits:
                    cpu: "8"
                    memory: "32Gi"
                    nvidia.com/gpu: "1"
```

---

### Exercise 7: Multi-Model Serving

```python
# multi_model.py — Serve multiple models with routing
from ray import serve
from vllm import LLM, SamplingParams

@serve.deployment(ray_actor_options={"num_gpus": 1})
class SmallModel:
    def __init__(self):
        self.llm = LLM(model="TinyLlama/TinyLlama-1.1B-Chat-v1.0")

    async def __call__(self, request):
        data = await request.json()
        params = SamplingParams(temperature=0.7, max_tokens=256)
        outputs = self.llm.generate([data["prompt"]], params)
        return {"text": outputs[0].outputs[0].text, "model": "tinyllama"}

@serve.deployment(ray_actor_options={"num_gpus": 1})
class LargeModel:
    def __init__(self):
        self.llm = LLM(model="meta-llama/Meta-Llama-3-8B-Instruct")

    async def __call__(self, request):
        data = await request.json()
        params = SamplingParams(temperature=0.7, max_tokens=256)
        outputs = self.llm.generate([data["prompt"]], params)
        return {"text": outputs[0].outputs[0].text, "model": "llama-3-8b"}

@serve.deployment
class Router:
    def __init__(self, small, large):
        self.small = small
        self.large = large

    async def __call__(self, request):
        data = await request.json()
        model = data.get("model", "small")
        if model == "large":
            return await self.large.handle_request(request)
        return await self.small.handle_request(request)

small = SmallModel.bind()
large = LargeModel.bind()
router = Router.bind(small, large)
```

---

## 7. Monitoring

### Key Metrics

```bash
# vLLM exposes Prometheus metrics at /metrics
curl http://localhost:8000/metrics

# Important metrics:
# vllm:num_requests_running        — Currently processing
# vllm:num_requests_waiting        — In queue
# vllm:gpu_cache_usage_perc        — KV cache utilization
# vllm:avg_prompt_throughput_toks_per_s   — Input processing speed
# vllm:avg_generation_throughput_toks_per_s — Output generation speed
```

### Prometheus Queries

```promql
# Request throughput
rate(vllm:num_requests_running[5m])

# GPU cache utilization
vllm:gpu_cache_usage_perc

# Average generation speed (tokens/sec)
vllm:avg_generation_throughput_toks_per_s

# P99 time to first token
histogram_quantile(0.99, rate(vllm:time_to_first_token_seconds_bucket[5m]))
```

### GPU Monitoring

```bash
# Check GPU utilization
nvidia-smi

# Continuous monitoring
watch -n 1 nvidia-smi

# Key metrics:
# - GPU Utilization % — should be high (>80%)
# - Memory Usage — PagedAttention manages this efficiently
# - Temperature — watch for thermal throttling
```

---

## 8. How It's Used in Our Project

- **Primary inference engine** — All LLM requests go through vLLM first
- **Circuit breaker** — If vLLM/GPU fails, falls back to llama.cpp on CPU
- **KubeRay autoscaling** — Scales GPU workers based on request queue depth
- **Tensor parallelism** — Large models split across multiple GPUs
- **OpenAI-compatible API** — Our FastAPI backend uses the OpenAI Python client to talk to vLLM
- **Prefix caching** — Common system prompts are cached for faster responses

---

## 9. Cost Optimization

1. **Quantization** — AWQ/GPTQ reduces GPU memory by 2-4x, enables running on fewer GPUs
2. **Batch processing** — Group requests for higher throughput
3. **Right-size GPUs** — Use A10G ($1.00/hr) for small models, A100 ($3.00/hr) for large
4. **Autoscaling** — Scale to zero during off-hours
5. **Prefix caching** — Cache common system prompts
6. **Model selection** — Use 8B for simple tasks, 70B only for complex ones

---

## 10. Further Reading

- [vLLM Documentation](https://docs.vllm.ai/)
- [vLLM GitHub](https://github.com/vllm-project/vllm)
- [Ray Documentation](https://docs.ray.io/)
- [KubeRay GitHub](https://github.com/ray-project/kuberay)
- [PagedAttention Paper](https://arxiv.org/abs/2309.06180)
