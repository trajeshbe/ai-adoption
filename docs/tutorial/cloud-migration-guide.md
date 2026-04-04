# Cloud Migration Guide: AI Agent Platform

> Deploy the entire AI Agent Platform to Google Cloud, Microsoft Azure, or AWS
> using a single `docker compose up` command. No Kubernetes required.

**Audience**: Fresh graduates and engineers new to cloud deployments.
**Time to complete**: 30-60 minutes per cloud provider.
**Last updated**: April 2026.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Architecture Overview](#2-architecture-overview)
3. [Google Cloud Platform (GCP) Deployment](#3-google-cloud-platform-gcp-deployment)
4. [Microsoft Azure Deployment](#4-microsoft-azure-deployment)
5. [CPU-Only Deployment (No GPU)](#5-cpu-only-deployment-no-gpu)
6. [AWS Deployment (Bonus)](#6-aws-deployment-bonus)
7. [Security Hardening for Cloud](#7-security-hardening-for-cloud)
8. [Scaling Options](#8-scaling-options)
9. [Monitoring and Maintenance](#9-monitoring-and-maintenance)
10. [Cost Estimation Table](#10-cost-estimation-table)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Prerequisites

Before you begin, make sure you have the following installed on your **local machine**
(the machine you will SSH from -- not the cloud VM itself):

### 1.1 Local Machine Requirements

| Tool          | Purpose                        | Install Guide                                |
|---------------|--------------------------------|----------------------------------------------|
| Git           | Clone the repository           | https://git-scm.com/downloads                |
| gcloud CLI    | Manage GCP resources           | https://cloud.google.com/sdk/docs/install    |
| az CLI        | Manage Azure resources         | https://learn.microsoft.com/cli/azure/install-azure-cli |
| aws CLI       | Manage AWS resources (optional)| https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html |
| SSH client    | Connect to cloud VMs           | Built into macOS/Linux; use PuTTY on Windows |

### 1.2 Cloud Account Requirements

- **GCP**: A Google Cloud account with billing enabled. Free tier credits ($300) work.
- **Azure**: An Azure account with an active subscription. Free tier credits ($200) work.
- **AWS** (optional): An AWS account with billing enabled. Free tier has limited GPU options.

### 1.3 What Gets Installed on the Cloud VM

The following will be installed on the cloud VM (not your local machine):

- Docker Engine 24+
- Docker Compose v2 (bundled with Docker Engine)
- NVIDIA Container Toolkit (GPU instances only)
- NVIDIA GPU drivers (GPU instances only)
- Git

### 1.4 Verify Your CLI Tools Locally

```bash
# Google Cloud
gcloud version
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Azure
az version
az login
az account set --subscription YOUR_SUBSCRIPTION_ID

# AWS (optional)
aws --version
aws configure
```

---

## 2. Architecture Overview

### 2.1 System Diagram

All 11 containers run on a single virtual machine. There is no Kubernetes, no
load balancer, and no multi-node cluster. This is the simplest possible
production deployment.

```
+------------------------------------------------------------------+
|                      Cloud VM (GCP / Azure / AWS)                |
|                                                                  |
|  +--------------------+    +---------------------+               |
|  |  Frontend (Next.js)|    |  Gateway (FastAPI)   |               |
|  |  :8055 -> 3000     |    |  :8050 -> 8000       |               |
|  +--------+-----------+    +---+--------+--------+               |
|           |                    |        |        |               |
|           |   +----------------+        |        |               |
|           |   |                         |        |               |
|  +--------v---v-------+  +-------------v--+ +---v-----------+   |
|  | Agent Engine       |  | Document Svc   | | Cache Service |   |
|  | :8053 -> 8003      |  | :8051 -> 8001  | | :8052 -> 8002 |   |
|  +--------+-----------+  +-------+--------+ +-------+-------+   |
|           |                      |                  |            |
|           |              +-------v--------+ +-------v-------+   |
|  +--------v-----------+ | Postgres        | | Redis         |   |
|  | Ollama (LLM)       | | (pgvector:pg16) | | (redis-stack) |   |
|  | :11434             | | :5432           | | :6379         |   |
|  | [GPU accelerated]  | +---------+-------+ +---------------+   |
|  +--------------------+           |                              |
|                          +--------v--------+                     |
|  +--------------------+  | MinIO (S3)      |  +--------------+  |
|  | Cost Tracker       |  | :9000 API       |  | ollama-init  |  |
|  | :8054 -> 8004      |  | :9001 UI        |  | (pulls model)|  |
|  +--------------------+  +-----------------+  +--------------+  |
|                                                                  |
|  [=== Docker Bridge Network: aiadopt-net ===]                    |
+------------------------------------------------------------------+
         |
    External Access:
      - :8055  Frontend UI
      - :8050  GraphQL API
```

### 2.2 Container Inventory

| #  | Container          | Image                          | Host Port | Internal Port | Purpose                        |
|----|--------------------|--------------------------------|-----------|---------------|--------------------------------|
| 1  | aiadopt-postgres   | pgvector/pgvector:pg16         | 5432      | 5432          | SQL database + vector search   |
| 2  | aiadopt-redis      | redis/redis-stack:7.2.0-v10    | 6379      | 6379          | Caching + vector similarity    |
| 3  | aiadopt-minio      | minio/minio:latest             | 9000/9001 | 9000/9001     | S3-compatible object storage   |
| 4  | aiadopt-ollama     | ollama/ollama:0.11.0           | 11434     | 11434         | LLM inference engine           |
| 5  | aiadopt-ollama-init| ollama/ollama:0.11.0           | --        | --            | One-shot: pulls the LLM model  |
| 6  | aiadopt-gateway    | Built from services/gateway    | 8050      | 8000          | GraphQL API gateway            |
| 7  | aiadopt-agent-engine| Built from services/agent-engine| 8053     | 8003          | LLM agent orchestration        |
| 8  | aiadopt-document-service | Built from services/document-service | 8051 | 8001   | RAG document pipeline          |
| 9  | aiadopt-cache-service | Built from services/cache-service | 8052  | 8002          | Semantic caching layer         |
| 10 | aiadopt-cost-tracker| Built from services/cost-tracker| 8054     | 8004          | Per-inference cost tracking    |
| 11 | aiadopt-frontend   | Built from frontend/           | 8055      | 3000          | Next.js web UI                 |

### 2.3 Docker Volumes (Persistent Data)

| Volume          | Mounted In       | Contains                           |
|-----------------|------------------|------------------------------------|
| postgres-data   | postgres         | All SQL data, vector indexes       |
| redis-data      | redis            | Cache entries, vector similarity   |
| minio-data      | minio            | Uploaded documents (S3 objects)    |
| ollama-models   | ollama           | Downloaded LLM model weights       |

### 2.4 GPU vs CPU Trade-offs

| Aspect              | GPU Instance               | CPU Instance              |
|---------------------|----------------------------|---------------------------|
| LLM response time   | 0.5-2 seconds              | 5-15 seconds              |
| Monthly cost         | $380-900/month             | $100-140/month            |
| Model size supported | Up to 8B parameters        | Up to 1.5B recommended   |
| Best for             | Production, demos, multi-user | Development, testing, single-user |
| Setup complexity     | Higher (driver install)    | Lower (just Docker)      |

---

## 3. Google Cloud Platform (GCP) Deployment

This section walks through deploying the platform on a GCP Compute Engine VM,
step by step.

### 3.1 Choose Your Instance Type

| Use Case       | Machine Type      | GPU     | vCPUs | RAM  | Monthly Cost |
|----------------|-------------------|---------|-------|------|-------------|
| Development    | e2-standard-4     | None    | 4     | 16GB | ~$100       |
| Production     | n1-standard-8     | T4 x1   | 8     | 30GB | ~$500       |
| Heavy workload | n1-standard-16    | T4 x1   | 16    | 60GB | ~$700       |

### 3.2 Create a GPU VM

> If you want a CPU-only VM, skip to [Section 5](#5-cpu-only-deployment-no-gpu)
> and come back here using `e2-standard-4` without the `--accelerator` flag.

```bash
# Set variables -- change these for your deployment
export GCP_PROJECT="your-gcp-project-id"
export GCP_ZONE="us-central1-a"
export VM_NAME="ai-agent-platform"

# Authenticate and set project
gcloud auth login
gcloud config set project $GCP_PROJECT

# Create the GPU VM
gcloud compute instances create $VM_NAME \
  --project=$GCP_PROJECT \
  --zone=$GCP_ZONE \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --maintenance-policy=TERMINATE \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-ssd \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --metadata=install-nvidia-driver=True \
  --tags=ai-platform
```

**What each flag does**:
- `--machine-type=n1-standard-8`: 8 vCPUs, 30GB RAM. Enough for all 11 containers.
- `--accelerator=type=nvidia-tesla-t4,count=1`: Attaches one NVIDIA T4 GPU.
- `--maintenance-policy=TERMINATE`: Required for GPU instances (they cannot live-migrate).
- `--boot-disk-size=100GB`: Docker images + LLM model weights need space.
- `--boot-disk-type=pd-ssd`: SSD for faster Docker builds and database I/O.
- `--metadata=install-nvidia-driver=True`: Auto-installs NVIDIA drivers on first boot.

### 3.3 Reserve a Static External IP

By default, GCP gives you an ephemeral IP that changes when the VM restarts.
Reserve a static IP so your frontend URL stays the same.

```bash
# Reserve a static IP
gcloud compute addresses create ai-platform-ip \
  --project=$GCP_PROJECT \
  --region=us-central1

# Get the reserved IP address
gcloud compute addresses describe ai-platform-ip \
  --project=$GCP_PROJECT \
  --region=us-central1 \
  --format="get(address)"

# Assign it to your VM
gcloud compute instances delete-access-config $VM_NAME \
  --project=$GCP_PROJECT \
  --zone=$GCP_ZONE \
  --access-config-name="External NAT"

gcloud compute instances add-access-config $VM_NAME \
  --project=$GCP_PROJECT \
  --zone=$GCP_ZONE \
  --access-config-name="External NAT" \
  --address=$(gcloud compute addresses describe ai-platform-ip \
    --project=$GCP_PROJECT \
    --region=us-central1 \
    --format="get(address)")
```

Save the IP address -- you will need it for the `.env` file:

```bash
export EXTERNAL_IP=$(gcloud compute addresses describe ai-platform-ip \
  --project=$GCP_PROJECT \
  --region=us-central1 \
  --format="get(address)")
echo "Your static IP: $EXTERNAL_IP"
```

### 3.4 Open Firewall Ports

```bash
# Allow frontend (8055) and API (8050) from anywhere
gcloud compute firewall-rules create allow-ai-platform \
  --project=$GCP_PROJECT \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --action=ALLOW \
  --rules=tcp:8050,tcp:8055 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=ai-platform \
  --description="Allow AI Agent Platform frontend and API"
```

> **Security note**: `0.0.0.0/0` means "allow from anywhere". For production,
> restrict to your office IP or VPN range. See [Section 7](#7-security-hardening-for-cloud).

### 3.5 SSH into the VM

```bash
gcloud compute ssh $VM_NAME \
  --project=$GCP_PROJECT \
  --zone=$GCP_ZONE
```

### 3.6 Install Docker on the VM

Run these commands **inside the VM** (after SSH):

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker using the official convenience script
curl -fsSL https://get.docker.com | sudo sh

# Add your user to the docker group (avoids needing sudo for docker commands)
sudo usermod -aG docker $USER

# Apply group changes (or log out and back in)
newgrp docker

# Verify Docker is working
docker --version
docker compose version
```

### 3.7 Install NVIDIA Container Toolkit (GPU Only)

Skip this step if you are using a CPU-only instance.

```bash
# Add the NVIDIA Container Toolkit repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify GPU is visible to Docker
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

You should see output showing your T4 GPU with driver version and CUDA version.
If you see an error, the NVIDIA drivers may still be installing (can take 5-10
minutes after VM creation). Wait and try again.

### 3.8 Clone the Repository

```bash
cd ~
git clone https://github.com/YOUR_ORG/ai-agent-platform.git
cd ai-agent-platform
```

### 3.9 Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file
nano .env
```

**Critical change**: Set `NEXT_PUBLIC_GRAPHQL_URL` to your VM's external IP.
This variable is baked into the frontend at **build time**, so it must be set
before running `docker compose build`.

```bash
# Replace the NEXT_PUBLIC_GRAPHQL_URL line with your external IP
# If your external IP is 35.202.100.50, the line should be:
NEXT_PUBLIC_GRAPHQL_URL=http://35.202.100.50:8050/graphql
```

Also update the security credentials:

```bash
# Generate a strong JWT secret
JWT_SECRET=$(openssl rand -hex 32)

# Set strong MinIO credentials
MINIO_ROOT_USER=minio-admin-$(openssl rand -hex 4)
MINIO_ROOT_PASSWORD=$(openssl rand -hex 16)
```

Your final `.env` file should look like this:

```dotenv
# .env -- Production settings for GCP deployment
LLM_MODEL=qwen2.5:1.5b
NEXT_PUBLIC_GRAPHQL_URL=http://35.202.100.50:8050/graphql

FRONTEND_PORT=8055
GATEWAY_PORT=8050
AGENT_ENGINE_PORT=8053
DOC_SERVICE_PORT=8051
CACHE_SERVICE_PORT=8052
COST_TRACKER_PORT=8054
POSTGRES_PORT=5432
REDIS_PORT=6379
REDIS_UI_PORT=8001
MINIO_API_PORT=9000
MINIO_UI_PORT=9001
OLLAMA_PORT=11434

JWT_SECRET=a1b2c3d4e5f6...your-generated-secret...
MINIO_ROOT_USER=minio-admin-abc123
MINIO_ROOT_PASSWORD=your-generated-password

DEBUG=false
```

### 3.10 Build and Start the Platform

```bash
# Build all images and start all containers in detached mode
docker compose up -d --build
```

This will:
1. Build 6 application images (gateway, agent-engine, document-service, cache-service, cost-tracker, frontend)
2. Pull 4 infrastructure images (postgres, redis, minio, ollama)
3. Start all 11 containers
4. Pull the LLM model (qwen2.5:1.5b is ~1GB, takes 1-3 minutes)

**Expected time**: 5-15 minutes for the first build (depends on network speed).

Watch the logs to monitor progress:

```bash
# Watch all container logs (Ctrl+C to stop watching)
docker compose logs -f

# Watch just the model download progress
docker compose logs -f ollama-init
```

### 3.11 Verify the Deployment

```bash
# Check all containers are running
docker compose ps

# Expected output: all containers should show "running" or "healthy"
# ollama-init will show "exited (0)" -- that is normal (it is a one-shot task)

# Test the gateway health endpoint
curl http://localhost:8050/healthz

# Test from outside the VM (run this on your local machine)
curl http://35.202.100.50:8050/healthz
```

### 3.12 Access the Application

Open your browser and go to:

- **Frontend UI**: `http://<EXTERNAL_IP>:8055`
- **GraphQL Playground**: `http://<EXTERNAL_IP>:8050/graphql`
- **MinIO Console**: `http://<EXTERNAL_IP>:9001` (use your MINIO_ROOT_USER/PASSWORD)

### 3.13 Auto-Restart on Reboot (Startup Script)

If the VM restarts (maintenance, crash, etc.), Docker containers with
`restart: unless-stopped` will automatically restart. But the Docker daemon
itself needs to be enabled:

```bash
# Ensure Docker starts on boot
sudo systemctl enable docker

# Verify
sudo systemctl is-enabled docker
# Should output: enabled
```

To also handle the case where the VM is stopped and started (not just rebooted),
create a startup script:

```bash
# Create a startup script
sudo tee /etc/systemd/system/ai-platform.service << 'EOF'
[Unit]
Description=AI Agent Platform
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/$USER/ai-agent-platform
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Replace $USER with your actual username
sudo sed -i "s/\$USER/$(whoami)/g" /etc/systemd/system/ai-platform.service

# Enable the service
sudo systemctl daemon-reload
sudo systemctl enable ai-platform.service
```

### 3.14 Persistent Disk for Volumes

The default boot disk stores Docker volumes. For better durability, attach a
separate persistent disk:

```bash
# Run these on your LOCAL machine (not the VM)

# Create a 50GB SSD persistent disk
gcloud compute disks create ai-platform-data \
  --project=$GCP_PROJECT \
  --zone=$GCP_ZONE \
  --size=50GB \
  --type=pd-ssd

# Attach it to the VM
gcloud compute instances attach-disk $VM_NAME \
  --project=$GCP_PROJECT \
  --zone=$GCP_ZONE \
  --disk=ai-platform-data \
  --device-name=ai-platform-data
```

Then on the VM, format and mount the disk:

```bash
# SSH into the VM first, then:

# Find the disk (usually /dev/sdb)
lsblk

# Format it (only do this ONCE -- it erases all data)
sudo mkfs.ext4 -m 0 -E lazy_itable_init=0,lazy_journal_init=0,discard /dev/sdb

# Create mount point
sudo mkdir -p /mnt/ai-platform-data

# Mount it
sudo mount -o discard,defaults /dev/sdb /mnt/ai-platform-data

# Make it persist across reboots
echo UUID=$(sudo blkid -s UUID -o value /dev/sdb) /mnt/ai-platform-data ext4 discard,defaults,nofail 0 2 \
  | sudo tee -a /etc/fstab

# Move Docker data directory to the persistent disk
sudo systemctl stop docker
sudo mv /var/lib/docker /mnt/ai-platform-data/docker
sudo ln -s /mnt/ai-platform-data/docker /var/lib/docker
sudo systemctl start docker
```

---

## 4. Microsoft Azure Deployment

This section walks through deploying on an Azure Virtual Machine.

### 4.1 Choose Your Instance Type

| Use Case       | VM Size             | GPU     | vCPUs | RAM  | Monthly Cost |
|----------------|---------------------|---------|-------|------|-------------|
| Development    | Standard_D4s_v3     | None    | 4     | 16GB | ~$140       |
| Production     | Standard_NC6s_v3    | V100 x1 | 6     | 112GB| ~$900       |
| Budget GPU     | Standard_NC4as_T4_v3| T4 x1   | 4     | 28GB | ~$380       |

### 4.2 Create a Resource Group

```bash
# Set variables
export AZURE_RG="ai-agent-platform-rg"
export AZURE_LOCATION="eastus"
export VM_NAME="ai-agent-platform"

# Login
az login

# Create resource group
az group create \
  --name $AZURE_RG \
  --location $AZURE_LOCATION
```

### 4.3 Create a GPU VM

```bash
# Create the VM with a GPU
az vm create \
  --resource-group $AZURE_RG \
  --name $VM_NAME \
  --size Standard_NC4as_T4_v3 \
  --image Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest \
  --admin-username azureuser \
  --generate-ssh-keys \
  --os-disk-size-gb 100 \
  --storage-sku Premium_LRS \
  --public-ip-sku Standard \
  --output json
```

**What each flag does**:
- `--size Standard_NC4as_T4_v3`: 4 vCPUs, 28GB RAM, 1x NVIDIA T4 GPU.
- `--image`: Ubuntu 22.04 LTS, generation 2.
- `--generate-ssh-keys`: Creates SSH keys if you don't have them yet.
- `--os-disk-size-gb 100`: 100GB OS disk for Docker images and model weights.
- `--storage-sku Premium_LRS`: Premium SSD for better I/O performance.
- `--public-ip-sku Standard`: Static public IP (does not change on restart).

Save the public IP from the output:

```bash
# Get the public IP
export AZURE_IP=$(az vm show \
  --resource-group $AZURE_RG \
  --name $VM_NAME \
  --show-details \
  --query publicIps \
  --output tsv)
echo "Your Azure VM IP: $AZURE_IP"
```

### 4.4 Create a CPU-Only VM (Alternative)

If you do not need a GPU:

```bash
az vm create \
  --resource-group $AZURE_RG \
  --name $VM_NAME \
  --size Standard_D4s_v3 \
  --image Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest \
  --admin-username azureuser \
  --generate-ssh-keys \
  --os-disk-size-gb 100 \
  --storage-sku Premium_LRS \
  --public-ip-sku Standard
```

### 4.5 Open Network Security Group (NSG) Ports

Azure blocks all inbound traffic by default. Open the ports you need:

```bash
# Open frontend port (8055)
az vm open-port \
  --resource-group $AZURE_RG \
  --name $VM_NAME \
  --port 8055 \
  --priority 1010

# Open API port (8050)
az vm open-port \
  --resource-group $AZURE_RG \
  --name $VM_NAME \
  --port 8050 \
  --priority 1020
```

> **Security note**: These rules allow traffic from any source IP. For production,
> restrict the source:
>
> ```bash
> az network nsg rule create \
>   --resource-group $AZURE_RG \
>   --nsg-name ${VM_NAME}NSG \
>   --name AllowOfficeIP \
>   --priority 1010 \
>   --direction Inbound \
>   --access Allow \
>   --protocol Tcp \
>   --destination-port-ranges 8050 8055 \
>   --source-address-prefixes "YOUR_OFFICE_IP/32"
> ```

### 4.6 SSH into the VM

```bash
ssh azureuser@$AZURE_IP
```

### 4.7 Install Docker on the VM

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### 4.8 Install NVIDIA Drivers and Container Toolkit (GPU Only)

Azure NC-series VMs do not come with NVIDIA drivers pre-installed. Install them:

```bash
# Install NVIDIA drivers
sudo apt-get install -y linux-headers-$(uname -r)
sudo apt-get install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall

# Reboot to load the driver
sudo reboot
```

After rebooting, SSH back in and continue:

```bash
# Verify GPU is detected
nvidia-smi

# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify GPU is visible to Docker
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

### 4.9 Clone and Configure

```bash
cd ~
git clone https://github.com/YOUR_ORG/ai-agent-platform.git
cd ai-agent-platform

# Copy and edit environment file
cp .env.example .env
nano .env
```

Set the following in `.env`:

```dotenv
NEXT_PUBLIC_GRAPHQL_URL=http://<YOUR_AZURE_IP>:8050/graphql
JWT_SECRET=<generate-with-openssl-rand--hex-32>
MINIO_ROOT_USER=minio-admin-<random>
MINIO_ROOT_PASSWORD=<generate-with-openssl-rand--hex-16>
```

### 4.10 Build and Start

```bash
docker compose up -d --build
```

### 4.11 Verify

```bash
# Check container status
docker compose ps

# Test health endpoint
curl http://localhost:8050/healthz

# From your local machine
curl http://$AZURE_IP:8050/healthz
```

### 4.12 Access the Application

- **Frontend UI**: `http://<AZURE_IP>:8055`
- **GraphQL Playground**: `http://<AZURE_IP>:8050/graphql`

### 4.13 Configure DNS with Azure DNS Zones (Optional)

Instead of accessing via IP address, set up a domain name:

```bash
# Create a DNS zone (you must own the domain)
az network dns zone create \
  --resource-group $AZURE_RG \
  --name ai-platform.yourdomain.com

# Create an A record pointing to your VM
az network dns record-set a add-record \
  --resource-group $AZURE_RG \
  --zone-name ai-platform.yourdomain.com \
  --record-set-name @ \
  --ipv4-address $AZURE_IP

# Create a CNAME for www
az network dns record-set cname set-record \
  --resource-group $AZURE_RG \
  --zone-name ai-platform.yourdomain.com \
  --record-set-name www \
  --cname ai-platform.yourdomain.com
```

Then update the nameservers at your domain registrar to point to the Azure DNS
zone nameservers:

```bash
az network dns zone show \
  --resource-group $AZURE_RG \
  --name ai-platform.yourdomain.com \
  --query nameServers \
  --output tsv
```

### 4.14 Managed Disks for Persistence

Azure VM disks persist across reboots by default. To add a dedicated data disk:

```bash
# Create and attach a 64GB Premium SSD
az vm disk attach \
  --resource-group $AZURE_RG \
  --vm-name $VM_NAME \
  --name ai-platform-data-disk \
  --size-gb 64 \
  --sku Premium_LRS \
  --new
```

On the VM, format and mount:

```bash
# Find the disk
lsblk

# Format (only once)
sudo mkfs.ext4 /dev/sdc

# Mount
sudo mkdir -p /mnt/ai-platform-data
sudo mount /dev/sdc /mnt/ai-platform-data

# Persist across reboots
echo "/dev/sdc /mnt/ai-platform-data ext4 defaults,nofail 0 2" \
  | sudo tee -a /etc/fstab

# Move Docker data
sudo systemctl stop docker
sudo mv /var/lib/docker /mnt/ai-platform-data/docker
sudo ln -s /mnt/ai-platform-data/docker /var/lib/docker
sudo systemctl start docker
```

### 4.15 Auto-Start on Boot

```bash
# Enable Docker
sudo systemctl enable docker

# Create systemd service (same as GCP section)
sudo tee /etc/systemd/system/ai-platform.service << 'EOF'
[Unit]
Description=AI Agent Platform
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/azureuser/ai-agent-platform
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=azureuser

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ai-platform.service
```

---

## 5. CPU-Only Deployment (No GPU)

If you want to save 70-80% on compute costs, deploy without a GPU. Ollama will
use CPU inference instead. This is perfectly fine for development, testing, and
low-traffic scenarios.

### 5.1 Create a docker-compose.override.yml

Instead of modifying the main `docker-compose.yml`, create an override file that
removes the GPU reservation:

```bash
cat > docker-compose.override.yml << 'EOF'
# Override: Remove GPU requirement for CPU-only deployment
services:
  ollama:
    deploy:
      resources:
        reservations: {}
EOF
```

Docker Compose automatically merges `docker-compose.yml` with
`docker-compose.override.yml`. The override replaces the GPU reservation with an
empty one, effectively removing the GPU requirement.

### 5.2 Alternative: Edit docker-compose.yml Directly

If you prefer to edit the main file:

```bash
# Open the file
nano docker-compose.yml
```

Find the `ollama` service and remove (or comment out) the `deploy` block:

```yaml
  ollama:
    container_name: aiadopt-ollama
    image: ollama/ollama:0.11.0
    restart: unless-stopped
    ports:
      - "${OLLAMA_PORT:-11434}:11434"
    volumes:
      - ollama-models:/root/.ollama
    # REMOVED: GPU reservation
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]
    networks:
      - app-net
```

### 5.3 Choose a Smaller Model

Large models (7B+ parameters) are painfully slow on CPU. Use smaller models:

| Model              | Parameters | CPU Speed (tokens/s) | RAM Needed | Quality      |
|--------------------|-----------|----------------------|------------|--------------|
| qwen2.5:0.5b       | 0.5B      | 15-25 t/s            | 1GB        | Basic        |
| qwen2.5:1.5b       | 1.5B      | 8-15 t/s             | 2GB        | Good (default) |
| phi3:mini (3.8B)    | 3.8B      | 3-6 t/s              | 4GB        | Better       |
| gemma2:2b           | 2B        | 6-12 t/s             | 3GB        | Good         |
| llama3.2:1b         | 1B        | 10-20 t/s            | 2GB        | Good         |

To change the model, edit `.env`:

```dotenv
# For faster CPU inference, use a smaller model
LLM_MODEL=qwen2.5:0.5b
```

Also update `ollama-init` to pull the right model. The init container reads from
the `OLLAMA_HOST` environment and runs `ollama pull qwen2.5:1.5b`. If you change
the model, update the entrypoint in `docker-compose.yml`:

```yaml
  ollama-init:
    entrypoint: >
      sh -c "sleep 5 && ollama pull qwen2.5:0.5b && echo 'Model ready!'"
```

### 5.4 Performance Expectations

With CPU-only deployment on a 4-vCPU, 16GB RAM instance:

| Operation                    | GPU (T4)     | CPU (4 vCPUs)  |
|------------------------------|-------------|----------------|
| First token latency          | 200-500ms   | 1-3 seconds    |
| Full response (100 tokens)   | 1-2 seconds | 5-15 seconds   |
| Concurrent users supported   | 5-10        | 1-2            |
| Model loading time           | 2-5 seconds | 5-15 seconds   |

### 5.5 Cost Savings

| Cloud | GPU Instance        | Cost/month | CPU Instance    | Cost/month | Savings |
|-------|---------------------|-----------|-----------------|-----------|---------|
| GCP   | n1-standard-8 + T4  | ~$500     | e2-standard-4   | ~$100     | 80%     |
| Azure | Standard_NC4as_T4_v3| ~$380     | Standard_D4s_v3 | ~$140     | 63%     |
| AWS   | g4dn.xlarge          | ~$380     | t3.xlarge       | ~$120     | 68%     |

---

## 6. AWS Deployment (Bonus)

This section provides a condensed guide for deploying on AWS EC2.

### 6.1 Choose Your Instance Type

| Use Case       | Instance Type   | GPU    | vCPUs | RAM  | Monthly Cost |
|----------------|-----------------|--------|-------|------|-------------|
| Development    | t3.xlarge       | None   | 4     | 16GB | ~$120       |
| Production     | g4dn.xlarge     | T4 x1  | 4     | 16GB | ~$380       |
| Heavy workload | p3.2xlarge      | V100 x1| 8     | 61GB | ~$2,200     |

### 6.2 Launch a GPU Instance

```bash
# Set variables
export AWS_REGION="us-east-1"
export KEY_NAME="ai-platform-key"
export SG_NAME="ai-platform-sg"

# Create a key pair (if you don't have one)
aws ec2 create-key-pair \
  --key-name $KEY_NAME \
  --query 'KeyMaterial' \
  --output text > ${KEY_NAME}.pem
chmod 400 ${KEY_NAME}.pem

# Create security group
export VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" \
  --output text)

export SG_ID=$(aws ec2 create-security-group \
  --group-name $SG_NAME \
  --description "AI Agent Platform" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text)

# Open SSH (22), Frontend (8055), API (8050)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8055 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8050 \
  --cidr 0.0.0.0/0

# Find the latest Ubuntu 22.04 AMI
export AMI_ID=$(aws ec2 describe-images \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
  --query "Images | sort_by(@, &CreationDate) | [-1].ImageId" \
  --output text)

# Launch the instance
export INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type g4dn.xlarge \
  --key-name $KEY_NAME \
  --security-group-ids $SG_ID \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ai-agent-platform}]' \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "Instance ID: $INSTANCE_ID"

# Wait for it to start
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Get the public IP
export AWS_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)
echo "Public IP: $AWS_IP"
```

### 6.3 Allocate an Elastic IP (Static IP)

```bash
# Allocate an Elastic IP
export ALLOC_ID=$(aws ec2 allocate-address \
  --domain vpc \
  --query 'AllocationId' \
  --output text)

# Associate it with your instance
aws ec2 associate-address \
  --instance-id $INSTANCE_ID \
  --allocation-id $ALLOC_ID

# Get the Elastic IP
export AWS_IP=$(aws ec2 describe-addresses \
  --allocation-ids $ALLOC_ID \
  --query 'Addresses[0].PublicIp' \
  --output text)
echo "Elastic IP: $AWS_IP"
```

### 6.4 SSH and Setup

```bash
# SSH in
ssh -i ${KEY_NAME}.pem ubuntu@$AWS_IP

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# For GPU instances: install NVIDIA drivers
sudo apt-get install -y linux-headers-$(uname -r)
sudo apt-get install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall
sudo reboot
```

After reboot:

```bash
ssh -i ${KEY_NAME}.pem ubuntu@$AWS_IP

# Install NVIDIA Container Toolkit (same as GCP/Azure sections)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

# Clone and configure
cd ~
git clone https://github.com/YOUR_ORG/ai-agent-platform.git
cd ai-agent-platform
cp .env.example .env
nano .env
# Set NEXT_PUBLIC_GRAPHQL_URL=http://<AWS_IP>:8050/graphql

# Launch
docker compose up -d --build
```

### 6.5 CPU-Only on AWS

For CPU-only, use `t3.xlarge` instead of `g4dn.xlarge` and follow
[Section 5](#5-cpu-only-deployment-no-gpu) to create the override file.

---

## 7. Security Hardening for Cloud

The default configuration is designed for ease of setup, not security. Before
exposing the platform to real users, apply these hardening steps.

### 7.1 Change All Default Passwords

The `.env.example` file has insecure defaults. Change every credential:

```bash
# Generate strong secrets
cat >> .env << EOF

# ---- PRODUCTION SECRETS (generated) ----
JWT_SECRET=$(openssl rand -hex 32)
MINIO_ROOT_USER=minio-$(openssl rand -hex 4)
MINIO_ROOT_PASSWORD=$(openssl rand -hex 16)
EOF
```

The Postgres password is hardcoded in `docker-compose.yml` as `agent_platform`.
To change it, set environment variables in your `.env`:

```dotenv
# Add to .env (then update docker-compose.yml to use these)
POSTGRES_USER=agent_platform
POSTGRES_PASSWORD=<strong-generated-password>
```

> **Important**: If you change the Postgres password, you must also update the
> `DATABASE_URL` in every service that connects to Postgres (gateway,
> agent-engine, document-service, cost-tracker). The cleanest way is to
> parameterize `DATABASE_URL` in docker-compose.yml.

### 7.2 Restrict Firewall Rules

Never leave ports open to `0.0.0.0/0` in production.

**GCP**:
```bash
# Delete the open rule
gcloud compute firewall-rules delete allow-ai-platform --project=$GCP_PROJECT

# Create a restricted rule (replace with your IP)
gcloud compute firewall-rules create allow-ai-platform-restricted \
  --project=$GCP_PROJECT \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --action=ALLOW \
  --rules=tcp:8050,tcp:8055 \
  --source-ranges="YOUR_OFFICE_IP/32" \
  --target-tags=ai-platform
```

**Azure**:
```bash
# Update the NSG rules with source IP restrictions
az network nsg rule update \
  --resource-group $AZURE_RG \
  --nsg-name ${VM_NAME}NSG \
  --name open-port-8055 \
  --source-address-prefixes "YOUR_OFFICE_IP/32"

az network nsg rule update \
  --resource-group $AZURE_RG \
  --nsg-name ${VM_NAME}NSG \
  --name open-port-8050 \
  --source-address-prefixes "YOUR_OFFICE_IP/32"
```

### 7.3 Enable HTTPS with Let's Encrypt and Nginx

Running on plain HTTP means all traffic (including any authentication tokens)
is sent in cleartext. Set up HTTPS:

```bash
# Install nginx and certbot on the VM
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Create nginx config
sudo tee /etc/nginx/sites-available/ai-platform << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8055;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /graphql {
        proxy_pass http://localhost:8050/graphql;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (for GraphQL subscriptions)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /healthz {
        proxy_pass http://localhost:8050/healthz;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/ai-platform /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com --non-interactive --agree-tos -m your@email.com
```

After HTTPS is set up, update your `.env` to use the HTTPS URL:

```dotenv
NEXT_PUBLIC_GRAPHQL_URL=https://your-domain.com/graphql
```

Then rebuild the frontend:

```bash
docker compose build frontend
docker compose up -d frontend
```

Now close the direct ports (8050, 8055) and only allow 80/443 through the
firewall.

### 7.4 Use Cloud-Managed Databases (Advanced)

For production workloads, consider replacing containerized Postgres and Redis
with managed services:

| Container     | GCP Managed Alternative       | Azure Managed Alternative           |
|---------------|-------------------------------|-------------------------------------|
| Postgres      | Cloud SQL for PostgreSQL      | Azure Database for PostgreSQL       |
| Redis         | Memorystore for Redis         | Azure Cache for Redis               |
| MinIO         | Cloud Storage (GCS)           | Azure Blob Storage                  |

**Why managed databases are better for production**:
- Automatic backups and point-in-time recovery
- High availability with replicas
- Automatic patching and updates
- Monitoring and alerting built in
- No risk of data loss when VM is deleted

To switch to Cloud SQL (GCP example):

```bash
# Create a Cloud SQL instance
gcloud sql instances create ai-platform-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=YOUR_STRONG_PASSWORD

# Create the database
gcloud sql databases create agent_platform \
  --instance=ai-platform-db
```

Then update the `DATABASE_URL` in your `.env` or docker-compose.yml to point to
the Cloud SQL instance instead of the containerized Postgres.

### 7.5 Use Cloud IAM

Instead of managing credentials in `.env` files:

- **GCP**: Use a Service Account with minimal permissions. Attach it to the VM.
- **Azure**: Use Managed Identity. Enable it on the VM.

This eliminates the need to store cloud credentials on the VM.

---

## 8. Scaling Options

### 8.1 Vertical Scaling (Bigger VM)

The simplest scaling approach: stop the VM, resize it, start it again.

**GCP**:
```bash
# Stop the VM
gcloud compute instances stop $VM_NAME \
  --project=$GCP_PROJECT \
  --zone=$GCP_ZONE

# Resize to a bigger machine type
gcloud compute instances set-machine-type $VM_NAME \
  --project=$GCP_PROJECT \
  --zone=$GCP_ZONE \
  --machine-type=n1-standard-16

# Start the VM
gcloud compute instances start $VM_NAME \
  --project=$GCP_PROJECT \
  --zone=$GCP_ZONE
```

**Azure**:
```bash
# Resize (VM will be restarted automatically)
az vm resize \
  --resource-group $AZURE_RG \
  --name $VM_NAME \
  --size Standard_D8s_v3
```

### 8.2 Docker Compose Replicas

You can run multiple copies of a service using Docker Compose:

```bash
# Scale the agent-engine to 3 replicas
docker compose up -d --scale agent-engine=3
```

> **Important**: When using `--scale`, you must remove the `container_name`
> property from the service in `docker-compose.yml`, because Docker requires
> unique container names and replicas would conflict.

```yaml
# Before (single instance):
  agent-engine:
    container_name: aiadopt-agent-engine  # REMOVE this line for scaling
    build: ...

# After (scalable):
  agent-engine:
    # container_name removed
    build: ...
```

The gateway will automatically load-balance requests across replicas because
Docker's internal DNS resolves `agent-engine` to all running containers in
round-robin fashion.

### 8.3 When to Move from Compose to Kubernetes

Docker Compose on a single VM works well for:
- 1-10 concurrent users
- Development and staging environments
- Demos and proofs of concept
- Small team internal tools

Consider moving to Kubernetes when you need:
- **High availability**: If the VM goes down, everything goes down. K8s
  distributes across multiple nodes.
- **Auto-scaling**: K8s can add/remove pods based on CPU/memory/custom metrics.
- **Zero-downtime deployments**: K8s supports rolling updates out of the box.
- **Multi-region**: K8s can span regions for lower latency worldwide.
- **More than 20 concurrent users**: A single VM will bottleneck.

### 8.4 Cloud-Managed Kubernetes

If you decide to move to K8s, use a managed service:

| Cloud | Service       | Key Feature                    | Starting Cost |
|-------|---------------|--------------------------------|---------------|
| GCP   | GKE Autopilot | Fully managed, pay-per-pod     | ~$75/month    |
| Azure | AKS           | Free control plane             | ~$0 + nodes   |
| AWS   | EKS           | Broad ecosystem integration    | ~$75/month    |

The project already has Kubernetes manifests in `infra/k8s/` and Helm charts in
`infra/helm/` for this migration path. See the tutorial phases (Phase 7-8) for
detailed K8s deployment guides.

---

## 9. Monitoring and Maintenance

### 9.1 Checking Container Status

```bash
# See all containers with their status, ports, and health
docker compose ps

# Expected output:
# NAME                      STATUS           PORTS
# aiadopt-postgres          running (healthy) 0.0.0.0:5432->5432/tcp
# aiadopt-redis             running (healthy) 0.0.0.0:6379->6379/tcp
# aiadopt-minio             running          0.0.0.0:9000-9001->9000-9001/tcp
# aiadopt-ollama            running          0.0.0.0:11434->11434/tcp
# aiadopt-ollama-init       exited (0)
# aiadopt-gateway           running (healthy) 0.0.0.0:8050->8000/tcp
# aiadopt-agent-engine      running (healthy) 0.0.0.0:8053->8003/tcp
# aiadopt-document-service  running (healthy) 0.0.0.0:8051->8001/tcp
# aiadopt-cache-service     running (healthy) 0.0.0.0:8052->8002/tcp
# aiadopt-cost-tracker      running (healthy) 0.0.0.0:8054->8004/tcp
# aiadopt-frontend          running          0.0.0.0:8055->3000/tcp
```

### 9.2 Viewing Logs

```bash
# View logs from all containers (latest 100 lines)
docker compose logs --tail=100

# Follow logs in real time (Ctrl+C to stop)
docker compose logs -f

# View logs from a specific service
docker compose logs -f gateway
docker compose logs -f agent-engine
docker compose logs -f ollama

# View logs with timestamps
docker compose logs -f -t gateway

# View logs from the last 30 minutes
docker compose logs --since=30m gateway
```

### 9.3 Checking Resource Usage

```bash
# See CPU, memory, and network usage for all containers
docker stats

# One-time snapshot (not live)
docker stats --no-stream
```

### 9.4 Health Checks

Each application service exposes a `/healthz` endpoint:

```bash
# Check all services
for port in 8050 8051 8052 8053 8054; do
  echo -n "Port $port: "
  curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/healthz
  echo ""
done
```

Expected output:

```
Port 8050: 200
Port 8051: 200
Port 8052: 200
Port 8053: 200
Port 8054: 200
```

### 9.5 Volume Backup Strategy

Docker volumes contain all persistent data. Back them up regularly.

**Manual backup**:
```bash
# Create a backup directory
mkdir -p ~/backups

# Backup Postgres data
docker compose exec postgres pg_dump -U agent_platform agent_platform \
  | gzip > ~/backups/postgres-$(date +%Y%m%d-%H%M%S).sql.gz

# Backup all Docker volumes (stop services first for consistency)
docker compose stop

# Backup each volume
for vol in postgres-data redis-data minio-data ollama-models; do
  docker run --rm \
    -v ai-agent-platform_${vol}:/data \
    -v ~/backups:/backup \
    alpine tar czf /backup/${vol}-$(date +%Y%m%d).tar.gz -C /data .
done

# Start services again
docker compose start
```

**Automated daily backup with cron**:
```bash
# Create the backup script
cat > ~/backup-ai-platform.sh << 'SCRIPT'
#!/bin/bash
set -e
BACKUP_DIR=~/backups
mkdir -p $BACKUP_DIR

# Postgres logical backup (no downtime)
cd ~/ai-agent-platform
docker compose exec -T postgres pg_dump -U agent_platform agent_platform \
  | gzip > $BACKUP_DIR/postgres-$(date +%Y%m%d-%H%M%S).sql.gz

# Clean up backups older than 7 days
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed at $(date)"
SCRIPT

chmod +x ~/backup-ai-platform.sh

# Add to crontab (runs daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * ~/backup-ai-platform.sh >> ~/backups/backup.log 2>&1") | crontab -
```

**Upload backups to cloud storage**:

```bash
# GCP: Upload to Cloud Storage
gsutil cp ~/backups/postgres-*.gz gs://your-backup-bucket/ai-platform/

# Azure: Upload to Blob Storage
az storage blob upload-batch \
  --destination your-backup-container \
  --source ~/backups/ \
  --account-name yourstorageaccount

# AWS: Upload to S3
aws s3 sync ~/backups/ s3://your-backup-bucket/ai-platform/
```

### 9.6 Updating the Application

When new code is pushed to the repository:

```bash
cd ~/ai-agent-platform

# Pull the latest code
git pull origin main

# Rebuild and restart (only rebuilds changed services)
docker compose up -d --build

# Verify everything is healthy
docker compose ps
```

To update only a specific service (faster):

```bash
# Rebuild and restart just the gateway
docker compose build gateway
docker compose up -d gateway

# Rebuild and restart just the frontend
# (Remember: NEXT_PUBLIC_GRAPHQL_URL is baked in at build time)
docker compose build frontend
docker compose up -d frontend
```

### 9.7 Disk Space Management

Docker images and volumes can consume significant disk space over time:

```bash
# Check disk usage
df -h

# See Docker's disk usage breakdown
docker system df

# Clean up unused images, containers, and build cache
docker system prune -f

# Also remove unused volumes (WARNING: deletes data in unused volumes)
# docker system prune --volumes -f

# Remove dangling images only
docker image prune -f
```

---

## 10. Cost Estimation Table

All costs are approximate monthly estimates (as of early 2026) for running the
VM 24/7. Actual costs may vary by region and usage.

### 10.1 Compute Costs (VM Only)

| Cloud  | Instance Type          | GPU     | vCPUs | RAM   | Storage | Monthly Cost |
|--------|------------------------|---------|-------|-------|---------|-------------|
| GCP    | e2-standard-4          | None    | 4     | 16GB  | 100GB SSD| ~$100      |
| GCP    | n1-standard-8 + T4     | T4 x1   | 8     | 30GB  | 100GB SSD| ~$500      |
| GCP    | n1-standard-16 + T4    | T4 x1   | 16    | 60GB  | 100GB SSD| ~$700      |
| Azure  | Standard_D4s_v3        | None    | 4     | 16GB  | 100GB SSD| ~$140      |
| Azure  | Standard_NC4as_T4_v3   | T4 x1   | 4     | 28GB  | 100GB SSD| ~$380      |
| Azure  | Standard_NC6s_v3       | V100 x1 | 6     | 112GB | 100GB SSD| ~$900      |
| AWS    | t3.xlarge              | None    | 4     | 16GB  | 100GB gp3| ~$120      |
| AWS    | g4dn.xlarge            | T4 x1   | 4     | 16GB  | 100GB gp3| ~$380      |
| AWS    | p3.2xlarge             | V100 x1 | 8     | 61GB  | 100GB gp3| ~$2,200    |

### 10.2 Additional Costs

| Resource                  | GCP          | Azure        | AWS          |
|---------------------------|-------------|-------------|-------------|
| Static IP (while VM runs) | Free         | Free         | Free         |
| Static IP (VM stopped)    | ~$3/month    | ~$4/month    | ~$4/month    |
| Extra SSD disk (50GB)     | ~$8/month    | ~$8/month    | ~$4/month    |
| Egress (first 1GB)        | Free         | Free (5GB)   | Free         |
| Egress (per GB after free)| $0.12        | $0.087       | $0.09        |
| Cloud SQL (managed DB)    | ~$10/month   | ~$25/month   | ~$15/month   |
| DNS zone                  | ~$0.20/month | ~$0.50/month | ~$0.50/month |

### 10.3 Cost-Saving Tips

1. **Use preemptible/spot instances** for development (60-90% cheaper, but can
   be interrupted):
   ```bash
   # GCP: Add --preemptible flag
   gcloud compute instances create ... --preemptible

   # Azure: Add --priority Spot
   az vm create ... --priority Spot --eviction-policy Deallocate --max-price 0.15

   # AWS: Use spot instances
   aws ec2 run-instances ... --instance-market-options '{"MarketType":"spot","SpotOptions":{"MaxPrice":"0.15"}}'
   ```

2. **Stop the VM when not in use**:
   ```bash
   # GCP
   gcloud compute instances stop $VM_NAME --zone=$GCP_ZONE

   # Azure
   az vm deallocate --resource-group $AZURE_RG --name $VM_NAME

   # AWS
   aws ec2 stop-instances --instance-ids $INSTANCE_ID
   ```

3. **Use committed use discounts** (1-year or 3-year) for production workloads:
   - GCP: 20-57% savings
   - Azure: 20-72% savings (Reserved Instances)
   - AWS: 30-60% savings (Reserved or Savings Plans)

4. **Right-size your instance**: Start with CPU-only, move to GPU only when you
   need faster inference.

---

## 11. Troubleshooting

### 11.1 Container Won't Start

**Symptom**: `docker compose ps` shows a container as `restarting` or `exited`.

```bash
# Check the container's logs
docker compose logs gateway
# or whichever container is failing

# Common causes:
# - Port already in use: another process is using the port
# - Missing dependencies: a required service hasn't started yet
# - Configuration error: bad environment variable
```

**Fix for port conflicts**:
```bash
# Find what's using a port
sudo lsof -i :8050
# or
sudo ss -tlnp | grep 8050

# Kill the process using the port
sudo kill <PID>

# Or change the port in .env
GATEWAY_PORT=8060
```

### 11.2 GPU Not Detected

**Symptom**: Ollama starts but inference is very slow (CPU fallback).

```bash
# Check if the GPU is visible to the host
nvidia-smi

# If nvidia-smi fails:
# 1. Check if drivers are installed
dpkg -l | grep nvidia-driver

# 2. Check if NVIDIA Container Toolkit is installed
dpkg -l | grep nvidia-container-toolkit

# 3. Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

**Common fixes**:
```bash
# Reinstall NVIDIA drivers
sudo apt-get install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall
sudo reboot

# Reinstall Container Toolkit
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 11.3 Model Download Timeout

**Symptom**: `ollama-init` exits with an error, or the model never finishes
downloading.

```bash
# Check ollama-init logs
docker compose logs ollama-init

# If it timed out, manually pull the model
docker compose exec ollama ollama pull qwen2.5:1.5b

# If network is slow, use a smaller model
docker compose exec ollama ollama pull qwen2.5:0.5b
# Then update LLM_MODEL in .env
```

### 11.4 CORS Errors in Browser

**Symptom**: The frontend loads but cannot connect to the API. Browser console
shows CORS errors.

**Root cause**: `NEXT_PUBLIC_GRAPHQL_URL` was set incorrectly at build time.

```bash
# Check what URL the frontend was built with
docker compose exec frontend printenv | grep GRAPHQL
# This won't work because it's baked into the JS at build time

# The fix: rebuild the frontend with the correct URL
# 1. Make sure .env has the right URL:
#    NEXT_PUBLIC_GRAPHQL_URL=http://<YOUR_VM_IP>:8050/graphql
# 2. Rebuild:
docker compose build frontend
docker compose up -d frontend
```

**Common mistake**: Using `localhost` instead of the VM's external IP. The
frontend runs in the user's browser, which cannot reach `localhost` on the VM.

### 11.5 Services Cannot Reach Each Other

**Symptom**: Gateway returns 502 or connection refused when calling agent-engine.

```bash
# Check if all services are on the same network
docker network inspect aiadopt-net

# Test connectivity between containers
docker compose exec gateway ping agent-engine -c 3
docker compose exec gateway curl -s http://agent-engine:8003/healthz
```

### 11.6 Out of Disk Space

**Symptom**: Docker builds fail, or containers crash with disk errors.

```bash
# Check disk usage
df -h

# Check Docker's disk usage
docker system df

# Clean up
docker system prune -f
docker image prune -a -f   # Remove ALL unused images (not just dangling)

# If still low, resize the boot disk:
# GCP (VM must be stopped first):
gcloud compute disks resize $VM_NAME --size=200GB --zone=$GCP_ZONE

# Azure:
az vm deallocate --resource-group $AZURE_RG --name $VM_NAME
az disk update --resource-group $AZURE_RG --name ${VM_NAME}_OsDisk_1 --size-gb 200
az vm start --resource-group $AZURE_RG --name $VM_NAME
# Then on the VM:
sudo growpart /dev/sda 1
sudo resize2fs /dev/sda1
```

### 11.7 Out of Memory (OOM)

**Symptom**: Containers are killed unexpectedly. `dmesg` shows OOM killer messages.

```bash
# Check which container was killed
sudo dmesg | grep -i "oom\|killed"

# Check memory usage
docker stats --no-stream

# Solutions:
# 1. Use a bigger instance (more RAM)
# 2. Use a smaller model (qwen2.5:0.5b uses ~1GB, vs 1.5b uses ~2GB)
# 3. Reduce container memory by setting limits in docker-compose.yml:
#    services:
#      agent-engine:
#        deploy:
#          resources:
#            limits:
#              memory: 2G
```

### 11.8 Frontend Shows Blank Page

```bash
# Check frontend logs
docker compose logs frontend

# Check if the frontend container is running
docker compose ps frontend

# Common causes:
# 1. Build failed silently -- rebuild:
docker compose build --no-cache frontend
docker compose up -d frontend

# 2. Gateway not ready yet -- wait for health check:
curl http://localhost:8050/healthz
```

### 11.9 Rebuilding a Single Service

When you make changes to just one service, you do not need to rebuild everything:

```bash
# Rebuild and restart just the gateway
docker compose build gateway
docker compose up -d gateway

# Rebuild without cache (forces a clean build)
docker compose build --no-cache gateway
docker compose up -d gateway

# Rebuild and restart multiple specific services
docker compose build gateway agent-engine
docker compose up -d gateway agent-engine
```

### 11.10 Full Reset (Nuclear Option)

If everything is broken and you want to start fresh:

```bash
# Stop and remove all containers, networks, and volumes
docker compose down -v

# Remove all Docker images built by this project
docker compose down --rmi local

# Start from scratch
docker compose up -d --build
```

> **Warning**: `docker compose down -v` deletes all persistent data (database,
> cache, uploaded documents, downloaded models). The model will be re-downloaded
> on next start. Back up your data first if needed.

### 11.11 Quick Diagnostic Script

Copy and run this script to get a full status report:

```bash
#!/bin/bash
echo "========== AI Agent Platform Diagnostics =========="
echo ""
echo "--- Docker Version ---"
docker --version
docker compose version
echo ""
echo "--- Container Status ---"
docker compose ps
echo ""
echo "--- GPU Status ---"
nvidia-smi 2>/dev/null || echo "No GPU detected (CPU-only mode)"
echo ""
echo "--- Disk Usage ---"
df -h / | tail -1
echo ""
echo "--- Docker Disk Usage ---"
docker system df
echo ""
echo "--- Memory Usage ---"
free -h
echo ""
echo "--- Health Checks ---"
for port in 8050 8051 8052 8053 8054; do
  status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/healthz 2>/dev/null)
  echo "Port $port: $status"
done
echo ""
echo "--- Recent Errors (last 20 lines) ---"
docker compose logs --tail=20 2>&1 | grep -i "error\|exception\|fatal" || echo "No errors found"
echo ""
echo "==================================================="
```

---

## Quick Reference: Command Cheat Sheet

| Task                                | Command                                              |
|-------------------------------------|------------------------------------------------------|
| Start the platform                  | `docker compose up -d --build`                       |
| Stop the platform                   | `docker compose down`                                |
| Stop and delete all data            | `docker compose down -v`                             |
| View all logs                       | `docker compose logs -f`                             |
| View one service's logs             | `docker compose logs -f gateway`                     |
| Check container status              | `docker compose ps`                                  |
| Rebuild one service                 | `docker compose build gateway && docker compose up -d gateway` |
| Rebuild everything (clean)          | `docker compose build --no-cache`                    |
| Scale a service                     | `docker compose up -d --scale agent-engine=3`        |
| Check resource usage                | `docker stats`                                       |
| Pull a different LLM model          | `docker compose exec ollama ollama pull llama3.2:1b`  |
| List downloaded models              | `docker compose exec ollama ollama list`              |
| Backup Postgres                     | `docker compose exec postgres pg_dump -U agent_platform agent_platform > backup.sql` |
| SSH into a container                | `docker compose exec gateway bash`                   |
| Check health                        | `curl http://localhost:8050/healthz`                  |

---

## Next Steps

After deploying with Docker Compose, consider these improvements:

1. **Set up HTTPS** (Section 7.3) -- required for any public-facing deployment.
2. **Automate backups** (Section 9.5) -- do not rely on manual backups.
3. **Restrict firewall rules** (Section 7.2) -- never leave ports open to the internet.
4. **Set up monitoring** -- consider adding Prometheus + Grafana (see Phase 6 tutorial).
5. **Plan for Kubernetes** -- when you outgrow a single VM, see the K8s manifests in `infra/k8s/`.

For the full Kubernetes deployment with auto-scaling, service mesh, and GitOps,
follow Phases 7-10 of the tutorial.
