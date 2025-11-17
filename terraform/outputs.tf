output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.video_storage.id
}

output "bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.video_storage.arn
}

output "bucket_region" {
  description = "Region of the S3 bucket"
  value       = aws_s3_bucket.video_storage.region
}

output "iam_user_name" {
  description = "Name of the IAM user"
  value       = aws_iam_user.video_generator_app.name
}

output "iam_user_arn" {
  description = "ARN of the IAM user"
  value       = aws_iam_user.video_generator_app.arn
}

output "access_key_id" {
  description = "AWS Access Key ID for the application user"
  value       = aws_iam_access_key.video_generator_app.id
  sensitive   = false  # Not sensitive, just the ID
}

output "secret_access_key" {
  description = "AWS Secret Access Key for the application user (SENSITIVE - Store securely!)"
  value       = aws_iam_access_key.video_generator_app.secret
  sensitive   = true
}

output "env_file_config" {
  description = "Configuration to add to your .env file"
  value       = <<-EOT
    # Add these to your backend/.env file:
    STORAGE_BACKEND=s3
    STORAGE_BUCKET=${aws_s3_bucket.video_storage.id}
    AWS_ACCESS_KEY_ID=${aws_iam_access_key.video_generator_app.id}
    AWS_SECRET_ACCESS_KEY=${aws_iam_access_key.video_generator_app.secret}
    AWS_REGION=${var.aws_region}
  EOT
  sensitive   = true
}

# ===== App Runner Outputs =====

output "ecr_repository_url_app" {
  description = "ECR repository URL for the application"
  value       = aws_ecr_repository.video_generator_app.repository_url
}

output "ecr_repository_url_worker" {
  description = "ECR repository URL for the worker"
  value       = aws_ecr_repository.video_generator_worker.repository_url
}

output "app_runner_service_url" {
  description = "URL of the App Runner service"
  value       = "https://${aws_apprunner_service.video_generator.service_url}"
}

output "app_runner_service_id" {
  description = "ID of the App Runner service"
  value       = aws_apprunner_service.video_generator.service_id
}

output "app_runner_service_arn" {
  description = "ARN of the App Runner service"
  value       = aws_apprunner_service.video_generator.arn
}

output "app_runner_status" {
  description = "Status of the App Runner service"
  value       = aws_apprunner_service.video_generator.status
}

output "secrets_manager_secret_arn" {
  description = "ARN of the Secrets Manager secret for app configuration"
  value       = aws_secretsmanager_secret.app_config.arn
}

output "deployment_summary" {
  description = "Summary of deployment information"
  value       = <<-EOT
    ==========================================
    AWS App Runner Deployment Summary
    ==========================================
    
    Service URL: https://${aws_apprunner_service.video_generator.service_url}
    Service Name: ${aws_apprunner_service.video_generator.service_name}
    Service Status: ${aws_apprunner_service.video_generator.status}
    
    ECR Repositories:
    - App: ${aws_ecr_repository.video_generator_app.repository_url}
    - Worker: ${aws_ecr_repository.video_generator_worker.repository_url}
    
    S3 Bucket: ${aws_s3_bucket.video_storage.id}
    Region: ${var.aws_region}
    
    Next Steps:
    1. Build and push Docker images to ECR
    2. Update secrets in AWS Secrets Manager
    3. Monitor deployment in App Runner console
    
    For detailed deployment instructions, see: terraform/DEPLOYMENT.md
    ==========================================
  EOT
}

