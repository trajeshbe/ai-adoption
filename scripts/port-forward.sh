#!/bin/bash
# ============================================================================
# Port Forward: Forward all K8s services to localhost (20xxx range)
# Uses 20xxx ports to avoid conflicts with other apps on this host.
# Usage: ./scripts/port-forward.sh
# ============================================================================
set -euo pipefail

NAMESPACE="agent-platform"

echo "==> Port forwarding all services (ai-adoption)..."
echo "  Gateway:   http://localhost:20800"
echo "  Frontend:  http://localhost:20300"
echo "  Grafana:   http://localhost:20301"
echo "  Prefect:   http://localhost:20420"
echo "  MinIO UI:  http://localhost:20901"
echo ""
echo "Press Ctrl+C to stop."
echo ""

kubectl port-forward -n $NAMESPACE svc/gateway 20800:8000 &
kubectl port-forward -n $NAMESPACE svc/frontend 20300:3000 &
kubectl port-forward -n $NAMESPACE svc/grafana 20301:3000 &
kubectl port-forward -n $NAMESPACE svc/prefect-server 20420:4200 &
kubectl port-forward -n $NAMESPACE svc/minio 20901:9001 &

wait
