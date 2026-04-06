#!/usr/bin/env bash
set -euo pipefail
# ============================================================================
# Stop GCP VMs and application services
# Usage: bash scripts/gcp-vm-stop.sh [cpu|gpu|all]
#        bash scripts/gcp-vm-stop.sh gpu --delete    # Delete GPU VM entirely
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
DELETE="${2:-}"

# ── Stop services on a VM ────────────────────────────────────────────────────
stop_services() {
  local ip="$1" label="$2"
  log "Stopping application services on $label ($ip)..."

  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "${SSH_USER}@${ip}" bash -s << 'REMOTE'
    set -e
    cd ~/kiaa/ai-adoption

    # Stop minikube if running
    if command -v minikube &>/dev/null; then
      if minikube status --profile=aiadopt 2>/dev/null | grep -q "Running"; then
        echo "Stopping minikube..."
        minikube stop --profile=aiadopt 2>&1 | tail -1
      fi
    fi

    # Stop all Docker Compose services
    echo "Stopping Docker Compose services..."
    docker compose down 2>&1 | tail -5

    echo ""
    echo "=== Remaining containers ==="
    docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "(none)"
REMOTE

  log "$label services stopped"
}

# ── Stop a VM ────────────────────────────────────────────────────────────────
stop_vm() {
  local vm="$1" zone="$2" label="$3" delete="${4:-}"

  STATUS=$(gcloud compute instances describe "$vm" \
    --project="$PROJECT" --zone="$zone" \
    --format="value(status)" 2>/dev/null || echo "NOT_FOUND")

  if [ "$STATUS" = "NOT_FOUND" ]; then
    warn "$label VM not found (already deleted?)"
    return 0
  fi

  if [ "$STATUS" = "TERMINATED" ] || [ "$STATUS" = "STOPPED" ]; then
    log "$label VM is already stopped"
  else
    # Get IP to stop services first
    local ip
    ip=$(gcloud compute instances describe "$vm" \
      --project="$PROJECT" --zone="$zone" \
      --format="value(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null || echo "")

    if [ -n "$ip" ]; then
      stop_services "$ip" "$label" || warn "Could not stop services (VM may be unreachable)"
    fi
  fi

  if [ "$delete" = "--delete" ]; then
    log "DELETING $label VM ($vm)..."
    gcloud compute instances delete "$vm" \
      --project="$PROJECT" --zone="$zone" --quiet
    log "$label VM DELETED (billing stopped)"
  else
    if [ "$STATUS" = "RUNNING" ]; then
      log "Stopping $label VM ($vm)..."
      gcloud compute instances stop "$vm" \
        --project="$PROJECT" --zone="$zone" --quiet
      log "$label VM stopped (disk billing continues, ~\$1/mo)"
    fi
  fi
}

# ── Main ─────────────────────────────────────────────────────────────────────
echo "============================================"
echo " GCP VM Stop Script"
echo " Target: $TARGET"
if [ "$DELETE" = "--delete" ]; then
  echo " Mode: DELETE (permanent!)"
fi
echo "============================================"
echo ""

if [ "$TARGET" = "cpu" ] || [ "$TARGET" = "all" ]; then
  stop_vm "$CPU_VM" "$CPU_ZONE" "CPU"
  echo ""
fi

if [ "$TARGET" = "gpu" ] || [ "$TARGET" = "all" ]; then
  stop_vm "$GPU_VM" "$GPU_ZONE" "GPU" "$DELETE"
  echo ""
fi

echo "============================================"
echo " Done!"
echo ""
echo " Billing status:"
echo "   Stopped VM: disk charges only (~\$1/mo per VM)"
echo "   Deleted VM: no charges"
echo ""
echo " To delete GPU VM permanently:"
echo "   bash scripts/gcp-vm-stop.sh gpu --delete"
echo "============================================"
