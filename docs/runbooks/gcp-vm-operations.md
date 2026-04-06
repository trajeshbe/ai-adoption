# GCP VM Operations Runbook

Quick reference for starting, stopping, and managing the AI Agent Platform on GCP.

---

## VM Inventory

| VM | Type | Zone | IP | Cost | Purpose |
|----|------|------|----|------|---------|
| `ai-agent-platform` | e2-standard-2 (2 vCPU, 8 GB) | us-central1-a | 34.121.112.167 | ~$49/mo | Always-on demo (CPU) |
| `ai-agent-gpu-test` | n1-standard-8 + T4 GPU (8 vCPU, 30 GB) | us-east4-c | 8.228.119.177 | ~$0.70/hr | Temporary testing (GPU) |

> **IPs change** when VMs are stopped and restarted (unless you reserve a static IP).

---

## Quick Commands

```bash
# Check status of everything
bash scripts/gcp-vm-status.sh

# Start VMs and services
bash scripts/gcp-vm-start.sh all     # Both VMs
bash scripts/gcp-vm-start.sh cpu     # CPU VM only
bash scripts/gcp-vm-start.sh gpu     # GPU VM only

# Stop VMs (preserves disks, ~$1/mo each)
bash scripts/gcp-vm-stop.sh all      # Both VMs
bash scripts/gcp-vm-stop.sh cpu      # CPU VM only
bash scripts/gcp-vm-stop.sh gpu      # GPU VM only

# Delete GPU VM permanently (stops all billing)
bash scripts/gcp-vm-stop.sh gpu --delete
```

---

## Manual Operations

### Start a VM

```bash
# Start
gcloud compute instances start ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a

# Get the new IP (changes after stop/start)
gcloud compute instances describe ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
```

### Stop a VM

```bash
# Stop (disk preserved, ~$1/mo for disk storage)
gcloud compute instances stop ai-agent-gpu-test \
  --project=ai-adoption-492510 --zone=us-east4-c

# Delete permanently (all billing stops)
gcloud compute instances delete ai-agent-gpu-test \
  --project=ai-adoption-492510 --zone=us-east4-c --quiet
```

### SSH into a VM

```bash
ssh merit@34.121.112.167    # CPU VM
ssh merit@8.228.119.177     # GPU VM
```

---

## Service Management (Inside a VM)

### Start All Services

```bash
cd ~/kiaa/ai-adoption
docker compose up -d
```

### Stop All Services

```bash
cd ~/kiaa/ai-adoption
docker compose down
```

### Restart a Single Service

```bash
docker compose restart gateway          # Restart gateway
docker compose restart agent-engine     # Restart agent-engine
docker compose up -d --build gateway    # Rebuild and restart
```

### View Logs

```bash
docker logs aiadopt-gateway --tail 50 -f         # Gateway logs (follow)
docker logs aiadopt-agent-engine --tail 50 -f     # Agent engine logs
docker logs aiadopt-ollama --tail 50 -f           # LLM logs
docker compose logs --tail 20                      # All services (last 20 lines)
```

### Check Service Health

```bash
# All containers
docker ps --format "table {{.Names}}\t{{.Status}}"

# Individual health endpoints
curl http://localhost:8050/healthz     # Gateway
curl http://localhost:8053/healthz     # Agent Engine
curl http://localhost:8052/healthz     # Cache Service
curl http://localhost:8054/healthz     # Cost Tracker

# GPU status (GPU VM only)
nvidia-smi
```

### Pull Latest Code and Rebuild

```bash
cd ~/kiaa/ai-adoption
git pull origin master
docker compose up -d --build    # Rebuild changed images
```

---

## Minikube / K8s Operations (GPU VM Only)

### Start minikube

```bash
minikube start --cpus=4 --memory=8192 --driver=docker --profile=aiadopt
minikube addons enable metrics-server --profile=aiadopt
kubectl apply -f infra/k8s/demo/
```

### Stop minikube

```bash
minikube stop --profile=aiadopt
```

### Delete minikube cluster

```bash
minikube delete --profile=aiadopt
```

### Check K8s Status

```bash
kubectl get pods,hpa,svc -n agent-platform
kubectl top pods -n agent-platform           # CPU/memory per pod
kubectl describe hpa gateway -n agent-platform  # HPA events and decisions
```

### Reconnect Gateway to minikube (After Restart)

After restarting the gateway container, it loses its connection to the minikube Docker network:

```bash
docker network connect aiadopt aiadopt-gateway

# Verify
curl -s http://localhost:8050/k8s | python3 -m json.tool | head -10
```

---

## Troubleshooting

### Services won't start

```bash
# Check if Docker is running
sudo systemctl status docker

# Check disk space
df -h /

# Check memory
free -h

# View container logs for errors
docker compose logs --tail 50
```

### GPU not detected

```bash
# Check driver
nvidia-smi

# If "driver not loaded", reboot may be needed after first install
sudo reboot

# Verify Docker can see GPU
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### Ollama model not found

```bash
docker exec aiadopt-ollama ollama list          # What models are installed?
docker exec aiadopt-ollama ollama pull qwen2.5:1.5b   # Re-pull
```

### Agent engine 500 error

```bash
docker logs aiadopt-agent-engine --tail 30

# Common fix: ensure Prefect home is writable
docker exec aiadopt-agent-engine ls -la /tmp/prefect/

# Restart
docker compose restart agent-engine
```

### Scaling dashboard empty

```bash
# Is minikube running?
minikube status --profile=aiadopt

# Is gateway connected to minikube network?
docker network connect aiadopt aiadopt-gateway

# Can gateway reach K8s API?
docker exec aiadopt-gateway /tmp/kube/kubectl \
  --kubeconfig=/tmp/kube/kubeconfig get pods -n agent-platform
```

### VM IP changed after restart

IPs are ephemeral by default. After stopping and starting a VM:

```bash
# Get new IP
gcloud compute instances describe <VM_NAME> \
  --project=ai-adoption-492510 --zone=<ZONE> \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)"

# Update .env on the VM with new IP for frontend
ssh merit@<NEW_IP>
cd ~/kiaa/ai-adoption
echo "NEXT_PUBLIC_GRAPHQL_URL=http://<NEW_IP>:8050/graphql" > .env
echo "LLM_MODEL=qwen2.5:1.5b" >> .env
docker compose up -d --build frontend    # Rebuild with new URL
```

---

## Cost Management

### Current Billing

```bash
# Check running instances
gcloud compute instances list --project=ai-adoption-492510

# Estimate: Running VMs
# CPU VM (e2-standard-2):   ~$0.067/hr  (~$49/mo)
# GPU VM (n1-standard-8+T4): ~$0.70/hr  (~$504/mo if left running!)
# Stopped VM disk (100GB):   ~$1/mo
```

### Cost-Saving Tips

1. **Always stop/delete the GPU VM** when not testing (`bash scripts/gcp-vm-stop.sh gpu`)
2. **Stop the CPU VM overnight** if not needed 24/7 (`bash scripts/gcp-vm-stop.sh cpu`)
3. **Use preemptible/spot VMs** for testing (60-80% cheaper, may be reclaimed)
4. **Reserve a static IP** ($4/mo) if you need a permanent URL for the CPU VM

### Emergency: Stop All Billing

```bash
# Nuclear option: stop everything
bash scripts/gcp-vm-stop.sh all

# Or delete everything
gcloud compute instances delete ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a --quiet
gcloud compute instances delete ai-agent-gpu-test \
  --project=ai-adoption-492510 --zone=us-east4-c --quiet
```
