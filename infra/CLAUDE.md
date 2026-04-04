# Infrastructure

## Layout
- `k8s/base/` -- Kustomize base manifests per service (canonical specs)
- `k8s/overlays/` -- Environment patches (dev, staging, prod)
- `k8s/demo/` -- Lightweight proxy Deployments + Services + HPAs for scaling demos
- `helm/values/` -- Helm values for third-party charts (Postgres, Redis, Grafana, etc.)
- `argocd/` -- App-of-apps pattern. `app-of-apps.yaml` is the root.
- `tekton/` -- CI/CD tasks, pipelines, triggers. All declarative.
- `policy/` -- OPA Gatekeeper constraint templates + constraints.
- `terraform/` -- Optional. Only for cloud-managed K8s.

## K8s Demo Setup (minikube)
- Profile: `aiadopt` (4 CPUs, 8GB RAM, Docker driver)
- Namespace: `agent-platform`
- Deployments: gateway, agent-engine, frontend (proxy pods → host services)
- HPAs: gateway + agent-engine (1-5 replicas, 50% CPU target)
- Proxy pattern: lightweight Python HTTP servers inside pods forward to host at 192.168.49.1
- Metrics-server addon enabled for HPA CPU metrics
- Scale-up: +2 pods/15s, 10s stabilization. Scale-down: -1 pod/30s, 30s stabilization

## Rules
- NEVER use `kubectl apply` directly in production. All changes go through Argo CD.
- Exception: `k8s/demo/` manifests are for local minikube demos only.
- Kustomize overlays ONLY patch; they never duplicate base manifests.
- Every deployment must have: resource limits, liveness/readiness probes,
  PodDisruptionBudget, anti-affinity for prod overlay.
- Helm values files reference upstream charts; we do not fork charts.
- All policies must have both a ConstraintTemplate and a Constraint.
