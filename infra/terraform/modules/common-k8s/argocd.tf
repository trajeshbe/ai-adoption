# ============================================================================
# Common Kubernetes Module -- Argo CD Installation and App-of-Apps Bootstrap
#
# Installs Argo CD via Helm, then creates the root Application that
# points at infra/argocd/apps/ in the Git repo. Argo CD will reconcile
# all child Applications from there (gateway, agent-engine, frontend,
# document-service, cache-service, cost-tracker, mesh, observability).
# ============================================================================

# ----------------------------------------------------------------------------
# Argo CD -- GitOps delivery controller
# ----------------------------------------------------------------------------

resource "helm_release" "argocd" {
  count = var.enable_argocd ? 1 : 0

  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = "7.3.4"
  namespace        = "argocd"
  create_namespace = true
  wait             = true
  timeout          = 600

  set {
    name  = "server.service.type"
    value = "ClusterIP"
  }

  set {
    name  = "configs.params.server\\.insecure"
    value = "true"
  }

  set {
    name  = "controller.replicas"
    value = "1"
  }

  depends_on = [helm_release.cert_manager]
}

# ----------------------------------------------------------------------------
# App-of-Apps -- Root Application that syncs all child apps
#
# Mirrors the structure in infra/argocd/app-of-apps.yaml but managed by
# Terraform so the Git repo URL and branch are parameterised per environment.
# ----------------------------------------------------------------------------

resource "kubernetes_manifest" "argocd_project" {
  count = var.enable_argocd ? 1 : 0

  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "AppProject"
    metadata = {
      name      = "agent-platform"
      namespace = "argocd"
    }
    spec = {
      description = "AI Agent Platform -- all microservices and infrastructure"
      sourceRepos = [var.git_repo_url]
      destinations = [
        {
          server    = "https://kubernetes.default.svc"
          namespace = "*"
        }
      ]
      clusterResourceWhitelist = [
        {
          group = "*"
          kind  = "*"
        }
      ]
    }
  }

  depends_on = [helm_release.argocd]
}

resource "kubernetes_manifest" "argocd_app_of_apps" {
  count = var.enable_argocd ? 1 : 0

  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      name      = "agent-platform"
      namespace = "argocd"
    }
    spec = {
      project = "agent-platform"
      source = {
        repoURL        = var.git_repo_url
        targetRevision = var.git_branch
        path           = "infra/argocd/apps"
      }
      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = "argocd"
      }
      syncPolicy = {
        automated = {
          prune    = true
          selfHeal = true
        }
      }
    }
  }

  depends_on = [kubernetes_manifest.argocd_project]
}
