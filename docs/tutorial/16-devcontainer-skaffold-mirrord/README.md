# Tutorial 16: DevContainer + Skaffold + mirrord — Developer Loop

> **Objective:** Set up a seamless local development experience that connects to Kubernetes services.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [DevContainer](#2-devcontainer)
3. [Skaffold](#3-skaffold)
4. [mirrord](#4-mirrord)
5. [Installation & Setup](#5-installation--setup)
6. [Exercises](#6-exercises)
7. [How It's Used in Our Project](#7-how-its-used-in-our-project)
8. [Tips & Further Reading](#8-tips--further-reading)

---

## 1. Introduction

### What is a Dev Loop?

The **dev loop** is the cycle: write code → build → test → see results → repeat.

```
Fast dev loop (seconds):    Code → Hot reload → See change
Slow dev loop (minutes):    Code → Build image → Push → Deploy → See change
```

### The Three Tools

| Tool | Purpose | Key Benefit |
|------|---------|-------------|
| **DevContainer** | Standardized dev environment | "Works on my machine" → "Works everywhere" |
| **Skaffold** | Build + deploy to K8s | Hot reload for Kubernetes |
| **mirrord** | Connect local code to K8s | Debug locally against remote services |

### How They Work Together

```
Developer Experience:
1. Open repo in VS Code → DevContainer starts (all tools pre-installed)
2. Run `skaffold dev` → builds, deploys, watches for changes
3. Use mirrord → run/debug local code against remote K8s services
```

---

## 2. DevContainer

### What is a DevContainer?

A **DevContainer** is a Docker container configured as a full development environment. It ensures every developer has identical tools, versions, and configurations.

### devcontainer.json

```json
{
  "name": "AI Platform Dev",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",

  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {
      "helm": "latest",
      "minikube": "latest"
    },
    "ghcr.io/devcontainers/features/node:1": {
      "version": "20"
    }
  },

  "postCreateCommand": "pip install -r requirements.txt && npm install",

  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "bradlc.vscode-tailwindcss",
        "redhat.vscode-yaml",
        "ms-kubernetes-tools.vscode-kubernetes-tools"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "editor.formatOnSave": true
      }
    }
  },

  "forwardPorts": [3000, 8000, 8080, 9090],
  "remoteUser": "vscode"
}
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Features** | Pre-built tool installers (Docker, kubectl, Node, etc.) |
| **Lifecycle scripts** | Commands at different stages (create, start, attach) |
| **Port forwarding** | Expose container ports to host |
| **Extensions** | VS Code extensions auto-installed |
| **Mounts** | Share files between host and container |

---

## 3. Skaffold

### What is Skaffold?

**Skaffold** handles the build-test-deploy cycle for Kubernetes:

```
skaffold dev
  ├── Detects file changes
  ├── Rebuilds container image
  ├── Deploys to Kubernetes
  ├── Streams logs
  └── Repeats on next change
```

### skaffold.yaml

```yaml
apiVersion: skaffold/v4beta11
kind: Config
metadata:
  name: ai-platform
build:
  artifacts:
    - image: ai-api
      context: services/api
      docker:
        dockerfile: Dockerfile
      sync:
        manual:
          - src: "**/*.py"
            dest: /app
  local:
    push: false   # Don't push to registry (local development)

deploy:
  kubectl:
    manifests:
      - k8s/*.yaml

portForward:
  - resourceType: service
    resourceName: ai-api
    port: 8000
    localPort: 8000
```

### Key Features

| Feature | Description |
|---------|-------------|
| **File sync** | Copy changed files without rebuilding image |
| **Hot reload** | Restart process on file change |
| **Port forwarding** | Automatic port-forward to local |
| **Profiles** | Different configs for dev/staging |
| **Multi-module** | Build multiple services together |

---

## 4. mirrord

### What is mirrord?

**mirrord** lets you run local code as if it's running inside the Kubernetes cluster:

```
Without mirrord:
  Local code → calls localhost:5432 → fails (no database locally)

With mirrord:
  Local code → mirrord intercepts → forwards to K8s PostgreSQL pod → works!
```

### What It Does

| Feature | Description |
|---------|-------------|
| **Traffic mirroring** | Copy incoming traffic from K8s pod to local |
| **Traffic stealing** | Redirect traffic from K8s pod to local |
| **Env mirroring** | Get environment variables from K8s pod |
| **File mirroring** | Access K8s pod's filesystem |
| **DNS resolution** | Resolve K8s service names locally |

---

## 5. Installation & Setup

### DevContainer in VS Code

```bash
# Install VS Code extension
code --install-extension ms-vscode-remote.remote-containers

# Or use the CLI
npm install -g @devcontainers/cli
devcontainer up --workspace-folder .
```

### Skaffold

```bash
# Linux
curl -Lo skaffold https://storage.googleapis.com/skaffold/releases/latest/skaffold-linux-amd64
chmod +x skaffold && sudo mv skaffold /usr/local/bin/

# Verify
skaffold version
```

### mirrord

```bash
# CLI
curl -fsSL https://raw.githubusercontent.com/metalbear-co/mirrord/main/scripts/install.sh | bash

# VS Code extension
code --install-extension MetalBear.mirrord

# Verify
mirrord --version
```

---

## 6. Exercises

### Exercise 1: Create a DevContainer for FastAPI

Create `.devcontainer/devcontainer.json`:

```json
{
  "name": "FastAPI Dev",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",

  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/git:1": {}
  },

  "postCreateCommand": "pip install fastapi uvicorn httpx pytest",

  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "python.testing.pytestEnabled": true
      }
    }
  },

  "forwardPorts": [8000],
  "remoteUser": "vscode"
}
```

```bash
# Open in VS Code
code .
# Click "Reopen in Container" when prompted
# Or: Ctrl+Shift+P → "Dev Containers: Reopen in Container"

# Inside the container:
python -c "import fastapi; print(fastapi.__version__)"
uvicorn main:app --reload --port 8000
```

---

### Exercise 2: DevContainer with Docker Compose Services

```json
// .devcontainer/devcontainer.json
{
  "name": "Full Stack Dev",
  "dockerComposeFile": "docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspace",

  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "cweijan.vscode-database-client2"
      ]
    }
  },

  "forwardPorts": [8000, 5432, 6379]
}
```

```yaml
# .devcontainer/docker-compose.yml
version: "3.8"
services:
  app:
    image: mcr.microsoft.com/devcontainers/python:3.12
    volumes:
      - ..:/workspace:cached
    command: sleep infinity
    depends_on:
      - postgres
      - redis

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: aiplatform
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: devpass
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis/redis-stack:latest
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

```bash
# Inside the dev container, services are accessible:
psql postgresql://dev:devpass@postgres:5432/aiplatform
redis-cli -h redis
```

---

### Exercise 3: Skaffold Basic Setup

```yaml
# skaffold.yaml
apiVersion: skaffold/v4beta11
kind: Config
metadata:
  name: ai-api
build:
  artifacts:
    - image: ai-api
      context: .
      docker:
        dockerfile: Dockerfile
deploy:
  kubectl:
    manifests:
      - k8s/deployment.yaml
      - k8s/service.yaml
portForward:
  - resourceType: service
    resourceName: ai-api
    port: 8000
    localPort: 8000
```

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-api
spec:
  replicas: 1
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
          image: ai-api  # Skaffold replaces this
          ports:
            - containerPort: 8000
---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-api
spec:
  selector:
    app: ai-api
  ports:
    - port: 8000
```

```bash
# Start dev loop
skaffold dev

# Skaffold will:
# 1. Build the Docker image
# 2. Deploy to your K8s cluster
# 3. Port-forward to localhost:8000
# 4. Watch for file changes and rebuild

# In another terminal:
curl http://localhost:8000/health
```

---

### Exercise 4: Skaffold File Sync (No Rebuild)

```yaml
# skaffold.yaml — with file sync
apiVersion: skaffold/v4beta11
kind: Config
build:
  artifacts:
    - image: ai-api
      context: .
      docker:
        dockerfile: Dockerfile
      sync:
        manual:
          # Sync Python files without rebuilding image
          - src: "**/*.py"
            dest: /app
          # Sync config files
          - src: "**/*.yaml"
            dest: /app
deploy:
  kubectl:
    manifests:
      - k8s/*.yaml
```

```dockerfile
# Dockerfile (use --reload for auto-restart)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

```bash
skaffold dev

# Now edit main.py — changes sync in ~1 second (no image rebuild!)
# uvicorn's --reload picks up the synced file
```

---

### Exercise 5: Skaffold Profiles

```yaml
# skaffold.yaml
apiVersion: skaffold/v4beta11
kind: Config
build:
  artifacts:
    - image: ai-api
      context: .
deploy:
  kubectl:
    manifests:
      - k8s/base/*.yaml

profiles:
  - name: dev
    activation:
      - env: SKAFFOLD_PROFILE=dev
    patches:
      - op: replace
        path: /deploy/kubectl/manifests
        value:
          - k8s/base/*.yaml
          - k8s/dev/*.yaml
    deploy:
      kubectl:
        defaultNamespace: ai-dev

  - name: staging
    patches:
      - op: replace
        path: /deploy/kubectl/manifests
        value:
          - k8s/base/*.yaml
          - k8s/staging/*.yaml
    deploy:
      kubectl:
        defaultNamespace: ai-staging

  - name: prod
    build:
      artifacts:
        - image: ai-api
          context: .
          docker:
            buildArgs:
              ENVIRONMENT: production
    deploy:
      kubectl:
        defaultNamespace: ai-prod
```

```bash
# Use specific profile
skaffold dev -p dev
skaffold run -p staging
skaffold run -p prod
```

---

### Exercise 6: mirrord — Run Local Against Remote K8s

```bash
# Run a local Python script as if it's inside K8s
mirrord exec --target deployment/ai-api -- python main.py

# This makes your local code:
# - See the same env vars as the K8s pod
# - Resolve K8s DNS (redis.ai-platform.svc → works!)
# - Receive traffic meant for the K8s pod
```

```json
// .mirrord/mirrord.json — configuration
{
  "target": {
    "path": "deployment/ai-api",
    "namespace": "ai-platform"
  },
  "feature": {
    "network": {
      "incoming": "mirror",    // Copy incoming traffic (doesn't steal)
      "outgoing": true         // Route outgoing through K8s
    },
    "fs": "read",              // Read K8s pod's filesystem
    "env": true                // Get K8s pod's env vars
  }
}
```

```bash
# With config file
mirrord exec -- uvicorn main:app --port 8000

# Your local app now:
# ✓ Connects to K8s PostgreSQL
# ✓ Connects to K8s Redis
# ✓ Receives mirrored traffic from the K8s pod
# ✓ Has the same environment variables
```

VS Code integration:

```json
// .vscode/launch.json
{
  "configurations": [
    {
      "name": "Python: mirrord",
      "type": "python",
      "request": "launch",
      "program": "main.py",
      "env": {
        "MIRRORD_AGENT_RUST_LOG": "info",
        "MIRRORD_CONFIG_FILE": "${workspaceFolder}/.mirrord/mirrord.json"
      }
    }
  ]
}
```

---

### Exercise 7: Full Dev Loop

Combining all three tools:

```bash
# Step 1: Open project in DevContainer
# → All tools (Python, kubectl, Skaffold, mirrord) are pre-installed

# Step 2: Start services with Skaffold
skaffold dev -p dev
# → Builds and deploys to local K8s
# → Hot reload on file changes
# → Port-forwarded to localhost

# Step 3: Debug a specific service with mirrord
# In VS Code, press F5 with mirrord config
# → Local debugger connects to K8s services
# → Set breakpoints, inspect variables
# → Traffic from K8s flows to your debugger

# Step 4: Make changes
# Edit main.py → Skaffold syncs file → uvicorn reloads → see changes in ~2s

# Step 5: Run tests against real services
mirrord exec -- pytest tests/ -v
# Tests run locally but connect to K8s databases and services
```

### Complete DevContainer for the project:

```json
// .devcontainer/devcontainer.json
{
  "name": "AI Platform Full Dev",
  "dockerComposeFile": "docker-compose.yml",
  "service": "dev",
  "workspaceFolder": "/workspace",

  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {},
    "ghcr.io/devcontainers/features/node:1": { "version": "20" }
  },

  "postCreateCommand": "bash .devcontainer/post-create.sh",

  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
        "bradlc.vscode-tailwindcss",
        "redhat.vscode-yaml",
        "ms-kubernetes-tools.vscode-kubernetes-tools",
        "MetalBear.mirrord"
      ]
    }
  },

  "forwardPorts": [3000, 8000, 8080, 5432, 6379, 9090]
}
```

```bash
#!/bin/bash
# .devcontainer/post-create.sh

# Install Python dependencies
pip install -r requirements.txt

# Install Skaffold
curl -Lo skaffold https://storage.googleapis.com/skaffold/releases/latest/skaffold-linux-amd64
chmod +x skaffold && sudo mv skaffold /usr/local/bin/

# Install mirrord
curl -fsSL https://raw.githubusercontent.com/metalbear-co/mirrord/main/scripts/install.sh | bash

# Install Tekton CLI
curl -sSL https://github.com/tektoncd/cli/releases/latest/download/tkn_Linux_x86_64.tar.gz | tar xz tkn
sudo mv tkn /usr/local/bin/

# Install ArgoCD CLI
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd && sudo mv argocd /usr/local/bin/

echo "Dev environment ready!"
```

---

## 7. How It's Used in Our Project

- **DevContainer** — Every developer gets the same environment (Python, Node, kubectl, Helm, Skaffold, mirrord)
- **Skaffold** — `skaffold dev` for rapid iteration on any service
- **File sync** — Python and TypeScript changes sync without image rebuild
- **Profiles** — Dev/staging configurations with different resource limits
- **mirrord** — Debug locally against staging K8s cluster
- **Standardization** — New team members are productive in minutes, not days

---

## 8. Tips & Further Reading

### Performance Tips

1. **Use file sync** over image rebuilds whenever possible
2. **Cache Docker layers** — order Dockerfile for maximum cache hits
3. **Use mirrord for debugging** — faster than deploying and tailing logs
4. **Pre-build DevContainer images** — avoid long `postCreateCommand` times
5. **Use `skaffold debug`** — attaches debugger automatically

### Common Issues

| Issue | Fix |
|-------|-----|
| DevContainer slow to start | Pre-build image, use features cache |
| Skaffold rebuilds too often | Configure `sync` for interpreted languages |
| mirrord permission denied | Ensure RBAC allows pod exec |
| File sync not working | Check `.dockerignore` isn't excluding files |

### Further Reading

- [DevContainers Specification](https://containers.dev/)
- [Skaffold Documentation](https://skaffold.dev/docs/)
- [mirrord Documentation](https://mirrord.dev/docs/)
- [VS Code DevContainers Guide](https://code.visualstudio.com/docs/devcontainers/containers)
