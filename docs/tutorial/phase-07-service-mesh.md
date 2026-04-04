# Phase 7: Service Mesh

## Summary

Deploy Istio in ambient mode (no sidecars) for transparent mTLS and traffic management, and configure Contour as the Kubernetes ingress controller backed by Envoy. This phase secures service-to-service communication and exposes the platform externally.

## Learning Objectives

- Install Istio ambient mesh with ztunnel per-node proxies
- Configure Contour HTTPProxy resources for ingress routing
- Define authorization policies for inter-service access control
- Enable automatic mTLS between all mesh workloads

## Key Commands

```bash
# Install Istio ambient
istioctl install --set profile=ambient

# Verify ztunnel pods
kubectl get pods -n istio-system -l app=ztunnel

# Apply Contour ingress
kubectl apply -f infra/contour/httpproxy.yaml
```

## Slash Command

Run `/07-service-mesh` in Claude Code to begin this phase.

## Next Phase

[Phase 8: GitOps & CI/CD](phase-08-gitops-cicd.md)
