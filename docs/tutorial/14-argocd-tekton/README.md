# Tutorial 14: Argo CD + Tekton — GitOps CI/CD

> **Objective:** Learn GitOps-based continuous delivery with Argo CD and cloud-native CI pipelines with Tekton.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Argo CD Concepts](#2-argo-cd-concepts)
3. [Tekton Concepts](#3-tekton-concepts)
4. [Installation & Setup](#4-installation--setup)
5. [Exercises](#5-exercises)
6. [How It's Used in Our Project](#6-how-its-used-in-our-project)
7. [Further Reading](#7-further-reading)

---

## 1. Introduction

### What is GitOps?

**GitOps** = Git as the single source of truth for infrastructure and application state.

```
Traditional:  Developer → kubectl apply → Cluster  (push-based, who did what?)
GitOps:       Developer → Git commit → Argo CD → Cluster  (pull-based, audited, reversible)
```

### CI vs CD

| | CI (Tekton) | CD (Argo CD) |
|--|-------------|--------------|
| **What** | Build, test, push images | Deploy to Kubernetes |
| **Trigger** | Git push/PR | Git commit to deploy repo |
| **Model** | Push-based | Pull-based |
| **Output** | Container image | Running application |

### The Full Flow

```
Code Push → [Tekton: lint→test→build→push image] → [Update deploy repo] → [Argo CD: sync to cluster]
```

---

## 2. Argo CD Concepts

### Application

An Application maps a Git repo path to a Kubernetes namespace:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ai-api
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/deploy-repo.git
    path: apps/ai-api          # K8s manifests here
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: ai-platform
  syncPolicy:
    automated:
      prune: true       # Delete resources removed from Git
      selfHeal: true    # Fix manual changes (drift)
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Auto-sync** | Automatically deploy when Git changes |
| **Self-heal** | Revert manual kubectl changes |
| **Prune** | Delete resources removed from Git |
| **ApplicationSet** | Template multiple apps (dev/staging/prod) |
| **App-of-apps** | One app that manages other apps |

---

## 3. Tekton Concepts

### Pipeline Model

```
Pipeline
├── Task 1: Lint
│   └── Step: run eslint
├── Task 2: Test
│   ├── Step: run unit tests
│   └── Step: run integration tests
├── Task 3: Build
│   └── Step: build Docker image (Kaniko)
└── Task 4: Push
    └── Step: push to registry
```

| Resource | Description |
|----------|-------------|
| **Task** | A sequence of steps (containers) |
| **TaskRun** | An execution of a Task |
| **Pipeline** | A sequence of Tasks with dependencies |
| **PipelineRun** | An execution of a Pipeline |
| **Workspace** | Shared storage between Tasks |
| **Trigger** | Auto-run Pipeline on events (webhook) |

---

## 4. Installation & Setup

### Argo CD

```bash
# Install Argo CD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Port-forward the UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Open https://localhost:8080 (admin / <password>)

# Install CLI
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd && sudo mv argocd /usr/local/bin/

# Login
argocd login localhost:8080 --username admin --password <password> --insecure
```

### Tekton

```bash
# Install Tekton Pipelines
kubectl apply -f https://storage.googleapis.com/tekton-releases/pipeline/latest/release.yaml

# Install Tekton Triggers
kubectl apply -f https://storage.googleapis.com/tekton-releases/triggers/latest/release.yaml

# Install Tekton Dashboard (optional)
kubectl apply -f https://storage.googleapis.com/tekton-releases/dashboard/latest/release.yaml

# Port-forward dashboard
kubectl port-forward svc/tekton-dashboard -n tekton-pipelines 9097:9097
# Open http://localhost:9097

# Install CLI
curl -sSL https://github.com/tektoncd/cli/releases/latest/download/tkn_Linux_x86_64.tar.gz | tar xz tkn
sudo mv tkn /usr/local/bin/
```

---

## 5. Exercises

### Exercise 1: Deploy First Argo CD Application

```yaml
# Create a simple app to deploy
# deploy-repo/apps/hello/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: hello
  template:
    metadata:
      labels:
        app: hello
    spec:
      containers:
        - name: hello
          image: hashicorp/http-echo
          args: ["-text=Hello from GitOps!"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: hello-svc
spec:
  selector:
    app: hello
  ports:
    - port: 80
      targetPort: 5678
```

```yaml
# argo-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: hello-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/deploy-repo.git
    path: apps/hello
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: default
```

```bash
# Create the application
kubectl apply -f argo-app.yaml

# Or via CLI
argocd app create hello-app \
  --repo https://github.com/your-org/deploy-repo.git \
  --path apps/hello \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace default

# Sync (deploy)
argocd app sync hello-app

# Check status
argocd app get hello-app
```

---

### Exercise 2: Auto-sync with Self-heal

```yaml
# auto-sync-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ai-api
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/deploy-repo.git
    path: apps/ai-api
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: ai-platform
  syncPolicy:
    automated:
      prune: true              # Remove deleted resources
      selfHeal: true           # Revert manual changes
      allowEmpty: false        # Don't sync if source is empty
    syncOptions:
      - CreateNamespace=true   # Create namespace if missing
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

```bash
# Test self-heal: manually change replicas
kubectl scale deployment ai-api --replicas=5 -n ai-platform
# Watch Argo CD revert it back to the Git-defined value!

argocd app get ai-api
# Status should show "Synced" after self-heal
```

---

### Exercise 3: ApplicationSet for Multi-Environment

```yaml
# appset-multi-env.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: ai-platform-envs
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - env: dev
            namespace: ai-dev
            cluster: https://kubernetes.default.svc
            replicas: "1"
          - env: staging
            namespace: ai-staging
            cluster: https://kubernetes.default.svc
            replicas: "2"
          - env: prod
            namespace: ai-prod
            cluster: https://kubernetes.default.svc
            replicas: "3"
  template:
    metadata:
      name: "ai-api-{{env}}"
    spec:
      project: default
      source:
        repoURL: https://github.com/your-org/deploy-repo.git
        path: "apps/ai-api/overlays/{{env}}"
        targetRevision: main
      destination:
        server: "{{cluster}}"
        namespace: "{{namespace}}"
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

```bash
kubectl apply -f appset-multi-env.yaml

# This creates 3 applications:
# - ai-api-dev      (1 replica)
# - ai-api-staging  (2 replicas)
# - ai-api-prod     (3 replicas)

argocd app list
```

---

### Exercise 4: Tekton Task — Build Docker Image

```yaml
# kaniko-build-task.yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: kaniko-build
spec:
  params:
    - name: image
      description: Docker image to build
    - name: dockerfile
      default: Dockerfile
    - name: context
      default: .
  workspaces:
    - name: source
  results:
    - name: IMAGE_DIGEST
      description: Digest of the built image
  steps:
    - name: build-and-push
      image: gcr.io/kaniko-project/executor:latest
      args:
        - "--dockerfile=$(params.dockerfile)"
        - "--context=$(workspaces.source.path)/$(params.context)"
        - "--destination=$(params.image)"
        - "--digest-file=$(results.IMAGE_DIGEST.path)"
```

```bash
# Run the task
tkn task start kaniko-build \
  --param image=registry.example.com/ai-api:latest \
  --workspace name=source,claimName=source-pvc \
  --showlog
```

---

### Exercise 5: Tekton Pipeline — Full CI

```yaml
# ci-pipeline.yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: ai-api-ci
spec:
  params:
    - name: repo-url
    - name: revision
      default: main
    - name: image
  workspaces:
    - name: shared-workspace

  tasks:
    # Step 1: Clone repo
    - name: clone
      taskRef:
        name: git-clone
      params:
        - name: url
          value: $(params.repo-url)
        - name: revision
          value: $(params.revision)
      workspaces:
        - name: output
          workspace: shared-workspace

    # Step 2: Lint
    - name: lint
      runAfter: [clone]
      taskSpec:
        workspaces:
          - name: source
        steps:
          - name: lint
            image: python:3.12
            workingDir: $(workspaces.source.path)
            script: |
              pip install ruff
              ruff check .
      workspaces:
        - name: source
          workspace: shared-workspace

    # Step 3: Test
    - name: test
      runAfter: [lint]
      taskSpec:
        workspaces:
          - name: source
        steps:
          - name: test
            image: python:3.12
            workingDir: $(workspaces.source.path)
            script: |
              pip install -r requirements.txt
              pip install pytest pytest-asyncio
              pytest tests/ -v
      workspaces:
        - name: source
          workspace: shared-workspace

    # Step 4: Build and push image
    - name: build
      runAfter: [test]
      taskRef:
        name: kaniko-build
      params:
        - name: image
          value: $(params.image)
      workspaces:
        - name: source
          workspace: shared-workspace
```

```bash
# Run the pipeline
tkn pipeline start ai-api-ci \
  --param repo-url=https://github.com/your-org/ai-api.git \
  --param revision=main \
  --param image=registry.example.com/ai-api:v1.2.3 \
  --workspace name=shared-workspace,volumeClaimTemplateFile=pvc-template.yaml \
  --showlog
```

---

### Exercise 6: Tekton Triggers — Auto-run on Git Push

```yaml
# trigger.yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: github-listener
spec:
  serviceAccountName: tekton-triggers-sa
  triggers:
    - name: github-push
      interceptors:
        - ref:
            name: github
          params:
            - name: secretRef
              value:
                secretName: github-webhook-secret
                secretKey: token
            - name: eventTypes
              value: ["push"]
      bindings:
        - ref: github-push-binding
      template:
        ref: ci-trigger-template

---
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: github-push-binding
spec:
  params:
    - name: repo-url
      value: $(body.repository.clone_url)
    - name: revision
      value: $(body.after)
    - name: image
      value: "registry.example.com/ai-api:$(body.after)"

---
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: ci-trigger-template
spec:
  params:
    - name: repo-url
    - name: revision
    - name: image
  resourcetemplates:
    - apiVersion: tekton.dev/v1
      kind: PipelineRun
      metadata:
        generateName: ai-api-ci-
      spec:
        pipelineRef:
          name: ai-api-ci
        params:
          - name: repo-url
            value: $(tt.params.repo-url)
          - name: revision
            value: $(tt.params.revision)
          - name: image
            value: $(tt.params.image)
        workspaces:
          - name: shared-workspace
            volumeClaimTemplate:
              spec:
                accessModes: [ReadWriteOnce]
                resources:
                  requests:
                    storage: 1Gi
```

```bash
# Expose the event listener
kubectl get svc el-github-listener
# Configure GitHub webhook to point to this URL
```

---

### Exercise 7: Full GitOps Flow

```
1. Developer pushes code to source repo
   └── GitHub webhook triggers Tekton

2. Tekton Pipeline runs:
   ├── Clone → Lint → Test → Build → Push image
   └── Update deploy repo with new image tag

3. Argo CD detects change in deploy repo
   └── Auto-syncs: deploys new version to cluster
```

```yaml
# Update deploy repo task (add to pipeline)
- name: update-deploy-repo
  runAfter: [build]
  taskSpec:
    params:
      - name: image
    steps:
      - name: update-manifests
        image: alpine/git
        script: |
          git clone https://github.com/your-org/deploy-repo.git
          cd deploy-repo
          
          # Update image tag in kustomization
          sed -i "s|image:.*|image: $(params.image)|" apps/ai-api/deployment.yaml
          
          git config user.email "ci@example.com"
          git config user.name "Tekton CI"
          git add .
          git commit -m "Update ai-api image to $(params.image)"
          git push
  params:
    - name: image
      value: $(params.image)
```

---

### Exercise 8: Progressive Rollout with Argo Rollouts

```yaml
# Install Argo Rollouts
# kubectl apply -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# rollout.yaml — Canary deployment
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: ai-api
  namespace: ai-platform
spec:
  replicas: 5
  strategy:
    canary:
      steps:
        - setWeight: 10    # 10% traffic to canary
        - pause:
            duration: 5m   # Wait 5 minutes
        - setWeight: 30    # 30% traffic
        - pause:
            duration: 5m
        - setWeight: 60    # 60% traffic
        - pause:
            duration: 5m
        - setWeight: 100   # Full rollout
      canaryMetadata:
        labels:
          role: canary
      stableMetadata:
        labels:
          role: stable
      # Auto-rollback on high error rate
      analysis:
        templates:
          - templateName: success-rate
        startingStep: 1
  selector:
    matchLabels:
      app: ai-api
  template:
    metadata:
      labels:
        app: ai-api
    spec:
      containers:
        - name: ai-api
          image: registry.example.com/ai-api:v1.2.3
          ports:
            - containerPort: 8000
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
    - name: success-rate
      interval: 1m
      successCondition: result[0] > 0.95
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            sum(rate(http_requests_total{status=~"2.."}[5m]))
            / sum(rate(http_requests_total[5m]))
```

```bash
# Monitor rollout
kubectl argo rollouts get rollout ai-api -n ai-platform --watch

# Manually promote or abort
kubectl argo rollouts promote ai-api -n ai-platform
kubectl argo rollouts abort ai-api -n ai-platform
```

---

## 6. How It's Used in Our Project

- **Argo CD** — Deploys all services from the deploy repo (auto-sync, self-heal)
- **Tekton** — CI pipelines for all services (lint, test, build, push)
- **ApplicationSet** — Same app deployed to dev/staging/prod
- **Argo Rollouts** — Canary deployments for model serving changes
- **Triggers** — GitHub webhooks auto-trigger CI on push

---

## 7. Further Reading

- [Argo CD Documentation](https://argo-cd.readthedocs.io/)
- [Tekton Documentation](https://tekton.dev/docs/)
- [Argo Rollouts](https://argoproj.github.io/argo-rollouts/)
- [GitOps Principles](https://opengitops.dev/)
