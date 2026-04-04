# Phase 6: Observability

## Summary

Instrument the entire platform with OpenTelemetry (OTEL) for distributed tracing and metrics, and deploy the Grafana stack (Grafana, Loki, Tempo, Prometheus) for visualization, log aggregation, and alerting.

## Learning Objectives

- Add OTEL SDK instrumentation to FastAPI and agent services
- Deploy Grafana, Prometheus, Loki, and Tempo via Docker Compose
- Build dashboards for LLM latency, token throughput, and error rates
- Configure alert rules for SLO breaches

## Key Commands

```bash
# Start the observability stack
docker compose --profile observability up -d

# Verify OTEL collector is receiving spans
curl http://localhost:4318/v1/traces

# Open Grafana
open http://localhost:3001
```

## Slash Command

Run `/06-observability` in Claude Code to begin this phase.

## Next Phase

[Phase 7: Service Mesh](phase-07-service-mesh.md)
