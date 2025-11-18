# =============================================================================
# ECS Fargate Deployment Outputs
# =============================================================================

# ECR Repository
output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.backend.name
}

# ECS Cluster
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

# ECS Service
output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = var.create_vpc ? aws_ecs_service.main[0].name : "VPC not created"
}

output "ecs_service_arn" {
  description = "ARN of the ECS service"
  value       = var.create_vpc ? aws_ecs_service.main[0].id : "VPC not created"
}

# ECS Task Definition
output "ecs_task_definition_family" {
  description = "Family name of the ECS task definition"
  value       = aws_ecs_task_definition.main.family
}

output "ecs_task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.main.arn
}

# Application Load Balancer
output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = var.create_vpc ? aws_lb.main[0].dns_name : "VPC not created"
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = var.create_vpc ? aws_lb.main[0].arn : "VPC not created"
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer (for Route53)"
  value       = var.create_vpc ? aws_lb.main[0].zone_id : "VPC not created"
}

output "alb_url" {
  description = "Full URL of the Application Load Balancer"
  value       = var.create_vpc ? (var.enable_https ? "https://${aws_lb.main[0].dns_name}" : "http://${aws_lb.main[0].dns_name}") : "VPC not created"
}

output "alb_http_url" {
  description = "HTTP URL of the Application Load Balancer"
  value       = var.create_vpc ? "http://${aws_lb.main[0].dns_name}" : "VPC not created"
}

output "alb_https_url" {
  description = "HTTPS URL of the Application Load Balancer (if HTTPS enabled)"
  value       = var.create_vpc && var.enable_https ? "https://${aws_lb.main[0].dns_name}" : "HTTPS not enabled"
}

output "https_enabled" {
  description = "Whether HTTPS is enabled"
  value       = var.enable_https
}

output "certificate_arn" {
  description = "ARN of the ACM certificate (if HTTPS enabled)"
  value       = var.enable_https ? var.certificate_arn : "HTTPS not enabled"
}

# Target Group
output "target_group_arn" {
  description = "ARN of the target group"
  value       = var.create_vpc ? aws_lb_target_group.main[0].arn : "VPC not created"
}

# VPC Information
output "vpc_id" {
  description = "ID of the VPC"
  value       = var.create_vpc ? aws_vpc.main[0].id : "VPC not created"
}

output "public_subnet_ids" {
  description = "IDs of the public subnets (ALB and ECS tasks)"
  value       = var.create_vpc ? aws_subnet.public[*].id : []
}

# Security Groups
output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = var.create_vpc ? aws_security_group.alb[0].id : "VPC not created"
}

output "ecs_security_group_id" {
  description = "ID of the ECS tasks security group"
  value       = var.create_vpc ? aws_security_group.ecs_tasks[0].id : "VPC not created"
}

# IAM Roles
output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task.arn
}

# GitHub Actions IAM User
output "github_actions_user_name" {
  description = "Name of the GitHub Actions IAM user"
  value       = aws_iam_user.github_actions.name
}

output "github_actions_access_key_id" {
  description = "Access Key ID for GitHub Actions (use in GitHub Secrets)"
  value       = aws_iam_access_key.github_actions.id
  sensitive   = false
}

output "github_actions_secret_access_key" {
  description = "Secret Access Key for GitHub Actions (use in GitHub Secrets)"
  value       = aws_iam_access_key.github_actions.secret
  sensitive   = true
}

# CloudWatch Logs
output "cloudwatch_log_group" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.ecs.name
}

# Redis Service
output "redis_service_name" {
  description = "Name of the Redis ECS service"
  value       = var.create_vpc ? aws_ecs_service.redis[0].name : "VPC not created"
}

output "redis_endpoint" {
  description = "Redis connection endpoint (service discovery)"
  value       = var.create_vpc ? "redis.${var.environment}.local:6379" : "VPC not created"
}

# =============================================================================
# Helpful Configuration Outputs
# =============================================================================

output "deployment_url" {
  description = "URL to access the deployed application"
  value       = var.create_vpc ? (var.enable_https ? "https://${aws_lb.main[0].dns_name}/health" : "http://${aws_lb.main[0].dns_name}/health") : "VPC not created"
}

output "github_secrets_config" {
  description = "Configuration values to add as GitHub Secrets"
  value = <<-EOT
    Add these secrets to your GitHub repository:
    
    AWS_ACCESS_KEY_ID: ${aws_iam_access_key.github_actions.id}
    AWS_SECRET_ACCESS_KEY: ${aws_iam_access_key.github_actions.secret}
    AWS_REGION: ${var.aws_region}
    
    These values are already configured in the GitHub Actions workflow:
    ECR_REPOSITORY: ${aws_ecr_repository.backend.name}
    ECS_CLUSTER: ${aws_ecs_cluster.main.name}
    ECS_SERVICE: ${var.create_vpc ? aws_ecs_service.main[0].name : "VPC not created"}
    ECS_TASK_DEFINITION: ${aws_ecs_task_definition.main.family}
    CONTAINER_NAME: ${var.container_name}
  EOT
  sensitive = true
}

output "quick_start_commands" {
  description = "Quick start commands for deployment"
  value = <<-EOT
    # Test the deployment
    curl ${var.create_vpc ? (var.enable_https ? "https://${aws_lb.main[0].dns_name}/health" : "http://${aws_lb.main[0].dns_name}/health") : "VPC not created"}
    
    # View logs
    aws logs tail /ecs/${var.ecs_task_family} --follow
    
    # Check ECS service status
    aws ecs describe-services --cluster ${aws_ecs_cluster.main.name} --services ${var.create_vpc ? aws_ecs_service.main[0].name : "VPC not created"}
    
    # Push a manual image to ECR (for testing)
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.backend.repository_url}
    docker build -t ${aws_ecr_repository.backend.repository_url}:latest ./backend
    docker push ${aws_ecr_repository.backend.repository_url}:latest
  EOT
}

