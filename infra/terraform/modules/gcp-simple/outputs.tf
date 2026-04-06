# =============================================================================
# GCP Simple Deployment -- Outputs
# =============================================================================

output "public_ip" {
  description = "Static external IP address of the Compute Engine instance"
  value       = google_compute_address.ai_platform.address
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh ${var.ssh_user}@${google_compute_address.ai_platform.address}"
}

output "frontend_url" {
  description = "URL to access the Next.js frontend (via Caddy reverse proxy)"
  value       = local.site_domain != "" ? "https://${local.site_domain}" : "http://${google_compute_address.ai_platform.address}"
}

output "graphql_url" {
  description = "URL to access the GraphQL API endpoint (via Caddy reverse proxy)"
  value       = local.site_domain != "" ? "https://${local.site_domain}/graphql" : "http://${google_compute_address.ai_platform.address}:8050/graphql"
}
