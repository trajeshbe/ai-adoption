# Phase 8: GitOps + CI/CD -- Argo CD App-of-Apps and Tekton Pipelines

## What You Will Learn
- GitOps principles: git as the single source of truth for deployments
- Argo CD app-of-apps pattern for managing multi-service deployments
- Tekton cloud-native CI/CD pipelines (lint, test, build, scan, deploy)
- Kaniko for rootless container image builds
- Automated promotion across environments (dev -> staging -> prod)
- GitHub Actions for initial CI (lint, test on PR)

## Prerequisites
- Phase 7 complete (Service mesh and ingress configured)
- Kubernetes cluster with Argo CD and Tekton installed
- GitHub repository with push access

## Background: Why GitOps?
Traditional deployment: engineer runs `kubectl apply` or `helm upgrade` from their
laptop. Problems: no audit trail, no rollback, drift between git and cluster state,
"who deployed what when?" is unanswerable. GitOps solves all of these: Argo CD
continuously reconciles cluster state with git. Every deployment is a git commit.
Rollback = git revert. Audit trail = git log. Drift detection = automatic.

## Step-by-Step Instructions

### Step 1: Create the Argo CD App-of-Apps

Create `infra/argocd/app-of-apps.yaml`:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: agent-platform
  namespace: argocd
spec:
  project: platform
  source:
    repoURL: https://github.com/your-org/ai_adoption.git
    targetRevision: main
    path: infra/argocd/apps
  destination:
    server: https://kubernetes.default.svc
    namespace: agent-platform
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

**App-of-apps pattern:** One root Application points to a directory of child
Application manifests. Argo CD manages all of them. Add a service = add a YAML file.
Delete a service = delete the YAML file. No imperative commands.

### Step 2: Create Individual App Manifests

Create one Application per service/component in `infra/argocd/apps/`:
- `gateway.yaml`, `agent-engine.yaml`, `document-service.yaml`, `cache-service.yaml`,
  `cost-tracker.yaml`, `frontend.yaml`
- `postgres.yaml`, `redis.yaml`, `minio.yaml`
- `vllm.yaml`, `grafana-stack.yaml`, `istio.yaml`, `opencost.yaml`

Each uses Kustomize with the appropriate overlay:
```yaml
spec:
  source:
    path: infra/k8s/overlays/dev
    # or for third-party: helm chart with values from infra/helm/values/
  syncPolicy:
    syncOptions:
      - ApplyOutOfSyncOnly=true
```

### Step 3: Create Tekton Tasks

Create reusable tasks in `infra/tekton/tasks/`:

**lint.yaml:**
```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: lint
spec:
  params:
    - name: service-path
  steps:
    - name: ruff
      image: python:3.11-slim
      script: |
        pip install ruff mypy
        ruff check $(params.service-path)
        mypy $(params.service-path) --strict --ignore-missing-imports
```

**test.yaml** -- Run pytest with coverage
**build-image.yaml** -- Build container image with Kaniko (rootless, no Docker daemon)
**trivy-scan.yaml** -- Scan container image for CVEs
**deploy.yaml** -- Update image tag in Kustomize overlay, commit to git (triggers Argo CD sync)

### Step 4: Create Tekton Pipeline

Create `infra/tekton/pipelines/service-pipeline.yaml`:
```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: service-ci-cd
spec:
  params:
    - name: service-name
    - name: git-revision
  tasks:
    - name: lint
      taskRef: { name: lint }
    - name: test
      taskRef: { name: test }
      runAfter: [lint]
    - name: build
      taskRef: { name: build-image }
      runAfter: [test]
    - name: scan
      taskRef: { name: trivy-scan }
      runAfter: [build]
    - name: deploy
      taskRef: { name: deploy }
      runAfter: [scan]
```

### Step 5: Create Tekton Triggers

Create `infra/tekton/triggers/github-push.yaml`:
- EventListener receives GitHub webhook on push to main
- TriggerBinding extracts repo URL, commit SHA, changed files
- TriggerTemplate creates PipelineRun for affected services

### Step 6: Create GitHub Actions CI

Create `.github/workflows/ci.yml` for PR checks:
```yaml
name: CI
on: [pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: make lint
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
      redis:
        image: redis/redis-stack:7.2.0-v10
    steps:
      - uses: actions/checkout@v4
      - run: make test
```

### Step 7: Automated Environment Promotion

The promotion flow:
1. Push to `main` -> Tekton builds image, tags as `sha-abc123`
2. Tekton updates `infra/k8s/overlays/dev/kustomization.yaml` with new image tag
3. Argo CD syncs dev cluster automatically
4. After dev validation, PR to update staging overlay -> merge -> Argo CD syncs staging
5. After staging validation, PR to update prod overlay -> merge -> Argo CD syncs prod

**No imperative deployments.** Every promotion is a git commit. Every rollback is a git revert.

## Verification
```bash
# Check Argo CD sync status
argocd app list
argocd app get agent-platform  # Should show "Synced" and "Healthy"

# Trigger a pipeline
git push origin main
tkn pipelinerun list  # Should show new run
tkn pipelinerun logs -f  # Watch the pipeline execute

# Verify image scanning
tkn taskrun logs trivy-scan-xxx  # Should show CVE report

# Test GitOps: manually change a deployment, watch Argo CD self-heal
kubectl scale deploy gateway --replicas=5  # Argo CD will revert to git-declared replicas
```

## Key Concepts Taught
1. **GitOps** -- Git as the single source of truth, no imperative deploys
2. **App-of-apps** -- One root Application manages all child Applications
3. **Tekton** -- Cloud-native, declarative CI/CD (vs imperative Jenkins)
4. **Kaniko** -- Rootless image builds (no Docker-in-Docker security risk)
5. **Sync waves** -- Ordered deployment (infra before apps, databases before services)
6. **Self-healing** -- Argo CD detects and corrects configuration drift automatically

## What's Next
Phase 9 (`/09-add-policy`) adds OPA Gatekeeper for policy enforcement and OpenCost
for real-time cost tracking per inference.
