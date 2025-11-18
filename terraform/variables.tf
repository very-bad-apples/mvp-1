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
  description = "List of allowed origins for CORS (wildcards not recommended for production)"
  type        = list(string)
  default     = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://badapples.vercel.app"
  ]
  
  # Add your production frontend URLs:
  # Example: ["https://yourdomain.com", "https://www.yourdomain.com", "https://app.yourdomain.com"]
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

# ===== App Runner Configuration =====

variable "app_runner_service_name" {
  description = "Name of the App Runner service"
  type        = string
  default     = "video-generator-api"
}

variable "app_runner_ecr_repo_name" {
  description = "Name of the ECR repository for the application"
  type        = string
  default     = "video-generator-app"
}

variable "worker_ecr_repo_name" {
  description = "Name of the ECR repository for the worker"
  type        = string
  default     = "video-generator-worker"
}

variable "app_runner_cpu" {
  description = "CPU units for App Runner (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "1024"  # 1 vCPU
}

variable "app_runner_memory" {
  description = "Memory for App Runner in MB (512, 1024, 2048, 3072, 4096, 6144, 8192, 10240, 12288)"
  type        = string
  default     = "2048"  # 2 GB
}

variable "app_runner_min_instances" {
  description = "Minimum number of App Runner instances"
  type        = number
  default     = 1
}

variable "app_runner_max_instances" {
  description = "Maximum number of App Runner instances"
  type        = number
  default     = 5
}

variable "app_runner_max_concurrency" {
  description = "Maximum concurrent requests per instance"
  type        = number
  default     = 100
}

variable "app_runner_auto_deploy" {
  description = "Enable automatic deployments when new images are pushed"
  type        = bool
  default     = false
}

variable "app_runner_cors_origins" {
  description = "Allowed CORS origins for App Runner service"
  type        = list(string)
  default     = ["http://localhost:3000"]
}

variable "mock_video_generation" {
  description = "Enable mock video generation (for testing)"
  type        = bool
  default     = false
}

# ===== Secrets Configuration (store these in AWS Secrets Manager) =====

variable "anthropic_api_key" {
  description = "Anthropic API Key (sensitive)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API Key (sensitive)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "replicate_api_key" {
  description = "Replicate API Key (sensitive)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "elevenlabs_api_key" {
  description = "ElevenLabs API Key (sensitive)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Google Gemini API Key (sensitive)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "database_url" {
  description = "Database connection URL"
  type        = string
  default     = "sqlite:///./video_generator.db"
  sensitive   = true
}

variable "redis_url" {
  description = "Redis connection URL"
  type        = string
  default     = ""
  sensitive   = true
}

variable "aws_access_key_id" {
  description = "AWS Access Key ID for S3 access (sensitive)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "aws_secret_access_key" {
  description = "AWS Secret Access Key for S3 access (sensitive)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "api_key" {
  description = "API key for authenticating API requests (sensitive)"
  type        = string
  default     = ""
  sensitive   = true
}

# ===== VPC Configuration (optional) =====

variable "enable_vpc_connector" {
  description = "Enable VPC connector for App Runner"
  type        = bool
  default     = false
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for VPC connector"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "List of security group IDs for VPC connector"
  type        = list(string)
  default     = []
}

variable "custom_domain" {
  description = "Custom domain for App Runner service (requires ACM certificate)"
  type        = string
  default     = ""
}

