# Runbook: Incident Response

## Purpose

Step-by-step procedure for responding to production incidents on the AI Agent Platform.

---

## Severity Levels

| Level | Definition | Response Time | Example |
|---|---|---|---|
| SEV-1 | Platform fully unavailable | 15 min | All LLM inference down, API unresponsive |
| SEV-2 | Major feature degraded | 30 min | One bot type failing, >50% error rate |
| SEV-3 | Minor degradation | 2 hours | Elevated latency, partial cache failures |
| SEV-4 | Cosmetic / low impact | Next business day | Dashboard rendering issue |

---

## Step-by-Step Procedure

### 1. Detect and Acknowledge

- Alert fires via Grafana Alertmanager (Slack / PagerDuty).
- On-call engineer acknowledges the alert within the response time SLA.
- Create an incident channel (e.g., `#inc-YYYY-MM-DD-short-desc`).

### 2. Triage

```bash
# Check overall cluster health
kubectl get nodes
kubectl top nodes

# Check pod status across key namespaces
kubectl get pods -n default
kubectl get pods -n ai-agents
kubectl get pods -n llm-runtime

# Review recent events
kubectl get events --sort-by='.lastTimestamp' -A | tail -30
```

### 3. Assess Impact

- How many users are affected? Check Grafana dashboard: `AI Platform / Request Rate`.
- Which services are failing? Check Tempo traces for error spans.
- Is the issue spreading? Check Prometheus alert correlation.

### 4. Mitigate

Choose the fastest path to reduce user impact:

| Scenario | Mitigation |
|---|---|
| Bad deployment | `argocd app rollback ai-platform` |
| LLM runtime OOM | Scale down batch size, restart pods |
| Database overload | Enable read replicas, kill long queries |
| Cache stampede | Enable circuit breaker on cache service |
| External API down | Switch to fallback provider or cached responses |

### 5. Communicate

- Post status update every 15 minutes for SEV-1, every 30 minutes for SEV-2.
- Template: "**[SEV-X] [Service]** -- Impact: [what users see]. Status: [investigating/mitigating/resolved]. ETA: [time or unknown]."

### 6. Resolve

- Confirm metrics return to normal baselines.
- Verify no error spikes in the last 10 minutes.
- Remove any temporary mitigations (e.g., scaled-down configs).

### 7. Post-Incident Review

Within 48 hours of resolution:

1. Write a blameless post-mortem with timeline, root cause, and action items.
2. File tickets for preventive measures.
3. Update runbooks if the incident type was novel.
4. Share the post-mortem in the team sync.

---

## Key Dashboards

| Dashboard | URL | Purpose |
|---|---|---|
| Platform Overview | `http://grafana:3001/d/platform` | Request rate, error rate, latency p99 |
| LLM Runtime | `http://grafana:3001/d/llm` | Token throughput, GPU utilization |
| Cost Monitor | `http://opencost:9090` | Real-time spend by namespace |
