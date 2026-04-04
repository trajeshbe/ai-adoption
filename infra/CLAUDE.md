# Infrastructure

## Layout
- `k8s/` -- Kustomize manifests. `base/` has canonical specs, `overlays/` patches per env.
- `helm/values/` -- Helm values files for third-party charts (Postgres, Redis, Grafana, etc.)
- `argocd/` -- App-of-apps pattern. `app-of-apps.yaml` is the root.
- `tekton/` -- CI/CD tasks, pipelines, triggers. All declarative.
- `policy/` -- OPA Gatekeeper constraint templates + constraints.
- `terraform/` -- Optional. Only for cloud-managed K8s.

## Rules
- NEVER use `kubectl apply` directly. All changes go through Argo CD.
- Kustomize overlays ONLY patch; they never duplicate base manifests.
- Every deployment must have: resource limits, liveness/readiness probes,
  PodDisruptionBudget, anti-affinity for prod overlay.
- Helm values files reference upstream charts; we do not fork charts.
- All policies must have both a ConstraintTemplate and a Constraint.
