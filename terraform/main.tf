terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  # Optional: Use AWS profile if you have multiple AWS accounts
  # profile = "your-profile-name"
}

# S3 Bucket for Video Storage
resource "aws_s3_bucket" "video_storage" {
  bucket = var.bucket_name

  tags = {
    Name        = "AI Video Generator Storage"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "bad-apples-mvp"
  }
}

# Enable versioning for the bucket
resource "aws_s3_bucket_versioning" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Configure server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access (recommended for security)
resource "aws_s3_bucket_public_access_block" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS configuration for web access
resource "aws_s3_bucket_cors_configuration" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    allowed_origins = ["*"]  # Allow all origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Lifecycle policy to manage old versions and incomplete uploads
resource "aws_s3_bucket_lifecycle_configuration" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "cleanup-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Optional: Delete old backups after retention period
  rule {
    id     = "expire-old-backups"
    status = "Enabled"

    filter {
      prefix = "videos/"
    }

    expiration {
      days = var.asset_retention_days
    }
  }
}

# IAM User for Application
resource "aws_iam_user" "video_generator_app" {
  name = var.iam_user_name

  tags = {
    Name        = "Video Generator Application User"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# IAM Policy for S3 Access (Least Privilege)
resource "aws_iam_policy" "video_storage_access" {
  name        = "${var.iam_user_name}-s3-access"
  description = "Policy for video generator app to access S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:ListBucketMultipartUploads",
          "s3:ListBucketVersions",
          "s3:GetBucketVersioning",
          "s3:GetBucketAcl",
          "s3:GetBucketCORS"
        ]
        Resource = aws_s3_bucket.video_storage.arn
      },
      {
        Sid    = "ObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:GetObject",
          "s3:GetObjectAcl",
          "s3:GetObjectAttributes",
          "s3:DeleteObject",
          "s3:GetObjectVersion",
          "s3:DeleteObjectVersion",
          "s3:ListMultipartUploadParts",
          "s3:AbortMultipartUpload"
        ]
        Resource = "${aws_s3_bucket.video_storage.arn}/*"
      },
      {
        Sid    = "ObjectCopy"
        Effect = "Allow"
        Action = [
          "s3:CopyObject"
        ]
        Resource = "${aws_s3_bucket.video_storage.arn}/*"
      }
    ]
  })
}

# Attach Policy to User
resource "aws_iam_user_policy_attachment" "video_storage_access" {
  user       = aws_iam_user.video_generator_app.name
  policy_arn = aws_iam_policy.video_storage_access.arn
}

# Create Access Key for User
resource "aws_iam_access_key" "video_generator_app" {
  user = aws_iam_user.video_generator_app.name
}

# Optional: CloudWatch metric for bucket size monitoring
resource "aws_cloudwatch_metric_alarm" "bucket_size" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${var.bucket_name}-size-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BucketSizeBytes"
  namespace           = "AWS/S3"
  period              = "86400"  # 24 hours
  statistic           = "Average"
  threshold           = var.bucket_size_alarm_threshold_gb * 1073741824  # Convert GB to bytes
  alarm_description   = "Alert when bucket size exceeds threshold"

  dimensions = {
    BucketName  = aws_s3_bucket.video_storage.id
    StorageType = "StandardStorage"
  }
}

# =============================================================================
# IAM User and Policy for GitHub Actions CI/CD
# =============================================================================

# IAM User for GitHub Actions
resource "aws_iam_user" "github_actions" {
  name = "${var.ecs_cluster_name}-github-actions"

  tags = {
    Name        = "GitHub Actions CI/CD User"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "ECR and ECS deployment"
  }
}

# IAM Policy for GitHub Actions - ECR Push Access
resource "aws_iam_policy" "github_actions_ecr" {
  name        = "${var.ecs_cluster_name}-github-actions-ecr"
  description = "Policy for GitHub Actions to push images to ECR"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRAuthToken"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Sid    = "ECRPushPull"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = aws_ecr_repository.backend.arn
      }
    ]
  })
}

# IAM Policy for GitHub Actions - ECS Deployment Access
resource "aws_iam_policy" "github_actions_ecs" {
  name        = "${var.ecs_cluster_name}-github-actions-ecs"
  description = "Policy for GitHub Actions to deploy to ECS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECSDescribe"
        Effect = "Allow"
        Action = [
          "ecs:DescribeTaskDefinition",
          "ecs:DescribeServices",
          "ecs:DescribeClusters"
        ]
        Resource = "*"
      },
      {
        Sid    = "ECSRegisterTaskDefinition"
        Effect = "Allow"
        Action = [
          "ecs:RegisterTaskDefinition"
        ]
        Resource = "*"
      },
      {
        Sid    = "ECSUpdateService"
        Effect = "Allow"
        Action = [
          "ecs:UpdateService"
        ]
        Resource = aws_ecs_service.main[0].id
      },
      {
        Sid    = "PassRole"
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_task.arn
        ]
      }
    ]
  })
}

# Attach ECR policy to GitHub Actions user
resource "aws_iam_user_policy_attachment" "github_actions_ecr" {
  user       = aws_iam_user.github_actions.name
  policy_arn = aws_iam_policy.github_actions_ecr.arn
}

# Attach ECS policy to GitHub Actions user
resource "aws_iam_user_policy_attachment" "github_actions_ecs" {
  user       = aws_iam_user.github_actions.name
  policy_arn = aws_iam_policy.github_actions_ecs.arn
}

# Create Access Key for GitHub Actions
resource "aws_iam_access_key" "github_actions" {
  user = aws_iam_user.github_actions.name
}

