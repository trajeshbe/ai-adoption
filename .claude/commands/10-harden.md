# Phase 10: Production Hardening -- Load, Chaos, Security, Runbooks, SLOs

## What You Will Learn
- Load testing with Locust and k6 for throughput and latency baselines
- Chaos engineering with LitmusChaos for resilience validation
- Container security scanning with Trivy
- Dynamic application security testing (DAST) with OWASP ZAP
- Runbook creation for incident response
- SLO definitions and error budget alerting
- Production readiness review checklist

## Prerequisites
- Phases 0-9 complete (full platform running with GitOps and policy enforcement)
- Understanding of SRE concepts (SLIs, SLOs, error budgets)

## Background: Why Hardening Before Production?
Building features is half the job. The other half is proving the system is production-worthy.
Load testing reveals bottlenecks before users find them. Chaos engineering verifies
resilience claims. Security scanning catches vulnerabilities before attackers do.
Runbooks ensure on-call engineers can resolve incidents without tribal knowledge.
SLOs define "good enough" so you don't over-engineer reliability.

## Step-by-Step Instructions

### Step 1: Load Testing with Locust

Create `tests/load/locustfile.py`:
```python
from locust import HttpUser, task, between

class AgentPlatformUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    @task(3)
    def send_chat_message(self):
        self.client.post("/graphql", json={
            "query": '''mutation {
                sendMessage(agentId: "weather", content: "Weather in NYC?") {
                    response costUsd latencyMs
                }
            }'''
        })

    @task(1)
    def list_agents(self):
        self.client.post("/graphql", json={
            "query": "{ agents { id name agentType } }"
        })

    @task(1)
    def list_documents(self):
        self.client.post("/graphql", json={
            "query": "{ documents { id filename chunkCount } }"
        })
```

Run:
```bash
# Ramp from 0 to 1000 users over 5 minutes, sustain for 10 minutes
locust -f tests/load/locustfile.py --headless -u 1000 -r 50 -t 15m \
  --html=reports/load-test.html
```

### Step 2: Load Testing with k6 (Alternative)

Create `tests/load/k6/chat-load.js`:
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 500 },
    { duration: '2m', target: 1000 },
    { duration: '5m', target: 1000 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};
```

### Step 3: Chaos Engineering with LitmusChaos

Create `tests/chaos/litmus/pod-kill.yaml`:
```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: agent-engine-pod-kill
spec:
  appinfo:
    appns: agent-platform
    applabel: app=agent-engine
  chaosServiceAccount: litmus-admin
  experiments:
    - name: pod-delete
      spec:
        components:
          env:
            - name: TOTAL_CHAOS_DURATION
              value: "60"
            - name: CHAOS_INTERVAL
              value: "10"
            - name: FORCE
              value: "true"
```

**What to validate:**
- Killing an agent-engine pod during inference: Does the request retry and succeed?
- Killing the gateway: Does the load balancer route to surviving replicas?
- Network delay between agent-engine and vLLM: Does the circuit breaker trip to llama.cpp?

### Step 4: Security Scanning

**Container scanning (Trivy):**
```yaml
# Already in Tekton pipeline (Phase 8), but also run manually:
trivy image agent-platform-gateway:latest --severity HIGH,CRITICAL
trivy image agent-platform-frontend:latest --severity HIGH,CRITICAL
```

**DAST (OWASP ZAP):**
Create `tests/security/zap-config.yaml` and run:
```bash
docker run -t owasp/zap2docker-stable zap-api-scan.py \
  -t http://localhost:8000/graphql -f graphql
```

### Step 5: Create Runbooks

Create runbooks in `docs/runbooks/`:

**incident-response.md:**
1. Acknowledge alert within 5 minutes
2. Check Grafana dashboard for affected service
3. Check traces in Tempo for error spans
4. Check logs in Loki for error messages
5. Identify root cause and apply fix
6. Create postmortem document

**scaling-vllm.md:**
1. Check GPU utilization: `kubectl top pods -l app=vllm`
2. If >80% utilization: increase KubeRay maxReplicas
3. If queue depth >100: scale GPU workers
4. If no GPU available: verify llama.cpp fallback is healthy

**cost-runaway-mitigation.md:**
1. Check OpenCost dashboard for anomalous spending
2. Identify the service/pod causing overspend
3. Check for infinite loops, runaway queries, or cache misses
4. Temporarily rate-limit the affected endpoint
5. Fix root cause and deploy fix via GitOps

### Step 6: Define SLOs

```yaml
# SLO: Chat Response Latency
- name: chat-response-p99-latency
  target: 99.9%
  threshold: "p99 < 2000ms"  # 2 seconds for full agent response
  measurement: |
    histogram_quantile(0.99,
      sum(rate(http_request_duration_seconds_bucket{service="gateway",path="/graphql"}[5m]))
      by (le))

# SLO: Availability
- name: platform-availability
  target: 99.9%  # 43 min downtime/month
  threshold: "error_rate < 0.1%"
  measurement: |
    1 - (sum(rate(http_requests_total{status=~"5.."}[5m]))
         / sum(rate(http_requests_total[5m])))

# SLO: Cache Hit Rate
- name: semantic-cache-hit-rate
  target: 60%
  measurement: |
    sum(rate(cache_semantic_hits_total[5m]))
    / (sum(rate(cache_semantic_hits_total[5m])) + sum(rate(cache_semantic_misses_total[5m])))
```

### Step 7: Create Grafana Alerts

Create alert rules that fire when SLOs are at risk of breaching their error budget.

### Step 8: Production Readiness Review

Checklist before going live:
- [ ] All services have liveness/readiness probes
- [ ] All services have resource limits (enforced by OPA)
- [ ] All images scanned by Trivy with no CRITICAL CVEs
- [ ] Load test proves p99 < 2s at 1000 concurrent users
- [ ] Chaos test proves recovery from pod kill within 30s
- [ ] Runbooks exist for top 3 incident scenarios
- [ ] SLOs defined and alerting configured
- [ ] GitOps: all deployments via Argo CD, no manual kubectl
- [ ] mTLS enabled mesh-wide (Istio ambient)
- [ ] Cost tracking functional with $/inference visible in UI

## Verification
```bash
# Run full test suite
make test-all

# Run load test
make test-load  # Check reports/load-test.html

# Run chaos experiment
kubectl apply -f tests/chaos/litmus/pod-kill.yaml
# Watch: does the system recover? Do requests succeed?

# Run security scan
trivy image agent-platform-gateway:latest

# Check SLO dashboard in Grafana
# All SLOs should show "within budget"
```

## Key Concepts Taught
1. **Load testing** -- Establish baselines, find bottlenecks before users do
2. **Chaos engineering** -- Verify resilience claims with controlled failure injection
3. **Security scanning** -- CVE detection in containers, DAST for application vulnerabilities
4. **Runbooks** -- Codified incident response (no tribal knowledge dependency)
5. **SLOs + Error budgets** -- Define "good enough" to avoid over-engineering reliability
6. **Production readiness** -- Systematic checklist before going live

## Congratulations!
You have built a FAANG-grade AI Agent Platform from scratch using Claude Code.
The platform includes: GraphQL API, streaming chat UI, RAG with vector search,
semantic caching, agent orchestration, self-hosted LLM inference, full observability,
service mesh, GitOps CI/CD, policy enforcement, cost tracking, and production hardening.
