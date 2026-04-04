# Cost Tracker Service

## Purpose
Aggregates OpenCost data to calculate real-time $/inference. Polls OpenCost API,
correlates GPU pod costs with inference trace counts from Prometheus, and serves
cost breakdowns via the gateway's GraphQL API.

## Tech
FastAPI, httpx (OpenCost + Prometheus API clients)

## Key Files
- `src/cost_tracker/collector.py` -- OpenCost API polling for per-pod cost data
- `src/cost_tracker/calculator.py` -- $/inference calculation (GPU cost / inference count)
- `src/cost_tracker/models.py` -- InferenceCost, CostBreakdown Pydantic models

## Run
`uv run uvicorn cost_tracker.main:create_app --factory --reload --port 8004`
