# ============================================================================
# AWS Production Deployment -- Input Variables
# ============================================================================

variable "region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "agent-platform"
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.30"
}

variable "node_instance_type" {
  description = "EC2 instance type for EKS managed node group (m6i.xlarge = 4 vCPU, 16GB RAM)"
  type        = string
  default     = "m6i.xlarge"
}

variable "node_min" {
  description = "Minimum number of nodes in the managed node group"
  type        = number
  default     = 2
}

variable "node_max" {
  description = "Maximum number of nodes in the managed node group"
  type        = number
  default     = 5
}

variable "node_desired" {
  description = "Desired number of nodes in the managed node group"
  type        = number
  default     = 3
}

variable "db_instance_class" {
  description = "RDS instance class for PostgreSQL (db.t3.large = 2 vCPU, 8GB RAM)"
  type        = string
  default     = "db.t3.large"
}

variable "db_password" {
  description = "Master password for the RDS PostgreSQL instance"
  type        = string
  sensitive   = true
}

variable "domain" {
  description = "Domain name for the platform (used for ingress and TLS certificates)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}
