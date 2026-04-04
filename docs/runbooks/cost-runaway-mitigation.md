# Runbook: Cost Runaway Mitigation

## Purpose

Detect and stop unexpected cost spikes before they exceed budget thresholds.

---

## Detection

### Automated Alerts

OpenCost and Prometheus fire alerts based on these rules:

| Alert | Condition | Severity |
|---|---|---|
| `CostAnomalyDetected` | Hourly spend > 2x the 7-day rolling average | Warning |
| `BudgetThresholdExceeded` | Daily projected spend > 80% of monthly budget | Warning |
| `BudgetCritical` | Daily projected spend > 100% of monthly budget | Critical |
| `GPUCostSpike` | GPU namespace cost > 3x baseline for 30 min | Critical |

### Manual Check

```bash
# View current cost breakdown by namespace
kubectl port-forward -n opencost svc/opencost 9090:9090
open http://localhost:9090

# Query Prometheus for hourly cost rate
curl -s "http://prometheus:9090/api/v1/query?query=sum(rate(opencost_total_cost[1h]))" | jq .
```

---

## Immediate Mitigation Steps

### Step 1: Identify the Source

```bash
# Top cost consumers by namespace
kubectl top pods -A --sort-by=cpu | head -20

# Check for runaway pods (restarts, scaling loops)
kubectl get pods -A | grep -E "CrashLoop|Error|Evicted"

# Check HPA activity
kubectl get hpa -A
```

### Step 2: Stop the Bleeding

Choose the appropriate action based on the source:

#### Runaway Auto-Scaler

```bash
# Pause the HPA by setting min=max to current replicas
kubectl patch hpa <name> -n <namespace> -p '{"spec":{"minReplicas":1,"maxReplicas":1}}'
```

#### Excessive LLM Requests

```bash
# Enable rate limiting on the API gateway
kubectl set env deployment/api-gateway -n default \
  RATE_LIMIT_PER_USER=10 \
  RATE_LIMIT_WINDOW_SECONDS=60

# If critical, scale LLM runtime to minimum
kubectl scale deployment vllm-server -n llm-runtime --replicas=1
```

#### Orphaned Resources

```bash
# Find and delete completed/failed jobs
kubectl delete jobs -A --field-selector=status.successful=1
kubectl delete pods -A --field-selector=status.phase=Failed

# Check for orphaned PVCs
kubectl get pvc -A | grep -v Bound
```

#### External API Cost Spike

```bash
# Disable external API calls temporarily
kubectl set env deployment/agent-engine -n ai-agents \
  EXTERNAL_API_ENABLED=false

# Agents will return cached results or graceful errors
```

### Step 3: Set a Hard Spending Cap

Apply a ResourceQuota to prevent further resource consumption:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: emergency-quota
  namespace: llm-runtime
spec:
  hard:
    requests.cpu: "8"
    requests.memory: "32Gi"
    requests.nvidia.com/gpu: "2"
    pods: "4"
```

```bash
kubectl apply -f emergency-quota.yaml
```

---

## Root Cause Analysis

After the immediate threat is contained, investigate:

1. **Check deployment history**: `argocd app history ai-platform`
2. **Review recent config changes**: `git log --oneline -10`
3. **Inspect HPA and VPA logs** for scaling decisions
4. **Check for traffic spikes** in Grafana request-rate dashboard
5. **Review external API usage** in provider dashboards

---

## Prevention

| Measure | Implementation |
|---|---|
| Budget alerts at 50%, 80%, 100% | OpenCost alert rules in Prometheus |
| HPA max replica caps | Set `maxReplicas` conservatively on all HPAs |
| Resource quotas per namespace | Apply `ResourceQuota` to every namespace |
| Rate limiting on all public endpoints | Envoy rate limit filter via Contour |
| Monthly cost review | Calendar reminder, review OpenCost trends |
