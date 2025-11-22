# IAM Identity Center Configuration

# Get the IAM Identity Center instance
data "aws_ssoadmin_instances" "main" {}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Create a Permission Set for S3 Read-Only Access
resource "aws_ssoadmin_permission_set" "s3_readonly" {
  name             = "S3ReadOnlyAccess"
  description      = "Grants read-only access to S3 bucket objects"
  instance_arn     = tolist(data.aws_ssoadmin_instances.main.arns)[0]
  session_duration = "PT8H" # 8 hours
}

# Attach inline policy to the Permission Set
resource "aws_ssoadmin_permission_set_inline_policy" "s3_readonly_policy" {
  instance_arn       = tolist(data.aws_ssoadmin_instances.main.arns)[0]
  permission_set_arn = aws_ssoadmin_permission_set.s3_readonly.arn

  inline_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.video_storage.arn}/*"
      }
    ]
  })
}

# Variables for the s3 group
variable "s3_group_id" {
  description = "The ID of the s3 group in IAM Identity Center (find this in the IAM Identity Center console under Groups)"
  type        = string
  # You'll need to provide this value - get it from IAM Identity Center console
}

# Assign the permission set to the s3 group
resource "aws_ssoadmin_account_assignment" "s3_group_assignment" {
  instance_arn       = tolist(data.aws_ssoadmin_instances.main.arns)[0]
  permission_set_arn = aws_ssoadmin_permission_set.s3_readonly.arn

  principal_id   = var.s3_group_id
  principal_type = "GROUP"

  target_id   = data.aws_caller_identity.current.account_id
  target_type = "AWS_ACCOUNT"
}
