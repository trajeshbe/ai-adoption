# =============================================================================
# GCP Production Deployment -- Outputs
# =============================================================================

output "cluster_name" {
  description = "Name of the GKE Autopilot cluster"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "Endpoint IP for the GKE cluster control plane"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "kubeconfig_command" {
  description = "gcloud command to configure kubectl for this cluster"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${var.region} --project ${var.project}"
}

output "database_connection_name" {
  description = "Cloud SQL instance connection name (project:region:instance) for Cloud SQL Auth Proxy"
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_ip" {
  description = "Private IP address of the Cloud SQL PostgreSQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "storage_bucket" {
  description = "GCS bucket name for document storage (replaces MinIO)"
  value       = google_storage_bucket.documents.name
}

output "registry_url" {
  description = "Artifact Registry repository URL for pushing container images"
  value       = "${var.region}-docker.pkg.dev/${var.project}/${google_artifact_registry_repository.containers.repository_id}"
}

output "load_balancer_ip" {
  description = "Static external IP address reserved for the load balancer"
  value       = google_compute_address.lb.address
}
