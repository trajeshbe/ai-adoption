# Phase 9: Policy + Governance -- OPA Gatekeeper and OpenCost

## What You Will Learn
- OPA Gatekeeper for Kubernetes policy-as-code enforcement
- Constraint templates and constraints for security guardrails
- OpenCost for real-time Kubernetes cost attribution
- Building a cost-tracker service that calculates $/inference
- FinOps principles for LLM workloads
- Shift-left governance: catch policy violations before deployment

## Prerequisites
- Phase 8 complete (Argo CD + Tekton CI/CD operational)
- Understanding of Kubernetes admission controllers

## Background: Why Policy-as-Code?
Without policy enforcement, engineers can deploy containers without resource limits
(noisy neighbor problem), run as root (security risk), or pull images from untrusted
registries (supply chain attack). OPA Gatekeeper is a Kubernetes admission controller
that evaluates every resource against policies written in Rego. If a deployment violates
a policy, it's rejected before it reaches the cluster. Shift-left: catch issues at
admission time, not at 3 AM when the pager goes off.

## Step-by-Step Instructions

### Step 1: Install OPA Gatekeeper
```bash
helm install gatekeeper gatekeeper/gatekeeper -f infra/helm/values/opa-gatekeeper.yaml
```

### Step 2: Create Constraint Templates

Create `infra/policy/templates/k8srequiredlabels.yaml`:
```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels
        violation[{"msg": msg}] {
          provided := {label | input.review.object.metadata.labels[label]}
          required := {label | label := input.parameters.labels[_]}
          missing := required - provided
          count(missing) > 0
          msg := sprintf("Missing required labels: %v", [missing])
        }
```

### Step 3: Create Constraints

Create constraints in `infra/policy/constraints/`:

**require-labels.yaml** -- All pods must have `app`, `version`, `team` labels
**require-resource-limits.yaml** -- All containers must declare CPU and memory limits
**require-probes.yaml** -- All containers must have liveness and readiness probes
**disallow-privileged.yaml** -- No containers can run in privileged mode
**restrict-image-registries.yaml** -- Images must come from approved registries only

### Step 4: Install OpenCost
```bash
helm install opencost opencost/opencost -f infra/helm/values/opencost.yaml
```

OpenCost reads Prometheus metrics and Kubernetes metadata to calculate real-time
cost per pod, namespace, and label. It knows your cloud provider's pricing.

### Step 5: Build the Cost Tracker Service

Create `services/cost-tracker/src/cost_tracker/`:

**collector.py** -- Polls OpenCost API for per-pod cost data
**calculator.py** -- Correlates costs with inference traces:
```python
async def calculate_cost_per_inference(timerange: str) -> list[InferenceCost]:
    # Get GPU pod costs from OpenCost
    gpu_costs = await opencost_client.get_allocation(
        window=timerange, aggregate="pod", filter="label:app=vllm"
    )
    # Get inference count from Prometheus
    inference_count = await prometheus_client.query(
        f'sum(increase(llm_inference_latency_ms_count[{timerange}]))'
    )
    cost_per_inference = gpu_costs.total / inference_count
    return cost_per_inference
```

### Step 6: Wire to Gateway and Frontend

- Add GraphQL resolvers in gateway for cost queries
- Build `frontend/src/app/costs/page.tsx` with:
  - Real-time cost chart (last 24h, 7d, 30d)
  - Cost breakdown by model, agent type, user
  - InferenceCostBadge component showing $/request on each chat message

### Step 7: Create Cost Alerts

In Grafana, create alert rules for:
- Cost per inference exceeds $0.10 (investigate model efficiency)
- Daily GPU cost exceeds budget threshold
- Cache hit rate drops below 50% (cache may need tuning)

## Verification
```bash
# Test Gatekeeper: try deploying without resource limits
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: test-no-limits
spec:
  containers:
    - name: test
      image: nginx
EOF
# Should be REJECTED with "Missing required resource limits"

# Check OpenCost
kubectl port-forward svc/opencost 9003:9003
curl http://localhost:9003/allocation/compute?window=1d
# Should show cost per pod

# Check cost dashboard in frontend
# http://localhost:3000/costs -- should show $/inference chart
```

## Key Concepts Taught
1. **Policy-as-code** -- Rego policies enforced at Kubernetes admission time
2. **Shift-left governance** -- Catch violations before deployment, not after incidents
3. **OpenCost** -- Real-time cost attribution per pod, namespace, label
4. **FinOps for LLM** -- Cost per inference tracking for budget management
5. **Guardrails** -- Resource limits, probes, non-privileged, trusted registries

## What's Next
Phase 10 (`/10-harden`) is the final phase: load testing, chaos engineering,
security scanning, runbooks, and SLO definitions. This is production readiness.
