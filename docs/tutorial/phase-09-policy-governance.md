# Phase 9: Policy & Governance

## Summary

Enforce platform policies with Open Policy Agent (OPA) for admission control and runtime authorization, and deploy OpenCost for real-time Kubernetes cost monitoring and budget enforcement.

## Learning Objectives

- Deploy OPA Gatekeeper with constraint templates for pod security
- Write Rego policies for image allowlists and resource limits
- Install OpenCost and configure cost allocation by namespace
- Set budget alerts and automated cost anomaly notifications

## Key Commands

```bash
# Install OPA Gatekeeper
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.14/deploy/gatekeeper.yaml

# Apply a constraint template
kubectl apply -f policies/require-resource-limits.yaml

# View cost breakdown
open http://localhost:9090  # OpenCost UI
```

## Slash Command

Run `/09-policy-governance` in Claude Code to begin this phase.

## Next Phase

[Phase 10: Production Hardening](phase-10-production-hardening.md)
