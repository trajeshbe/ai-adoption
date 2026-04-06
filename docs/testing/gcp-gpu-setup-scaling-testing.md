# GCP GPU VM: Setup, Kubernetes Auto-Scaling, and Load Testing

**Date**: 2026-04-06
**Platform**: Google Cloud Platform
**VM**: n1-standard-8 + NVIDIA T4 GPU

---

## Table of Contents

1. [Overview](#1-overview)
2. [VM Provisioning](#2-vm-provisioning)
3. [Software Installation](#3-software-installation)
4. [Application Deployment](#4-application-deployment)
5. [Kubernetes (minikube) Setup](#5-kubernetes-minikube-setup)
6. [How Auto-Scaling Works](#6-how-auto-scaling-works)
7. [Scaling Dashboard](#7-scaling-dashboard)
8. [Load Testing](#8-load-testing)
9. [Scaling Test Results](#9-scaling-test-results)
10. [Tear Down](#10-tear-down)

---

## 1. Overview

This document covers the end-to-end process of deploying the AI Agent Platform on a GCP GPU VM, setting up Kubernetes auto-scaling with minikube, and running load tests to verify scaling behavior.

### Architecture

The deployment runs two layers simultaneously:

```
┌─────────────────────────────────────────────────────────────────┐
│                    GCP VM (n1-standard-8 + T4)                  │
│                                                                 │
│  ┌─── Docker Compose (Application Layer) ──────────────────┐   │
│  │  Frontend (:8055) → Gateway (:8050) → Agent Engine      │   │
│  │      → Ollama (GPU :11434) → qwen2.5:1.5b              │   │
│  │  + Postgres, Redis, MinIO, Cache, Cost Tracker, Docs    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↑ proxies to                          │
│  ┌─── Minikube (Kubernetes Scaling Layer) ─────────────────┐   │
│  │  Namespace: agent-platform                               │   │
│  │  Pods: gateway, agent-engine, frontend (proxy pods)      │   │
│  │  HPA: gateway (1-5 replicas), agent-engine (1-5 replicas)│  │
│  │  Metrics Server: CPU/memory metrics for HPA decisions    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**Docker Compose** runs the actual application services with GPU-accelerated LLM inference.
**Minikube** runs lightweight proxy pods that forward traffic to Docker Compose services, demonstrating Kubernetes HPA auto-scaling behavior.

### Cost

| Resource | Spec | Cost |
|----------|------|------|
| VM | n1-standard-8 (8 vCPU, 30 GB RAM) | ~$195/mo |
| GPU | NVIDIA Tesla T4 (16 GB VRAM) | ~$256/mo |
| Disk | 100 GB pd-balanced | ~$10/mo |
| **Total** | | **~$0.70/hr ($17/day)** |

> **Important**: This is a temporary test VM. Delete it after testing to stop billing.

---

## 2. VM Provisioning

### Prerequisites

- GCP project with billing enabled
- GPU quota: `GPUS_ALL_REGIONS >= 1` (request via IAM & Admin > Quotas)
- gcloud CLI authenticated

### Step 2.1: Request GPU Quota (if needed)

```bash
# Check current quota
gcloud compute project-info describe --project=<PROJECT_ID> \
  --format="json(quotas)" | grep -A2 GPUS_ALL_REGIONS

# If limit is 0, request increase via console:
# https://console.cloud.google.com/iam-admin/quotas
# Filter: "GPUs (all regions)", request limit = 1
```

### Step 2.2: Create Firewall Rule

```bash
gcloud compute firewall-rules create agent-platform-allow-web \
  --project=<PROJECT_ID> \
  --allow=tcp:80,tcp:443,tcp:22,tcp:8050,tcp:8055 \
  --target-tags=agent-platform \
  --description="Allow HTTP, HTTPS, SSH, and app ports"
```

### Step 2.3: Create the GPU VM

```bash
gcloud compute instances create ai-agent-gpu-test \
  --project=<PROJECT_ID> \
  --zone=us-east4-c \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --maintenance-policy=TERMINATE \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-balanced \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --tags=agent-platform
```

> **Note**: T4 GPUs can be exhausted in popular zones. Try multiple zones:
> `us-east4-c`, `us-central1-a/b/c/f`, `us-east1-b/c/d`, `us-west1-a/b`

### Step 2.4: Add SSH Key

```bash
gcloud compute instances add-metadata ai-agent-gpu-test \
  --project=<PROJECT_ID> \
  --zone=us-east4-c \
  --metadata-from-file=ssh-keys=<(echo "<username>:$(cat ~/.ssh/id_rsa.pub)")
```

---

## 3. Software Installation

SSH into the VM:
```bash
ssh <username>@<VM_EXTERNAL_IP>
```

### Step 3.1: Add Package Repositories

```bash
# Docker CE repository
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list

# NVIDIA Container Toolkit repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
```

### Step 3.2: Install Packages

```bash
sudo apt-get install -y \
  nvidia-driver-550 \
  nvidia-container-toolkit \
  docker-ce docker-ce-cli containerd.io docker-compose-plugin \
  git python3-aiohttp
```

### Step 3.3: Configure Docker + NVIDIA Runtime

```bash
# Register NVIDIA runtime with Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify GPU
nvidia-smi
```

Expected output:
```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 580.126.09             Driver Version: 580.126.09     CUDA Version: 13.0     |
| GPU  Name: Tesla T4               16 GB VRAM                                            |
+-----------------------------------------------------------------------------------------+
```

### Step 3.4: Install kubectl and minikube

```bash
# kubectl
curl -LO https://dl.k8s.io/release/v1.32.0/bin/linux/amd64/kubectl
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
rm kubectl

# minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
rm minikube-linux-amd64
```

---

## 4. Application Deployment

### Step 4.1: Clone and Configure

```bash
mkdir -p ~/kiaa
git clone https://github.com/trajeshbe/ai-adoption.git ~/kiaa/ai-adoption
cd ~/kiaa/ai-adoption

# Set environment variables
cat > .env << EOF
NEXT_PUBLIC_GRAPHQL_URL=http://<VM_EXTERNAL_IP>:8050/graphql
LLM_MODEL=qwen2.5:1.5b
EOF
```

### Step 4.2: Build and Start All Services

```bash
docker compose up -d --build
```

This starts 11 containers:

| Container | Purpose | Port |
|-----------|---------|------|
| aiadopt-frontend | Next.js Web UI | 8055 |
| aiadopt-gateway | GraphQL API Gateway | 8050 |
| aiadopt-agent-engine | LangGraph Agent Orchestration | 8053 |
| aiadopt-ollama | LLM Inference (GPU) | 11434 |
| aiadopt-ollama-init | Model puller (one-shot) | - |
| aiadopt-postgres | PostgreSQL + pgvector | 5432 |
| aiadopt-redis | Redis Stack (RediSearch) | 6379 |
| aiadopt-cache-service | Semantic Cache | 8052 |
| aiadopt-cost-tracker | Cost Tracking | 8054 |
| aiadopt-document-service | RAG Document Pipeline | 8051 |
| aiadopt-minio | S3-compatible Object Store | 9000 |

### Step 4.3: Pull the LLM Model

```bash
# Wait for ollama-init to finish, or pull manually:
docker exec aiadopt-ollama ollama pull qwen2.5:1.5b
```

### Step 4.4: Verify

```bash
# All containers healthy?
docker ps

# GPU being used?
nvidia-smi

# Chat works?
curl -s -X POST http://localhost:8050/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { sendMessage(input: {agentId: \"00000000-0000-0000-0000-000000000001\", content: \"Hello!\"}) { content latencyMs } }"}'
```

Expected: ~1.5s response time with GPU, ~31s without.

---

## 5. Kubernetes (minikube) Setup

### Step 5.1: Start minikube

```bash
minikube start \
  --cpus=4 \
  --memory=8192 \
  --driver=docker \
  --profile=aiadopt
```

This creates a single-node Kubernetes cluster named `aiadopt` running inside Docker.

### Step 5.2: Enable Metrics Server

```bash
minikube addons enable metrics-server --profile=aiadopt
```

The **Metrics Server** collects CPU and memory usage from pods every 15 seconds. This data is what the HPA uses to make scaling decisions.

### Step 5.3: Deploy Application Manifests

```bash
cd ~/kiaa/ai-adoption
kubectl apply -f infra/k8s/demo/
```

This creates:
- **Namespace**: `agent-platform`
- **Deployments**: gateway (1 replica), agent-engine (1 replica), frontend (1 replica)
- **Services**: ClusterIP for each deployment
- **HPAs**: gateway (1-5 replicas, 50% CPU), agent-engine (1-5 replicas, 50% CPU)

The pods are lightweight Python proxies that forward traffic to the Docker Compose services running on the host (via minikube bridge IP `192.168.49.1`).

### Step 5.4: Connect Gateway to minikube Network

For the scaling dashboard to work, the Docker Compose gateway needs to reach the minikube API server:

```bash
# Create a flattened kubeconfig with embedded certificates
mkdir -p /tmp/kubectl-bin
cp /usr/local/bin/kubectl /tmp/kubectl-bin/kubectl
kubectl config view --flatten --minify > /tmp/kubectl-bin/kubeconfig

# Mount into gateway container (add to docker-compose.yml):
#   volumes:
#     - /tmp/kubectl-bin:/tmp/kube:ro
#   environment:
#     KUBECONFIG: /tmp/kube/kubeconfig
#     PATH: /tmp/kube:/usr/local/bin:/usr/bin:/bin
#   networks:
#     - app-net
#     - minikube-net  # (external: true, name: aiadopt)

# Restart gateway
docker compose up -d gateway

# Connect gateway container to minikube's Docker network
docker network connect aiadopt aiadopt-gateway
```

### Step 5.5: Verify K8s Integration

```bash
# Should return pods, HPAs, and nodes
curl -s http://localhost:8050/k8s | python3 -m json.tool
```

---

## 6. How Auto-Scaling Works

### The HPA (Horizontal Pod Autoscaler) Control Loop

The HPA runs a continuous control loop every **15 seconds**:

```
┌──────────────────────────────────────────────────────────────┐
│                    HPA Control Loop (every 15s)               │
│                                                               │
│  1. OBSERVE: Query Metrics Server for current CPU usage       │
│     └─→ "gateway pod is using 83% CPU (target: 50%)"        │
│                                                               │
│  2. CALCULATE: Determine desired replica count                │
│     └─→ desiredReplicas = ceil(currentReplicas × (83/50))   │
│     └─→ desiredReplicas = ceil(1 × 1.66) = 2                │
│                                                               │
│  3. SCALE: Update Deployment replica count                    │
│     └─→ kubectl scale deployment/gateway --replicas=2        │
│                                                               │
│  4. STABILIZE: Wait before scaling again                      │
│     └─→ Scale-up window: 10 seconds                          │
│     └─→ Scale-down window: 30 seconds                        │
└──────────────────────────────────────────────────────────────┘
```

### HPA Configuration Explained

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gateway
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gateway         # Which deployment to scale
  minReplicas: 1          # Never go below 1 pod
  maxReplicas: 5          # Never exceed 5 pods
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50    # Target: 50% CPU per pod
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 10   # Wait 10s before scaling up again
      policies:
        - type: Pods
          value: 2                      # Add up to 2 pods at a time
          periodSeconds: 15             # Every 15 seconds
    scaleDown:
      stabilizationWindowSeconds: 30   # Wait 30s before scaling down
      policies:
        - type: Pods
          value: 1                      # Remove 1 pod at a time
          periodSeconds: 30             # Every 30 seconds
```

### Scaling Formula

```
desiredReplicas = ceil(currentReplicas × (currentMetricValue / targetMetricValue))
```

**Example**: If 1 pod is at 83% CPU and target is 50%:
```
desiredReplicas = ceil(1 × (83 / 50)) = ceil(1.66) = 2
```

### Scaling Timeline

```
t=0s     Load starts hitting pods
t=15s    Metrics Server reports first CPU spike (83%)
t=15s    HPA calculates: need 2 replicas
t=15s    HPA creates new pod (scale-up stabilization: 10s)
t=25s    New pod is Running and Ready
t=45s    Load decreases, CPU drops to 3%
t=75s    HPA waits (scale-down stabilization: 30s)
t=75s    HPA terminates extra pod
t=105s   Back to 1 replica
```

### Why Scale-Down is Slower

The `stabilizationWindowSeconds` for scale-down (30s) is deliberately longer than scale-up (10s). This prevents **flapping** -- rapid scale-up/scale-down cycles caused by transient load changes.

---

## 7. Scaling Dashboard

The scaling dashboard is available at:

```
http://<VM_EXTERNAL_IP>:8055/scaling
```

### What It Shows

| Section | Description |
|---------|-------------|
| **Cluster Nodes** | minikube node with CPU/memory/status |
| **HPA Gauges** | Visual gauges showing current vs target CPU for gateway and agent-engine |
| **Pods Table** | All pods in agent-platform namespace with status, readiness, restarts, IP |
| **Service Health** | Health check status of all 6 microservices |
| **Live Traffic** | Request count, latency, active connections from /metrics endpoint |

### How It Works

```
Frontend (/scaling page)
  ├── Polls GET /metrics every 3s → Traffic stats, service health
  └── Polls GET /k8s every 3s → Pod list, HPA data, node info
         └── Gateway shells out to kubectl
              └── kubectl talks to minikube API server (192.168.49.2:8443)
                   └── Returns pods, HPAs, nodes as JSON
```

### Screenshot Walkthrough

When under load, the dashboard shows:
1. **HPA gauges** turn yellow/red as CPU exceeds target
2. **New pods appear** in the pods table with status "Running" 
3. **Replica count** in HPA section increases (e.g., "2/5")
4. When load drops, pods show "Terminating" then disappear

---

## 8. Load Testing

### Test 1: 30 Concurrent Users (LLM Chat Load)

This test measures the platform's capacity for concurrent AI chat sessions.

**Tool**: Custom Python asyncio harness (`tests/load/loadtest_gpu_30users.py`)

```bash
python3 tests/load/loadtest_gpu_30users.py
```

**Ramp schedule**:
```
  0-15s:   5 users
 15-30s:  10 users
 30-45s:  15 users
 45-60s:  20 users
 60-75s:  25 users
 75-120s: 30 users (sustained)
120-150s: ramp down
```

### Test 2: K8s Scaling Load (HPA Trigger)

This test generates CPU load on K8s proxy pods to demonstrate HPA auto-scaling.

**Option A**: Use the existing load test script:
```bash
cd ~/kiaa/ai-adoption
NUM_USERS=10 DURATION_SECONDS=60 GATEWAY_URL=http://localhost:8050 \
  bash scripts/load-test.sh
```

**Option B**: Direct CPU stress injection (guaranteed to trigger HPA):
```bash
# Get pod names
GW_POD=$(kubectl get pods -n agent-platform -l app=gateway \
  -o jsonpath='{.items[0].metadata.name}')
AE_POD=$(kubectl get pods -n agent-platform -l app=agent-engine \
  -o jsonpath='{.items[0].metadata.name}')

# Inject CPU stress (runs ~60 seconds)
kubectl exec -n agent-platform $GW_POD -- sh -c \
  "for i in 1 2 3; do python3 -c \
  'import time; [x**2 for x in range(10**7) for _ in range(100)]' & done"

kubectl exec -n agent-platform $AE_POD -- sh -c \
  "for i in 1 2 3; do python3 -c \
  'import time; [x**2 for x in range(10**7) for _ in range(100)]' & done"
```

**Monitor HPA during test**:
```bash
# Watch HPA in real-time
kubectl get hpa -n agent-platform -w

# Or check every 15 seconds
watch -n 15 'kubectl get hpa,pods -n agent-platform'
```

---

## 9. Scaling Test Results

### 9.1 LLM Chat Load Test Results (30 Users)

| Metric | Value |
|--------|-------|
| **Total Requests** | 287 |
| **Success Rate** | 34.1% (100% at ≤15 users) |
| **Throughput** | 2.18 req/s |
| **GPU Utilization** | avg 67%, max 74% |

**Latency by concurrency**:

| Users | Avg E2E | p95 E2E | Success Rate |
|-------|---------|---------|-------------|
| 5 | 4.4s | 5.9s | 100% |
| 10 | 7.9s | 12.2s | 100% |
| 15 | 16.5s | 20.0s | 100% |
| 20 | 20.9s | 27.1s | 38% |
| 30 | 24.7s | 36.1s | 21% |

**Bottleneck**: Ollama serializes inference requests. At 30 users, queue depth causes timeouts.

### 9.2 HPA Auto-Scaling Test Results

The HPA successfully scaled pods in response to CPU load:

```
Time   Event                        Gateway  Agent-Engine  CPU
─────  ──────────────────────────── ──────── ──────────── ─────
 0s    Baseline                      1 pod    1 pod        10%
 45s   CPU spike detected (83%)      1→2      1→2          83%
 60s   Scale-up complete             2 pods   2 pods       80%
105s   CPU drops to 3%               2 pods   2 pods       3%
120s   Scale-down begins             2→1      2→1          3%
150s   Scale-down complete           1 pod    1 pod        3%
```

**Key observations**:
- **Scale-up latency**: ~15 seconds from CPU spike to new pod Running
- **Scale-down latency**: ~30 seconds from CPU drop to pod Terminated
- **HPA respected policies**: Added 2 pods at once (scaleUp policy), removed 1 at a time (scaleDown policy)
- **Stabilization worked**: No flapping between states

---

## 10. Tear Down

**Critical**: Delete the GPU VM when testing is complete to stop billing (~$17/day).

```bash
# Delete the GPU VM
gcloud compute instances delete ai-agent-gpu-test \
  --project=<PROJECT_ID> \
  --zone=us-east4-c \
  --quiet

# Optional: Delete the firewall rule
gcloud compute firewall-rules delete agent-platform-allow-web \
  --project=<PROJECT_ID> \
  --quiet
```

### Verify Deletion

```bash
# Should return empty
gcloud compute instances list --project=<PROJECT_ID>
```

---

## Appendix A: Troubleshooting

### GPU not detected by Docker

```bash
# Verify NVIDIA driver
nvidia-smi

# Verify runtime configuration
cat /etc/docker/daemon.json  # Should have "nvidia" runtime

# Reconfigure
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### HPA shows `<unknown>` for CPU

```bash
# Check metrics-server is running
kubectl get pods -n kube-system | grep metrics-server

# Wait 60 seconds after deploying pods for metrics to populate
kubectl top pods -n agent-platform
```

### Scaling dashboard shows empty pods

```bash
# Verify kubectl works from gateway container
docker exec aiadopt-gateway /tmp/kube/kubectl \
  --kubeconfig=/tmp/kube/kubeconfig get pods -n agent-platform

# Ensure gateway is on minikube network
docker network connect aiadopt aiadopt-gateway
```

### Ollama model not found

```bash
docker exec aiadopt-ollama ollama list    # Check installed models
docker exec aiadopt-ollama ollama pull qwen2.5:1.5b  # Re-pull
```

---

## Appendix B: File References

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Application services definition |
| `infra/k8s/demo/namespace.yaml` | K8s namespace |
| `infra/k8s/demo/gateway.yaml` | Gateway deployment + HPA + service |
| `infra/k8s/demo/agent-engine.yaml` | Agent-engine deployment + HPA + service |
| `infra/k8s/demo/frontend.yaml` | Frontend deployment + service |
| `scripts/load-test.sh` | Shell-based load test (10 users, 30s) |
| `tests/load/loadtest_gpu_30users.py` | Python asyncio load test (30 users, ramping) |
| `docs/testing/load-test-gcp-gpu-30-users.md` | Detailed load test report |
