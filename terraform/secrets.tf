# =============================================================================
# AWS Secrets Manager for Application Secrets
# =============================================================================

# Create a single secret to store all API keys
resource "aws_secretsmanager_secret" "app_secrets" {
  name        = "${var.ecs_task_family}-secrets"
  description = "Application secrets for ${var.ecs_task_family}"

  recovery_window_in_days = 7  # Can be recovered within 7 days if deleted

  tags = {
    Name        = "${var.ecs_task_family}-secrets"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Store the secret values
resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id

  secret_string = jsonencode({
    ANTHROPIC_API_KEY    = var.anthropic_api_key
    OPENAI_API_KEY       = var.openai_api_key
    REPLICATE_API_KEY    = var.replicate_api_key
    ELEVENLABS_API_KEY   = var.elevenlabs_api_key
    GEMINI_API_KEY       = var.gemini_api_key
    AWS_ACCESS_KEY_ID    = var.aws_access_key_id
    AWS_SECRET_ACCESS_KEY = var.aws_secret_access_key
    API_KEY              = var.api_key
    DATABASE_URL         = var.database_url
  })

  # Lifecycle to prevent recreation on every apply if values haven't changed
  lifecycle {
    ignore_changes = [secret_string]
  }
}

# =============================================================================
# IAM Policy for ECS Task Execution Role to Read Secrets
# =============================================================================

resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${var.ecs_task_family}-secrets-policy"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.app_secrets.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = "*"  # Required for default AWS managed keys
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# =============================================================================
# Outputs
# =============================================================================

output "secrets_manager_arn" {
  description = "ARN of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.app_secrets.arn
}

output "secrets_manager_name" {
  description = "Name of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.app_secrets.name
}

