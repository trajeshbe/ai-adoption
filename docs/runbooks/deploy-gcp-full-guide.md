# Deploy to GCP & Access via ai-adoption.uk

Complete step-by-step guide to sync the repo to the GCP VM, deploy all services,
and access the platform at `https://ai-adoption.uk`.

---

## Prerequisites

| Item | Value |
|------|-------|
| GCP Project | `ai-adoption-492510` |
| GCP VM | `ai-agent-platform` (e2-standard-2, us-central1-a) |
| SSH User | `merit` |
| Domain | `ai-adoption.uk` (Cloudflare) |
| GitHub Repos | `trajeshbe/ai-adoption` (origin), `merit-data-tech/ai-adoption` (merit) |
| LLM Model | `qwen2.5:1.5b` (Ollama, CPU) |

---

## Quick Deploy (If Everything Is Already Set Up)

If the VM already has Docker, the repo cloned, and Cloudflare DNS configured:

```bash
# 1. Start the VM
bash scripts/gcp-vm-start.sh cpu

# 2. SSH in and deploy
ssh merit@<VM_IP>
cd ~/kiaa/ai-adoption
git pull origin master
docker compose --profile web up -d --build

# 3. Access the site
# https://ai-adoption.uk        (Frontend)
# https://ai-adoption.uk/graphql (GraphQL API)
```

If this is a **first-time setup** or the VM IP has changed, follow the full guide below.

---

## Full Deployment Guide

### Step 1: Start the GCP VM

```bash
# From your local machine
gcloud compute instances start ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a

# Get the VM's external IP (changes on each start unless static IP is reserved)
gcloud compute instances describe ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
```

Note the IP address -- you'll need it for Cloudflare DNS and SSH.

**Or use the helper script:**

```bash
bash scripts/gcp-vm-start.sh cpu
```

### Step 2: SSH into the VM

```bash
ssh merit@<VM_IP>

# Password (if prompted): W3lc0m32025
# Or use gcloud SSH:
gcloud compute ssh ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a
```

### Step 3: Sync the Repo

If the repo is already cloned on the VM:

```bash
cd ~/kiaa/ai-adoption
git pull origin master
```

If cloning for the **first time**:

```bash
mkdir -p ~/kiaa
cd ~/kiaa

# From the primary repo (trajeshbe)
git clone https://github.com/trajeshbe/ai-adoption.git

# Or from the merit-data-tech repo
git clone https://github.com/merit-data-tech/ai-adoption.git

cd ai-adoption
```

### Step 4: Configure Environment Variables

Create the `.env` file on the VM:

```bash
cd ~/kiaa/ai-adoption

cat > .env << 'EOF'
SITE_DOMAIN=ai-adoption.uk
NEXT_PUBLIC_GRAPHQL_URL=https://ai-adoption.uk/graphql
LLM_MODEL=qwen2.5:1.5b
EOF
```

**Important**: `NEXT_PUBLIC_GRAPHQL_URL` is baked into the Next.js frontend at
**build time**. If you change it, you must rebuild the frontend container.

### Step 5: Deploy All Services

```bash
# Build and start all services + Caddy reverse proxy
docker compose --profile web up -d --build
```

This starts 8 containers:

| Container | Service | Port |
|-----------|---------|------|
| `aiadopt-postgres` | PostgreSQL + pgvector | 5432 |
| `aiadopt-redis` | Redis Stack (RediSearch + ReJSON) | 6379 |
| `aiadopt-minio` | MinIO object store | 9000/9001 |
| `aiadopt-ollama` | Ollama LLM runtime | 11434 |
| `aiadopt-gateway` | FastAPI + GraphQL API | 8050 → 8000 |
| `aiadopt-agent-engine` | Prefect + LangGraph agents | 8053 → 8003 |
| `aiadopt-frontend` | Next.js web UI | 8055 → 3000 |
| `aiadopt-caddy` | Caddy reverse proxy | 80/443 |

First deployment takes **5-10 minutes** (building images, downloading Ollama model).
Subsequent deployments take 1-2 minutes.

### Step 6: Verify Services Are Running

```bash
# Check all containers are up
docker ps --format "table {{.Names}}\t{{.Status}}"

# Check health endpoints
curl -s http://localhost:8050/healthz    # Gateway
curl -s http://localhost:8053/healthz    # Agent Engine
curl -s http://localhost:8055/           # Frontend (returns HTML)

# Check Caddy is proxying correctly
curl -s http://localhost:80/healthz      # Should reach gateway via Caddy
```

All health checks should return `{"status": "ok"}` or HTTP 200.

### Step 7: Ensure Ollama Model Is Loaded

```bash
# Check if the model is available
docker exec aiadopt-ollama ollama list

# If qwen2.5:1.5b is not listed, pull it:
docker exec aiadopt-ollama ollama pull qwen2.5:1.5b
```

### Step 8: Update Cloudflare DNS (If IP Changed)

The VM IP changes every time it is stopped and restarted. Update Cloudflare:

1. Go to **https://dash.cloudflare.com** → select `ai-adoption.uk` → **DNS**
2. Edit the **A record** for `@` → set Content to `<NEW_VM_IP>`
3. Edit the **A record** for `www` → set Content to `<NEW_VM_IP>`
4. Ensure both are **Proxied** (orange cloud icon)

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | `@` | `<VM_IP>` | Proxied |
| A | `www` | `<VM_IP>` | Proxied |

**DNS propagation** through Cloudflare is nearly instant (under 30 seconds).

### Step 9: Verify Cloudflare SSL Settings

In Cloudflare Dashboard → **SSL/TLS**:

- **Encryption mode** must be set to `Full` (not `Flexible`)
- `Flexible` causes infinite redirect loops because Cloudflare sends HTTP to Caddy,
  Caddy redirects to HTTPS, Cloudflare sends HTTP again

### Step 10: Access the Platform

Open in your browser:

| URL | What You'll See |
|-----|----------------|
| `https://ai-adoption.uk` | Chat UI (Next.js frontend) |
| `https://ai-adoption.uk/graphql` | GraphQL Playground |
| `https://ai-adoption.uk/healthz` | `{"status": "ok"}` |
| `https://ai-adoption.uk/metrics` | Live traffic metrics |

Try the chat: Type a message in the chat interface. The agent engine processes it
through LangGraph, calls Ollama for LLM inference, and streams the response back.

---

## Architecture: Request Flow

```
Browser (https://ai-adoption.uk)
    │
    │  HTTPS (Cloudflare edge certificate)
    ▼
Cloudflare CDN (DDoS protection, caching, SSL termination)
    │
    │  HTTPS (Let's Encrypt origin cert) or HTTP to :80
    ▼
Caddy (aiadopt-caddy, port 80)
    │
    ├── /graphql*  → Gateway (aiadopt-gateway:8000)
    ├── /healthz   → Gateway
    ├── /readyz    → Gateway
    ├── /metrics*  → Gateway
    │
    └── /*         → Frontend (aiadopt-frontend:3000)
                        │
Gateway (aiadopt-gateway:8000)
    │
    ├── GraphQL queries/mutations
    │   └── → Agent Engine (aiadopt-agent-engine:8003)
    │            └── → Ollama (aiadopt-ollama:11434)
    │                   └── qwen2.5:1.5b model
    │
    ├── → Document Service → Postgres + MinIO
    ├── → Cache Service → Redis Stack
    └── → Cost Tracker → Postgres
```

---

## Updating the Application

When you push new code to the repo:

### From Your Local Machine

```bash
# Make changes, commit, and push
git add .
git commit -m "Your changes"
git push origin master

# Also push to merit-data-tech
git push merit master
```

### On the GCP VM

```bash
ssh merit@<VM_IP>
cd ~/kiaa/ai-adoption

# Pull latest code
git pull origin master

# Rebuild only changed services (faster than --build all)
docker compose --profile web up -d --build gateway      # If gateway changed
docker compose --profile web up -d --build frontend     # If frontend changed
docker compose --profile web up -d --build agent-engine # If agent-engine changed

# Or rebuild everything
docker compose --profile web up -d --build
```

**Important**: If you changed `NEXT_PUBLIC_GRAPHQL_URL` in `.env`, you must rebuild
the frontend:

```bash
docker compose --profile web up -d --build frontend
```

---

## Stopping the Service

### Stop Services (Keep VM Running)

```bash
ssh merit@<VM_IP>
cd ~/kiaa/ai-adoption
docker compose --profile web down
```

### Stop the VM (Stop Billing ~$49/mo → ~$1/mo for disk)

```bash
# From local machine
gcloud compute instances stop ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a

# Or use the helper script
bash scripts/gcp-vm-stop.sh cpu
```

**Note**: When the VM is stopped, `ai-adoption.uk` will show a Cloudflare 522 error
(Connection timed out). This is expected. Start the VM and services to restore access.

---

## Troubleshooting

### Site shows Cloudflare 522 (Connection timed out)

**Cause**: VM is stopped, Caddy is not running, or firewall blocks port 80/443.

```bash
# Check VM status
gcloud compute instances describe ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a \
  --format="value(status)"

# If TERMINATED, start it:
gcloud compute instances start ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a

# SSH in and check services
ssh merit@<VM_IP>
docker ps | grep caddy
docker compose --profile web up -d    # Restart if needed
```

### Site shows "too many redirects"

**Cause**: Cloudflare SSL mode is `Flexible` instead of `Full`.

**Fix**: Cloudflare Dashboard → SSL/TLS → set to `Full`.

### Chat says "Failed to fetch"

**Cause**: Frontend was built with wrong `NEXT_PUBLIC_GRAPHQL_URL`.

```bash
ssh merit@<VM_IP>
cd ~/kiaa/ai-adoption

# Check current .env
cat .env

# Ensure it has:
# NEXT_PUBLIC_GRAPHQL_URL=https://ai-adoption.uk/graphql

# Rebuild frontend with correct URL
docker compose --profile web up -d --build frontend
```

### Containers keep restarting

```bash
# Check logs for the failing container
docker logs aiadopt-gateway --tail 30
docker logs aiadopt-agent-engine --tail 30
docker logs aiadopt-frontend --tail 30

# Common fixes:
# - Disk full: docker system prune -f
# - Out of memory: docker compose restart
# - Port conflict: check nothing else uses 80/443/8050-8055
```

### Ollama model not responding

```bash
# Check if Ollama is running
docker logs aiadopt-ollama --tail 20

# Re-pull the model
docker exec aiadopt-ollama ollama pull qwen2.5:1.5b

# Test inference directly
docker exec aiadopt-ollama ollama run qwen2.5:1.5b "Hello"
```

### VM IP Changed After Restart

```bash
# Get new IP
gcloud compute instances describe ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)"

# Update Cloudflare DNS (both @ and www A records)
# Then SSH in with new IP and verify services are running
ssh merit@<NEW_IP>
cd ~/kiaa/ai-adoption
docker compose --profile web up -d
```

### Git Pull Fails on VM

```bash
# If there are local changes on the VM
cd ~/kiaa/ai-adoption
git stash
git pull origin master
git stash pop    # Re-apply local changes if needed

# If .env was overwritten by git pull (it shouldn't be -- .env is gitignored)
cat > .env << 'EOF'
SITE_DOMAIN=ai-adoption.uk
NEXT_PUBLIC_GRAPHQL_URL=https://ai-adoption.uk/graphql
LLM_MODEL=qwen2.5:1.5b
EOF
```

---

## Complete Cheat Sheet

```bash
# ── Start Everything ──────────────────────────────────────
bash scripts/gcp-vm-start.sh cpu                  # Start VM
ssh merit@<IP> "cd ~/kiaa/ai-adoption && git pull origin master"
ssh merit@<IP> "cd ~/kiaa/ai-adoption && docker compose --profile web up -d --build"
# Update Cloudflare DNS if IP changed
# Access: https://ai-adoption.uk

# ── Check Status ──────────────────────────────────────────
bash scripts/gcp-vm-status.sh                     # VM + service status
ssh merit@<IP> "docker ps"                         # Container status
curl https://ai-adoption.uk/healthz                # Public health check

# ── Update Code ──────────────────────────────────────────
git push origin master && git push merit master    # Push from local
ssh merit@<IP> "cd ~/kiaa/ai-adoption && git pull && docker compose --profile web up -d --build"

# ── Stop Everything ──────────────────────────────────────
bash scripts/gcp-vm-stop.sh cpu                    # Stop VM (~$1/mo disk only)

# ── Logs ──────────────────────────────────────────────────
ssh merit@<IP> "docker logs aiadopt-gateway --tail 30"
ssh merit@<IP> "docker logs aiadopt-agent-engine --tail 30"
ssh merit@<IP> "docker logs aiadopt-caddy --tail 30"
```

---

## Cost Summary

| Component | Running | Stopped |
|-----------|---------|---------|
| GCP VM (e2-standard-2) | ~$49/mo | ~$1/mo (disk) |
| Cloudflare (domain + DNS + CDN) | ~$5/yr | ~$5/yr |
| **Total** | **~$50/mo** | **~$1/mo** |

To eliminate all costs: delete the VM and cancel the domain.

---

## Keeping Both GitHub Repos in Sync

The project lives in two GitHub repos. Keep them in sync:

```bash
# Push to both remotes after every commit
git push origin master    # trajeshbe/ai-adoption
git push merit master     # merit-data-tech/ai-adoption

# Or set up a single command to push to both:
git remote set-url --add --push origin https://github.com/trajeshbe/ai-adoption.git
git remote set-url --add --push origin https://github.com/merit-data-tech/ai-adoption.git

# Now 'git push origin master' pushes to BOTH repos
```

On the GCP VM, pull from whichever repo you prefer:

```bash
git pull origin master    # Uses whichever remote is configured as 'origin'
```
