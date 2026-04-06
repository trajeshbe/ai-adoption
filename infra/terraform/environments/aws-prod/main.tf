# AWS Production Tier -- EKS + RDS + S3
#
# Usage:
#   cd infra/terraform/environments/aws-prod
#   terraform init
#   terraform plan
#   terraform apply

terraform {
  required_version = ">= 1.5"

  # Uncomment for remote state:
  # backend "s3" {
  #   bucket = "agent-platform-tfstate"
  #   key    = "aws-prod/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

module "aws_prod" {
  source = "../../modules/aws-prod"

  region              = var.region
  cluster_name        = var.cluster_name
  cluster_version     = var.cluster_version
  node_instance_type  = var.node_instance_type
  node_min            = var.node_min
  node_max            = var.node_max
  node_desired        = var.node_desired
  db_instance_class   = var.db_instance_class
  db_password         = var.db_password
  domain              = var.domain
  vpc_cidr            = var.vpc_cidr
}

module "common_k8s" {
  source = "../../modules/common-k8s"

  domain       = var.domain
  git_repo_url = var.git_repo_url
  git_branch   = var.git_branch

  depends_on = [module.aws_prod]
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "agent-platform"
}

variable "cluster_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.30"
}

variable "node_instance_type" {
  description = "EC2 instance type for EKS nodes"
  type        = string
  default     = "m6i.xlarge"
}

variable "node_min" {
  description = "Minimum number of nodes"
  type        = number
  default     = 2
}

variable "node_max" {
  description = "Maximum number of nodes"
  type        = number
  default     = 5
}

variable "node_desired" {
  description = "Desired number of nodes"
  type        = number
  default     = 3
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.large"
}

variable "db_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "domain" {
  description = "Domain name for the platform"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "git_repo_url" {
  description = "Git repository URL for Argo CD"
  type        = string
  default     = "https://github.com/trajeshbe/ai-adoption.git"
}

variable "git_branch" {
  description = "Git branch for Argo CD"
  type        = string
  default     = "main"
}

output "cluster_name" {
  value = module.aws_prod.cluster_name
}

output "kubeconfig_command" {
  value = module.aws_prod.kubeconfig_command
}

output "database_endpoint" {
  value = module.aws_prod.database_endpoint
}

output "ecr_repositories" {
  value = module.aws_prod.ecr_repositories
}
