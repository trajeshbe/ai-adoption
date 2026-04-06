# ============================================================================
# AWS Simple Deployment -- Input Variables
# ============================================================================

variable "region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type (t3.2xlarge = 8 vCPU, 32GB RAM, recommended minimum)"
  type        = string
  default     = "t3.2xlarge"
}

variable "disk_size" {
  description = "Root EBS volume size in GB (100GB recommended for container images and model weights)"
  type        = number
  default     = 100
}

variable "repo_url" {
  description = "Git repository URL to clone on the instance"
  type        = string
}

variable "domain" {
  description = "Domain name for the platform (used for Caddy auto-TLS and CORS)"
  type        = string
}

variable "ssh_public_key" {
  description = "SSH public key content for EC2 access (e.g., contents of ~/.ssh/id_rsa.pub)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}
