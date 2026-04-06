# ============================================================================
# AWS Production Deployment -- EKS Cluster with Managed Services
#
# Deploys the AI Agent Platform on a production-grade EKS cluster with:
#   - Multi-AZ VPC with public/private subnets and NAT gateway
#   - EKS managed node group with auto-scaling
#   - RDS PostgreSQL 16 (pgvector) with Multi-AZ standby
#   - S3 bucket (replaces MinIO for object storage)
#   - ECR repositories for all 6 platform services
#
# Usage:
#   terraform init
#   terraform apply -var="db_password=<secure-password>" \
#                   -var="domain=app.example.com"
# ============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "agent-platform"
      ManagedBy = "terraform"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

locals {
  name_prefix = "agent-platform"
  azs         = slice(data.aws_availability_zones.available.names, 0, 3)

  services = toset([
    "gateway",
    "agent-engine",
    "document-service",
    "cache-service",
    "cost-tracker",
    "frontend",
  ])

  common_tags = {
    Project   = "agent-platform"
    ManagedBy = "terraform"
  }
}

data "aws_availability_zones" "available" {
  state = "available"

  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

# ----------------------------------------------------------------------------
# VPC -- Multi-AZ with public/private subnets and NAT gateway
# ----------------------------------------------------------------------------

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${local.name_prefix}-vpc"
  cidr = var.vpc_cidr

  azs             = local.azs
  public_subnets  = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 8, i)]
  private_subnets = [for i, az in local.azs : cidrsubnet(var.vpc_cidr, 8, i + 10)]

  enable_nat_gateway   = true
  single_nat_gateway   = false
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Tags required for EKS subnet discovery
  public_subnet_tags = {
    "kubernetes.io/role/elb"                              = 1
    "kubernetes.io/cluster/${var.cluster_name}"            = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"                     = 1
    "kubernetes.io/cluster/${var.cluster_name}"            = "shared"
  }

  tags = {
    Name = "${local.name_prefix}-vpc"
  }
}

# ----------------------------------------------------------------------------
# EKS Cluster -- Managed node group with auto-scaling
# ----------------------------------------------------------------------------

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Public endpoint for kubectl access; restrict in production via allowed CIDRs
  cluster_endpoint_public_access = true

  # Enable IRSA for pod-level IAM roles
  enable_irsa = true

  # Cluster addons
  cluster_addons = {
    coredns                = { most_recent = true }
    kube-proxy             = { most_recent = true }
    vpc-cni                = { most_recent = true }
    aws-ebs-csi-driver     = { most_recent = true }
  }

  eks_managed_node_groups = {
    platform = {
      name           = "${local.name_prefix}-nodes"
      instance_types = [var.node_instance_type]
      min_size       = var.node_min
      max_size       = var.node_max
      desired_size   = var.node_desired

      # Use Amazon Linux 2023 for EKS-optimized AMI
      ami_type = "AL2023_x86_64_STANDARD"

      disk_size = 100

      labels = {
        role = "platform"
      }

      tags = {
        Name = "${local.name_prefix}-node"
      }
    }
  }

  tags = {
    Name = "${local.name_prefix}-eks"
  }
}

# ----------------------------------------------------------------------------
# RDS PostgreSQL 16 -- pgvector for document embeddings
# ----------------------------------------------------------------------------

resource "aws_db_subnet_group" "platform" {
  name       = "${local.name_prefix}-db-subnet"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Name = "${local.name_prefix}-db-subnet"
  }
}

resource "aws_security_group" "rds" {
  name        = "${local.name_prefix}-rds-sg"
  description = "Allow PostgreSQL access from EKS nodes"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-rds-sg"
  }
}

resource "aws_db_instance" "platform" {
  identifier = "${local.name_prefix}-db"

  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  allocated_storage     = 50
  max_allocated_storage = 200
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "agent_platform"
  username = "agent_platform"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.platform.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az            = true
  publicly_accessible = false

  backup_retention_period = 7
  skip_final_snapshot     = false
  final_snapshot_identifier = "${local.name_prefix}-db-final-snapshot"
  deletion_protection     = true

  # NOTE: pgvector extension must be enabled manually after provisioning:
  #   psql -h <endpoint> -U agent_platform -d agent_platform \
  #     -c "CREATE EXTENSION IF NOT EXISTS vector;"
  # AWS RDS PostgreSQL 16 supports pgvector natively.

  tags = {
    Name = "${local.name_prefix}-db"
  }
}

# ----------------------------------------------------------------------------
# S3 Bucket -- Replaces MinIO for object storage
# ----------------------------------------------------------------------------

resource "aws_s3_bucket" "platform" {
  bucket = "${local.name_prefix}-documents-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${local.name_prefix}-documents"
  }
}

resource "aws_s3_bucket_versioning" "platform" {
  bucket = aws_s3_bucket.platform.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "platform" {
  bucket = aws_s3_bucket.platform.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "platform" {
  bucket = aws_s3_bucket.platform.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_caller_identity" "current" {}

# ----------------------------------------------------------------------------
# ECR Repositories -- One per platform service
# ----------------------------------------------------------------------------

resource "aws_ecr_repository" "services" {
  for_each = local.services

  name                 = "${local.name_prefix}/${each.key}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name    = "${local.name_prefix}-${each.key}"
    Service = each.key
  }
}

resource "aws_ecr_lifecycle_policy" "services" {
  for_each = local.services

  repository = aws_ecr_repository.services[each.key].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 20 tagged images"
        selection = {
          tagStatus   = "tagged"
          tagPrefixList = ["v"]
          countType   = "imageCountMoreThan"
          countNumber = 20
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Expire untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
