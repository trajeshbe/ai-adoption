# =============================================================================
# Azure Production Deployment -- Variables
#
# AKS cluster with managed PostgreSQL, Blob Storage, and Container Registry
# for the AI Agent Platform.
# =============================================================================

variable "location" {
  description = "Azure region for all resources (e.g. eastus, westus2, westeurope). Choose a region with AKS and PostgreSQL Flexible Server availability."
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Name of the Azure Resource Group. All production resources are grouped here for unified lifecycle and RBAC management."
  type        = string
  default     = "agent-platform-rg"
}

variable "cluster_name" {
  description = "Name of the AKS cluster. Also used as the DNS prefix and as a base name for associated resources (database, storage)."
  type        = string
  default     = "agent-platform"
}

variable "node_vm_size" {
  description = "VM size for AKS worker nodes. Standard_D4s_v5 provides 4 vCPUs / 16 GB RAM per node, suitable for running all platform microservices."
  type        = string
  default     = "Standard_D4s_v5"
}

variable "node_count" {
  description = "Number of nodes in the default AKS node pool. 3 nodes provides high availability across fault domains."
  type        = number
  default     = 3
}

variable "db_sku" {
  description = "SKU for Azure Database for PostgreSQL Flexible Server. B_Standard_B2s is a burstable tier suitable for moderate workloads."
  type        = string
  default     = "B_Standard_B2s"
}

variable "db_storage_mb" {
  description = "Storage size in MB for the PostgreSQL Flexible Server. 65536 MB (64 GB) accommodates pgvector embeddings and document metadata."
  type        = number
  default     = 65536
}

variable "db_password" {
  description = "Administrator password for the PostgreSQL Flexible Server. Must be at least 8 characters with uppercase, lowercase, and numbers."
  type        = string
  sensitive   = true
}

variable "domain" {
  description = "Domain name for the platform (e.g. ai.example.com). Used for ingress configuration and TLS certificate provisioning."
  type        = string
  default     = ""
}

variable "acr_name" {
  description = "Name of the Azure Container Registry. Must be globally unique, 5-50 alphanumeric characters only. Used to store platform container images."
  type        = string
  default     = "agentplatformacr"
}
