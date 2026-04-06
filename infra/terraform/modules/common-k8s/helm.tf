# ============================================================================
# Common Kubernetes Module -- Helm Releases for Shared Infrastructure
#
# Installation order enforced via depends_on:
#   1. cert-manager  (TLS foundation, must be early)
#   2. istio-base    (CRDs for the mesh)
#   3. istiod        (control plane, requires istio-base CRDs)
#   4. contour       (ingress, benefits from mesh being ready)
#   5. redis         (data layer)
#   6. otel / grafana (observability, can come last)
# ============================================================================

# ----------------------------------------------------------------------------
# cert-manager -- X.509 certificate lifecycle management
# ----------------------------------------------------------------------------

resource "helm_release" "cert_manager" {
  name             = "cert-manager"
  repository       = "https://charts.jetstack.io"
  chart            = "cert-manager"
  version          = "1.15.1"
  namespace        = "cert-manager"
  create_namespace = true
  wait             = true
  timeout          = 600

  set {
    name  = "installCRDs"
    value = "true"
  }

  set {
    name  = "global.leaderElection.namespace"
    value = "cert-manager"
  }
}

# ----------------------------------------------------------------------------
# Istio -- Ambient mesh (base CRDs + istiod control plane)
# ----------------------------------------------------------------------------

resource "helm_release" "istio_base" {
  count = var.enable_istio ? 1 : 0

  name             = "istio-base"
  repository       = "https://istio-release.storage.googleapis.com/charts"
  chart            = "base"
  version          = "1.22.1"
  namespace        = "istio-system"
  create_namespace = true
  wait             = true
  timeout          = 300

  depends_on = [helm_release.cert_manager]
}

resource "helm_release" "istiod" {
  count = var.enable_istio ? 1 : 0

  name       = "istiod"
  repository = "https://istio-release.storage.googleapis.com/charts"
  chart      = "istiod"
  version    = "1.22.1"
  namespace  = "istio-system"
  wait       = true
  timeout    = 600

  set {
    name  = "profile"
    value = "ambient"
  }

  set {
    name  = "meshConfig.defaultConfig.tracing.zipkin.address"
    value = "otel-collector.observability.svc.cluster.local:9411"
  }

  depends_on = [helm_release.istio_base]
}

# ----------------------------------------------------------------------------
# Contour -- Envoy-based ingress controller (via Bitnami chart)
# ----------------------------------------------------------------------------

resource "helm_release" "contour" {
  name             = "contour"
  repository       = "https://charts.bitnami.com/bitnami"
  chart            = "contour"
  version          = "18.2.3"
  namespace        = "projectcontour"
  create_namespace = true
  wait             = true
  timeout          = 600

  values = [
    file("${path.module}/../../../helm/values/contour.yaml")
  ]

  depends_on = [
    helm_release.cert_manager,
    helm_release.istiod,
  ]
}

# ----------------------------------------------------------------------------
# Redis Stack -- Redis 7.2 with RediSearch for Vector Similarity Search
# NOTE: Uses redis-stack-server image, NOT standard redis. The values file
# at infra/helm/values/redis.yaml overrides the image to redis/redis-stack-server.
# ----------------------------------------------------------------------------

resource "helm_release" "redis" {
  name             = "redis-stack"
  repository       = "https://charts.bitnami.com/bitnami"
  chart            = "redis"
  version          = "19.6.1"
  namespace        = kubernetes_namespace.agent_platform.metadata[0].name
  create_namespace = false
  wait             = true
  timeout          = 600

  values = [
    file("${path.module}/../../../helm/values/redis.yaml")
  ]

  depends_on = [kubernetes_namespace.agent_platform]
}

# ----------------------------------------------------------------------------
# OpenTelemetry Collector -- Receives traces, metrics, and logs from all services
# ----------------------------------------------------------------------------

resource "helm_release" "otel_collector" {
  count = var.enable_observability ? 1 : 0

  name             = "otel-collector"
  repository       = "https://open-telemetry.github.io/opentelemetry-helm-charts"
  chart            = "opentelemetry-collector"
  version          = "0.92.0"
  namespace        = kubernetes_namespace.observability.metadata[0].name
  create_namespace = false
  wait             = true
  timeout          = 600

  values = [
    file("${path.module}/../../../helm/values/otel-collector.yaml")
  ]

  depends_on = [kubernetes_namespace.observability]
}

# ----------------------------------------------------------------------------
# Grafana -- Dashboards for Tempo (traces), Loki (logs), Mimir (metrics)
# ----------------------------------------------------------------------------

resource "helm_release" "grafana" {
  count = var.enable_observability ? 1 : 0

  name             = "grafana"
  repository       = "https://grafana.github.io/helm-charts"
  chart            = "grafana"
  version          = "8.3.2"
  namespace        = kubernetes_namespace.observability.metadata[0].name
  create_namespace = false
  wait             = true
  timeout          = 600

  values = [
    file("${path.module}/../../../helm/values/grafana-stack.yaml")
  ]

  depends_on = [
    kubernetes_namespace.observability,
    helm_release.otel_collector,
  ]
}
