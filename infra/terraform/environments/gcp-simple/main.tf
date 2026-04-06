# GCP Simple Tier -- Single VM + Docker Compose
#
# Usage:
#   cd infra/terraform/environments/gcp-simple
#   terraform init
#   terraform plan -var="project=my-gcp-project" -var="domain=app.example.com"
#   terraform apply -var="project=my-gcp-project" -var="domain=app.example.com"

terraform {
  required_version = ">= 1.5"

  # Uncomment for remote state:
  # backend "gcs" {
  #   bucket = "agent-platform-tfstate"
  #   prefix = "gcp-simple"
  # }
}

module "gcp_simple" {
  source = "../../modules/gcp-simple"

  project        = var.project
  region         = var.region
  zone           = var.zone
  machine_type   = var.machine_type
  disk_size      = var.disk_size
  repo_url       = var.repo_url
  domain         = var.domain
  ssh_user       = var.ssh_user
  ssh_public_key = var.ssh_public_key
}

variable "project" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "machine_type" {
  description = "Compute Engine machine type"
  type        = string
  default     = "e2-standard-2"
}

variable "disk_size" {
  description = "Boot disk size in GB"
  type        = number
  default     = 100
}

variable "repo_url" {
  description = "Git repository URL to clone"
  type        = string
  default     = "https://github.com/trajeshbe/ai-adoption.git"
}

variable "domain" {
  description = "Domain name for HTTPS (e.g., app.example.com)"
  type        = string
  default     = ""
}

variable "ssh_user" {
  description = "SSH username"
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
  default     = ""
}

output "public_ip" {
  value = module.gcp_simple.public_ip
}

output "frontend_url" {
  value = module.gcp_simple.frontend_url
}

output "graphql_url" {
  value = module.gcp_simple.graphql_url
}

output "ssh_command" {
  value = module.gcp_simple.ssh_command
}
