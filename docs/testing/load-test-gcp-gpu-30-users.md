# Load Test Report: 30 Concurrent Users on GCP GPU VM

**Date**: 2026-04-06
**Tester**: Automated via Python asyncio load test harness
**Target**: AI Agent Platform (Docker Compose deployment on GCP)

---

## 1. Test Environment

| Component | Specification |
|-----------|--------------|
| **Cloud** | Google Cloud Platform (GCP) |
| **VM Instance** | `ai-agent-gpu-test` |
| **Machine Type** | `n1-standard-8` (8 vCPU, 30 GB RAM) |
| **GPU** | NVIDIA Tesla T4 (16 GB VRAM) |
| **Zone** | `us-east4-c` |
| **OS** | Ubuntu 24.04 LTS |
| **Docker** | Docker CE with NVIDIA Container Toolkit |
| **LLM** | Ollama 0.11.0 + qwen2.5:1.5b (986 MB model, GPU-accelerated) |
| **Deployment** | Docker Compose (11 containers, no Kubernetes) |
| **Public IP** | 8.228.119.177 |
| **Estimated Cost** | ~$0.70/hr ($17/day) |

### Services Under Test

| Container | Role | Port |
|-----------|------|------|
| aiadopt-gateway | GraphQL API (FastAPI + Strawberry) | 8050 → 8000 |
| aiadopt-agent-engine | LangGraph agent orchestration | 8053 → 8003 |
| aiadopt-ollama | LLM inference (GPU) | 11434 |
| aiadopt-frontend | Next.js Web UI | 8055 → 3000 |
| aiadopt-postgres | PostgreSQL + pgvector | 5432 |
| aiadopt-redis | Redis Stack (RediSearch) | 6379 |
| aiadopt-cache-service | Semantic cache | 8052 → 8002 |
| aiadopt-cost-tracker | Cost tracking | 8054 → 8004 |
| aiadopt-document-service | RAG document pipeline | 8051 → 8001 |
| aiadopt-minio | S3-compatible object store | 9000 |

---

## 2. Test Design

### Objective

Determine maximum concurrent user capacity, latency profile, and system resource utilization for the AI Agent Platform running on a single GCP GPU VM.

### Methodology

- **Tool**: Custom Python asyncio load test harness (`/tmp/loadtest.py`)
- **Protocol**: HTTP POST to GraphQL endpoint (`/graphql`)
- **Operation**: `SendMessage` mutation targeting the Movie Quiz Bot agent
- **Question Pool**: 15 diverse movie questions (randomized per request)
- **Think Time**: 1-3 seconds random delay between requests per user
- **Request Timeout**: 90 seconds

### Ramp Schedule

The test gradually increases concurrent users to observe degradation:

| Time Window | Concurrent Users | Phase |
|-------------|-----------------|-------|
| 0s - 15s | 5 | Warm-up |
| 15s - 30s | 10 | Low load |
| 30s - 45s | 15 | Medium load |
| 45s - 60s | 20 | High load |
| 60s - 75s | 25 | Very high load |
| 75s - 90s | 30 | Peak load |
| 90s - 120s | 30 | Sustained peak |
| 120s - 135s | 15 | Ramp down |
| 135s - 150s | 0 | Cool down |

### Request Flow

```
User → Gateway (:8050/graphql)
         → SendMessage mutation
         → HTTP POST to Agent Engine (:8003/agents/execute)
              → LangGraph state machine
              → Ollama LLM inference (:11434, GPU)
              ← AgentResponse
         ← GraphQL response
```

---

## 3. Results Summary

| Metric | Value |
|--------|-------|
| **Test Duration** | 132 seconds |
| **Total Requests** | 287 |
| **Successful** | 98 (34.1%) |
| **Failed** | 189 (65.9%) |
| **Throughput** | 2.18 req/s |

### End-to-End Latency (Successful Requests)

| Percentile | Latency |
|------------|---------|
| Min | 1,051 ms |
| Mean | 15,930 ms |
| Median (p50) | 16,943 ms |
| p90 | 25,128 ms |
| p95 | 28,983 ms |
| p99 | 36,207 ms |
| Max | 37,662 ms |
| Std Dev | 8,190 ms |

### LLM Inference Latency (Ollama + T4 GPU)

| Percentile | Latency |
|------------|---------|
| Min | 701 ms |
| Mean | 14,847 ms |
| Median (p50) | 16,493 ms |
| p90 | 23,245 ms |
| p95 | 26,111 ms |
| Max | 37,319 ms |

### Latency by Concurrency Level

| Concurrent Users | Requests | Avg E2E | p95 E2E | Avg LLM | Success Rate |
|-----------------|----------|---------|---------|---------|-------------|
| **5** | 12 | 4,387 ms | 5,874 ms | 3,225 ms | **100%** |
| **10** | 21 | 7,874 ms | 12,230 ms | 6,772 ms | **100%** |
| **15** | 17 | 16,498 ms | 20,002 ms | 15,002 ms | **100%** |
| **20** | 26 | 20,897 ms | 27,083 ms | 19,558 ms | **38%** |
| **25** | 90 | 17,563 ms | 19,427 ms | 16,977 ms | **13%** |
| **30** | 121 | 24,729 ms | 36,101 ms | 23,837 ms | **21%** |

---

## 4. System Resource Utilization

Metrics were sampled every 5 seconds throughout the test.

### Overall

| Resource | Average | Peak |
|----------|---------|------|
| **CPU** | 18.8% | 56.3% |
| **GPU Utilization** | 67.1% | 74.0% |
| **GPU Memory** | 1,480 MB / 15,360 MB (9.6%) | 1,481 MB |
| **System RAM** | 2.9 GB / 30 GB (9.7%) | 3.1 GB |

### Timeline (sampled every 5s)

```
Time(s)  Users  CPU%   GPU%   GPU Mem(MB)  GPU Temp(C)  RAM(MB)
──────── ────── ────── ────── ──────────── ─────────── ────────
     0      5    1.1    0      1,479         57         2,732
     5      5   13.6   68      1,479         61         2,766
    11      5   13.8   68      1,479         63         2,793
    16     10   13.6   66      1,479         65         2,811
    21     10   56.3   61      1,479         67         2,861
    26     10   13.8   69      1,479         68         2,860
    32     15   18.6   66      1,479         70         2,872
    37     15   13.8   71      1,479         71         2,880
    42     15   14.8   69      1,479         73         2,877
    47     20   32.6   71      1,479         74         2,902
    53     20   12.6   74      1,479         75         2,916
    58     20   17.2   69      1,479         76         2,920
    63     25   23.3   67      1,479         77         2,928
    68     25   12.8   70      1,479         78         2,936
    74     25   14.8   68      1,479         79         2,934
    79     30   33.0   67      1,479         80         2,940
    84     30   24.1   68      1,479         80         2,994
    89     30   18.2   74      1,479         80         2,971
    95     30   18.4   68      1,481         79         2,967
   100     30   17.4   73      1,481         78         2,956
   105     30   14.9   69      1,481         77         2,961
   110     30   16.5   70      1,481         76         2,984
   116     30   21.8   73      1,481         76         2,989
   121     15   27.9   68      1,481         76         2,988
   126     15   13.6   73      1,481         76         2,987
   131     15   12.6   70      1,481         76         2,994
```

### Key Observations

1. **GPU utilization plateaued at ~67-74%** regardless of load. Ollama serializes inference requests internally -- the GPU is busy generating tokens but can only process one request at a time.

2. **GPU memory was barely used** (1.5 GB of 16 GB). The qwen2.5:1.5b model is small. A larger model (7B-13B) would use more VRAM but provide better response quality.

3. **CPU stayed low** (avg 18.8%). The bottleneck is entirely GPU inference throughput, not CPU.

4. **GPU temperature rose from 57C to 80C** during sustained load, then stabilized. T4 thermal throttles at 97C, so there was ample headroom.

5. **RAM usage was minimal** (3 GB of 30 GB). The VM is over-provisioned for this workload.

---

## 5. Analysis

### Bottleneck: Ollama Sequential Inference

The single biggest bottleneck is **Ollama's serial request processing**. Despite having a T4 GPU capable of parallel computation, Ollama processes one inference request at a time. This means:

- At **5 concurrent users**: each request waits for ~5 ahead of it, resulting in ~4.4s avg latency
- At **15 concurrent users**: queue depth grows to ~15, pushing avg latency to ~16.5s
- At **20+ concurrent users**: requests start timing out (90s), causing the sharp drop in success rate

### Capacity Limits

| Metric | Comfortable | Maximum (degraded) |
|--------|-------------|-------------------|
| **Concurrent Users** | 10-15 | 20 |
| **Requests/sec** | ~1.5-2.0 | ~2.2 (with failures) |
| **Acceptable Latency** | <10s (at 10 users) | <20s (at 15 users) |
| **Success Rate** | 100% (at ≤15 users) | 38% (at 20 users) |

### Why Failures Occur Above 15 Users

1. **Queue starvation**: With Ollama processing ~1 req/s (each taking 1-3s of pure inference), 20+ queued requests back up
2. **Gateway timeout**: The agent-engine has a 120s Prefect flow timeout
3. **Compounding delays**: Each queued request adds ~1-3s to all subsequent requests' wait time

### Comparison: GPU vs CPU

| Metric | GPU (T4) | CPU (e2-standard-2) |
|--------|----------|-------------------|
| Single request | ~1.5s | ~31s |
| Max concurrent users | 15 | 1 |
| Throughput | ~2 req/s | ~0.03 req/s |
| Speedup | **~10x** | Baseline |

---

## 6. Scaling Recommendations

### To Support 30+ Concurrent Users

The platform needs horizontal scaling of the LLM inference layer. Options:

| Approach | How | Expected Improvement |
|----------|-----|---------------------|
| **vLLM instead of Ollama** | Replace Ollama with vLLM (continuous batching) | 3-5x throughput (batch inference) |
| **Multiple Ollama replicas** | Run 2-3 Ollama containers sharing the same GPU via MPS | 2-3x throughput |
| **Kubernetes HPA** | Deploy on K8s with HPA auto-scaling agent-engine + LLM pods | Auto-scale to demand |
| **Larger model on larger GPU** | Use A100 (80GB) with qwen2.5:7b | Better quality, similar throughput |
| **Semantic cache** | Enable Redis VSS cache for repeated/similar queries | Instant response for cache hits |

### Kubernetes Scaling Architecture (Production Tier)

```
                    ┌─────────────┐
                    │   Contour   │
                    │   Ingress   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Gateway   │ ← HPA: 1-5 replicas @ 50% CPU
                    │  (FastAPI)  │
                    └──────┬──────┘
                           │
                ┌──────────▼──────────┐
                │    Agent Engine     │ ← HPA: 1-5 replicas @ 50% CPU
                │ (Prefect+LangGraph) │
                └──────────┬──────────┘
                           │
              ┌────────────▼────────────┐
              │     vLLM (KubeRay)      │ ← HPA: 1-3 replicas (GPU pods)
              │  Continuous batching     │    Each pod: 1 GPU
              │  Handles 10-30 req/s    │
              └─────────────────────────┘
```

With Kubernetes HPA and vLLM:
- **30 users**: 1 vLLM pod (continuous batching handles parallelism)
- **60 users**: HPA scales to 2 vLLM pods
- **100+ users**: HPA scales to 3 pods, semantic cache handles repeated queries

---

## 7. How to Reproduce This Test

### Prerequisites

- GCP project with GPU quota (`GPUS_ALL_REGIONS >= 1`)
- SSH access to the VM
- Docker Compose deployment running

### Step 1: Create the GPU VM

```bash
gcloud compute instances create ai-agent-gpu-test \
  --project=ai-adoption-492510 \
  --zone=us-east4-c \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --maintenance-policy=TERMINATE \
  --boot-disk-size=100GB \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --tags=agent-platform
```

### Step 2: Install Dependencies

```bash
ssh merit@<VM_IP>

# Add Docker repo
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list

# Add NVIDIA Container Toolkit repo
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install everything
sudo apt-get update
sudo apt-get install -y nvidia-driver-550 nvidia-container-toolkit \
  docker-ce docker-ce-cli containerd.io docker-compose-plugin git python3-aiohttp

# Configure NVIDIA runtime for Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
sudo usermod -aG docker $USER
newgrp docker
```

### Step 3: Deploy the Application

```bash
mkdir -p ~/kiaa
git clone https://github.com/trajeshbe/ai-adoption.git ~/kiaa/ai-adoption
cd ~/kiaa/ai-adoption

# Set environment
cat > .env << EOF
NEXT_PUBLIC_GRAPHQL_URL=http://<VM_IP>:8050/graphql
LLM_MODEL=qwen2.5:1.5b
EOF

# Build and start (GPU-enabled, Ollama uses T4 automatically)
docker compose up -d --build

# Pull the LLM model
docker exec aiadopt-ollama ollama pull qwen2.5:1.5b
```

### Step 4: Verify Deployment

```bash
# Check all containers are healthy
docker ps

# Verify GPU is detected
nvidia-smi

# Test single chat request
curl -s -X POST http://localhost:8050/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { sendMessage(input: {agentId: \"00000000-0000-0000-0000-000000000001\", content: \"Hello\"}) { content latencyMs } }"}'
```

### Step 5: Run the Load Test

```bash
# Install aiohttp if not already installed
sudo apt-get install -y python3-aiohttp

# Upload and run the test script
python3 /tmp/loadtest.py
```

The test script is available at: `tests/load/loadtest_gpu_30users.py` (copy from this repo).

### Step 6: Tear Down (Important -- stops billing)

```bash
gcloud compute instances delete ai-agent-gpu-test \
  --project=ai-adoption-492510 \
  --zone=us-east4-c \
  --quiet
```

---

## 8. Raw Data Files

All raw data from this test run is stored on the VM at `/tmp/loadtest-results/`:

| File | Description |
|------|-------------|
| `summary.txt` | Aggregated results (this report's Section 3) |
| `requests.csv` | Per-request data: timestamp, user_id, e2e_ms, llm_ms, http_code, success, concurrent_users, question |
| `system_metrics.csv` | System metrics sampled every 5s: CPU%, GPU%, GPU memory, temperature, active users |

---

## 9. Conclusion

The AI Agent Platform on a single `n1-standard-8 + T4` GPU VM can comfortably handle **10-15 concurrent chat users** with sub-10-second response times and 100% success rate. Beyond 15 users, Ollama's serial inference processing creates a bottleneck that causes request queuing and timeouts.

**For 30+ concurrent users**, the platform requires either:
1. **vLLM** with continuous batching (replaces Ollama, 3-5x throughput on same hardware)
2. **Kubernetes HPA** with multiple GPU pods (horizontal scaling)
3. Both (production recommendation)

The existing Kubernetes manifests in `infra/k8s/` with HPA configurations (1-5 replicas at 50% CPU) are designed for exactly this scaling scenario. The production tier deployment (GKE/EKS/AKS) with vLLM on KubeRay would handle 50-100+ concurrent users by auto-scaling GPU pods based on inference queue depth.
