# Phase 10: Production Hardening

## Summary

Validate production readiness through load testing, chaos engineering, security scanning, and SLO definition. This final phase stress-tests every layer of the platform and establishes the operational baseline for production deployment.

## Learning Objectives

- Run load tests with k6 against the GraphQL and LLM endpoints
- Inject failures with Litmus Chaos (pod kill, network partition)
- Scan container images and manifests with Trivy and Kubescape
- Define SLOs (availability, latency, error rate) and configure burn-rate alerts

## Key Commands

```bash
# Run a load test
k6 run tests/load/chat-endpoint.js

# Inject chaos experiment
kubectl apply -f chaos/pod-kill-agent-engine.yaml

# Security scan
trivy image ai-platform/api:latest
kubescape scan framework nsa -t 40
```

## Slash Command

Run `/10-production-hardening` in Claude Code to begin this phase.

## Congratulations

You have built a production-grade AI Agent Platform from scratch. Review the [Architecture docs](../architecture/) and [Runbooks](../runbooks/) for ongoing operations guidance.
