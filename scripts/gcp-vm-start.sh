#!/usr/bin/env bash
set -euo pipefail
# ============================================================================
# Start GCP VMs and application services
# Usage: bash scripts/gcp-vm-start.sh [cpu|gpu|all]
# ============================================================================

PROJECT="ai-adoption-492510"
CPU_VM="ai-agent-platform"
CPU_ZONE="us-central1-a"
GPU_VM="ai-agent-gpu-test"
GPU_ZONE="us-east4-c"
SSH_USER="merit"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN:${NC} $*"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $*"; }

TARGET="${1:-all}"

# ── Start a VM ───────────────────────────────────────────────────────────────
start_vm() {
  local vm="$1" zone="$2" label="$3"
  log "Starting $label VM ($vm in $zone)..."

  STATUS=$(gcloud compute instances describe "$vm" \
    --project="$PROJECT" --zone="$zone" \
    --format="value(status)" 2>/dev/null || echo "NOT_FOUND")

  if [ "$STATUS" = "RUNNING" ]; then
    log "$label VM is already running"
  elif [ "$STATUS" = "NOT_FOUND" ]; then
    err "$label VM not found. Create it first."
    return 1
  else
    gcloud compute instances start "$vm" \
      --project="$PROJECT" --zone="$zone" --quiet
    log "$label VM started. Waiting for SSH..."
    sleep 15
  fi

  # Get external IP
  local ip
  ip=$(gcloud compute instances describe "$vm" \
    --project="$PROJECT" --zone="$zone" \
    --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
  echo "$ip"
}

# ── Start services on a VM ───────────────────────────────────────────────────
start_services() {
  local ip="$1" label="$2" has_gpu="${3:-false}"

  log "Starting application services on $label ($ip)..."

  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "${SSH_USER}@${ip}" bash -s << 'REMOTE'
    set -e
    cd ~/kiaa/ai-adoption

    # Start all services
    docker compose up -d 2>&1 | tail -5

    echo ""
    echo "=== Container Status ==="
    docker ps --format "table {{.Names}}\t{{.Status}}"
REMOTE

  if [ "$has_gpu" = "true" ]; then
    log "Verifying GPU..."
    ssh -o StrictHostKeyChecking=no "${SSH_USER}@${ip}" "nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>&1"

    log "Ensuring LLM model is loaded..."
    ssh -o StrictHostKeyChecking=no "${SSH_USER}@${ip}" \
      "docker exec aiadopt-ollama ollama list 2>&1 | head -5"
  fi

  log "Verifying health endpoints..."
  ssh -o StrictHostKeyChecking=no "${SSH_USER}@${ip}" bash -s << 'REMOTE'
    sleep 5
    for svc in "gateway:8050" "agent-engine:8053" "cache-service:8052" "cost-tracker:8054"; do
      name="${svc%%:*}"
      port="${svc##*:}"
      status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://localhost:${port}/healthz" 2>/dev/null || echo "000")
      if [ "$status" = "200" ]; then
        echo "  ✓ $name (:$port) - healthy"
      else
        echo "  ✗ $name (:$port) - HTTP $status"
      fi
    done
REMOTE

  echo ""
  log "$label services are running"
  log "  Frontend: http://${ip}:8055"
  log "  GraphQL:  http://${ip}:8050/graphql"
}

# ── Start minikube (GPU VM only) ─────────────────────────────────────────────
start_minikube() {
  local ip="$1"
  log "Starting minikube on GPU VM ($ip)..."

  ssh -o StrictHostKeyChecking=no "${SSH_USER}@${ip}" bash -s << 'REMOTE'
    set -e
    if minikube status --profile=aiadopt 2>/dev/null | grep -q "Running"; then
      echo "minikube is already running"
    else
      minikube start --cpus=4 --memory=8192 --driver=docker --profile=aiadopt 2>&1 | tail -3
      minikube addons enable metrics-server --profile=aiadopt 2>&1 | tail -1
    fi
    cd ~/kiaa/ai-adoption
    kubectl apply -f infra/k8s/demo/ 2>&1
    echo ""
    kubectl get pods -n agent-platform --no-headers 2>&1
REMOTE

  log "minikube running. Scaling dashboard: http://${ip}:8055/scaling"
}

# ── Main ─────────────────────────────────────────────────────────────────────
echo "============================================"
echo " GCP VM Start Script"
echo " Target: $TARGET"
echo "============================================"
echo ""

if [ "$TARGET" = "cpu" ] || [ "$TARGET" = "all" ]; then
  CPU_IP=$(start_vm "$CPU_VM" "$CPU_ZONE" "CPU")
  if [ -n "$CPU_IP" ]; then
    start_services "$CPU_IP" "CPU VM" "false"
  fi
  echo ""
fi

if [ "$TARGET" = "gpu" ] || [ "$TARGET" = "all" ]; then
  GPU_IP=$(start_vm "$GPU_VM" "$GPU_ZONE" "GPU")
  if [ -n "$GPU_IP" ]; then
    start_services "$GPU_IP" "GPU VM" "true"
    start_minikube "$GPU_IP"
  fi
  echo ""
fi

echo "============================================"
echo " All done!"
echo "============================================"
