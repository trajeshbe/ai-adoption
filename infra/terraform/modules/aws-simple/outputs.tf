# ============================================================================
# AWS Simple Deployment -- Outputs
# ============================================================================

output "public_ip" {
  description = "Elastic IP address of the EC2 instance"
  value       = aws_eip.platform.public_ip
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.platform.id
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i <private-key> ubuntu@${aws_eip.platform.public_ip}"
}

output "frontend_url" {
  description = "URL for the frontend web UI"
  value       = "https://${var.domain}"
}

output "graphql_url" {
  description = "URL for the GraphQL API endpoint"
  value       = "https://${var.domain}/graphql"
}
