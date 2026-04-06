# Azure Simple Tier -- Single VM + Docker Compose
#
# Usage:
#   cd infra/terraform/environments/azure-simple
#   terraform init
#   terraform plan -var="domain=app.example.com"
#   terraform apply -var="domain=app.example.com"

terraform {
  required_version = ">= 1.5"

  # Uncomment for remote state:
  # backend "azurerm" {
  #   resource_group_name  = "tfstate-rg"
  #   storage_account_name = "agentplatformtfstate"
  #   container_name       = "tfstate"
  #   key                  = "azure-simple.tfstate"
  # }
}

module "azure_simple" {
  source = "../../modules/azure-simple"

  location            = var.location
  resource_group_name = var.resource_group_name
  vm_size             = var.vm_size
  disk_size           = var.disk_size
  repo_url            = var.repo_url
  domain              = var.domain
  admin_username      = var.admin_username
  ssh_public_key      = var.ssh_public_key
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

variable "vm_size" {
  description = "Azure VM size"
  type        = string
  default     = "Standard_D8as_v5"
}

variable "disk_size" {
  description = "OS disk size in GB"
  type        = number
  default     = 128
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

variable "admin_username" {
  description = "VM admin username"
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
}

output "public_ip" {
  value = module.azure_simple.public_ip
}

output "frontend_url" {
  value = module.azure_simple.frontend_url
}

output "ssh_command" {
  value = module.azure_simple.ssh_command
}
