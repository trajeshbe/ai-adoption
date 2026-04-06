# =============================================================================
# GCP Production Deployment -- Variables
#
# GKE Autopilot cluster with Cloud SQL, GCS, and Artifact Registry.
# =============================================================================

variable "project" {
  description = "GCP project ID where all production resources will be created"
  type        = string
}

variable "region" {
  description = "GCP region for the GKE cluster and managed services (multi-zone availability)"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "Name of the GKE Autopilot cluster"
  type        = string
  default     = "agent-platform"
}

variable "db_tier" {
  description = "Cloud SQL machine tier (db-custom-2-8192 provides 2 vCPUs / 8 GB RAM for pgvector workloads)"
  type        = string
  default     = "db-custom-2-8192"
}

variable "db_password" {
  description = "Password for the Cloud SQL agent_platform user (must be at least 16 characters)"
  type        = string
  sensitive   = true
}

variable "domain" {
  description = "Domain name for the platform (e.g. ai.example.com). Used for DNS records and ingress configuration."
  type        = string
  default     = ""
}

variable "enable_dns" {
  description = "Whether to create a Cloud DNS managed zone and A record for the domain"
  type        = bool
  default     = false
}

variable "dns_zone_name" {
  description = "Name of the Cloud DNS managed zone (required when enable_dns is true, e.g. 'ai-example-com')"
  type        = string
  default     = ""
}
