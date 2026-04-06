# Cloud Deployment -- Terraform

Infrastructure as Code for deploying the AI Agent Platform on GCP, Azure, and AWS.

## Architecture

Each cloud has two deployment tiers:

| Tier | What | Cost Range |
|------|------|-----------|
| **Simple** | Single VM + Docker Compose + Caddy (auto-HTTPS) | $210-276/mo |
| **Production** | Managed K8s + Managed Postgres + Object Storage + GitOps | $480-700/mo |

## Quick Start (Simple Tier)

Pick a cloud, copy the tfvars example, and apply:

```bash
# GCP
cd environments/gcp-simple
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project ID, domain, SSH key
terraform init && terraform apply

# AWS
cd environments/aws-simple
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply

# Azure
cd environments/azure-simple
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
```

After apply, point your DNS A record to the output `public_ip`. The VM auto-provisions with Docker Compose and Caddy handles HTTPS via Let's Encrypt.

## Production Tier

```bash
# GCP (GKE + Cloud SQL + GCS)
cd environments/gcp-prod
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply

# AWS (EKS + RDS + S3)
cd environments/aws-prod
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply

# Azure (AKS + PostgreSQL Flexible + Blob)
cd environments/azure-prod
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
```

Production tier provisions:
1. Managed Kubernetes cluster
2. Managed PostgreSQL with pgvector extension
3. Object storage (replaces MinIO)
4. Container registry
5. Shared K8s infrastructure (Redis Stack, Istio, Contour, cert-manager, OTEL, Grafana, Argo CD)

## Module Structure

```
modules/
  gcp-simple/     Compute Engine VM + firewall + static IP
  gcp-prod/       GKE Autopilot + Cloud SQL + GCS + Artifact Registry
  aws-simple/     EC2 + VPC + security group + EIP
  aws-prod/       EKS + VPC + RDS + S3 + ECR
  azure-simple/   VM + VNet + NSG + public IP
  azure-prod/     AKS + PostgreSQL Flexible + Blob + ACR
  common-k8s/     Helm releases for shared K8s infrastructure

environments/
  {cloud}-{tier}/ Per-deployment tfvars and backend config
```

## Key Decisions

- **Redis Stack must be self-hosted** -- no managed Redis on any cloud supports RediSearch + ReJSON modules
- **PostgreSQL pgvector** is natively supported on Cloud SQL, RDS, and Azure PostgreSQL Flexible
- **MinIO** is replaced by cloud-native object storage (GCS, S3, Azure Blob) in production
- **Caddy** provides zero-config HTTPS for simple tier via Let's Encrypt
- **cert-manager** provides TLS for production tier via Let's Encrypt

## CI/CD Integration

The GitHub Actions release workflow (`.github/workflows/release.yml`) pushes images to all configured registries. Set these repository variables/secrets:

| Variable/Secret | Purpose |
|----------------|---------|
| `GCP_PROJECT_ID` | GCP project (enables GCP push) |
| `GCP_REGION` | Artifact Registry region (default: us-central1) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | OIDC provider for GCP auth |
| `GCP_SERVICE_ACCOUNT` | GCP service account email |
| `AWS_ACCOUNT_ID` | AWS account (enables ECR push) |
| `AWS_REGION` | ECR region (default: us-east-1) |
| `AWS_ROLE_ARN` | IAM role ARN for OIDC federation |
| `AZURE_ACR_NAME` | ACR name (enables Azure push) |
| `AZURE_ACR_USERNAME` | ACR admin username |
| `AZURE_ACR_PASSWORD` | ACR admin password |

## Cost Comparison

| Component | GCP Simple | AWS Simple | Azure Simple |
|-----------|-----------|-----------|-------------|
| VM | $195/mo | $243/mo | $252/mo |
| Disk | $10/mo | $8/mo | $19/mo |
| Static IP | $5/mo | $4/mo | $4/mo |
| **Total** | **~$210** | **~$256** | **~$276** |

| Component | GCP Prod | AWS Prod | Azure Prod |
|-----------|---------|---------|-----------|
| K8s Control Plane | $73/mo | $73/mo | Free |
| Nodes (3x) | $290/mo | $415/mo | $420/mo |
| PostgreSQL | $95/mo | $98/mo | $48/mo |
| Object Storage | $1/mo | $1/mo | $1/mo |
| Load Balancer | $20/mo | $25/mo | $20/mo |
| **Total** | **~$480** | **~$612** | **~$495** |
