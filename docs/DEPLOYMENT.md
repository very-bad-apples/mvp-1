# AWS ECS Fargate Deployment Guide

Complete guide for deploying the backend application to AWS ECS Fargate with automated CI/CD using GitHub Actions.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Deploy Infrastructure](#deploy-infrastructure)
- [Configure GitHub Secrets](#configure-github-secrets)
- [Deploy Application](#deploy-application)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)
- [Cost Estimation](#cost-estimation)

## Architecture Overview

### Components

```
┌─────────────────┐
│  GitHub Actions │ ──► Build & Push Docker Image
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Amazon ECR    │ ──► Container Registry
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│   ECS Fargate   │ ◄──►│     ALB      │ ──► Internet
│   (1-4 tasks)   │     │ Load Balancer│
└────────┬────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐
│   CloudWatch    │ ──► Logs & Metrics
└─────────────────┘
```

### Specifications

- **Compute**: AWS ECS Fargate (1 vCPU / 2 GB RAM)
- **Auto-scaling**: 1-4 tasks (CPU target: 70%)
- **Load Balancer**: Application Load Balancer (HTTP/HTTPS)
- **Logging**: CloudWatch Logs (7-day retention)
- **Networking**: VPC with public/private subnets, NAT gateways
- **Security**: Security groups, IAM roles, encrypted storage

## Prerequisites

### Required Tools

1. **AWS Account** - Active AWS account with billing enabled
2. **Terraform** - Version 1.0 or higher
3. **AWS CLI** - Version 2.x
4. **Docker** - For local testing
5. **Git** - Version control

### Install Tools

#### Windows (PowerShell)

```powershell
# Install Chocolatey (if not already installed)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

# Install tools
choco install terraform awscli docker-desktop git -y
```

#### macOS

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install tools
brew install terraform awscli docker git
```

#### Linux (Ubuntu/Debian)

```bash
# Terraform
wget https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip
unzip terraform_1.7.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Docker
sudo apt-get update
sudo apt-get install docker.io docker-compose -y
```

### Configure AWS CLI

```bash
# Configure AWS credentials
aws configure

# You'll be prompted for:
# AWS Access Key ID: [Your AWS access key]
# AWS Secret Access Key: [Your secret key]
# Default region name: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

## Initial Setup

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd mvp-1
```

### 2. Review Configuration

Edit Terraform variables if needed:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
# Basic Configuration
aws_region      = "us-east-1"
environment     = "prod"
bucket_name     = "your-unique-bucket-name"  # Must be globally unique

# ECS Configuration
ecs_cluster_name    = "bad-apples-cluster"
ecs_service_name    = "bad-apples-backend-service"
ecr_repository_name = "bad-apples-backend"

# Resource Sizing
ecs_task_cpu    = 1024  # 1 vCPU
ecs_task_memory = 2048  # 2 GB RAM

# Auto-scaling
ecs_min_capacity = 1
ecs_max_capacity = 4
autoscaling_target_cpu = 70

# Optional: Enable HTTPS (requires ACM certificate)
enable_https    = false
certificate_arn = ""
```

## Deploy Infrastructure

### Step 1: Initialize Terraform

```bash
cd terraform
terraform init
```

This downloads the AWS provider and initializes the backend.

### Step 2: Review Planned Changes

```bash
terraform plan
```

Review the output. You should see resources being created:
- ECR repository
- ECS cluster, service, and task definition
- VPC with subnets and NAT gateways
- Application Load Balancer
- Security groups
- IAM roles and policies
- CloudWatch log groups

### Step 3: Apply Infrastructure

```bash
terraform apply
```

Type `yes` when prompted.

**Time**: This takes approximately 5-8 minutes.

### Step 4: Save Outputs

```bash
# View all outputs
terraform output

# Save GitHub secrets configuration
terraform output -raw github_secrets_config > github-secrets.txt

# Get ALB URL
terraform output -raw alb_url
```

**Important**: Keep the GitHub secrets configuration secure. You'll need it in the next step.

## Configure GitHub Secrets

GitHub Actions needs AWS credentials to deploy. Add these secrets to your GitHub repository.

### 1. Navigate to GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**

### 2. Add Required Secrets

Add each of these secrets (get values from `terraform output`):

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `AWS_ACCESS_KEY_ID` | GitHub Actions access key | `terraform output github_actions_access_key_id` |
| `AWS_SECRET_ACCESS_KEY` | GitHub Actions secret key | `terraform output -raw github_actions_secret_access_key` |
| `AWS_REGION` | AWS region | `us-east-1` (or your region) |

**Note**: The workflow already has the correct ECR, ECS cluster, and service names configured.

### 3. Add Application Secrets (Optional)

If your application needs API keys or database URLs, add them as environment variables in the ECS task definition:

Edit `terraform/ecs.tf` and add to the `environment` section:

```hcl
environment = [
  # ... existing variables ...
  {
    name  = "ANTHROPIC_API_KEY"
    value = var.anthropic_api_key
  },
  {
    name  = "REDIS_URL"
    value = var.redis_url
  }
]
```

Or use AWS Secrets Manager for sensitive values (recommended for production):

```hcl
secrets = [
  {
    name      = "ANTHROPIC_API_KEY"
    valueFrom = "arn:aws:secretsmanager:us-east-1:123456789:secret:anthropic-key"
  }
]
```

## Deploy Application

### Option 1: Deploy via GitHub (Recommended)

The easiest way to deploy is to push to the `main` branch:

```bash
# Make sure you're on main branch
git checkout main

# Push changes
git add .
git commit -m "Initial deployment"
git push origin main
```

GitHub Actions will automatically:
1. Build the Docker image
2. Push to ECR
3. Update ECS service
4. Wait for deployment to stabilize

**Time**: Deployment takes 5-10 minutes.

### Option 2: Manual Deployment

For testing or troubleshooting, deploy manually:

```bash
# Get ECR repository URL
export ECR_REPO=$(terraform output -raw ecr_repository_url)
export AWS_REGION=us-east-1
export ECS_CLUSTER=$(terraform output -raw ecs_cluster_name)
export ECS_SERVICE=$(terraform output -raw ecs_service_name)

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REPO

# Build and push image
cd ../backend
docker build -t $ECR_REPO:latest .
docker push $ECR_REPO:latest

# Force new deployment
cd ../terraform
aws ecs update-service \
  --cluster $ECS_CLUSTER \
  --service $ECS_SERVICE \
  --force-new-deployment
```

### Verify Deployment

```bash
# Get application URL
export APP_URL=$(terraform output -raw alb_url)

# Test health endpoint
curl $APP_URL/health

# Expected response:
# {"status": "healthy"}
```

## Monitoring and Maintenance

### View Logs

#### Using AWS Console

1. Go to [CloudWatch Console](https://console.aws.amazon.com/cloudwatch/)
2. Navigate to **Logs** → **Log groups**
3. Find `/ecs/bad-apples-backend-task`
4. View log streams

#### Using AWS CLI

```bash
# Tail logs (like `tail -f`)
aws logs tail /ecs/bad-apples-backend-task --follow

# View recent logs
aws logs tail /ecs/bad-apples-backend-task --since 1h

# Search logs
aws logs filter-log-events \
  --log-group-name /ecs/bad-apples-backend-task \
  --filter-pattern "ERROR"
```

### Monitor ECS Service

```bash
# Check service status
aws ecs describe-services \
  --cluster bad-apples-cluster \
  --services bad-apples-backend-service

# List running tasks
aws ecs list-tasks \
  --cluster bad-apples-cluster \
  --service-name bad-apples-backend-service

# View task details
aws ecs describe-tasks \
  --cluster bad-apples-cluster \
  --tasks <task-id>
```

### Check Auto-scaling

```bash
# View auto-scaling policies
aws application-autoscaling describe-scaling-policies \
  --service-namespace ecs \
  --resource-id service/bad-apples-cluster/bad-apples-backend-service

# View current capacity
aws application-autoscaling describe-scalable-targets \
  --service-namespace ecs \
  --resource-ids service/bad-apples-cluster/bad-apples-backend-service
```

### CloudWatch Metrics

Key metrics to monitor:
- **CPUUtilization**: Should stay below 70% (auto-scaling threshold)
- **MemoryUtilization**: Should stay below 80%
- **TargetResponseTime**: Request latency
- **HealthyHostCount**: Number of healthy tasks
- **RequestCount**: Total requests

### Update Application

To update the application, simply push changes to `main`:

```bash
git add .
git commit -m "Update feature X"
git push origin main
```

GitHub Actions will automatically deploy the update with zero downtime.

### Rollback Deployment

If a deployment fails, rollback to the previous version:

```bash
# List task definitions
aws ecs list-task-definitions \
  --family-prefix bad-apples-backend-task

# Update service to use previous version
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --task-definition bad-apples-backend-task:X  # Replace X with previous version
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

**Symptom**: Tasks start but immediately stop.

**Solution**:
```bash
# Check task logs
aws logs tail /ecs/bad-apples-backend-task --since 10m

# Common issues:
# - Port mismatch (check container_port in terraform)
# - Missing environment variables
# - Application crash on startup
```

#### 2. Health Check Failing

**Symptom**: Tasks are unhealthy and keep restarting.

**Solution**:
```bash
# Test health endpoint locally
curl http://<alb-dns>/health

# Check if /health endpoint exists in your app
# Verify health_check_path in terraform/ecs_variables.tf
```

#### 3. Can't Access Application

**Symptom**: Cannot reach ALB URL.

**Solution**:
```bash
# Check security groups
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=*alb-sg*"

# Verify ALB is active
aws elbv2 describe-load-balancers \
  --names bad-apples-cluster-alb

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>
```

#### 4. Deployment Timeout

**Symptom**: GitHub Actions times out during deployment.

**Solution**:
```bash
# Increase wait time in .github/workflows/deploy-backend.yml
# Change wait-for-minutes: 10 to wait-for-minutes: 15

# Or check ECS service events
aws ecs describe-services \
  --cluster bad-apples-cluster \
  --services bad-apples-backend-service \
  --query 'services[0].events[0:10]'
```

#### 5. Out of Memory

**Symptom**: Tasks crash with exit code 137.

**Solution**:
- Increase task memory in `terraform/ecs_variables.tf`:
```hcl
ecs_task_memory = 4096  # Increase to 4 GB
```
- Run `terraform apply` to update

#### 6. Image Pull Errors

**Symptom**: "Unable to pull image" errors.

**Solution**:
```bash
# Verify ECR permissions
aws ecr describe-repositories --repository-names bad-apples-backend

# Check if image exists
aws ecr list-images --repository-name bad-apples-backend

# Re-push image
./docs/test-deployment.sh
```

### Debug with ECS Exec

Enable ECS Exec for interactive debugging:

```bash
# Enable in terraform
# Set enable_ecs_exec = true in terraform.tfvars
terraform apply

# Connect to running task
TASK_ID=$(aws ecs list-tasks --cluster bad-apples-cluster --service bad-apples-backend-service --query 'taskArns[0]' --output text)

aws ecs execute-command \
  --cluster bad-apples-cluster \
  --task $TASK_ID \
  --container bad-apples-backend \
  --interactive \
  --command "/bin/sh"
```

### Get Support

1. Check CloudWatch logs first
2. Review ECS service events
3. Verify security groups and IAM permissions
4. Test locally with Docker

## Cost Estimation

### Monthly Costs (us-east-1)

#### Minimal Usage (1 task, low traffic)
- **Fargate**: ~$14.40/month (1 vCPU, 2GB, 100% uptime)
- **ALB**: ~$16.20/month (base)
- **NAT Gateway**: ~$32.40/month (per AZ, 2 AZs = $64.80)
- **Data Transfer**: ~$1-5/month (first 100GB free)
- **ECR Storage**: ~$0.50/month (5GB images)
- **CloudWatch Logs**: ~$0.50/month (1GB logs)

**Total**: ~$97/month

#### Moderate Usage (2 tasks average, moderate traffic)
- **Fargate**: ~$28.80/month (2 tasks)
- **ALB**: ~$18/month (with LCU charges)
- **NAT Gateway**: ~$64.80/month
- **Data Transfer**: ~$5-10/month
- **ECR Storage**: ~$1/month
- **CloudWatch Logs**: ~$1-2/month

**Total**: ~$118-125/month

#### High Usage (4 tasks average, high traffic)
- **Fargate**: ~$57.60/month (4 tasks)
- **ALB**: ~$25/month (higher LCU)
- **NAT Gateway**: ~$64.80/month
- **Data Transfer**: ~$20-50/month
- **ECR Storage**: ~$2/month
- **CloudWatch Logs**: ~$3-5/month

**Total**: ~$172-205/month

### Cost Optimization Tips

1. **Reduce NAT Gateway Costs**
   - Use VPC endpoints for AWS services (S3, ECR)
   - Use single AZ for dev/staging (not recommended for prod)

2. **Optimize Fargate Usage**
   - Reduce task size if possible (512 CPU / 1GB RAM)
   - Set aggressive scale-in policies
   - Use Fargate Spot for non-critical workloads (70% discount)

3. **Reduce Data Transfer**
   - Use CloudFront CDN for static assets
   - Enable compression in ALB
   - Use same region for all services

4. **Clean Up Resources**
   - Delete old ECR images (lifecycle policy already configured)
   - Reduce CloudWatch log retention (7 days → 3 days)

### Example Cost Reduction

For dev/testing, modify `terraform/ecs_variables.tf`:

```hcl
ecs_task_cpu      = 512   # 0.5 vCPU
ecs_task_memory   = 1024  # 1 GB
ecs_min_capacity  = 1
ecs_max_capacity  = 2
log_retention_days = 3

# Use single AZ (not for production!)
# Modify terraform/ecs.tf to create only 1 subnet/NAT
```

**New cost**: ~$40-50/month

## Clean Up

To destroy all infrastructure:

```bash
cd terraform

# Backup important data first!
aws s3 sync s3://your-bucket-name/ ./backup/

# Destroy infrastructure
terraform destroy
```

Type `yes` when prompted.

**Warning**: This deletes everything including:
- All ECS tasks and services
- Load balancer
- VPC and networking
- ECR images
- CloudWatch logs
- IAM roles

## Next Steps

1. **Custom Domain**: Set up Route53 and ACM certificate for HTTPS
2. **Secrets Management**: Move API keys to AWS Secrets Manager
3. **Monitoring**: Set up CloudWatch alarms and dashboards
4. **CI/CD**: Add staging environment and approval workflows
5. **Database**: Add RDS or DynamoDB for persistent storage
6. **Caching**: Add ElastiCache Redis for better performance

## Support Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [GitHub Actions Documentation](https://docs.github.com/actions)

---

**Last Updated**: November 2024  
**Maintained by**: Gauntlet MVP Team

