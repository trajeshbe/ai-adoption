# Azure Production Tier -- AKS + PostgreSQL Flexible + Blob Storage
#
# Usage:
#   cd infra/terraform/environments/azure-prod
#   terraform init
#   terraform plan
#   terraform apply

terraform {
  required_version = ">= 1.5"

  # Uncomment for remote state:
  # backend "azurerm" {
  #   resource_group_name  = "tfstate-rg"
  #   storage_account_name = "agentplatformtfstate"
  #   container_name       = "tfstate"
  #   key                  = "azure-prod.tfstate"
  # }
}

module "azure_prod" {
  source = "../../modules/azure-prod"

  location            = var.location
  resource_group_name = var.resource_group_name
  cluster_name        = var.cluster_name
  node_vm_size        = var.node_vm_size
  node_count          = var.node_count
  db_sku              = var.db_sku
  db_storage_mb       = var.db_storage_mb
  db_password         = var.db_password
  domain              = var.domain
  acr_name            = var.acr_name
}

module "common_k8s" {
  source = "../../modules/common-k8s"

  domain       = var.domain
  git_repo_url = var.git_repo_url
  git_branch   = var.git_branch

  depends_on = [module.azure_prod]
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = "agent-platform-rg"
}

variable "cluster_name" {
  description = "AKS cluster name"
  type        = string
  default     = "agent-platform"
}

variable "node_vm_size" {
  description = "AKS node VM size"
  type        = string
  default     = "Standard_D4s_v5"
}

variable "node_count" {
  description = "Number of AKS nodes"
  type        = number
  default     = 3
}

variable "db_sku" {
  description = "PostgreSQL Flexible Server SKU"
  type        = string
  default     = "B_Standard_B2s"
}

variable "db_storage_mb" {
  description = "PostgreSQL storage in MB"
  type        = number
  default     = 65536
}

variable "db_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "domain" {
  description = "Domain name for the platform"
  type        = string
}

variable "acr_name" {
  description = "Azure Container Registry name (globally unique)"
  type        = string
  default     = "agentplatformacr"
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
  value = module.azure_prod.cluster_name
}

output "kube_config_command" {
  value = module.azure_prod.kube_config_command
}

output "database_fqdn" {
  value = module.azure_prod.database_fqdn
}

output "acr_login_server" {
  value = module.azure_prod.acr_login_server
}
