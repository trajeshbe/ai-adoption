# Kubernetes Auto-Scaling: Deep Technical Guide

> **Prerequisites**: Basic understanding of Kubernetes (pods, deployments, services).
> See `docs/tutorial/kubernetes-scaling-guide.md` for fundamentals.

---

## Table of Contents

1. [The Three Dimensions of Kubernetes Scaling](#1-the-three-dimensions-of-kubernetes-scaling)
2. [The Metrics Pipeline: From Container to HPA](#2-the-metrics-pipeline-from-container-to-hpa)
3. [HPA Internals: The Control Loop](#3-hpa-internals-the-control-loop)
4. [The Scaling Algorithm (with Math)](#4-the-scaling-algorithm-with-math)
5. [Stabilization and Flap Prevention](#5-stabilization-and-flap-prevention)
6. [Our Platform's HPA Configuration Decoded](#6-our-platforms-hpa-configuration-decoded)
7. [What Happens During a Scale-Up (Step by Step)](#7-what-happens-during-a-scale-up-step-by-step)
8. [What Happens During a Scale-Down (Step by Step)](#8-what-happens-during-a-scale-down-step-by-step)
9. [Custom Metrics and Beyond CPU](#9-custom-metrics-and-beyond-cpu)
10. [VPA: Vertical Pod Autoscaler](#10-vpa-vertical-pod-autoscaler)
11. [Cluster Autoscaler: Scaling the Nodes](#11-cluster-autoscaler-scaling-the-nodes)
12. [KEDA: Event-Driven Autoscaling](#12-keda-event-driven-autoscaling)
13. [Scaling for LLM Inference Workloads](#13-scaling-for-llm-inference-workloads)
14. [Production Checklist](#14-production-checklist)
15. [Observed Results from Our Platform](#15-observed-results-from-our-platform)

---

## 1. The Three Dimensions of Kubernetes Scaling

Kubernetes provides three complementary auto-scaling mechanisms. They operate at different levels and solve different problems:

```
┌────────────────────────────────────────────────────────────────────────┐
│                     SCALING DIMENSIONS                                 │
│                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│  │   HORIZONTAL      │  │   VERTICAL        │  │   CLUSTER        │    │
│  │   Pod Autoscaler  │  │   Pod Autoscaler  │  │   Autoscaler     │    │
│  │   (HPA)           │  │   (VPA)           │  │   (CA)           │    │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤    │
│  │ Adds/removes      │  │ Increases/decreases│ │ Adds/removes     │    │
│  │ pod REPLICAS      │  │ pod CPU/memory     │  │ NODES from the   │    │
│  │                   │  │ requests & limits  │  │ cluster          │    │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤    │
│  │ "Hire more        │  │ "Give each worker  │  │ "Build more      │    │
│  │  workers"         │  │  a bigger desk"    │  │  office floors"  │    │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤    │
│  │ Scale trigger:    │  │ Scale trigger:     │  │ Scale trigger:   │    │
│  │ CPU/memory/custom │  │ Historical usage   │  │ Unschedulable    │    │
│  │ metric thresholds │  │ patterns           │  │ pods (no room)   │    │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘
```

**Our platform uses HPA** (the most common). VPA and CA are explained in Sections 10-11 for completeness.

---

## 2. The Metrics Pipeline: From Container to HPA

The HPA doesn't magically know how much CPU a pod uses. There's a multi-layer metrics pipeline that transforms raw Linux kernel counters into the percentage values the HPA consumes.

### The Complete Pipeline

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌─────┐
│ Linux   │───>│ cAdvisor │───>│ kubelet  │───>│ metrics-     │───>│ HPA │
│ cgroups │    │          │    │          │    │ server       │    │     │
└─────────┘    └──────────┘    └──────────┘    └──────────────┘    └─────┘
 CPU cycles     Container       Per-node        Cluster-wide       Scaling
 per cgroup     stats           aggregation     API endpoint       decisions
```

### Layer 1: Linux cgroups (Kernel)

Every container runs inside a **cgroup** (control group). The Linux kernel tracks:
- `cpuacct.usage` -- Total CPU nanoseconds consumed by this cgroup
- `memory.usage_in_bytes` -- Current resident memory

These are raw counters in `/sys/fs/cgroup/` inside the node.

### Layer 2: cAdvisor (Per-Container)

**cAdvisor** (Container Advisor) runs embedded inside every kubelet. It:
- Reads cgroup counters every 1 second
- Converts raw nanoseconds to CPU core-seconds (divides by 10^9)
- Computes delta between samples to get current CPU rate
- Exposes this as a Prometheus-compatible endpoint at `:10250/metrics/cadvisor`

**Example**: A container used 500,000,000 nanoseconds of CPU in the last second.
That's 0.5 CPU cores, or `500m` in Kubernetes notation.

### Layer 3: kubelet (Per-Node)

The **kubelet** on each node:
- Collects cAdvisor data for all pods on that node
- Exposes a **Summary API** at `/apis/metrics.k8s.io/v1beta1/` on the node
- Reports: `pod_name → {cpu_usage_nanoseconds, memory_bytes, timestamp}`

### Layer 4: metrics-server (Cluster-Wide)

**metrics-server** is a deployment that:
- Scrapes every kubelet's Summary API every **15 seconds** (configurable via `--metric-resolution`)
- Aggregates across all nodes into a single cluster-wide view
- Serves the **Metrics API** at `/apis/metrics.k8s.io/v1beta1/`
- This is what powers `kubectl top pods` and `kubectl top nodes`

```bash
# What the Metrics API returns (this is what HPA reads):
$ kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/agent-platform/pods
{
  "items": [
    {
      "metadata": {"name": "gateway-5c766db9f7-p8m6l", "namespace": "agent-platform"},
      "containers": [{
        "name": "gateway",
        "usage": {
          "cpu": "83m",      # 83 millicores = 83% of 100m request
          "memory": "48Mi"
        }
      }],
      "timestamp": "2026-04-06T17:04:50Z",
      "window": "15s"
    }
  ]
}
```

### Layer 5: HPA Controller

The **HPA controller** is part of `kube-controller-manager`. Every **15 seconds** (default `--horizontal-pod-autoscaler-sync-period`), it:
1. Reads the HPA spec (target metric, min/max replicas)
2. Queries the Metrics API for current pod metric values
3. Runs the scaling algorithm (Section 4)
4. Patches the Deployment's `spec.replicas` if needed

### Critical Latencies

```
Event                          Time
─────────────────────────────  ─────
Container CPU actually spikes   t=0s
cAdvisor sees it (1s sample)    t=1s
kubelet reports to metrics-server   t=1-15s (depends on scrape cycle)
metrics-server aggregates       t=15-30s
HPA controller reads metrics    t=15-45s (depends on sync period)
HPA patches Deployment          t=15-45s
Scheduler places new pod        t=+1-5s
Container image pull            t=+0-60s (if not cached)
Pod passes readiness probe      t=+3-10s
─────────────────────────────  ─────
Total: pod receiving traffic    t=~30-120s from CPU spike
```

This is why our HPA has `stabilizationWindowSeconds: 10` for scale-up -- the metrics pipeline already adds 15-45s of inherent delay, so the HPA reaction is the fast part.

---

## 3. HPA Internals: The Control Loop

The HPA implements a **proportional control loop** -- a concept from control theory used in everything from thermostats to cruise control.

### The Thermostat Analogy

Your home thermostat:
- **Setpoint**: 72F (what you want)
- **Measured value**: current room temperature
- **Error signal**: measured - setpoint
- **Control action**: turn heater on/off

The HPA:
- **Setpoint**: 50% CPU utilization (what you configure)
- **Measured value**: current average CPU across all pods
- **Error signal**: current% / target% (the ratio)
- **Control action**: add or remove pod replicas

### The Control Loop (Pseudocode)

```python
# This runs every 15 seconds inside kube-controller-manager
def hpa_control_loop(hpa_spec):
    # 1. Get current metrics for all pods in the deployment
    pods = get_pods_for_deployment(hpa_spec.target)
    ready_pods = [p for p in pods if p.is_ready()]

    # 2. Get CPU usage for each ready pod
    metrics = metrics_server.get_pod_metrics(ready_pods)

    # 3. Calculate average utilization
    total_usage = sum(m.cpu_usage for m in metrics)
    total_request = sum(pod.resources.requests.cpu for pod in ready_pods)
    current_utilization = (total_usage / total_request) * 100

    # 4. Calculate desired replicas
    current_replicas = len(ready_pods)
    ratio = current_utilization / hpa_spec.target_utilization
    desired_replicas = ceil(current_replicas * ratio)

    # 5. Clamp to min/max
    desired_replicas = max(hpa_spec.min_replicas, desired_replicas)
    desired_replicas = min(hpa_spec.max_replicas, desired_replicas)

    # 6. Apply stabilization (anti-flap)
    desired_replicas = apply_stabilization(desired_replicas, hpa_spec.behavior)

    # 7. Apply scaling policies (rate limiting)
    desired_replicas = apply_policies(desired_replicas, hpa_spec.behavior)

    # 8. Scale if different from current
    if desired_replicas != current_replicas:
        scale_deployment(hpa_spec.target, desired_replicas)
```

### Key Implementation Details

1. **Only ready pods count**: Pods that are starting up or failing health checks are excluded from the calculation. This prevents the HPA from seeing artificially low averages and not scaling enough.

2. **Missing metrics**: If metrics are missing for some pods (e.g., pod just started), those pods are assumed to be consuming 0% for scale-down and 100% for scale-up. This is a safety measure -- when in doubt, scale up.

3. **Tolerance band (10%)**: The HPA has a built-in tolerance of `0.1` (configurable via `--horizontal-pod-autoscaler-tolerance`). If the ratio is between 0.9 and 1.1, no scaling action is taken. This prevents churn from minor fluctuations.

   ```
   ratio = currentUtilization / targetUtilization

   if 0.9 <= ratio <= 1.1:
       # Within tolerance, do nothing
       pass
   elif ratio > 1.1:
       # Scale up
       desired = ceil(current * ratio)
   else:
       # Scale down (ratio < 0.9)
       desired = ceil(current * ratio)
   ```

---

## 4. The Scaling Algorithm (with Math)

### The Core Formula

```
desiredReplicas = ceil[ currentReplicas × ( currentMetricValue / desiredMetricValue ) ]
```

### Worked Example: Scale Up

**Scenario**: 1 gateway pod running, CPU at 83%, target is 50%

```
desiredReplicas = ceil(1 × (83 / 50))
                = ceil(1 × 1.66)
                = ceil(1.66)
                = 2
```

Result: HPA scales to 2 pods. Load is now distributed:

```
Before:  [Pod A: 83% CPU]                    → avg 83%
After:   [Pod A: ~42% CPU] [Pod B: ~42% CPU] → avg ~42%
```

### Worked Example: Larger Scale Up

**Scenario**: 2 gateway pods, each at 90% CPU, target is 50%

```
currentMetricValue = average of all pods = (90 + 90) / 2 = 90%

desiredReplicas = ceil(2 × (90 / 50))
                = ceil(2 × 1.8)
                = ceil(3.6)
                = 4
```

Result: HPA scales to 4 pods. But our max is 5, so 4 is within bounds.

### Worked Example: Scale Down

**Scenario**: 3 gateway pods, each at 10% CPU, target is 50%

```
desiredReplicas = ceil(3 × (10 / 50))
                = ceil(3 × 0.2)
                = ceil(0.6)
                = 1
```

Result: HPA scales down to 1 pod (but respects the stabilization window).

### Multi-Metric Scaling

When multiple metrics are configured (e.g., CPU AND memory), the HPA:
1. Calculates `desiredReplicas` for each metric independently
2. Takes the **maximum** across all metrics

```
desiredReplicas = max(
    ceil(current × (cpu_usage / cpu_target)),
    ceil(current × (memory_usage / memory_target)),
    ceil(current × (custom_metric / custom_target))
)
```

This ensures no metric is underserved.

---

## 5. Stabilization and Flap Prevention

### The Problem: Flapping

Without stabilization, a spike-then-drop pattern causes:
```
t=0s:  CPU=80% → HPA scales 1→3
t=15s: CPU=20% (load distributed) → HPA scales 3→1
t=30s: CPU=80% (overloaded again) → HPA scales 1→3
t=45s: CPU=20% → HPA scales 3→1
... (infinite loop)
```

### The Solution: Stabilization Windows

The HPA maintains a **sliding window** of recent scaling recommendations:

```python
# Simplified stabilization logic
class StabilizationWindow:
    def __init__(self, window_seconds):
        self.window = window_seconds
        self.recommendations = []  # (timestamp, desired_replicas)

    def add(self, timestamp, desired_replicas):
        self.recommendations.append((timestamp, desired_replicas))
        # Prune old entries
        cutoff = timestamp - self.window
        self.recommendations = [
            (t, r) for t, r in self.recommendations if t >= cutoff
        ]

    def get_stabilized_replicas(self, direction):
        if direction == "scale_up":
            # For scale-up: take the MAXIMUM over the window
            # This ensures we scale up to the highest needed level
            return max(r for _, r in self.recommendations)
        else:
            # For scale-down: take the MAXIMUM over the window
            # This ensures we don't scale down too aggressively
            return max(r for _, r in self.recommendations)
```

**For scale-up** (`stabilizationWindowSeconds: 10`):
- The HPA looks at all recommendations in the last 10 seconds
- It picks the highest recommendation (most aggressive scale-up)
- Short window = fast reaction to spikes

**For scale-down** (`stabilizationWindowSeconds: 30`):
- The HPA looks at all recommendations in the last 30 seconds
- It picks the highest recommendation (most conservative scale-down)
- Longer window = cautious about removing capacity

### Scaling Policies (Rate Limiting)

On top of stabilization, policies limit how fast scaling can happen:

```yaml
behavior:
  scaleUp:
    policies:
      - type: Pods
        value: 2           # Add at most 2 pods...
        periodSeconds: 15  # ...per 15-second window
  scaleDown:
    policies:
      - type: Pods
        value: 1           # Remove at most 1 pod...
        periodSeconds: 30  # ...per 30-second window
```

**Why asymmetric?** Scale-up should be fast (users are waiting). Scale-down should be slow (removing capacity too quickly risks another spike).

---

## 6. Our Platform's HPA Configuration Decoded

Here is our gateway HPA with every field explained:

```yaml
apiVersion: autoscaling/v2              # v2 supports multiple metrics and behaviors
kind: HorizontalPodAutoscaler
metadata:
  name: gateway
  namespace: agent-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gateway                        # Controls the "gateway" Deployment

  minReplicas: 1                         # Floor: always at least 1 pod running
  maxReplicas: 5                         # Ceiling: never more than 5 pods

  metrics:
    - type: Resource                     # Built-in metric type (CPU or memory)
      resource:
        name: cpu                        # Scale based on CPU utilization
        target:
          type: Utilization              # As a percentage of resource.requests.cpu
          averageUtilization: 50         # Target: 50% average across all pods

  behavior:
    scaleUp:
      stabilizationWindowSeconds: 10     # Look back 10s, pick the max recommendation
      policies:
        - type: Pods
          value: 2                       # Add up to 2 new pods per scaling action
          periodSeconds: 15              # Can scale up every 15 seconds
    scaleDown:
      stabilizationWindowSeconds: 30     # Look back 30s, pick the max (most conservative)
      policies:
        - type: Pods
          value: 1                       # Remove only 1 pod per scaling action
          periodSeconds: 30              # Can scale down every 30 seconds
```

### Resource Requests: The Denominator

The "50% CPU utilization" is calculated relative to `resources.requests.cpu`:

```yaml
resources:
  requests:
    cpu: 100m      # 100 millicores = 0.1 CPU core
  limits:
    cpu: 500m      # 500 millicores = 0.5 CPU core (burst limit)
```

**50% of 100m = 50m**. When the pod uses more than 50 millicores on average, the HPA starts scaling up.

```
  requests        target (50%)           limits
     |                |                     |
     0m              50m                  500m
     |=====[normal]===|====[scale up!]======|
```

The `request` is what the scheduler **guarantees** to the pod.
The `limit` is the **maximum** the pod can burst to before being throttled.

---

## 7. What Happens During a Scale-Up (Step by Step)

Here's exactly what happens inside the cluster when load triggers a scale-up:

```
t=0.0s   USER SENDS TRAFFIC
         ├── Requests hit gateway pods via Service (kube-proxy iptables rules)
         └── Pod CPU rises from 10% to 83%

t=1.0s   cAdvisor DETECTS CPU SPIKE
         ├── Reads /sys/fs/cgroup/cpuacct/usage for the container
         └── Computes: delta_cpu_ns / delta_time_ns = 0.083 CPU cores = 83m

t=15.0s  metrics-server SCRAPES kubelet
         ├── HTTP GET kubelet:10250/metrics/resource
         ├── Receives: gateway pod → cpu=83m, memory=48Mi
         └── Stores in memory (metrics-server has no persistent storage)

t=15.0s  HPA CONTROLLER SYNC (runs every 15s)
         ├── GET /apis/metrics.k8s.io/v1beta1/namespaces/agent-platform/pods
         ├── Receives: gateway → 83m CPU
         ├── Calculates: utilization = 83m / 100m (request) = 83%
         ├── Computes: desired = ceil(1 × (83/50)) = 2
         ├── Checks stabilization window: no recent recommendations → 2 is ok
         ├── Checks policies: +2 pods allowed per 15s → ok
         ├── Checks bounds: 2 ≤ maxReplicas(5) → ok
         └── PATCHES Deployment: spec.replicas = 2

t=15.1s  DEPLOYMENT CONTROLLER REACTS
         ├── Sees desired=2, current=1, needs 1 more ReplicaSet pod
         └── Creates new Pod spec

t=15.2s  SCHEDULER ASSIGNS POD TO NODE
         ├── Filters nodes: does any node have ≥100m CPU and ≥64Mi memory free?
         ├── Scores nodes: prefer least-loaded node
         └── Binds pod to selected node

t=15.3s  kubelet ON THE NODE RECEIVES POD
         ├── Checks if container image exists locally
         ├── If not: pulls image (can take 0-60s depending on size and cache)
         └── Starts container with specified command, env vars, volume mounts

t=16.0s  CONTAINER STARTS
         ├── Python process begins (our proxy server starts listening on :8000)
         └── Pod status → Running

t=19.0s  READINESS PROBE PASSES
         ├── kubelet sends HTTP GET :8000/healthz
         ├── Pod returns 200 OK
         ├── Pod status → Ready
         └── kube-proxy adds this pod's IP to the Service's iptables rules

t=19.0s  NEW POD RECEIVES TRAFFIC
         ├── Service load-balances between 2 pods (round-robin via iptables)
         ├── CPU load distributes: each pod now ~42%
         └── HPA target met (42% < 50%)
```

---

## 8. What Happens During a Scale-Down (Step by Step)

```
t=0.0s   LOAD DECREASES
         ├── Each of 2 pods drops to 10% CPU
         └── Total average: 10%

t=15.0s  HPA CONTROLLER SYNC
         ├── Reads: avg CPU = 10%
         ├── Computes: desired = ceil(2 × (10/50)) = ceil(0.4) = 1
         ├── Checks stabilization window (30s): recent recommendations still show 2
         └── NO ACTION (stabilization holds at 2 replicas)

t=30.0s  HPA CONTROLLER SYNC
         ├── Reads: avg CPU = 10%
         ├── Computes: desired = 1
         ├── Stabilization window: all recommendations in last 30s say 1
         ├── Checks policy: can remove 1 pod per 30s → ok
         └── PATCHES Deployment: spec.replicas = 1

t=30.1s  DEPLOYMENT CONTROLLER REACTS
         ├── Sees desired=1, current=2, needs to terminate 1 pod
         └── Selects pod to terminate (newest pod, or random)

t=30.2s  POD TERMINATION BEGINS
         ├── kube-proxy removes pod IP from Service iptables (no new traffic)
         ├── kubelet sends SIGTERM to the container
         ├── Container gets terminationGracePeriodSeconds (default: 30s) to shut down
         ├── If container doesn't exit, kubelet sends SIGKILL after grace period
         └── Pod status → Terminating

t=30.5s  CONTAINER EXITS
         ├── Pod is cleaned up
         ├── Resources (CPU, memory) returned to the node
         └── Pod disappears from kubectl get pods
```

---

## 9. Custom Metrics and Beyond CPU

CPU is the simplest metric, but the HPA supports three metric types:

### Type 1: Resource (built-in)

```yaml
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
```

Available: `cpu` and `memory` only.

### Type 2: Pods (custom, per-pod)

For application-specific metrics exposed via Prometheus:

```yaml
metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second    # Custom metric from your app
      target:
        type: AverageValue
        averageValue: 100                  # Scale when > 100 req/s per pod
```

Requires: **Prometheus Adapter** or **KEDA** (see Section 12) to bridge Prometheus → Kubernetes Custom Metrics API.

### Type 3: Object (cluster-wide)

For metrics on a single Kubernetes object (e.g., an Ingress):

```yaml
metrics:
  - type: Object
    object:
      describedObject:
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        name: agent-platform-ingress
      metric:
        name: requests_per_second
      target:
        type: Value
        value: 1000                        # Scale when Ingress gets > 1k req/s
```

### For Our LLM Platform

Better scaling signals than CPU:
- **Ollama queue depth** (requests waiting for inference)
- **LLM inference latency p95** (scale when latency exceeds SLO)
- **GPU utilization** (via DCGM exporter + Prometheus)

---

## 10. VPA: Vertical Pod Autoscaler

Instead of adding more pods, VPA makes each pod **bigger**.

```
HPA: 1 small pod → 3 small pods (horizontal)
VPA: 1 small pod → 1 large pod (vertical)
```

### How VPA Works

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: gateway-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gateway
  updatePolicy:
    updateMode: "Auto"      # Can be: Off (recommend only), Auto (apply changes)
  resourcePolicy:
    containerPolicies:
      - containerName: gateway
        minAllowed:
          cpu: 50m
          memory: 64Mi
        maxAllowed:
          cpu: 2
          memory: 2Gi
```

VPA watches usage patterns over hours/days and adjusts `requests` and `limits`:
- Pod consistently uses 400m CPU but requests 100m? VPA raises request to 400m.
- Pod never exceeds 128Mi memory but limits at 1Gi? VPA lowers limit to 256Mi.

### VPA vs HPA

| Aspect | HPA | VPA |
|--------|-----|-----|
| Scales what | Number of pods | Size of each pod |
| Reaction speed | 15-60 seconds | Hours (needs usage history) |
| Disruption | None (adds pods) | Must restart pods to resize |
| Best for | Stateless services | Databases, batch jobs, ML training |
| Works with | Stateless microservices | Single-instance workloads |

**Warning**: Do NOT use HPA and VPA on the same metric (e.g., both targeting CPU). They will fight each other. Use HPA for CPU scaling and VPA for memory right-sizing.

---

## 11. Cluster Autoscaler: Scaling the Nodes

What if the HPA wants 5 pods but the node only has room for 3?

### The Unschedulable Pod Trigger

```
1. HPA: "I need 5 replicas"
2. Scheduler: "Node has room for only 3 pods"
3. 2 pods stuck in Pending state with reason: Insufficient CPU
4. Cluster Autoscaler detects Pending pods
5. Cluster Autoscaler adds a new node to the cluster
6. Scheduler places the 2 pending pods on the new node
```

### How It Works (GKE/EKS/AKS)

```yaml
# GKE Autopilot does this automatically
# For Standard GKE, configure node pools:
apiVersion: container.cnrm.cloud.google.com/v1beta1
kind: ContainerNodePool
metadata:
  name: default-pool
spec:
  autoscaling:
    enabled: true
    minNodeCount: 1     # Never fewer than 1 node
    maxNodeCount: 10    # Never more than 10 nodes
```

**On minikube**: The Cluster Autoscaler doesn't apply (single-node cluster). Our HPA max of 5 replicas is sized to fit within minikube's 4 CPUs.

### Scale-Down Logic

The Cluster Autoscaler removes a node when:
1. All pods on the node can be scheduled elsewhere
2. The node has been underutilized (<50% CPU) for 10 minutes
3. No pods have `PodDisruptionBudget` that would be violated

---

## 12. KEDA: Event-Driven Autoscaling

**KEDA** (Kubernetes Event-Driven Autoscaling) extends HPA with 50+ external event sources:

```
Prometheus query → KEDA → HPA → scale pods
Kafka lag        → KEDA → HPA → scale consumers
Redis queue      → KEDA → HPA → scale workers
```

### Example: Scale on Ollama Queue Depth

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: agent-engine-scaler
spec:
  scaleTargetRef:
    name: agent-engine
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus:9090
        metricName: ollama_requests_queue_depth
        query: ollama_requests_total{status="pending"}
        threshold: "5"       # Scale when > 5 requests queued
```

This is more responsive than CPU-based scaling for LLM workloads because queue depth spikes before CPU does.

---

## 13. Scaling for LLM Inference Workloads

LLM inference has unique scaling challenges:

### Why CPU-Based HPA Is Insufficient for LLM

1. **GPU is the bottleneck**, not CPU. GPU utilization isn't in the default Metrics API.
2. **Requests queue internally** in Ollama/vLLM. Pod CPU looks normal while requests wait.
3. **Latency spikes before CPU** -- by the time CPU rises, users have already timed out.

### Production LLM Scaling Architecture

```
                         ┌─────────────┐
                         │  Prometheus  │
                         │  + DCGM     │ ← GPU metrics from NVIDIA DCGM exporter
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │    KEDA     │ ← Reads: GPU util, queue depth, p95 latency
                         └──────┬──────┘
                                │
                    ┌───────────▼───────────┐
                    │   HPA (KEDA-managed)  │
                    │   Metrics:            │
                    │   - GPU utilization   │
                    │   - Inference queue   │
                    │   - p95 latency       │
                    └───────────┬───────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │   vLLM Deployment (KubeRay)         │
              │   Replicas: 1-5                     │
              │   Each pod: 1 GPU                   │
              │   Continuous batching enabled        │
              └─────────────────────────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │   Cluster Autoscaler                │
              │   Adds GPU nodes when pods Pending  │
              │   Node pool: g2-standard-8 (L4 GPU) │
              │   Min: 1, Max: 5 nodes              │
              └─────────────────────────────────────┘
```

### vLLM vs Ollama for Production Scaling

| Feature | Ollama | vLLM |
|---------|--------|------|
| Request handling | Serial (one at a time) | **Continuous batching** (many at once) |
| GPU utilization under load | 67-74% | 90-95% |
| Throughput (qwen2.5:1.5b, T4) | ~1 req/s | ~5-10 req/s |
| Max concurrent users (single GPU) | 10-15 | 30-50 |
| Scaling approach | Add more GPU pods | Batch first, then add pods |
| Production-ready | Dev/prototyping | Yes |

**Our test showed Ollama saturates at 15 concurrent users** with 100% success rate. Switching to vLLM would 3-5x that capacity on the same hardware.

---

## 14. Production Checklist

Before deploying HPA to production:

### Resource Requests and Limits

- [ ] Every container has `resources.requests` set (HPA needs this as the denominator)
- [ ] CPU requests reflect actual baseline usage (check with `kubectl top pods` over 24 hours)
- [ ] Limits are 2-5x requests (allow burst headroom)

### HPA Configuration

- [ ] `minReplicas >= 2` for high-availability (survive a single pod failure)
- [ ] `maxReplicas` is bounded by your node capacity and budget
- [ ] Scale-up stabilization is short (10-30s) for fast reaction
- [ ] Scale-down stabilization is long (60-300s) for flap prevention
- [ ] Target utilization is 50-70% (leaves headroom for traffic spikes)

### Probes and Disruption

- [ ] Readiness probe is configured (new pods only get traffic when truly ready)
- [ ] Liveness probe is configured (dead pods get restarted)
- [ ] `PodDisruptionBudget` ensures at least N pods survive during scale-down/upgrades

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: gateway-pdb
spec:
  minAvailable: 1          # At least 1 pod must always be running
  selector:
    matchLabels:
      app: gateway
```

### Monitoring

- [ ] Alert on HPA at maxReplicas (means it can't keep up -- need bigger max or node scaling)
- [ ] Alert on pods in Pending state > 60s (means cluster needs more nodes)
- [ ] Dashboard shows: current replicas, desired replicas, target metric, current metric

---

## 15. Observed Results from Our Platform

### Test Environment

- **VM**: GCP n1-standard-8 + NVIDIA T4 (16 GB VRAM)
- **K8s**: minikube (profile: aiadopt, 4 CPU, 8 GB RAM)
- **Pods**: gateway + agent-engine proxy pods → Docker Compose services
- **HPA**: 1-5 replicas, target 50% CPU

### HPA Scaling Timeline (Observed)

```
Phase       Time    Gateway  Agent-Engine  Gateway CPU  Action
──────────  ──────  ───────  ───────────  ──────────── ──────────────────────
Baseline    t=0s     1 pod    1 pod        10%          Normal operation
Load start  t=15s    1 pod    1 pod        83%          CPU spike detected
Scale-up    t=45s    2 pods   2 pods       80%          HPA adds 1 pod each
Stabilized  t=60s    2 pods   2 pods       ~42%         Load distributed
Load ends   t=90s    2 pods   2 pods       3%           CPU drops
Scale-down  t=120s   1 pod    1 pod        3%           HPA removes 1 pod each
Baseline    t=150s   1 pod    1 pod        3%           Back to normal
```

### Key Timings

| Event | Duration | Why |
|-------|----------|-----|
| CPU spike → HPA detects | ~15-30s | Metrics pipeline latency (cAdvisor → metrics-server → HPA) |
| HPA detect → new pod running | ~5-10s | Scheduler + container start (image cached) |
| New pod → receiving traffic | ~3-5s | Readiness probe period (5s) |
| **Total scale-up reaction** | **~30-45s** | From load spike to capacity added |
| CPU drop → scale-down | ~30-45s | Stabilization window (30s) + HPA sync (15s) |
| **Total scale-down reaction** | **~45-60s** | Deliberately slow to prevent flapping |

### Dashboard View

The scaling dashboard at `/scaling` shows this in real-time:

```
Before Load:
  ┌─ Gateway HPA ─────┐  ┌─ Agent Engine HPA ──┐
  │ ▓░░░░ 10% / 50%   │  │ ▓░░░░ 3% / 50%     │
  │ Replicas: 1/5      │  │ Replicas: 1/5       │
  └────────────────────┘  └─────────────────────┘

During Load:
  ┌─ Gateway HPA ─────┐  ┌─ Agent Engine HPA ──┐
  │ ▓▓▓▓░ 83% / 50%   │  │ ▓▓▓▓░ 83% / 50%    │
  │ Replicas: 2/5 ↑   │  │ Replicas: 2/5 ↑     │
  └────────────────────┘  └─────────────────────┘

Pods Table:
  gateway-xxx-p8m6l     Running  Ready  0 restarts
  gateway-xxx-26b62     Running  Ready  0 restarts  ← NEW
  agent-engine-xxx-glz  Running  Ready  0 restarts
  agent-engine-xxx-6ww  Running  Ready  0 restarts  ← NEW
  frontend-xxx-x66tb    Running  Ready  0 restarts
```
