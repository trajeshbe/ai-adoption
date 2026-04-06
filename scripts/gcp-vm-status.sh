#!/usr/bin/env bash
set -euo pipefail
# ============================================================================
# Check status of GCP VMs and services
# Usage: bash scripts/gcp-vm-status.sh
# ============================================================================

PROJECT="ai-adoption-492510"
CPU_VM="ai-agent-platform"
CPU_ZONE="us-central1-a"
GPU_VM="ai-agent-gpu-test"
GPU_ZONE="us-east4-c"
SSH_USER="merit"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Check a VM ───────────────────────────────────────────────────────────────
check_vm() {
  local vm="$1" zone="$2" label="$3"

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo " $label"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  local info
  info=$(gcloud compute instances describe "$vm" \
    --project="$PROJECT" --zone="$zone" \
    --format="value(status,machineType.basename(),networkInterfaces[0].accessConfigs[0].natIP)" \
    2>/dev/null || echo "NOT_FOUND")

  if [ "$info" = "NOT_FOUND" ]; then
    echo -e "  Status: ${RED}NOT FOUND${NC}"
    echo ""
    return
  fi

  local status machine_type ip
  status=$(echo "$info" | cut -f1)
  machine_type=$(echo "$info" | cut -f2)
  ip=$(echo "$info" | cut -f3)

  if [ "$status" = "RUNNING" ]; then
    echo -e "  Status:       ${GREEN}RUNNING${NC}"
  elif [ "$status" = "TERMINATED" ] || [ "$status" = "STOPPED" ]; then
    echo -e "  Status:       ${YELLOW}STOPPED${NC} (disk charges ~\$1/mo)"
  else
    echo -e "  Status:       ${RED}${status}${NC}"
  fi

  echo "  Machine:      $machine_type"
  echo "  Zone:         $zone"
  echo "  IP:           ${ip:-N/A}"

  # Check GPU
  local gpu
  gpu=$(gcloud compute instances describe "$vm" \
    --project="$PROJECT" --zone="$zone" \
    --format="value(guestAccelerators[0].acceleratorType.basename())" 2>/dev/null || echo "")
  if [ -n "$gpu" ]; then
    echo "  GPU:          $gpu"
  fi

  if [ "$status" != "RUNNING" ] || [ -z "$ip" ]; then
    echo ""
    return
  fi

  # Check services
  echo ""
  echo "  Services:"

  local reachable=false
  if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "${SSH_USER}@${ip}" "echo ok" &>/dev/null; then
    reachable=true
  fi

  if [ "$reachable" = "true" ]; then
    ssh -o StrictHostKeyChecking=no "${SSH_USER}@${ip}" bash -s << 'REMOTE'
      cd ~/kiaa/ai-adoption 2>/dev/null || exit 0

      # Docker status
      running=$(docker ps --format '{{.Names}}' 2>/dev/null | wc -l)
      echo "    Docker:     $running containers running"

      # Health checks
      for svc in "gateway:8050" "agent-engine:8053" "frontend:8055" "cache-service:8052" "cost-tracker:8054"; do
        name="${svc%%:*}"
        port="${svc##*:}"
        if [ "$name" = "frontend" ]; then
          status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://localhost:${port}/" 2>/dev/null || echo "000")
        else
          status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://localhost:${port}/healthz" 2>/dev/null || echo "000")
        fi
        if [ "$status" = "200" ]; then
          echo "    $name: ✓ healthy (:$port)"
        else
          echo "    $name: ✗ HTTP $status (:$port)"
        fi
      done

      # GPU check
      if command -v nvidia-smi &>/dev/null; then
        gpu_info=$(nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>/dev/null || echo "N/A")
        echo "    GPU:        util=${gpu_info}%"
      fi

      # minikube check
      if command -v minikube &>/dev/null; then
        mk_status=$(minikube status --profile=aiadopt -f '{{.Host}}' 2>/dev/null || echo "Not installed")
        echo "    minikube:   $mk_status"
        if [ "$mk_status" = "Running" ]; then
          pods=$(kubectl get pods -n agent-platform --no-headers 2>/dev/null | wc -l)
          echo "    K8s pods:   $pods in agent-platform"
        fi
      fi
REMOTE
  else
    echo "    SSH:        unreachable"
  fi

  echo ""
  echo "  Access:"
  echo "    SSH:        ssh ${SSH_USER}@${ip}"
  echo "    Frontend:   http://${ip}:8055"
  echo "    GraphQL:    http://${ip}:8050/graphql"
  if [ -n "$gpu" ]; then
    echo "    Scaling:    http://${ip}:8055/scaling"
  fi
  echo ""
}

# ── Main ─────────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo " GCP VM Status Check"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

check_vm "$CPU_VM" "$CPU_ZONE" "CPU VM (always-on, ~\$49/mo)"
check_vm "$GPU_VM" "$GPU_ZONE" "GPU VM (temporary, ~\$0.70/hr)"

echo "============================================"
echo " Quick Commands:"
echo "   Start all:  bash scripts/gcp-vm-start.sh all"
echo "   Stop all:   bash scripts/gcp-vm-stop.sh all"
echo "   Start GPU:  bash scripts/gcp-vm-start.sh gpu"
echo "   Stop GPU:   bash scripts/gcp-vm-stop.sh gpu"
echo "   Delete GPU: bash scripts/gcp-vm-stop.sh gpu --delete"
echo "============================================"
