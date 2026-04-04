# Kubernetes & Scaling Guide for the Agent Platform

> **Audience:** Fresh graduates and engineers new to Kubernetes.
> This guide walks through every concept from scratch, using plain language,
> analogies, and real configurations from our Agent Platform project.

---

## Table of Contents

1. [What is Kubernetes?](#1-what-is-kubernetes)
2. [Minikube -- Local Kubernetes](#2-minikube----local-kubernetes)
3. [Our K8s Architecture](#3-our-k8s-architecture)
4. [Horizontal Pod Autoscaler (HPA)](#4-horizontal-pod-autoscaler-hpa)
5. [The Scaling Dashboard](#5-the-scaling-dashboard)
6. [Load Testing & Scaling Demo](#6-load-testing--scaling-demo)
7. [Production Considerations](#7-production-considerations)
8. [Key kubectl Commands](#8-key-kubectl-commands)
9. [Glossary](#9-glossary)

---

## 1. What is Kubernetes?

### The Airport Control Tower Analogy

Imagine a busy international airport. Hundreds of flights need to land, take off,
taxi, refuel, and park -- all without colliding or running out of gates.

- **The airport** is your cluster -- all the physical infrastructure.
- **Each terminal** is a Node -- a machine (physical or virtual) with runways and gates.
- **Each airplane** is a Pod -- the smallest deployable unit carrying your application.
- **Air Traffic Control (ATC)** is the Kubernetes control plane -- it decides which
  plane goes to which terminal, reroutes if a runway is blocked, and launches extra
  flights when passenger demand surges.

Without ATC, pilots would have to coordinate amongst themselves. That works for two
planes. It falls apart at two hundred. Kubernetes is your ATC for containers.

```
               +-----------------------------------------------+
               |              KUBERNETES CLUSTER               |
               |                                               |
               |   +-------------------+  +-----------------+  |
               |   |   CONTROL PLANE   |  |   CONTROL PLANE |  |
               |   |   (ATC Tower)     |  |   (Backup ATC)  |  |
               |   +--------+----------+  +--------+--------+  |
               |            |                      |            |
               |   +--------v-----------+----------v---------+ |
               |   |       NODE 1       |       NODE 2       | |
               |   |    (Terminal A)    |    (Terminal B)     | |
               |   |                    |                     | |
               |   |  [Pod] [Pod] [Pod] |  [Pod] [Pod]       | |
               |   |  (flights at gates)|  (flights at gates)| |
               |   +--------------------+---------------------+ |
               +-----------------------------------------------+
```

### Key Concepts

#### Pods

A Pod is the smallest thing Kubernetes manages. It wraps one or more containers that
share the same network and storage. Think of it as a single airplane -- it might carry
multiple cargo containers (application container + sidecar logger), but they travel
together as one unit.

```yaml
# A simple Pod definition
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
    - name: app
      image: my-app:1.0
      ports:
        - containerPort: 8080
```

Most of the time you do **not** create Pods directly. You create Deployments, which
manage Pods for you.

#### Deployments

A Deployment tells Kubernetes: "I want 3 copies of this Pod running at all times."
If one crashes, Kubernetes starts a replacement automatically. If you push a new
image version, Kubernetes does a rolling update -- replacing Pods one at a time so
your service never goes fully offline.

```
Deployment (desired state: 3 replicas)
  |
  +-- ReplicaSet (manages actual pod instances)
       |
       +-- Pod 1  [Running]
       +-- Pod 2  [Running]
       +-- Pod 3  [Running]
```

#### Services

Pods come and go (they crash, they scale, they get rescheduled). Their IP addresses
change every time. A Service gives your pods a **stable address** -- a single DNS name
and IP that never changes, no matter how many pods sit behind it.

```
                  +------------------+
   traffic  --->  |    Service       |  stable-ip:8080
                  |  (load balancer) |
                  +-------+----------+
                          |
              +-----------+-----------+
              |           |           |
          +---v---+   +---v---+   +---v---+
          | Pod 1 |   | Pod 2 |   | Pod 3 |
          +-------+   +-------+   +-------+
```

Think of a Service as the airline's booking phone number. Callers always dial the same
number; the airline routes them to whichever agent is free.

#### Namespaces

Namespaces are logical partitions inside a cluster. They let multiple teams or projects
share the same cluster without stepping on each other. In our project, everything lives
in the `agent-platform` namespace.

```
Cluster
  |
  +-- namespace: default          (K8s built-in)
  +-- namespace: kube-system      (K8s internal components)
  +-- namespace: agent-platform   (our project)
       |
       +-- deployment/gateway
       +-- deployment/agent-engine
       +-- deployment/frontend
       +-- service/gateway
       +-- service/agent-engine
       +-- service/frontend
       +-- hpa/gateway
       +-- hpa/agent-engine
```

#### Nodes

A Node is a machine (VM, bare-metal server, or in our case a minikube VM) that runs
Pods. Each node has a **kubelet** (an agent that talks to the control plane) and a
container runtime (Docker, containerd, etc.) to actually run containers.

### How Kubernetes Differs from Docker Compose

| Feature | Docker Compose | Kubernetes |
|---|---|---|
| **Scope** | Single machine | Cluster of machines |
| **Scaling** | `docker compose up --scale web=3` (manual) | HPA scales automatically based on metrics |
| **Self-healing** | Restart policy only | Replaces failed pods, reschedules to healthy nodes |
| **Networking** | Simple bridge network | Full service discovery, DNS, load balancing, ingress |
| **Rolling updates** | Recreate containers | Zero-downtime rolling deployments |
| **Storage** | Volume mounts | PersistentVolumes, StorageClasses, dynamic provisioning |
| **Config format** | `docker-compose.yml` | Multiple YAML manifests (Deployments, Services, etc.) |
| **Best for** | Local dev, small apps | Production workloads at any scale |

**Bottom line:** Docker Compose is a TV remote -- simple, one device. Kubernetes is a
universal remote that can control every screen, speaker, and light in the building.

---

## 2. Minikube -- Local Kubernetes

### What is Minikube?

Minikube runs a complete Kubernetes cluster on your laptop. It creates a virtual machine
(or Docker container) that acts as a single-node cluster, giving you the full Kubernetes
API without needing cloud infrastructure.

Think of it as a flight simulator -- the controls are identical to a real airplane, but
you are safely on the ground.

### Why We Use It

- **Free and local:** No cloud account, no billing surprises.
- **Fast feedback:** Deploy, test, and iterate without pushing to a remote cluster.
- **Parity with production:** Same kubectl commands, same YAML manifests.
- **Addons:** Built-in metrics-server, ingress, dashboard, and more.

### How We Set It Up

```bash
# Create the cluster with enough resources for our 3 services + HPA
minikube start \
  --cpus=4 \
  --memory=8192 \
  --driver=docker \
  --profile=aiadopt
```

**Breaking down the flags:**

| Flag | Purpose |
|---|---|
| `--cpus=4` | Allocate 4 CPU cores to the minikube VM. Our 3 services + HPA need headroom. |
| `--memory=8192` | 8 GB RAM. Kubernetes itself needs ~1-2 GB; the rest is for our pods. |
| `--driver=docker` | Use Docker as the virtualization driver (fastest, works on Linux/Mac/Windows). |
| `--profile=aiadopt` | Name our cluster "aiadopt" so it does not collide with other minikube clusters. |

### The Metrics-Server Addon

The HPA needs CPU/memory metrics to make scaling decisions. The metrics-server addon
collects these from every node's kubelet and exposes them via the Kubernetes Metrics API.

```bash
# Enable the metrics-server addon
minikube addons enable metrics-server --profile=aiadopt
```

Without metrics-server, running `kubectl top pods` returns an error and HPA cannot
function. It is the foundation of autoscaling.

```
kubelet (on each node)
   |
   +-- cAdvisor (built into kubelet, collects container CPU/mem stats)
          |
          v
   metrics-server (aggregates stats from all kubelets)
          |
          v
   Metrics API (/apis/metrics.k8s.io/v1beta1)
          |
          v
   HPA Controller (reads metrics, computes desired replicas)
```

---

## 3. Our K8s Architecture

### Namespace: agent-platform

All our resources live in the `agent-platform` namespace:

```bash
kubectl create namespace agent-platform
```

### The Three Deployments

```
+-------------------------------------------------------------+
|                  agent-platform namespace                    |
|                                                              |
|  +--------------+  +----------------+  +--------------+      |
|  |   gateway    |  |  agent-engine  |  |   frontend   |      |
|  |  Deployment  |  |   Deployment   |  |  Deployment  |      |
|  |   (proxy)    |  |    (proxy)     |  |   (proxy)    |      |
|  |  port: 8050  |  |   port: 8060   |  |  port: 3000  |      |
|  +------+-------+  +-------+--------+  +------+-------+      |
|         |                  |                   |              |
|  +------v-------+  +-------v--------+  +------v-------+      |
|  |   Service    |  |    Service     |  |   Service    |      |
|  | gateway:8050 |  | agent-eng:8060 |  | frontend:3000|      |
|  +--------------+  +----------------+  +--------------+      |
+-------------------------------------------------------------+
          |                  |                   |
          v                  v                   v
   +-----------+      +-----------+       +-----------+
   | Host:8050 |      | Host:8060 |       | Host:3000 |
   |  FastAPI   |      |  Prefect  |       |  Next.js  |
   |  Gateway   |      |  Engine   |       |  Frontend |
   +-----------+      +-----------+       +-----------+
```

### The Proxy Pod Pattern

Our Kubernetes pods do **not** run the actual services. Instead, each pod runs a tiny
Python HTTP server that forwards requests to the real service running on the host
machine (your laptop).

**Why this pattern?**

1. **GPU access:** The agent-engine and LLM runtime need GPU drivers and CUDA libraries
   that are complex to configure inside containers. Running them on the host lets them
   access the GPU directly.
2. **Heavy dependencies:** Full Python environments with PyTorch, vLLM, and LangGraph
   can be 10+ GB. Proxy pods are a few kilobytes.
3. **Fast iteration:** You edit code on the host and see changes immediately --
   no container rebuild needed.
4. **Real K8s behavior:** Even though the workload is proxied, Kubernetes still manages
   pod lifecycle, service discovery, HPA scaling, and health checks -- exactly like
   production.

### The Proxy Code

Here is the actual inline Python proxy that runs inside each pod:

```python
# Inside gateway.yaml - inline Python proxy server
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, os

HOST = os.environ.get("UPSTREAM_HOST", "192.168.49.1")  # minikube host IP
PORT = os.environ.get("UPSTREAM_PORT", "8050")

class Proxy(BaseHTTPRequestHandler):
    def do_GET(self):
        r = urllib.request.urlopen(
            f"http://{HOST}:{PORT}{self.path}", timeout=5
        )
        data = r.read()
        self.send_response(r.status)
        self.send_header("Content-Type", r.headers.get("Content-Type"))
        self.end_headers()
        self.wfile.write(data)

HTTPServer(("0.0.0.0", 8050), Proxy).serve_forever()
```

**How it works, step by step:**

1. Kubernetes routes traffic to the pod on port 8050.
2. The proxy receives the HTTP request.
3. It forwards the request to `192.168.49.1:8050` -- the minikube host IP where the
   real FastAPI gateway is running.
4. It reads the response and sends it back to the caller.
5. From the caller's perspective, the pod **is** the gateway.

The IP `192.168.49.1` is the special address minikube uses for "the machine running
minikube." It is the bridge between the Kubernetes network and your host network.

```
Browser/Client
     |
     v
[K8s Service: gateway:8050]
     |
     v
[Pod: proxy container]  -- forwards via HTTP -->  [Host: FastAPI on :8050]
     ^                                                     |
     |                                                     v
     +<-------------- response flows back ----------------+
```

---

## 4. Horizontal Pod Autoscaler (HPA)

### What It Is

The Horizontal Pod Autoscaler automatically adjusts the number of pod replicas in a
Deployment based on observed metrics (typically CPU utilization). When load increases,
it adds pods. When load decreases, it removes them.

**Analogy:** Think of a restaurant. On a quiet Tuesday, you need 2 waiters. On a Friday
night, you need 8. The HPA is the manager who watches how busy each waiter is and
calls in extra staff (or sends them home) automatically.

```
                         HPA Controller Loop (every 15s)
                                |
             +------------------+------------------+
             |                                     |
     Read current metrics               Compare to target
     (CPU: 75%)                         (Target: 50%)
             |                                     |
             +------------------+------------------+
                                |
                    desiredReplicas = ceil(
                      currentReplicas * (currentMetric / targetMetric)
                    )
                    = ceil(2 * (75 / 50))
                    = ceil(3.0) = 3
                                |
                                v
                    Scale Deployment to 3 replicas
```

### Our HPA Configuration

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gateway
  namespace: agent-platform
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
      policies:
        - type: Pods
          value: 1
          periodSeconds: 30
```

**Field-by-field breakdown:**

| Field | Value | Meaning |
|---|---|---|
| `scaleTargetRef` | `Deployment/gateway` | Which Deployment the HPA controls |
| `minReplicas` | `1` | Never scale below 1 pod (always at least one running) |
| `maxReplicas` | `5` | Never scale above 5 pods (cost/resource ceiling) |
| `averageUtilization` | `50` | Target: keep average CPU usage at 50% across all pods |
| **Scale-Up Behavior** | | |
| `stabilizationWindowSeconds` | `10` | Wait 10s after a scale-up before considering another |
| `policies: Pods` | `2 per 15s` | Add at most 2 pods every 15 seconds |
| **Scale-Down Behavior** | | |
| `stabilizationWindowSeconds` | `30` | Wait 30s after a scale-down before considering another |
| `policies: Pods` | `1 per 30s` | Remove at most 1 pod every 30 seconds |

**Why asymmetric scaling?** Scale-up is aggressive (add 2 pods, short stabilization)
because unresponsive services lose users immediately. Scale-down is conservative
(remove 1 pod, longer stabilization) because premature scale-down causes thrashing --
scaling up and down repeatedly.

### The Metrics Pipeline

```
+--------+     +----------+     +----------------+     +----------------+
| cAdvisor| --> | kubelet  | --> | metrics-server | --> | HPA Controller |
| (per    |     | (per     |     | (cluster-wide) |     | (control plane)|
| container)    | node)    |     |                |     |                |
+--------+     +----------+     +----------------+     +----------------+
  Collects       Exposes          Aggregates             Reads metrics,
  CPU/mem        metrics via      from all nodes,        computes desired
  stats from     Summary API      serves via             replicas, patches
  containers                      Metrics API            Deployment
```

1. **cAdvisor** is built into the kubelet. It watches each container's CPU and memory
   usage at the kernel level (via Linux cgroups).
2. **kubelet** exposes these stats via its Summary API on each node.
3. **metrics-server** scrapes every kubelet, aggregates the data, and serves it through
   the Kubernetes Metrics API (`/apis/metrics.k8s.io/v1beta1`).
4. **HPA Controller** queries the Metrics API every 15 seconds (default), computes the
   desired replica count, and patches the Deployment's `spec.replicas` field.

---

## 5. The Scaling Dashboard

### Overview

The frontend includes a dedicated `/scaling` page that provides a real-time view of
the Kubernetes cluster state. It is designed to make the invisible visible -- you can
watch pods spin up and down as the HPA reacts to load.

### How It Works

```
+------------------+         +------------------+         +------------------+
|    Browser       |  poll   |   Next.js API    |  exec   |    kubectl       |
|   /scaling page  | ------> |   /api/k8s       | ------> |   (CLI on host)  |
|   (every 3s)     |         |   route handler  |         |                  |
+------------------+         +------------------+         +------------------+
         |                           |                            |
         |    also polls             |                            v
         +---------->  /api/metrics  |                   Kubernetes API
                       (gateway      |                   Server
                        health data) |
                                     v
                              JSON response:
                              {
                                nodes: [...],
                                hpas: [...],
                                pods: [...],
                                services: [...]
                              }
```

- **Polling interval:** 3 seconds. Fast enough to see scaling in action, slow enough
  to not overwhelm the API.
- **`/api/k8s` endpoint:** Shells out to `kubectl` commands (`get pods`, `get hpa`,
  `get nodes`, `top pods`) and parses the output into JSON.
- **`/api/metrics` endpoint:** Returns gateway health metrics (request count, latency,
  error rate).

### Dashboard Sections

```
+-------------------------------------------------------------------+
|                    SCALING DASHBOARD                               |
+-------------------------------------------------------------------+
|                                                                   |
|  NODES                                                            |
|  +-------------------------------------------------------------+ |
|  | Name           | Status | Roles         | Version            | |
|  | aiadopt        | Ready  | control-plane | v1.33.1            | |
|  +-------------------------------------------------------------+ |
|                                                                   |
|  HORIZONTAL POD AUTOSCALERS                                       |
|  +-------------------------------------------------------------+ |
|  | Name         | Reference     | Min | Max | Replicas | CPU   | |
|  | gateway      | deploy/gw     |  1  |  5  |    2     | 45%   | |
|  | agent-engine | deploy/ae     |  1  |  5  |    1     | 12%   | |
|  +-------------------------------------------------------------+ |
|                                                                   |
|  PODS                                                             |
|  +-------------------------------------------------------------+ |
|  | Name              | Status  | Restarts | Age   | CPU  | Mem | |
|  | gateway-abc-123   | Running |    0     | 5m    | 23m  | 8Mi | |
|  | gateway-abc-456   | Running |    0     | 30s   | 45m  | 8Mi | |
|  | agent-eng-def-789 | Running |    0     | 5m    | 5m   | 4Mi | |
|  | frontend-ghi-012  | Running |    0     | 5m    | 2m   | 6Mi | |
|  +-------------------------------------------------------------+ |
|                                                                   |
|  REPLICA GAUGE                 CPU UTILIZATION                    |
|  gateway:    [|||..] 2/5       gateway:    [======----] 45%       |
|  agent-eng:  [|....] 1/5       agent-eng:  [==--------] 12%      |
|                                                                   |
|  SERVICE HEALTH                                                   |
|  +-------------------------------------------------------------+ |
|  | Service    | Status  | Requests | Avg Latency | Errors      | |
|  | gateway    | Healthy |   1,245  |    23ms     |   0.1%      | |
|  | agent-eng  | Healthy |     832  |    45ms     |   0.0%      | |
|  | frontend   | Healthy |   2,100  |    12ms     |   0.0%      | |
|  +-------------------------------------------------------------+ |
|                                                                   |
|  TRAFFIC METRICS (last 5 min)                                     |
|  Requests: 156 | Success: 60 | Rate Limited: 96 | Errors: 0     |
+-------------------------------------------------------------------+
```

---

## 6. Load Testing & Scaling Demo

### The Load Test Script

Our `scripts/load-test.sh` script uses `curl` in parallel to simulate concurrent
users hitting the gateway:

```bash
# Simplified version of scripts/load-test.sh
CONCURRENT_USERS=10
DURATION=60  # seconds
TARGET="http://localhost:8050/healthz"

for i in $(seq 1 $CONCURRENT_USERS); do
  (
    end=$((SECONDS + DURATION))
    while [ $SECONDS -lt $end ]; do
      curl -s -o /dev/null -w "%{http_code}" "$TARGET"
    done
  ) &
done
wait
```

### Load Test Results

```
+---------------------------+
|   Load Test Summary       |
+---------------------------+
| Total Requests:    156    |
| Successful (200):   60    |
| Rate Limited (429): 96    |
| Errors (5xx):        0    |
| Duration:           60s   |
| Concurrency:         10   |
+---------------------------+
```

The rate limiter is configured at 60 requests per minute. Of the 156 requests sent,
exactly 60 got through (one per second) and 96 were correctly rejected with HTTP 429
(Too Many Requests). Zero errors means the system handled the overload gracefully.

### The Scaling Lifecycle

This is what happens during a scaling demo, step by step. Follow along by watching
the `/scaling` dashboard.

```
TIME    EVENT                           PODS    CPU
─────   ─────────────────────────────   ────    ─────
t=0s    Baseline state                  3       ~2%
        gateway(1), agent-engine(1),
        frontend(1)

t=5s    CPU stress applied to pods      3       CPU rising...
        (Python burn loops injected)

t=15s   HPA detects CPU at 377%         3       377%
        (vs 50% target)
        Decision: scale up

t=20s   New pods scheduled              5       still high
        gateway: 1 -> 3
        agent-engine: 1 -> 3

t=23s   More pods added                 11      starting to
        gateway: 3 -> 5 (max)                   distribute
        agent-engine: 3 -> 5 (max)

t=30s   CPU stress ends                 11      normalizing

t=60s   HPA sees CPU below target       11      <50%
        Decision: start scaling down

t=90s   Scale down begins               10      low
        agent-engine: 5 -> 4

t=120s  Continued scale down            9       low
        gateway: 5 -> 4

t=150s  Further reduction               7       low

...     Gradual 1-pod-per-30s           ...     ...
        step-down continues

t=300s  Settled at minimum              3       ~2%
        gateway(1), agent-engine(1),
        frontend(1)
```

#### Step 1: Baseline (3 pods, ~2% CPU)

```
gateway(1 pod)  ----  [=..........]  2% CPU
agent-engine(1) ----  [=..........]  2% CPU
frontend(1)     ----  [=..........]  1% CPU
```

The cluster is idle. Each deployment has one pod, consuming almost no CPU.

#### Step 2: CPU Stress Applied

CPU stress is injected into pods using inline Python burn loops:

```python
# Burns CPU by running tight loops on multiple threads
import threading, time
def burn():
    while True:
        x = 1
        for _ in range(1000000):
            x *= 1.0001
for _ in range(4):
    threading.Thread(target=burn, daemon=True).start()
```

#### Step 3: HPA Detects High CPU (377%)

The HPA controller reads metrics-server and sees CPU at 377% of the target. It
calculates the desired replicas:

```
desiredReplicas = ceil(currentReplicas * (currentCPU / targetCPU))
                = ceil(1 * (377 / 50))
                = ceil(7.54)
                = 8   (capped at maxReplicas: 5 per deployment)
```

#### Step 4: Scale UP (3 to 11 pods in ~23 seconds)

```
t=15s   gateway:      [|]        -> 1 pod
t=20s   gateway:      [|||]      -> 3 pods  (+2, per policy)
t=23s   gateway:      [|||||]    -> 5 pods  (+2, hit max)

t=15s   agent-engine: [|]        -> 1 pod
t=20s   agent-engine: [|||]      -> 3 pods  (+2, per policy)
t=23s   agent-engine: [|||||]    -> 5 pods  (+2, hit max)

        frontend:     [|]        -> 1 pod   (no HPA, stays at 1)

Total: 5 + 5 + 1 = 11 pods
```

The scale-up policy allows adding 2 pods every 15 seconds, with only 10 seconds of
stabilization. This aggressive policy gets us to max capacity in about 23 seconds.

#### Step 5: CPU Stress Ends

The burn loops are terminated. CPU usage drops back to normal within seconds.

#### Step 6: Scale DOWN (gradual)

Scale-down is intentionally slow to prevent thrashing:

```
t=60s    11 pods  -- HPA waits for 30s stabilization window --
t=90s    10 pods  (agent-engine: 5 -> 4)    [-1 pod]
t=120s    9 pods  (gateway: 5 -> 4)          [-1 pod]
t=150s    8 pods  (agent-engine: 4 -> 3)    [-1 pod]
t=180s    7 pods  (gateway: 4 -> 3)          [-1 pod]
t=210s    6 pods  (agent-engine: 3 -> 2)    [-1 pod]
t=240s    5 pods  (gateway: 3 -> 2)          [-1 pod]
t=270s    4 pods  (agent-engine: 2 -> 1)    [-1 pod]
t=300s    3 pods  (gateway: 2 -> 1)          [-1 pod]
```

Notice: only 1 pod is removed per 30 seconds. If a new traffic spike hits during
scale-down, the HPA immediately switches back to scale-up mode.

#### Step 7: Graceful Shutdown

During scale-down, pods transition through statuses:

```
NAME                      STATUS        AGE
gateway-abc-123           Running       5m
gateway-abc-456           Terminating   2m    <-- being removed
gateway-abc-789           Terminating   2m    <-- being removed
agent-engine-def-012      Running       5m
agent-engine-def-345      Terminating   2m    <-- being removed
```

Kubernetes sends a SIGTERM to the pod, waits for the grace period (default 30s) for
it to finish in-flight requests, then sends SIGKILL if it is still running.

---

## 7. Production Considerations

### Why Proxy Pods Will Not Trigger HPA in the Real World

In our demo setup, the proxy pods are ultra-lightweight -- they just forward HTTP
requests. Their CPU usage is negligible. The CPU stress we applied was artificial
(burn loops injected into the pods). In a real deployment, the actual application code
running inside pods would naturally consume CPU under load, and the HPA would respond
to that genuine usage.

### Real Deployment: Services Run IN Kubernetes

In production, you would not use proxy pods. Each service runs directly in its pod:

```
Demo Setup (proxy pattern):
  K8s Pod [proxy] --> Host [actual service]

Production Setup:
  K8s Pod [actual service]   <-- everything inside the cluster
```

The Dockerfiles in `services/*/Dockerfile` build full container images with all
dependencies. The proxy pattern is a development convenience only.

### GPU Scheduling with NVIDIA Device Plugin

For the agent-engine and LLM runtime (vLLM), GPU access is critical:

```yaml
# Production pod spec requesting a GPU
spec:
  containers:
    - name: llm-runtime
      image: agent-platform/llm-runtime:1.0
      resources:
        limits:
          nvidia.com/gpu: 1    # Request 1 GPU
        requests:
          cpu: "2"
          memory: "16Gi"
```

The NVIDIA device plugin exposes GPUs as a schedulable resource. Kubernetes will only
place this pod on a node that has a free GPU. If no GPU is available, the pod stays in
`Pending` state.

### Pod Disruption Budgets (PDB)

A PDB tells Kubernetes: "You must keep at least N pods running during voluntary
disruptions (upgrades, node drains)."

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: gateway-pdb
  namespace: agent-platform
spec:
  minAvailable: 2           # Always keep at least 2 gateway pods running
  selector:
    matchLabels:
      app: gateway
```

This prevents scenarios like: "Kubernetes drained a node for maintenance and took down
all 3 gateway pods at once, causing an outage."

### Anti-Affinity Rules for High Availability

Anti-affinity ensures pods of the same Deployment are spread across different nodes:

```yaml
spec:
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchExpressions:
                - key: app
                  operator: In
                  values:
                    - gateway
            topologyKey: kubernetes.io/hostname
```

This means: "Try to schedule gateway pods on different nodes." If Node A goes down,
gateway pods on Node B and C keep serving traffic.

```
Without anti-affinity:           With anti-affinity:

  Node A                           Node A         Node B         Node C
  [gw-1]                          [gw-1]         [gw-2]         [gw-3]
  [gw-2]
  [gw-3]

  Node A dies = 100% outage       Node A dies = 33% capacity loss, still serving
```

### Resource Requests vs Limits

These two fields control how Kubernetes schedules and constrains your pods:

```yaml
resources:
  requests:
    cpu: "250m"       # Guaranteed minimum: 0.25 CPU cores
    memory: "256Mi"   # Guaranteed minimum: 256 MB RAM
  limits:
    cpu: "1000m"      # Hard ceiling: 1.0 CPU cores
    memory: "512Mi"   # Hard ceiling: 512 MB RAM (OOMKilled if exceeded)
```

| | Requests | Limits |
|---|---|---|
| **Purpose** | Scheduling: "I need at least this much" | Protection: "Never exceed this" |
| **CPU** | Guaranteed CPU time | Throttled if exceeded (slowed down, not killed) |
| **Memory** | Guaranteed memory | OOMKilled if exceeded (pod is terminated) |
| **Scheduler** | Uses requests to find a node with enough free resources | Does not affect scheduling |

**Analogy:** Requests are like a restaurant reservation (guaranteed table). Limits are
like the fire code (maximum occupancy, enforced strictly).

**Important:** If you set limits without requests, Kubernetes sets requests equal to
limits. If you set requests without limits, your pod can burst above its request but
may be evicted if the node runs low on resources.

---

## 8. Key kubectl Commands

### Viewing Resources

```bash
# List all pods in the agent-platform namespace
kubectl get pods -n agent-platform

# List pods with extra details (node, IP)
kubectl get pods -n agent-platform -o wide

# Watch pods in real-time (updates as they change)
kubectl get pods -n agent-platform -w

# List all HPAs and their current status
kubectl get hpa -n agent-platform

# Show CPU and memory usage for each pod
kubectl top pods -n agent-platform

# Show resource usage for nodes
kubectl top nodes
```

### Inspecting Resources

```bash
# Detailed info about an HPA (events, conditions, metrics)
kubectl describe hpa gateway -n agent-platform

# Detailed info about a pod (events, conditions, volumes)
kubectl describe pod <pod-name> -n agent-platform

# View logs from a pod (add -f to stream/follow)
kubectl logs <pod-name> -n agent-platform

# View logs from a specific container in a multi-container pod
kubectl logs <pod-name> -c <container-name> -n agent-platform

# View previous logs (from the last crashed container)
kubectl logs <pod-name> -n agent-platform --previous
```

### Modifying Resources

```bash
# Manually scale a deployment to 3 replicas
kubectl scale deployment gateway --replicas=3 -n agent-platform

# Apply a YAML manifest
kubectl apply -f deployment.yaml

# Delete a specific pod (Deployment will recreate it)
kubectl delete pod <pod-name> -n agent-platform

# Execute a command inside a running pod (interactive shell)
kubectl exec -it <pod-name> -n agent-platform -- /bin/sh
```

### Debugging

```bash
# Check events in the namespace (scheduling failures, OOM kills, etc.)
kubectl get events -n agent-platform --sort-by=.metadata.creationTimestamp

# Check why a pod is Pending (usually resource constraints)
kubectl describe pod <pending-pod-name> -n agent-platform | grep -A 10 Events

# Port-forward a service to your localhost for testing
kubectl port-forward svc/gateway 8050:8050 -n agent-platform

# View the raw YAML of a running deployment
kubectl get deployment gateway -n agent-platform -o yaml
```

---

## 9. Glossary

| Term | Definition |
|---|---|
| **Cluster** | A set of machines (nodes) running Kubernetes. Contains the control plane and worker nodes. |
| **Control Plane** | The brain of Kubernetes. Includes the API server, scheduler, controller manager, and etcd. Makes all orchestration decisions. |
| **Node** | A single machine (physical or virtual) in the cluster that runs pods. Each node runs a kubelet and a container runtime. |
| **Pod** | The smallest deployable unit in Kubernetes. Wraps one or more containers that share networking and storage. Ephemeral by design. |
| **Container** | A lightweight, isolated process running an application. Built from a container image (e.g., Docker image). |
| **Deployment** | A controller that manages a set of identical pods. Handles scaling, rolling updates, and self-healing. |
| **ReplicaSet** | Created by a Deployment to ensure the desired number of pod replicas are running. You rarely interact with ReplicaSets directly. |
| **Service** | A stable network endpoint (IP + DNS name) that routes traffic to a set of pods, even as pods are created or destroyed. |
| **Namespace** | A logical partition within a cluster for organizing resources and applying access controls. |
| **HPA (Horizontal Pod Autoscaler)** | A controller that automatically scales the number of pod replicas based on observed metrics (CPU, memory, custom metrics). |
| **kubelet** | The agent running on each node. It receives pod specs from the control plane and ensures the containers are running. |
| **cAdvisor** | Container Advisor. Built into the kubelet, it collects CPU, memory, and network stats from running containers. |
| **metrics-server** | A cluster-wide aggregator that collects resource metrics from kubelets and serves them via the Metrics API. Required for HPA and `kubectl top`. |
| **Ingress** | A rule set for routing external HTTP/HTTPS traffic to Services inside the cluster. Requires an Ingress Controller (e.g., Contour, NGINX). |
| **ConfigMap** | A Kubernetes object for storing non-sensitive configuration data (key-value pairs or files) that pods can consume. |
| **Secret** | Like a ConfigMap, but for sensitive data (passwords, tokens). Stored base64-encoded (not encrypted by default). |
| **PersistentVolume (PV)** | A piece of storage provisioned in the cluster. Independent of any pod's lifecycle. |
| **PersistentVolumeClaim (PVC)** | A request for storage by a pod. Binds to a PersistentVolume. |
| **DaemonSet** | Ensures one pod runs on every node (or a subset). Used for logging agents, monitoring, etc. |
| **StatefulSet** | Like a Deployment, but for stateful applications. Provides stable network IDs and persistent storage per pod. |
| **CronJob** | Runs a pod on a cron schedule (e.g., every night at 2 AM). |
| **Kustomize** | A tool for customizing Kubernetes YAML without templates. Uses overlays (base + patches). Built into kubectl. |
| **Helm** | A package manager for Kubernetes. Uses charts (templated YAML bundles) to install complex applications. |
| **RBAC** | Role-Based Access Control. Defines who (users, service accounts) can do what (verbs) on which resources. |
| **Pod Disruption Budget (PDB)** | Limits how many pods can be unavailable during voluntary disruptions (drains, upgrades). |
| **Taint / Toleration** | Taints mark a node as "off-limits" to most pods. Tolerations let specific pods ignore the taint and run on that node. |
| **Affinity / Anti-Affinity** | Rules that influence where pods are scheduled. Affinity = "place near X." Anti-affinity = "place away from X." |
| **Resource Requests** | The guaranteed minimum CPU/memory a pod needs. Used by the scheduler to find a suitable node. |
| **Resource Limits** | The maximum CPU/memory a pod can use. CPU is throttled; memory over limit causes OOMKill. |
| **OOMKilled** | Out Of Memory Killed. The Linux kernel terminates a container that exceeds its memory limit. |
| **Rolling Update** | The default Deployment strategy. Replaces pods one (or a few) at a time, ensuring zero-downtime updates. |
| **Liveness Probe** | A health check that tells Kubernetes whether to restart a container (e.g., "is the HTTP server responding?"). |
| **Readiness Probe** | A health check that tells Kubernetes whether to send traffic to a container (e.g., "is the database connection ready?"). |
| **SIGTERM** | The termination signal sent to a container before shutdown. Applications should handle it to finish in-flight requests. |
| **SIGKILL** | The forced kill signal sent if a container does not stop after the grace period (default 30s). Cannot be caught or ignored. |
| **etcd** | The distributed key-value store used by the control plane to persist all cluster state. |
| **kubectl** | The command-line tool for interacting with Kubernetes clusters. Sends requests to the API server. |
| **minikube** | A tool that runs a single-node Kubernetes cluster locally for development and testing. |

---

> **Next steps:** After understanding this guide, proceed to
> [Phase 7: Service Mesh](../phase-07-service-mesh.md) to learn about Istio ambient
> mesh and Contour/Envoy ingress, or
> [Phase 10: Production Hardening](../phase-10-production-hardening.md) for load
> testing, chaos engineering, and SLO configuration.
