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

