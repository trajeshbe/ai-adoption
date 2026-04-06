# =============================================================================
# Azure Simple Deployment -- Variables
#
# Single Azure VM running docker-compose for the AI Agent Platform.
# =============================================================================

variable "location" {
  description = "Azure region for all resources (e.g. eastus, westus2, westeurope). Choose a region close to your users."
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Name of the Azure Resource Group to create. All resources will be placed in this group for easy lifecycle management."
  type        = string
  default     = "agent-platform-rg"
}

variable "vm_size" {
  description = "Azure VM size. Standard_D8as_v5 provides 8 vCPUs / 32 GB RAM, sufficient for all platform containers including Ollama LLM inference."
  type        = string
  default     = "Standard_D8as_v5"
}

variable "disk_size" {
  description = "OS disk size in GB. 128 GB accommodates container images, LLM model weights (~3 GB for qwen2.5:1.5b), and document storage."
  type        = number
  default     = 128
}

variable "repo_url" {
  description = "Git repository URL to clone on the VM (HTTPS format, e.g. https://github.com/org/ai-adoption.git). The repo must contain docker-compose.yml at the root."
  type        = string
}

variable "domain" {
  description = "Domain name for Caddy auto-TLS and SITE_DOMAIN env var (e.g. ai.example.com). Leave empty to use the public IP address directly (HTTP only)."
  type        = string
  default     = ""
}

variable "admin_username" {
  description = "Username for SSH access to the Azure VM. This becomes the Linux admin user on the instance."
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key" {
  description = "SSH public key content for authenticating to the VM (e.g. contents of ~/.ssh/id_ed25519.pub). Password authentication is disabled."
  type        = string
}
