# Phase 8: GitOps & CI/CD

## Summary

Implement GitOps-driven deployments with Argo CD for continuous delivery and Tekton for CI pipelines. This phase automates building, testing, scanning, and deploying every commit through a declarative pipeline.

## Learning Objectives

- Deploy Argo CD and register the platform repository
- Define Tekton pipelines for build, test, scan, and push stages
- Configure automatic sync policies and health checks in Argo CD
- Set up image promotion across dev, staging, and prod overlays

## Key Commands

```bash
# Install Argo CD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Create the application
argocd app create ai-platform --repo <repo-url> --path k8s/overlays/dev

# Trigger a Tekton pipeline run
tkn pipeline start build-and-deploy
```

## Slash Command

Run `/08-gitops-cicd` in Claude Code to begin this phase.

## Next Phase

[Phase 9: Policy & Governance](phase-09-policy-governance.md)
