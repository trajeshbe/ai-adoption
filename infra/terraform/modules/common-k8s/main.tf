# ============================================================================
# Common Kubernetes Module -- Shared Infrastructure for All Cloud Providers
#
# This module is applied AFTER a managed Kubernetes cluster has been
# provisioned (EKS, GKE, or AKS). It installs shared platform
# infrastructure into the cluster via Helm and raw Kubernetes resources.
#
# Consumers pass in pre-configured kubernetes and helm providers that
# already point at the target cluster. This module never creates the
# cluster itself -- it only installs workloads into an existing one.
#
# Usage (from a cloud-specific root module):
#   module "common_k8s" {
#     source       = "../modules/common-k8s"
#     domain       = "app.example.com"
#     git_repo_url = "https://github.com/your-org/ai-adoption.git"
#   }
# ============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.14"
    }
  }
}

# ----------------------------------------------------------------------------
# Namespaces -- Core application and observability
# ----------------------------------------------------------------------------

resource "kubernetes_namespace" "agent_platform" {
  metadata {
    name = "agent-platform"

    labels = {
      "app.kubernetes.io/part-of" = "agent-platform"
      "istio.io/dataplane-mode"   = "ambient"
    }

    annotations = {
      "meta.helm.sh/release-name" = "agent-platform"
    }
  }
}

resource "kubernetes_namespace" "observability" {
  metadata {
    name = "observability"

    labels = {
      "app.kubernetes.io/part-of" = "agent-platform"
    }
  }
}
