# CI/CD Pipeline: Change & Release Management

Complete guide to the DevOps pipeline -- from code change to production deployment.

---

## Pipeline Overview

```
Developer                    GitHub                          GCP VM / K8s
────────                    ──────                          ─────────────

1. Create feature branch
   git checkout -b
   feature/my-change

2. Make changes + commit
   git push origin
   feature/my-change

3. Create Pull Request ──→  4. CI Triggers Automatically
                               ├─ Lint (ruff + eslint)
                               ├─ Type Check (mypy strict)
                               ├─ Python Tests (pytest + Postgres + Redis)
                               ├─ Frontend Tests (vitest)
                               └─ Security Scan (Trivy HIGH/CRITICAL)

                            5. CODEOWNERS assigns reviewers
                               Review + approve

                            6. All checks pass ✓
                               Review approved ✓

7. Merge to master ──────→  8. Deploy Workflow Triggers
                               ├─ CI runs again (quality gate)
                               ├─ UAT Approval (manual gate)
                               │     └─ Reviewer approves in Actions UI
                               └─ SSH Deploy ──────────────→ git pull
                                                              docker compose up
                                                              health checks ✓

                            9. Smoke Test
                               curl ai-adoption.uk/healthz ✓

                            ════════════════════════════════════

                            OPTIONAL: Tag a release
                            git tag v1.1.0 → release.yml
                            → Builds Docker images for all 6 services
                            → Pushes to GHCR (+ GCP/AWS/Azure registries)

                            K8s PATH (future, via Argo CD):
                            → Update image tags in infra/k8s/overlays/
                            → Argo CD auto-syncs to K8s cluster
                            → Rolling update with health probes
```

---

## Branch Strategy

**Primary branch:** `master` (protected, requires PRs)

**Branch naming conventions:**

| Prefix | Use Case | Example |
|--------|----------|---------|
| `feature/` | New functionality | `feature/add-cost-dashboard` |
| `fix/` | Bug fixes | `fix/graphql-timeout` |
| `docs/` | Documentation only | `docs/update-readme` |
| `infra/` | CI/CD, deployment, infrastructure | `infra/add-helm-chart` |

**No `develop` or `staging` branches.** Trunk-based development with short-lived
feature branches. UAT is handled via a manual approval gate in the deploy workflow.

---

## Two Deployment Paths

### Path 1: VM Deploy (Current -- ai-adoption.uk)

```
PR merged → deploy.yml → SSH to GCP VM → docker compose up
```

- **Where:** GCP VM `ai-agent-platform` (34.121.112.167)
- **How:** GitHub Actions SSHs into the VM, pulls code, rebuilds containers
- **Workflow:** `.github/workflows/deploy.yml`
- **Approval:** GitHub Environment `production` with required reviewers

### Path 2: K8s GitOps via Argo CD (Future)

```
PR merged → release.yml → Push images to GHCR → Update K8s manifests → Argo CD syncs
```

- **Where:** Kubernetes cluster (GKE/EKS/AKS)
- **How:** Argo CD watches `infra/k8s/overlays/prod/` for manifest changes
- **Config:** `infra/argocd/app-of-apps.yaml` (already configured)
- **Approval:** Argo CD sync policies + K8s admission controllers (OPA Gatekeeper)

Argo CD is fully configured with 8 applications (gateway, agent-engine, frontend,
cache-service, cost-tracker, document-service, mesh, observability). When a K8s
cluster is available, the same PR workflow triggers image builds, and Argo CD
handles the deployment automatically.

---

## GitHub Actions Workflows

### 1. CI (`ci.yml`) -- Runs on Every PR

| Job | What It Does | Tools |
|-----|-------------|-------|
| **Lint** | Python formatting + TypeScript linting | ruff, eslint |
| **Type Check** | Static type analysis | mypy (strict mode) |
| **Python Tests** | Unit + integration tests | pytest, Postgres, Redis |
| **Frontend Tests** | Component + unit tests | vitest |
| **Security Scan** | Vulnerability scanning | Trivy (HIGH/CRITICAL) |

All 5 jobs must pass before a PR can be merged.

### 2. Deploy (`deploy.yml`) -- Runs on Merge to Master

| Stage | What It Does | Automated? |
|-------|-------------|------------|
| **CI Gate** | Re-runs all CI checks | Yes |
| **UAT Approval** | Manual approval in GitHub Actions | No (requires human) |
| **SSH Deploy** | Pulls code + rebuilds on GCP VM | Yes |
| **Health Check** | Verifies all services respond 200 | Yes |
| **Smoke Test** | Tests public URL (ai-adoption.uk) | Yes |
| **Rollback** | Auto-rollback if health checks fail | Yes |

### 3. Release (`release.yml`) -- Runs on Git Tags

Triggered by `git tag v*`. Builds Docker images for all 6 services and pushes to:
- GitHub Container Registry (GHCR) -- always
- GCP Artifact Registry -- if `GCP_PROJECT_ID` is set
- AWS ECR -- if `AWS_ACCOUNT_ID` is set
- Azure ACR -- if `AZURE_ACR_NAME` is set

### 4. Sync Repos (`sync-repos.yml`) -- Runs on Push to Master

Auto-syncs `trajeshbe/ai-adoption` → `merit-data-tech/ai-adoption`.

---

## Setup Guide

### 1. Generate SSH Deploy Key

```bash
# Generate a new ed25519 key pair
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""

# Add the public key to the GCP VM
ssh merit@34.121.112.167 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys" < deploy_key.pub

# Copy the private key content -- you'll paste this into GitHub
cat deploy_key
```

### 2. Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** in both repos.

**Secrets:**

| Name | Value | Required On |
|------|-------|-------------|
| `GCP_VM_SSH_KEY` | Contents of `deploy_key` (private key) | Both repos |
| `MERIT_REPO_TOKEN` | PAT with push access to merit-data-tech | trajeshbe only |

**Variables:**

| Name | Value | Required On |
|------|-------|-------------|
| `GCP_VM_HOST` | `34.121.112.167` | Both repos |

### 3. Create GitHub Environment

1. Go to **Settings → Environments → New environment**
2. Name: `production`
3. Enable **Required reviewers** -- add the repo owner(s)
4. Enable **Prevent self-review** (optional)
5. Set wait timer to `0`

This creates the manual approval gate in the deploy workflow.

### 4. Configure Branch Protection

Go to **Settings → Branches → Add branch protection rule**.

| Setting | Value |
|---------|-------|
| Branch name pattern | `master` |
| Require a pull request before merging | **Yes** |
| Required approvals | **1** |
| Dismiss stale approvals on new pushes | **Yes** |
| Require status checks to pass | **Yes** |
| Required checks | `Lint`, `Type Check`, `Python Tests`, `Frontend Tests`, `Security Scan` |
| Require branches to be up to date | **Yes** |
| Require conversation resolution | **Yes** |
| Allow force pushes | **No** |
| Allow deletions | **No** |

---

## End-to-End Walkthrough: README Change → Production

### Step 1: Create Feature Branch

```bash
cd ~/kiaa/ai-adoption
git checkout master
git pull origin master
git checkout -b docs/add-readme
```

### Step 2: Make the Change

```bash
# Edit README.md (or any file)
vim README.md
```

### Step 3: Commit and Push

```bash
git add README.md
git commit -m "Add project README with setup and usage instructions"
git push origin docs/add-readme
```

### Step 4: Create Pull Request

```bash
gh pr create \
  --title "Add project README" \
  --body "## Summary
Adds README.md with project overview, quick start, and architecture.

## Type
- [x] Documentation

## Testing
- [x] Manual testing performed (verified markdown renders correctly)"
```

### Step 5: Watch CI Run

Go to the PR page on GitHub. Five CI jobs run automatically:

```
✓ Lint                  (30s)
✓ Type Check            (45s)
✓ Python Tests          (2m)
✓ Frontend Tests        (1m)
✓ Security Scan         (1m)
```

For a docs-only change, all pass quickly.

### Step 6: Code Review

CODEOWNERS auto-assigns reviewers based on file paths:
- `docs/` → `@platform-team`
- `services/gateway/` → `@api-team`
- `frontend/` → `@frontend-team`

Reviewer checks the changes and approves.

### Step 7: Merge

Click **"Squash and merge"** (recommended for clean commit history).

### Step 8: Deploy Workflow

On merge to `master`, the deploy workflow triggers automatically:

1. **CI Gate** -- all 5 checks run again
2. **UAT Approval** -- workflow pauses, shows yellow "Waiting" status
3. Go to **Actions → Deploy → Review deployments**
4. Select `production` environment → click **"Approve and deploy"**
5. **SSH Deploy** executes on the GCP VM:
   - `git pull origin master`
   - `docker compose --profile web up -d --build`
   - Health checks on all services
6. **Smoke Test** verifies `https://ai-adoption.uk` responds

### Step 9: Verify

Open `https://ai-adoption.uk` in your browser. The change is live.

### Step 10: Optional Release Tag

```bash
git checkout master
git pull origin master
git tag -a v1.1.0 -m "v1.1.0: Add project README"
git push origin v1.1.0
```

This triggers `release.yml` which builds Docker images and pushes to GHCR.

---

## Argo CD GitOps Path (K8s)

When the platform runs on Kubernetes instead of Docker Compose, the deployment
path changes but the PR workflow stays the same.

### How Argo CD Works

```
infra/argocd/
├── app-of-apps.yaml          # Root application (syncs child apps)
├── projects/
│   └── agent-platform.yaml   # AppProject (permissions)
└── apps/
    ├── gateway.yaml           # Watches infra/k8s/overlays/prod/
    ├── agent-engine.yaml
    ├── frontend.yaml
    ├── cache-service.yaml
    ├── cost-tracker.yaml
    ├── document-service.yaml
    ├── mesh.yaml
    └── observability.yaml
```

Each app has `syncPolicy.automated` with `prune: true` and `selfHeal: true`.
This means Argo CD automatically:
- **Detects** when K8s manifests change in git
- **Applies** the changes to the cluster
- **Prunes** resources that were removed from git
- **Self-heals** if someone manually changes a resource

### K8s Deployment Flow

1. PR merged → `release.yml` builds Docker images → pushes to GHCR
2. Developer updates image tags in `infra/k8s/overlays/prod/kustomization.yaml`:
   ```yaml
   images:
     - name: gateway
       newTag: "1.2.0"   # ← Update this
   ```
3. Commit and push the manifest change
4. Argo CD detects the change within 3 minutes (default polling interval)
5. Argo CD performs a rolling update:
   - Creates new pods with the new image
   - Waits for readiness probes to pass
   - Terminates old pods
   - Respects PodDisruptionBudgets (min 2 available in prod)
6. If the new pods fail health checks, the rollout stalls (no manual rollback needed)

### Argo CD vs SSH Deploy

| | SSH Deploy (VM) | Argo CD (K8s) |
|---|----------------|---------------|
| **Trigger** | Push to master | Manifest change in git |
| **Mechanism** | `docker compose up` | Kubernetes rolling update |
| **Rollback** | `git reset --hard` + rebuild | `argocd app rollback` or revert git commit |
| **Health checks** | curl /healthz | K8s liveness/readiness probes |
| **Scaling** | Manual | HPA auto-scaling (1-10 replicas) |
| **Zero downtime** | No (containers restart) | Yes (rolling update) |

---

## Emergency Procedures

### Rollback a Bad Deployment

```bash
# SSH into the VM
ssh merit@34.121.112.167
cd ~/kiaa/ai-adoption

# Check recent commits
git log --oneline -10

# Reset to a known good commit
git reset --hard <good-commit-sha>
docker compose --profile web up -d --build

# Verify
curl http://localhost:8050/healthz
```

### Emergency Deploy (Skip UAT)

Use `workflow_dispatch` with `skip_uat: true`:

1. Go to **Actions → Deploy → Run workflow**
2. Check **"Skip UAT approval"**
3. Click **"Run workflow"**

Or via CLI:
```bash
gh workflow run deploy.yml --field skip_uat=true
```

### Bypass Branch Protection (Admin Only)

Admins can push directly to `master` in emergencies:
```bash
git push origin master    # Only works for repo admins
```

This still triggers the deploy workflow with the UAT gate.

---

## Troubleshooting

### CI Fails: "ruff check" Errors

```bash
# Fix locally
uv run ruff check services/ libs/py-common/ --fix
uv run ruff format services/ libs/py-common/
git add -A && git commit -m "Fix lint errors" && git push
```

### CI Fails: "mypy" Type Errors

```bash
uv run mypy services/ libs/py-common/ --strict --ignore-missing-imports
# Fix the type annotations, commit, push
```

### Deploy Fails: SSH Connection Refused

- VM may be stopped: `gcloud compute instances start ai-agent-platform --project=ai-adoption-492510 --zone=us-central1-a`
- SSH key not configured: verify `GCP_VM_SSH_KEY` secret contains the correct private key
- VM IP changed: update `GCP_VM_HOST` variable in GitHub

### Deploy Fails: Health Check Failure

The deploy workflow auto-rolls back on health check failure. Check logs:

```bash
ssh merit@34.121.112.167
docker logs aiadopt-gateway --tail 30
docker logs aiadopt-agent-engine --tail 30
docker compose --profile web up -d    # Manual restart
```

### Smoke Test Warns: Non-200 Status

If the VM deploy succeeded but the public URL returns non-200:
- **Cloudflare 522**: VM firewall blocks ports 80/443
- **Cloudflare 521**: Caddy not running (`docker restart aiadopt-caddy`)
- **Redirect loop**: Cloudflare SSL mode must be `Full` (not `Flexible`)

### Sync Fails: Permission Denied to merit-data-tech

- `MERIT_REPO_TOKEN` secret is missing or expired
- Generate a new PAT at https://github.com/settings/tokens with `repo` scope
- Update the secret in trajeshbe/ai-adoption Settings

---

## Adding New Services to the Pipeline

The pipeline automatically handles new services. When you add a new microservice:

1. Create the service in `services/<name>/` with Dockerfile
2. Add it to `docker-compose.yml`
3. Add it to the `release.yml` matrix:
   ```yaml
   strategy:
     matrix:
       service: [gateway, agent-engine, ..., new-service]
   ```
4. Add CODEOWNERS entry: `services/<name>/ @responsible-team`
5. If deploying to K8s, create Kustomize manifests and Argo CD app

No changes needed to `deploy.yml` -- Docker Compose handles new services automatically.

---

## Cost of the Pipeline

| Component | Cost |
|-----------|------|
| GitHub Actions (CI) | Free (2,000 mins/month on free tier) |
| GitHub Actions (Deploy) | Free (< 5 mins per deploy) |
| GCP VM (running) | ~$49/month |
| GCP VM (stopped) | ~$1/month |
| Cloudflare (domain + CDN) | ~$5/year |
| **Total (running)** | **~$50/month** |
