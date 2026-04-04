# Deploy Local -- Start the Full Stack via Skaffold

## Usage
Run this command to deploy all services to a local Kubernetes cluster.

## Prerequisites
- Docker Desktop with Kubernetes enabled, or Kind/k3d cluster running
- Skaffold installed (included in DevContainer)
- All container images buildable (Dockerfiles exist for each service)

## What It Does
1. Builds all 6 container images (gateway, agent-engine, document-service, cache-service, cost-tracker, frontend)
2. Deploys to local K8s using Kustomize dev overlay
3. Sets up port forwarding: gateway (8000), frontend (3000), grafana (3001)
4. Watches for file changes and hot-reloads affected services

## Instructions
```bash
# Start local K8s cluster (if not already running)
kind create cluster --name agent-platform

# Deploy everything
skaffold dev --port-forward

# In another terminal, verify:
kubectl get pods -n agent-platform  # All pods Running
curl http://localhost:8000/healthz   # Gateway healthy
curl http://localhost:3000            # Frontend loads
```

## Troubleshooting
- **ImagePullBackOff**: Images are built locally. Ensure `skaffold.yaml` has `local.push: false`
- **CrashLoopBackOff**: Check logs: `kubectl logs deploy/<service-name> -n agent-platform`
- **Port conflict**: Change localPort in skaffold.yaml portForward section
