# =============================================================================
# GCP Production Deployment -- GKE Autopilot + Managed Services
#
# Deploys the AI Agent Platform on GKE Autopilot with Cloud SQL (pgvector),
# GCS (replacing MinIO), and Artifact Registry for container images.
#
# Usage:
#   terraform init
#   terraform apply -var="project=my-gcp-project" \
#                   -var="db_password=$(openssl rand -base64 24)"
# =============================================================================

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
  }
}

provider "google" {
  project = var.project
  region  = var.region
}

provider "kubernetes" {
  host                   = "https://${google_container_cluster.primary.endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(google_container_cluster.primary.master_auth[0].cluster_ca_certificate)
}

data "google_client_config" "default" {}

# ---------------------------------------------------------------------------
# Locals
# ---------------------------------------------------------------------------

locals {
  labels = {
    app        = "ai-agent-platform"
    managed-by = "terraform"
    env        = "production"
  }
}

# ---------------------------------------------------------------------------
# Networking -- VPC for private connectivity
# ---------------------------------------------------------------------------

resource "google_compute_network" "platform" {
  name                    = "${var.cluster_name}-vpc"
  auto_create_subnetworks = false
  description             = "VPC for the AI Agent Platform production environment"
}

resource "google_compute_subnetwork" "platform" {
  name                     = "${var.cluster_name}-subnet"
  ip_cidr_range            = "10.0.0.0/20"
  region                   = var.region
  network                  = google_compute_network.platform.id
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.4.0.0/14"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.8.0.0/20"
  }
}

resource "google_compute_global_address" "private_services" {
  name          = "${var.cluster_name}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.platform.id
  description   = "Private IP range for Cloud SQL and other managed services"
}

resource "google_service_networking_connection" "private_services" {
  network                 = google_compute_network.platform.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services.name]
}

# ---------------------------------------------------------------------------
# GKE Autopilot Cluster
# ---------------------------------------------------------------------------

resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region

  # Autopilot mode -- Google manages node pools, scaling, and security
  enable_autopilot = true

  network    = google_compute_network.platform.id
  subnetwork = google_compute_subnetwork.platform.id

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Private cluster -- nodes have no public IPs
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  # Release channel for automatic upgrades
  release_channel {
    channel = "REGULAR"
  }

  resource_labels = local.labels

  # Deletion protection -- disable explicitly when decommissioning
  deletion_protection = true

  depends_on = [google_service_networking_connection.private_services]
}

# ---------------------------------------------------------------------------
# Cloud SQL -- PostgreSQL 16 with pgvector
# ---------------------------------------------------------------------------

resource "google_sql_database_instance" "postgres" {
  name             = "${var.cluster_name}-pg"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = var.db_tier
    availability_type = "REGIONAL"
    disk_autoresize   = true
    disk_size         = 20
    disk_type         = "PD_SSD"

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.platform.id
      enable_private_path_for_google_cloud_services = true
    }

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
      transaction_log_retention_days = 7

      backup_retention_settings {
        retained_backups = 14
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 7 # Sunday
      hour         = 4 # 04:00 UTC
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = true
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
  }

  deletion_protection = true

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_service_networking_connection.private_services]
}

resource "google_sql_database" "agent_platform" {
  name     = "agent_platform"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "agent_platform" {
  name     = "agent_platform"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password

  deletion_policy = "ABANDON"
}

# ---------------------------------------------------------------------------
# GCS Bucket -- Document storage (replaces MinIO)
# ---------------------------------------------------------------------------

resource "google_storage_bucket" "documents" {
  name          = "${var.project}-${var.cluster_name}-documents"
  location      = var.region
  force_destroy = false
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  labels = local.labels
}

# ---------------------------------------------------------------------------
# Artifact Registry -- Container images
# ---------------------------------------------------------------------------

resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = "${var.cluster_name}-images"
  description   = "Container images for the AI Agent Platform microservices"
  format        = "DOCKER"

  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"

    most_recent_versions {
      keep_count = 10
    }
  }

  labels = local.labels
}

# ---------------------------------------------------------------------------
# Static IP -- Load balancer
# ---------------------------------------------------------------------------

resource "google_compute_address" "lb" {
  name        = "${var.cluster_name}-lb-ip"
  region      = var.region
  description = "Static external IP for the platform load balancer (used by Contour/Envoy ingress)"
}

# ---------------------------------------------------------------------------
# Cloud DNS (optional) -- Managed zone and A record
# ---------------------------------------------------------------------------

resource "google_dns_managed_zone" "platform" {
  count = var.enable_dns ? 1 : 0

  name        = var.dns_zone_name
  dns_name    = "${var.domain}."
  description = "DNS zone for the AI Agent Platform"

  labels = local.labels
}

resource "google_dns_record_set" "platform_a" {
  count = var.enable_dns ? 1 : 0

  name         = "${var.domain}."
  managed_zone = google_dns_managed_zone.platform[0].name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_address.lb.address]
}

resource "google_dns_record_set" "platform_wildcard" {
  count = var.enable_dns ? 1 : 0

  name         = "*.${var.domain}."
  managed_zone = google_dns_managed_zone.platform[0].name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_address.lb.address]
}
