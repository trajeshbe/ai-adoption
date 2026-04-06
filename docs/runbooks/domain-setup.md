# Domain & HTTPS Setup: ai-adoption.uk

**Domain**: `ai-adoption.uk`
**Registrar**: Cloudflare
**DNS/CDN**: Cloudflare (proxied)
**TLS**: Dual-layer -- Cloudflare edge SSL + Let's Encrypt origin cert via Caddy
**Cost**: ~$5/yr (`.uk` domain via Cloudflare Registrar)

---

## Architecture

```
User (browser)
  │
  │  HTTPS (Cloudflare edge certificate)
  ▼
┌─────────────────────────────────┐
│         Cloudflare CDN          │
│  • SSL termination (edge)       │
│  • DDoS protection              │
│  • Caching static assets        │
│  • HTTP → HTTPS redirect        │
└────────────┬────────────────────┘
             │
             │  HTTPS (Let's Encrypt origin cert)
             ▼
┌─────────────────────────────────┐
│    GCP VM: 34.121.112.167       │
│    Caddy reverse proxy (:80/443)│
│                                 │
│    /graphql*  → gateway:8000    │
│    /healthz   → gateway:8000    │
│    /readyz    → gateway:8000    │
│    /metrics*  → gateway:8000    │
│    /*         → frontend:3000   │
└─────────────────────────────────┘
```

### TLS Chain

```
Browser ──TLS──→ Cloudflare ──TLS──→ Caddy ──HTTP──→ Gateway/Frontend
         (CF cert)           (Let's Encrypt)        (internal Docker network)
```

- **Browser → Cloudflare**: Cloudflare's edge certificate (managed automatically)
- **Cloudflare → Origin**: Let's Encrypt certificate provisioned by Caddy (auto-renews every 60 days)
- **Caddy → Services**: Plain HTTP on Docker's internal `aiadopt-net` network

---

## How It Was Set Up

### Step 1: Register Domain on Cloudflare

1. Created account at https://www.cloudflare.com
2. Searched and purchased `ai-adoption.uk` via Cloudflare Registrar
3. Cloudflare automatically becomes the DNS provider (no nameserver transfer needed)

### Step 2: Configure DNS Records

In Cloudflare Dashboard → `ai-adoption.uk` → DNS → Records:

| Type | Name | Content | Proxy Status | TTL |
|------|------|---------|-------------|-----|
| A | `@` | `34.121.112.167` | Proxied (orange cloud) | Auto |
| A | `www` | `34.121.112.167` | Proxied (orange cloud) | Auto |

**Proxied** means traffic routes through Cloudflare's CDN/WAF before reaching the origin server. This provides:
- Free SSL certificate at the edge
- DDoS protection
- Caching for static assets
- Hides the origin server IP from public DNS lookups

### Step 3: Configure Cloudflare SSL

In Cloudflare Dashboard → SSL/TLS:

- **Encryption mode**: `Full`
  - `Off`: No encryption (bad)
  - `Flexible`: Cloudflare→origin is HTTP (insecure)
  - **`Full`**: Cloudflare→origin is HTTPS (accepts self-signed or Let's Encrypt)
  - `Full (Strict)`: Requires valid CA-signed cert on origin (works with our Let's Encrypt cert)

### Step 4: Configure Caddy Reverse Proxy

**File: `Caddyfile`** (repo root)

```
:80 {
    handle /graphql* {
        reverse_proxy gateway:8000
    }
    handle /healthz {
        reverse_proxy gateway:8000
    }
    handle /readyz {
        reverse_proxy gateway:8000
    }
    handle /metrics* {
        reverse_proxy gateway:8000
    }
    handle {
        reverse_proxy frontend:3000
    }
}
```

Caddy listens on `:80`. When behind Cloudflare proxy, Caddy also auto-provisions a Let's Encrypt certificate for HTTPS on `:443` (Cloudflare passes through the ACME HTTP-01 challenge).

### Step 5: Configure Docker Compose

**File: `docker-compose.yml`** -- Caddy service (activated with `--profile web`):

```yaml
caddy:
  container_name: aiadopt-caddy
  image: caddy:2-alpine
  restart: unless-stopped
  profiles: ["web"]
  ports:
    - "80:80"
    - "443:443"
    - "443:443/udp"    # HTTP/3 (QUIC)
  environment:
    SITE_DOMAIN: ${SITE_DOMAIN:-localhost}
  volumes:
    - ./Caddyfile:/etc/caddy/Caddyfile:ro
    - caddy-data:/data          # Stores TLS certificates
    - caddy-config:/config
  depends_on:
    frontend: { condition: service_started }
    gateway: { condition: service_healthy }
  networks:
    - app-net
```

### Step 6: Set Environment Variables

**File: `.env`** on the VM:

```env
SITE_DOMAIN=ai-adoption.uk
NEXT_PUBLIC_GRAPHQL_URL=https://ai-adoption.uk/graphql
LLM_MODEL=qwen2.5:1.5b
```

`NEXT_PUBLIC_GRAPHQL_URL` is **baked into the Next.js bundle at build time**. The frontend must be rebuilt (`docker compose --profile web up -d --build`) whenever this changes.

### Step 7: Start with Caddy Profile

```bash
docker compose --profile web up -d --build
```

The `--profile web` flag activates the Caddy container. Without it, only the application services start (for local development).

---

## URL Routing

| URL | Caddy Routes To | Service |
|-----|----------------|---------|
| `https://ai-adoption.uk/` | `frontend:3000` | Next.js Web UI (chat, agents, dashboard) |
| `https://ai-adoption.uk/graphql` | `gateway:8000` | GraphQL API (Strawberry) |
| `https://ai-adoption.uk/healthz` | `gateway:8000` | Health check endpoint |
| `https://ai-adoption.uk/readyz` | `gateway:8000` | Readiness check endpoint |
| `https://ai-adoption.uk/metrics` | `gateway:8000` | Live traffic metrics |

---

## Certificate Details

```
Subject:   CN = ai-adoption.uk
Issuer:    C = US, O = Let's Encrypt, CN = E7
Valid:     Apr 6, 2026 – Jul 5, 2026
Auto-renew: Yes (Caddy renews 30 days before expiry)
```

Certificates are stored in the `caddy-data` Docker volume. They persist across container restarts.

---

## Changing the Domain

If you need to point to a different domain:

### 1. Update Cloudflare DNS

Add an A record for the new domain pointing to the VM's IP.

### 2. Update `.env` on the VM

```bash
ssh merit@34.121.112.167
cd ~/kiaa/ai-adoption
cat > .env << EOF
SITE_DOMAIN=new-domain.com
NEXT_PUBLIC_GRAPHQL_URL=https://new-domain.com/graphql
LLM_MODEL=qwen2.5:1.5b
EOF
```

### 3. Rebuild and Restart

```bash
# Rebuild frontend (NEXT_PUBLIC_GRAPHQL_URL is baked at build time)
docker compose --profile web up -d --build

# Caddy will auto-provision a new Let's Encrypt cert for the new domain
docker logs aiadopt-caddy --tail 10
```

---

## Changing the VM IP

When the CPU VM is stopped and restarted, the IP may change (unless a static IP is reserved).

### 1. Get the New IP

```bash
gcloud compute instances describe ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
```

### 2. Update Cloudflare DNS

In Cloudflare Dashboard → DNS → Edit the A record for `@` and `www` with the new IP.

### 3. Update `.env` and Rebuild Frontend

```bash
ssh merit@<NEW_IP>
cd ~/kiaa/ai-adoption
cat > .env << EOF
SITE_DOMAIN=ai-adoption.uk
NEXT_PUBLIC_GRAPHQL_URL=https://ai-adoption.uk/graphql
LLM_MODEL=qwen2.5:1.5b
EOF
docker compose --profile web up -d --build
```

### Reserve a Static IP (Optional, ~$4/mo)

To avoid updating DNS on every restart:

```bash
gcloud compute addresses create agent-platform-ip \
  --project=ai-adoption-492510 --region=us-central1

gcloud compute instances delete-access-config ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a \
  --access-config-name="External NAT"

gcloud compute instances add-access-config ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a \
  --address=<STATIC_IP>
```

---

## Troubleshooting

### Site shows "too many redirects"

**Cause**: Cloudflare SSL mode is set to `Flexible`. Cloudflare sends HTTP to origin, Caddy redirects to HTTPS, Cloudflare sends HTTP again → infinite loop.

**Fix**: Set Cloudflare SSL/TLS mode to `Full`.

### Site shows Cloudflare 522 (Connection timed out)

**Cause**: VM is stopped, or Caddy is not running, or firewall blocks port 80/443.

**Fix**:
```bash
# Check VM is running
gcloud compute instances describe ai-agent-platform \
  --project=ai-adoption-492510 --zone=us-central1-a --format="value(status)"

# Check Caddy is running
ssh merit@34.121.112.167 "docker ps | grep caddy"

# Check firewall allows 80/443
gcloud compute firewall-rules list --project=ai-adoption-492510
```

### Site shows Cloudflare 521 (Web server is down)

**Cause**: Caddy is running but the upstream services (gateway/frontend) are down.

**Fix**:
```bash
ssh merit@34.121.112.167
docker ps                                    # Check container status
docker logs aiadopt-gateway --tail 20        # Check gateway logs
docker compose --profile web up -d           # Restart all services
```

### Let's Encrypt certificate errors in Caddy logs

**Cause**: ACME HTTP-01 challenge fails. Usually because Cloudflare caches the challenge response.

**Fix**: Temporarily set Cloudflare proxy to DNS-only (grey cloud) for the A record, restart Caddy, wait for cert, then re-enable proxy.

Or use Cloudflare's origin certificate instead:
1. Cloudflare Dashboard → SSL/TLS → Origin Server → Create Certificate
2. Save the cert and key to the VM
3. Configure Caddy to use the Cloudflare origin cert instead of Let's Encrypt

### "Failed to fetch" errors in chat UI

**Cause**: Frontend was built with wrong `NEXT_PUBLIC_GRAPHQL_URL`.

**Fix**:
```bash
ssh merit@34.121.112.167
cd ~/kiaa/ai-adoption
grep NEXT_PUBLIC .env                           # Verify URL
docker compose --profile web up -d --build      # Rebuild frontend
```
