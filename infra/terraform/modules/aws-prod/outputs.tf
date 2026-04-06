# ============================================================================
# AWS Production Deployment -- Outputs
# ============================================================================

output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "kubeconfig_command" {
  description = "AWS CLI command to update kubeconfig for kubectl access"
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "List of private subnet IDs (used by EKS nodes and RDS)"
  value       = module.vpc.private_subnets
}

output "database_endpoint" {
  description = "RDS PostgreSQL connection endpoint (host:port)"
  value       = aws_db_instance.platform.endpoint
}

output "database_address" {
  description = "RDS PostgreSQL hostname (without port)"
  value       = aws_db_instance.platform.address
}

output "s3_bucket" {
  description = "S3 bucket name for document storage (replaces MinIO)"
  value       = aws_s3_bucket.platform.id
}

output "ecr_repositories" {
  description = "Map of service name to ECR repository URL"
  value       = { for k, v in aws_ecr_repository.services : k => v.repository_url }
}
