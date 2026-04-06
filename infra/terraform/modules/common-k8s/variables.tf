# ============================================================================
# Common Kubernetes Module -- Input Variables
# ============================================================================

variable "domain" {
  description = "Primary domain name for the platform (used in TLS certificates and ingress rules)"
  type        = string
}

variable "git_repo_url" {
  description = "Git repository URL for Argo CD to sync application manifests from"
  type        = string
}

variable "git_branch" {
  description = "Git branch for Argo CD to track (targetRevision in Application specs)"
  type        = string
  default     = "main"
}

variable "enable_argocd" {
  description = "Whether to install Argo CD and the app-of-apps Application for GitOps delivery"
  type        = bool
  default     = true
}

variable "enable_istio" {
  description = "Whether to install Istio base and istiod for ambient mesh networking"
  type        = bool
  default     = true
}

variable "enable_observability" {
  description = "Whether to install the observability stack (OpenTelemetry Collector, Grafana)"
  type        = bool
  default     = true
}
