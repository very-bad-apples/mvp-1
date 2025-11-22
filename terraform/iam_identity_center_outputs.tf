# IAM Identity Center Outputs

output "identity_center_instance_arn" {
  description = "ARN of the IAM Identity Center instance"
  value       = try(tolist(data.aws_ssoadmin_instances.main.arns)[0], "")
}

output "s3_readonly_permission_set_arn" {
  description = "ARN of the S3 Read-Only Permission Set"
  value       = aws_ssoadmin_permission_set.s3_readonly.arn
}

output "s3_readonly_permission_set_name" {
  description = "Name of the S3 Read-Only Permission Set"
  value       = aws_ssoadmin_permission_set.s3_readonly.name
}

output "iam_identity_center_assignment_status" {
  description = "Status of the permission set assignment to the s3 group"
  value       = "Permission set '${aws_ssoadmin_permission_set.s3_readonly.name}' assigned to s3 group (g-murad, g-noah, g-will)"
}
