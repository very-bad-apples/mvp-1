# ECS Fargate Configuration Variables

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
  default     = "bad-apples-cluster"
}

variable "ecs_service_name" {
  description = "Name of the ECS service"
  type        = string
  default     = "bad-apples-backend-service"
}

variable "ecs_task_family" {
  description = "Family name for the ECS task definition"
  type        = string
  default     = "bad-apples-backend-task"
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "bad-apples-backend"
}

variable "container_name" {
  description = "Name of the container in the task definition"
  type        = string
  default     = "bad-apples-backend"
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8000
}

variable "ecs_task_cpu" {
  description = "CPU units for the ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
  
  validation {
    condition     = contains([256, 512, 1024, 2048, 4096], var.ecs_task_cpu)
    error_message = "Task CPU must be 256, 512, 1024, 2048, or 4096."
  }
}

variable "ecs_task_memory" {
  description = "Memory for the ECS task in MB"
  type        = number
  default     = 2048
  
  validation {
    condition     = var.ecs_task_memory >= 512 && var.ecs_task_memory <= 30720
    error_message = "Task memory must be between 512 and 30720 MB."
  }
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "ecs_min_capacity" {
  description = "Minimum number of tasks for auto-scaling"
  type        = number
  default     = 1
}

variable "ecs_max_capacity" {
  description = "Maximum number of tasks for auto-scaling"
  type        = number
  default     = 4
}

variable "autoscaling_target_cpu" {
  description = "Target CPU utilization percentage for auto-scaling"
  type        = number
  default     = 70
  
  validation {
    condition     = var.autoscaling_target_cpu > 0 && var.autoscaling_target_cpu <= 100
    error_message = "Target CPU must be between 1 and 100."
  }
}

variable "autoscaling_target_memory" {
  description = "Target memory utilization percentage for auto-scaling"
  type        = number
  default     = 80
  
  validation {
    condition     = var.autoscaling_target_memory > 0 && var.autoscaling_target_memory <= 100
    error_message = "Target memory must be between 1 and 100."
  }
}

variable "health_check_path" {
  description = "Health check path for the ALB target group"
  type        = string
  default     = "/health"
}

variable "health_check_interval" {
  description = "Health check interval in seconds"
  type        = number
  default     = 30
}

variable "health_check_timeout" {
  description = "Health check timeout in seconds"
  type        = number
  default     = 5
}

variable "health_check_healthy_threshold" {
  description = "Number of consecutive successful health checks"
  type        = number
  default     = 2
}

variable "health_check_unhealthy_threshold" {
  description = "Number of consecutive failed health checks"
  type        = number
  default     = 3
}

variable "deregistration_delay" {
  description = "Time to wait before deregistering a target in seconds"
  type        = number
  default     = 30
}

variable "enable_ecs_exec" {
  description = "Enable ECS Exec for debugging"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
  
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention must be a valid CloudWatch retention period."
  }
}

variable "alb_idle_timeout" {
  description = "ALB idle timeout in seconds"
  type        = number
  default     = 60
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for ALB"
  type        = bool
  default     = false
}

variable "create_vpc" {
  description = "Create a new VPC for ECS deployment"
  type        = bool
  default     = true
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_https" {
  description = "Enable HTTPS on ALB (requires ACM certificate ARN)"
  type        = bool
  default     = false
}

variable "certificate_arn" {
  description = "ARN of ACM certificate for HTTPS"
  type        = string
  default     = ""
}

variable "use_graviton" {
  description = "Use AWS Graviton (ARM64) processors for better performance and 20% cost savings"
  type        = bool
  default     = true
}

variable "redirect_http_to_https" {
  description = "Redirect HTTP traffic to HTTPS (only applies when enable_https is true)"
  type        = bool
  default     = true
}

# =============================================================================
# WAF (Web Application Firewall) Configuration
# =============================================================================

variable "enable_waf" {
  description = "Enable AWS WAF for ALB protection"
  type        = bool
  default     = false
}

variable "waf_rate_limit" {
  description = "Rate limit per IP (requests per 5 minutes). Set to 0 to disable. Recommended: 2000"
  type        = number
  default     = 0
  
  validation {
    condition     = var.waf_rate_limit >= 0 && var.waf_rate_limit <= 100000
    error_message = "Rate limit must be between 0 and 100000."
  }
}

variable "waf_allowed_ips" {
  description = "List of IP addresses/CIDR blocks to whitelist (e.g., [\"1.2.3.4/32\", \"5.6.7.0/24\"])"
  type        = list(string)
  default     = []
}

variable "waf_blocked_ips" {
  description = "List of IP addresses/CIDR blocks to blacklist"
  type        = list(string)
  default     = []
}

# =============================================================================
# ALB Authentication Configuration
# =============================================================================

variable "enable_alb_auth" {
  description = "Enable authentication on ALB (Cognito or OIDC)"
  type        = bool
  default     = false
}

variable "alb_auth_type" {
  description = "Type of authentication: 'cognito' or 'oidc'"
  type        = string
  default     = "cognito"
  
  validation {
    condition     = contains(["cognito", "oidc"], var.alb_auth_type)
    error_message = "Auth type must be 'cognito' or 'oidc'."
  }
}

variable "alb_auth_priority" {
  description = "Priority for authentication listener rule (lower = higher priority)"
  type        = number
  default     = 100
}

variable "alb_auth_paths" {
  description = "List of paths to protect with authentication (empty = all paths). Example: ['/admin/*', '/api/secure/*']"
  type        = list(string)
  default     = []  # Empty = protect all paths
}

# =============================================================================
# Cognito Configuration
# =============================================================================

variable "cognito_user_pool_name" {
  description = "Name of the Cognito User Pool"
  type        = string
  default     = "bad-apples-users"
}

variable "cognito_user_pool_domain" {
  description = "Domain name for Cognito User Pool (must be globally unique)"
  type        = string
  default     = "bad-apples-auth"
}

variable "cognito_callback_urls" {
  description = "Allowed callback URLs for Cognito OAuth"
  type        = list(string)
  default     = ["https://*"]  # Allow all HTTPS URLs
}

variable "cognito_logout_urls" {
  description = "Allowed logout URLs for Cognito OAuth"
  type        = list(string)
  default     = ["https://*"]
}

variable "cognito_scope" {
  description = "OAuth scopes for Cognito authentication"
  type        = string
  default     = "openid email profile"
}

variable "cognito_session_cookie_name" {
  description = "Name of the session cookie"
  type        = string
  default     = "AWSELBAuthSessionCookie"
}

variable "cognito_session_timeout" {
  description = "Session timeout in seconds (default: 7 days)"
  type        = number
  default     = 604800
}

variable "cognito_access_token_validity" {
  description = "Access token validity in minutes"
  type        = number
  default     = 60
}

variable "cognito_id_token_validity" {
  description = "ID token validity in minutes"
  type        = number
  default     = 60
}

variable "cognito_refresh_token_validity" {
  description = "Refresh token validity in days"
  type        = number
  default     = 30
}

variable "cognito_enable_mfa" {
  description = "Enable Multi-Factor Authentication for Cognito"
  type        = bool
  default     = false
}

# =============================================================================
# OIDC Configuration
# =============================================================================

variable "oidc_issuer" {
  description = "OIDC issuer URL (e.g., https://accounts.google.com)"
  type        = string
  default     = ""
}

variable "oidc_authorization_endpoint" {
  description = "OIDC authorization endpoint URL"
  type        = string
  default     = ""
}

variable "oidc_token_endpoint" {
  description = "OIDC token endpoint URL"
  type        = string
  default     = ""
}

variable "oidc_user_info_endpoint" {
  description = "OIDC user info endpoint URL"
  type        = string
  default     = ""
}

variable "oidc_client_id" {
  description = "OIDC client ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "oidc_client_secret" {
  description = "OIDC client secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "oidc_scope" {
  description = "OIDC scopes (e.g., 'openid email profile')"
  type        = string
  default     = "openid email profile"
}

variable "oidc_session_cookie_name" {
  description = "Name of the OIDC session cookie"
  type        = string
  default     = "AWSELBAuthSessionCookie"
}

variable "oidc_session_timeout" {
  description = "OIDC session timeout in seconds"
  type        = number
  default     = 604800
}

# =============================================================================
# CORS Configuration (defined in main variables.tf but documented here)
# =============================================================================
# 
# CORS (Cross-Origin Resource Sharing) settings are configured via the
# cors_allowed_origins variable in terraform/variables.tf
# 
# To add production URLs:
# 1. Edit terraform/terraform.tfvars
# 2. Add your frontend URLs to cors_allowed_origins list
# 3. Run: terraform apply
# 
# Example:
#   cors_allowed_origins = [
#     "http://localhost:3000",
#     "https://yourdomain.com",
#     "https://www.yourdomain.com"
#   ]
# 
# =============================================================================

