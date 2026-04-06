# ============================================================================
# Common Kubernetes Module -- Outputs
# ============================================================================

output "argocd_namespace" {
  description = "Namespace where Argo CD is installed (empty string if Argo CD is disabled)"
  value       = var.enable_argocd ? helm_release.argocd[0].namespace : ""
}

output "cert_manager_namespace" {
  description = "Namespace where cert-manager is installed"
  value       = helm_release.cert_manager.namespace
}

output "contour_namespace" {
  description = "Namespace where Contour ingress controller is installed"
  value       = helm_release.contour.namespace
}
