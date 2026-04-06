# AWS Simple Tier -- Single EC2 + Docker Compose
#
# Usage:
#   cd infra/terraform/environments/aws-simple
#   terraform init
#   terraform plan -var="domain=app.example.com"
#   terraform apply -var="domain=app.example.com"

terraform {
  required_version = ">= 1.5"

  # Uncomment for remote state:
  # backend "s3" {
  #   bucket = "agent-platform-tfstate"
  #   key    = "aws-simple/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

module "aws_simple" {
  source = "../../modules/aws-simple"

  region         = var.region
  instance_type  = var.instance_type
  disk_size      = var.disk_size
  repo_url       = var.repo_url
  domain         = var.domain
  ssh_public_key = var.ssh_public_key
  vpc_cidr       = var.vpc_cidr
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.2xlarge"
}

variable "disk_size" {
  description = "EBS volume size in GB"
  type        = number
  default     = 100
}

variable "repo_url" {
  description = "Git repository URL to clone"
  type        = string
  default     = "https://github.com/trajeshbe/ai-adoption.git"
}

variable "domain" {
  description = "Domain name for HTTPS (e.g., app.example.com)"
  type        = string
  default     = ""
}

variable "ssh_public_key" {
  description = "SSH public key for EC2 access"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

output "public_ip" {
  value = module.aws_simple.public_ip
}

output "frontend_url" {
  value = module.aws_simple.frontend_url
}

output "ssh_command" {
  value = module.aws_simple.ssh_command
}
