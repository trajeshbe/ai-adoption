#!/bin/bash
# ============================================================================
# Port Forward: Forward all K8s services to localhost
# Usage: ./scripts/port-forward.sh
# ============================================================================
set -euo pipefail

NAMESPACE="agent-platform"

echo "==> Port forwarding all services..."
echo "  Gateway:   http://localhost:8000"
echo "  Frontend:  http://localhost:3000"
echo "  Grafana:   http://localhost:3001"
echo "  Prefect:   http://localhost:4200"
echo "  MinIO:     http://localhost:9001"
echo ""
echo "Press Ctrl+C to stop."
echo ""

kubectl port-forward -n $NAMESPACE svc/gateway 8000:8000 &
kubectl port-forward -n $NAMESPACE svc/frontend 3000:3000 &
kubectl port-forward -n $NAMESPACE svc/grafana 3001:3000 &
kubectl port-forward -n $NAMESPACE svc/prefect-server 4200:4200 &
kubectl port-forward -n $NAMESPACE svc/minio 9001:9001 &

wait
