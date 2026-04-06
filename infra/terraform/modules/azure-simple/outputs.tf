# =============================================================================
# Azure Simple Deployment -- Outputs
# =============================================================================

output "public_ip" {
  description = "Static public IP address of the Azure VM"
  value       = azurerm_public_ip.main.ip_address
}

output "resource_group" {
  description = "Name of the Azure Resource Group containing all resources"
  value       = azurerm_resource_group.main.name
}

output "ssh_command" {
  description = "SSH command to connect to the VM"
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.main.ip_address}"
}

output "frontend_url" {
  description = "URL to access the Next.js frontend (via Caddy reverse proxy when domain is set)"
  value       = var.domain != "" ? "https://${var.domain}" : "http://${azurerm_public_ip.main.ip_address}"
}

output "graphql_url" {
  description = "URL to access the GraphQL API endpoint"
  value       = var.domain != "" ? "https://${var.domain}/graphql" : "http://${azurerm_public_ip.main.ip_address}:8050/graphql"
}
