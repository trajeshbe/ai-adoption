# GCP Production Tier -- GKE + Cloud SQL + GCS
#
# Usage:
#   cd infra/terraform/environments/gcp-prod
#   terraform init
#   terraform plan
#   terraform apply

terraform {
  required_version = ">= 1.5"

  # Uncomment for remote state:
  # backend "gcs" {
  #   bucket = "agent-platform-tfstate"
  #   prefix = "gcp-prod"
  # }
}

module "gcp_prod" {
  source = "../../modules/gcp-prod"

  project       = var.project
  region        = var.region
  cluster_name  = var.cluster_name
  db_tier       = var.db_tier
  db_password   = var.db_password
  domain        = var.domain
  enable_dns    = var.enable_dns
  dns_zone_name = var.dns_zone_name
}

module "common_k8s" {
  source = "../../modules/common-k8s"

  domain       = var.domain
  git_repo_url = var.git_repo_url
  git_branch   = var.git_branch

  depends_on = [module.gcp_prod]
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

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "agent-platform"
}

variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-custom-2-8192"
}

variable "db_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "domain" {
  description = "Domain name for the platform (e.g., app.example.com)"
  type        = string
}

variable "enable_dns" {
  description = "Create Cloud DNS managed zone"
  type        = bool
  default     = false
}

variable "dns_zone_name" {
  description = "Cloud DNS zone name (if enable_dns is true)"
  type        = string
  default     = "agent-platform"
}

variable "git_repo_url" {
  description = "Git repository URL for Argo CD"
  type        = string
  default     = "https://github.com/trajeshbe/ai-adoption.git"
}

variable "git_branch" {
  description = "Git branch for Argo CD"
  type        = string
  default     = "main"
}

output "cluster_name" {
  value = module.gcp_prod.cluster_name
}

output "kubeconfig_command" {
  value = module.gcp_prod.kubeconfig_command
}

output "database_connection_name" {
  value = module.gcp_prod.database_connection_name
}

output "registry_url" {
  value = module.gcp_prod.registry_url
}
