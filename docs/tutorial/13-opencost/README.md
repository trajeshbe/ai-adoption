# Tutorial 13: OpenCost — Real-time Cost Per Inference

> **Objective:** Track and optimize infrastructure costs, especially GPU costs per LLM inference.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [Architecture](#3-architecture)
4. [Installation & Setup](#4-installation--setup)
5. [Exercises](#5-exercises)
6. [How It's Used in Our Project](#6-how-its-used-in-our-project)
7. [Cost Optimization](#7-cost-optimization)
8. [Further Reading](#8-further-reading)

---

## 1. Introduction

### What is FinOps?

**FinOps** is the practice of bringing financial accountability to cloud spending. For AI platforms, the biggest costs are GPU instances for model inference.

### What is OpenCost?

**OpenCost** is an open-source CNCF project that provides real-time cost monitoring for Kubernetes. It tracks cost per namespace, deployment, pod, and container.

### Why Track Cost Per Inference?

```
Without cost tracking:
  "We spent $50K on GPUs last month. Was it worth it?"

With OpenCost:
  "Model A: $0.002/query, Model B: $0.015/query
   Route simple queries to A, complex ones to B → save 60%"
```

---

## 2. Core Concepts

| Concept | Description |
|---------|-------------|
| **Cost allocation** | Assign costs to teams/services/models |
| **GPU cost** | Most expensive resource in AI platforms |
| **Idle cost** | Cost of unused but allocated resources |
| **Shared cost** | Infrastructure costs split across services |
| **Cost per request** | Total cost ÷ number of requests |
| **Unit economics** | Revenue per request vs cost per request |

### Cost Model

```
Pod Cost = (CPU cost) + (Memory cost) + (GPU cost) + (Storage cost)

GPU cost = GPU hours × price per GPU hour
  A100-80GB: ~$3.00/hour
  A10G:      ~$1.00/hour
  T4:        ~$0.35/hour

Cost per inference = Pod cost / Number of inferences
```

---

## 3. Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  OpenCost    │◄───│  Prometheus  │◄───│  K8s Metrics │
│  Server      │    │              │    │  (kubelet)   │
│              │    │              │    └──────────────┘
│  ┌────────┐  │    │              │    ┌──────────────┐
│  │Pricing │  │    │              │◄───│  GPU Metrics │
│  │  API   │  │    │              │    │  (nvidia-smi)│
│  └────────┘  │    └──────────────┘    └──────────────┘
└──────┬───────┘
       │ /api/
       ▼
┌──────────────┐
│   Grafana    │
│  Dashboards  │
└──────────────┘
```

---

## 4. Installation & Setup

```bash
# Install OpenCost with Helm
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update

helm install opencost opencost/opencost \
  --namespace opencost \
  --create-namespace \
  --set opencost.prometheus.internal.enabled=true \
  --set opencost.ui.enabled=true

# Port-forward the UI
kubectl port-forward -n opencost svc/opencost 9090:9090
# Open http://localhost:9090
```

---

## 5. Exercises

### Exercise 1: Install and Query OpenCost API

```bash
# After installation, query the API
kubectl port-forward -n opencost svc/opencost 9003:9003

# Get cost allocation by namespace (last 24h)
curl "http://localhost:9003/allocation/compute?window=24h&aggregate=namespace" | python -m json.tool

# Get cost by deployment
curl "http://localhost:9003/allocation/compute?window=24h&aggregate=deployment" | python -m json.tool

# Get cost by pod
curl "http://localhost:9003/allocation/compute?window=1h&aggregate=pod&namespace=ai-platform" | python -m json.tool
```

---

### Exercise 2: Python Client

```python
# opencost_client.py
import httpx
from datetime import datetime

class OpenCostClient:
    def __init__(self, base_url: str = "http://localhost:9003"):
        self.base_url = base_url

    def get_allocation(self, window: str = "24h", aggregate: str = "namespace") -> dict:
        response = httpx.get(
            f"{self.base_url}/allocation/compute",
            params={"window": window, "aggregate": aggregate},
        )
        return response.json()

    def get_namespace_costs(self, window: str = "24h") -> list[dict]:
        data = self.get_allocation(window, "namespace")
        costs = []
        for item in data.get("data", [{}]):
            for name, info in item.items():
                costs.append({
                    "namespace": name,
                    "cpu_cost": info.get("cpuCost", 0),
                    "memory_cost": info.get("ramCost", 0),
                    "gpu_cost": info.get("gpuCost", 0),
                    "total_cost": info.get("totalCost", 0),
                })
        return sorted(costs, key=lambda x: x["total_cost"], reverse=True)

    def get_deployment_costs(self, namespace: str, window: str = "24h") -> list[dict]:
        data = self.get_allocation(window, "deployment")
        costs = []
        for item in data.get("data", [{}]):
            for name, info in item.items():
                if info.get("properties", {}).get("namespace") == namespace:
                    costs.append({
                        "deployment": name,
                        "total_cost": info.get("totalCost", 0),
                        "gpu_cost": info.get("gpuCost", 0),
                        "cpu_hours": info.get("cpuCoreHours", 0),
                    })
        return costs

# Usage
client = OpenCostClient()

print("Namespace costs (last 24h):")
for ns in client.get_namespace_costs():
    print(f"  {ns['namespace']}: ${ns['total_cost']:.2f} "
          f"(GPU: ${ns['gpu_cost']:.2f})")

print("\nAI Platform deployment costs:")
for dep in client.get_deployment_costs("ai-platform"):
    print(f"  {dep['deployment']}: ${dep['total_cost']:.2f}")
```

---

### Exercise 3: Cost Per Inference Calculator

```python
# cost_per_inference.py
import httpx
from dataclasses import dataclass

@dataclass
class InferenceCost:
    model: str
    cost_per_query: float
    gpu_cost_per_hour: float
    queries_per_hour: int
    avg_latency_ms: float

def calculate_cost_per_inference(
    model_deployment: str,
    gpu_cost_per_hour: float = 3.0,  # A100 price
    window: str = "1h",
) -> InferenceCost:
    """Calculate cost per inference for a model deployment."""

    # Get deployment cost from OpenCost
    opencost = httpx.get(
        "http://localhost:9003/allocation/compute",
        params={"window": window, "aggregate": "deployment"},
    ).json()

    # Get request count from Prometheus
    prom = httpx.get(
        "http://localhost:9090/api/v1/query",
        params={"query": f'sum(increase(vllm_num_requests_total{{deployment="{model_deployment}"}}[1h]))'},
    ).json()

    total_cost = 0
    for item in opencost.get("data", [{}]):
        if model_deployment in item:
            total_cost = item[model_deployment].get("totalCost", 0)

    total_requests = 0
    for result in prom.get("data", {}).get("result", []):
        total_requests += float(result.get("value", [0, 0])[1])

    cost_per_query = total_cost / max(total_requests, 1)

    # Get average latency
    latency_query = httpx.get(
        "http://localhost:9090/api/v1/query",
        params={"query": f'histogram_quantile(0.5, rate(vllm_time_to_first_token_seconds_bucket[1h]))'},
    ).json()

    avg_latency = 0
    for result in latency_query.get("data", {}).get("result", []):
        avg_latency = float(result.get("value", [0, 0])[1]) * 1000

    return InferenceCost(
        model=model_deployment,
        cost_per_query=cost_per_query,
        gpu_cost_per_hour=gpu_cost_per_hour,
        queries_per_hour=int(total_requests),
        avg_latency_ms=avg_latency,
    )

# Usage
cost = calculate_cost_per_inference("vllm-llama-3-70b")
print(f"Model: {cost.model}")
print(f"Cost per query: ${cost.cost_per_query:.4f}")
print(f"Queries/hour: {cost.queries_per_hour}")
print(f"GPU cost/hour: ${cost.gpu_cost_per_hour:.2f}")
print(f"Avg latency: {cost.avg_latency_ms:.0f}ms")
```

---

### Exercise 4: Grafana Cost Dashboard

```promql
# Total cost by namespace (last 24h)
# Use OpenCost's Prometheus metrics:

# CPU cost rate
sum by (namespace) (
  container_cpu_allocation * on(node) group_left() node_cpu_hourly_cost
)

# GPU cost rate
sum by (namespace) (
  container_gpu_allocation * on(node) group_left() node_gpu_hourly_cost
)

# Total cost per hour by deployment
sum by (deployment) (
  container_cpu_allocation * on(node) group_left() node_cpu_hourly_cost
  + container_memory_allocation_bytes / 1e9 * on(node) group_left() node_ram_hourly_cost
  + container_gpu_allocation * on(node) group_left() node_gpu_hourly_cost
)

# Cost per inference
(
  sum by (deployment) (container_gpu_allocation * on(node) group_left() node_gpu_hourly_cost)
  / sum by (deployment) (rate(vllm_num_requests_total[1h]) * 3600)
)
```

---

### Exercise 5: Cost Alerts

```yaml
# cost-alerts.yaml
groups:
  - name: cost-alerts
    rules:
      - alert: HighGPUCost
        expr: |
          sum(container_gpu_allocation * on(node) group_left() node_gpu_hourly_cost) > 50
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "GPU cost exceeding $50/hour"

      - alert: CostPerQueryHigh
        expr: |
          (sum(container_gpu_allocation * on(node) group_left() node_gpu_hourly_cost{namespace="ai-platform"}))
          /
          (sum(rate(vllm_num_requests_total[1h])) * 3600)
          > 0.05
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Cost per query exceeding $0.05"

      - alert: IdleGPU
        expr: |
          container_gpu_allocation > 0
          and
          rate(vllm_num_requests_total[30m]) == 0
        for: 30m
        labels:
          severity: info
        annotations:
          summary: "GPU allocated but no requests for 30 minutes"
```

---

### Exercise 6: Budget Tracking

```python
# budget_tracker.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Budget:
    monthly_limit: float
    alert_threshold: float  # percentage (0.8 = 80%)

BUDGETS = {
    "ai-platform": Budget(monthly_limit=5000.0, alert_threshold=0.8),
    "development": Budget(monthly_limit=1000.0, alert_threshold=0.9),
}

def check_budgets(current_costs: dict[str, float]):
    """Check current spending against budgets."""
    day_of_month = datetime.utcnow().day
    days_in_month = 30
    projected_monthly = {
        ns: cost * (days_in_month / day_of_month)
        for ns, cost in current_costs.items()
    }

    alerts = []
    for ns, budget in BUDGETS.items():
        projected = projected_monthly.get(ns, 0)
        if projected > budget.monthly_limit * budget.alert_threshold:
            alerts.append({
                "namespace": ns,
                "current_spend": current_costs.get(ns, 0),
                "projected_monthly": projected,
                "budget": budget.monthly_limit,
                "percentage": projected / budget.monthly_limit * 100,
            })

    return alerts

# Usage
current = {"ai-platform": 3500.0, "development": 200.0}
alerts = check_budgets(current)
for alert in alerts:
    print(f"ALERT: {alert['namespace']} projected at ${alert['projected_monthly']:.0f} "
          f"({alert['percentage']:.0f}% of ${alert['budget']:.0f} budget)")
```

---

### Exercise 7: Multi-Tenant Cost Allocation

```python
# multi_tenant.py
def allocate_shared_costs(
    namespace_costs: dict[str, float],
    shared_infra_cost: float,
    allocation_method: str = "proportional",
) -> dict[str, dict]:
    """Allocate shared infrastructure costs to tenants."""
    total_direct = sum(namespace_costs.values())

    results = {}
    for ns, direct_cost in namespace_costs.items():
        if allocation_method == "proportional":
            share = (direct_cost / total_direct) * shared_infra_cost
        elif allocation_method == "equal":
            share = shared_infra_cost / len(namespace_costs)
        else:
            share = 0

        results[ns] = {
            "direct_cost": direct_cost,
            "shared_cost": share,
            "total_cost": direct_cost + share,
        }

    return results

# Usage
costs = {
    "team-ml": 2000.0,
    "team-backend": 500.0,
    "team-frontend": 200.0,
}
shared = 1000.0  # Monitoring, mesh, ingress

allocated = allocate_shared_costs(costs, shared, "proportional")
for team, breakdown in allocated.items():
    print(f"{team}: direct=${breakdown['direct_cost']:.0f} + "
          f"shared=${breakdown['shared_cost']:.0f} = ${breakdown['total_cost']:.0f}")
```

---

## 6. How It's Used in Our Project

- **Real-time $/inference** — Track cost per query across all models
- **Model selection** — Route to cheaper models for simple queries
- **Budget alerts** — Notify teams approaching spending limits
- **GPU right-sizing** — Identify over-provisioned or idle GPU pods
- **Quantization ROI** — Measure cost savings from model quantization

---

## 7. Cost Optimization

| Strategy | Savings | Effort |
|----------|---------|--------|
| **Semantic caching** (Redis) | 30-60% | Medium |
| **Model quantization** (AWQ) | 50-75% GPU cost | Low |
| **Smart routing** (small/large) | 40-60% | Medium |
| **Autoscaling to zero** | Variable | Medium |
| **Spot/preemptible instances** | 60-90% | High |
| **Batch processing** (off-peak) | 20-40% | Low |

---

## 8. Further Reading

- [OpenCost Documentation](https://www.opencost.io/docs/)
- [OpenCost GitHub](https://github.com/opencost/opencost)
- [FinOps Foundation](https://www.finops.org/)
- [Kubernetes Cost Optimization](https://www.kubecost.com/kubernetes-cost-optimization)
