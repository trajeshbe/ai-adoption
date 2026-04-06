# =============================================================================
# Azure Production Deployment -- Outputs
# =============================================================================

output "cluster_name" {
  description = "Name of the AKS cluster"
  value       = azurerm_kubernetes_cluster.main.name
}

output "kube_config_command" {
  description = "Azure CLI command to configure kubectl for the AKS cluster"
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_kubernetes_cluster.main.name}"
}

output "resource_group" {
  description = "Name of the Azure Resource Group containing all resources"
  value       = azurerm_resource_group.main.name
}

output "database_fqdn" {
  description = "Fully qualified domain name of the PostgreSQL Flexible Server"
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "storage_account_name" {
  description = "Name of the Azure Storage Account (replaces MinIO for object storage)"
  value       = azurerm_storage_account.main.name
}

output "acr_login_server" {
  description = "Login server URL for the Azure Container Registry (use with docker login)"
  value       = azurerm_container_registry.main.login_server
}

output "acr_name" {
  description = "Name of the Azure Container Registry"
  value       = azurerm_container_registry.main.name
}
