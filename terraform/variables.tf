variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Name of the S3 bucket (must be globally unique)"
  type        = string
  default     = "video-generator-storage"  # Default bucket name
  
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]*[a-z0-9]$", var.bucket_name))
    error_message = "Bucket name must be lowercase alphanumeric with hyphens, and must start/end with alphanumeric character."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "iam_user_name" {
  description = "IAM user name for the application"
  type        = string
  default     = "video-generator-app"
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["http://localhost:3000", "http://localhost:8000"]
}

variable "asset_retention_days" {
  description = "Number of days to retain video assets before expiration (0 = never expire)"
  type        = number
  default     = 0  # Keep forever by default
}

variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring and alarms"
  type        = bool
  default     = false
}

variable "bucket_size_alarm_threshold_gb" {
  description = "Bucket size threshold in GB for CloudWatch alarm"
  type        = number
  default     = 100
}

