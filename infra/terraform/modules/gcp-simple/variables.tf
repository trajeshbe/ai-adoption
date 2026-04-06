# =============================================================================
# GCP Simple Deployment -- Variables
#
# Single Compute Engine VM running docker-compose for the AI Agent Platform.
# =============================================================================

variable "project" {
  description = "GCP project ID where resources will be created"
  type        = string
}

variable "region" {
  description = "GCP region for the Compute Engine instance"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone for the Compute Engine instance (must be within the selected region)"
  type        = string
  default     = "us-central1-a"
}

variable "machine_type" {
  description = "Compute Engine machine type (e2-standard-2 is the minimum: 2 vCPUs / 8 GB RAM for all containers + Ollama)"
  type        = string
  default     = "e2-standard-2"
}

variable "disk_size" {
  description = "Boot disk size in GB (50 GB is sufficient for container images, model weights, and document storage)"
  type        = number
  default     = 50
}

variable "repo_url" {
  description = "Git repository URL to clone on the VM (HTTPS format, e.g. https://github.com/org/repo.git)"
  type        = string
}

variable "domain" {
  description = "Domain name used for SITE_DOMAIN env var and Caddy auto-TLS (e.g. ai.example.com). Set to the public IP if no domain is configured."
  type        = string
  default     = ""
}

variable "ssh_user" {
  description = "Username for SSH access to the Compute Engine instance"
  type        = string
}

variable "ssh_public_key" {
  description = "SSH public key content (e.g. contents of ~/.ssh/id_ed25519.pub) for the ssh_user"
  type        = string
}
