# ECS Fargate Service Debugging Guide

## Issues Identified and Fixed

### 1. ✅ Missing Import in main.py (CRITICAL)
**Problem:** Application crashed on startup due to missing `settings` import.
**Fix:** Added `from config import settings` import.
**Impact:** This was causing immediate container crashes.

### 2. ✅ No Container Health Check
**Problem:** ECS had no way to know if the container was healthy during startup.
**Fix:** Added container health check with 60-second start period.
**Impact:** Gives the application time to initialize before health checks fail.

### 3. ✅ Docker Health Check Added
**Problem:** No health check in Dockerfile.
**Fix:** Added HEALTHCHECK directive to Dockerfile.
**Impact:** Better monitoring of container health.

---

## How to Debug Further

### Step 1: Check CloudWatch Logs
```bash
# Check ECS container logs
aws logs tail /ecs/bad-apples-backend-task --follow --region us-east-1

# Or use AWS Console:
# CloudWatch > Log Groups > /ecs/bad-apples-backend-task
```

**Look for:**
- `NameError: name 'settings' is not defined` ← Fixed now
- Import errors
- Redis connection failures
- Database initialization errors
- API key missing errors

### Step 2: Check ECS Service Events
```bash
aws ecs describe-services \
  --cluster bad-apples-cluster \
  --services bad-apples-backend-service \
  --region us-east-1 \
  --query 'services[0].events[0:10]'
```

**Common error messages:**
- `Task failed ELB health checks` → Health endpoint not responding
- `Task failed to start` → Container crash on startup
- `OutOfMemory` → Memory limit exceeded (current: 2GB)
- `Essential container exited` → Application crashed

### Step 3: Check Task Status
```bash
# List tasks
aws ecs list-tasks \
  --cluster bad-apples-cluster \
  --service-name bad-apples-backend-service \
  --region us-east-1

# Describe a specific task (replace TASK_ID)
aws ecs describe-tasks \
  --cluster bad-apples-cluster \
  --tasks TASK_ID \
  --region us-east-1
```

**Check:**
- `lastStatus`: Should be "RUNNING"
- `healthStatus`: Should be "HEALTHY"
- `stoppedReason`: If stopped, this explains why

### Step 4: Verify Docker Image Architecture
```bash
# Check if image was built for correct architecture
aws ecr describe-images \
  --repository-name bad-apples-backend \
  --region us-east-1 \
  --query 'imageDetails[0]'
```

**Important:** Since `use_graviton = true`, the image MUST be built for ARM64.

### Step 5: Test Health Endpoint Locally
```bash
# Test if health endpoint responds quickly
curl -w "\nTime: %{time_total}s\n" http://localhost:8000/health

# Should respond in < 5 seconds (current timeout)
```

### Step 6: Enable ECS Exec for Live Debugging
Update `terraform/ecs_variables.tf`:
```hcl
variable "enable_ecs_exec" {
  default     = true  # Change from false to true
}
```

Then connect to running container:
```bash
aws ecs execute-command \
  --cluster bad-apples-cluster \
  --task TASK_ID \
  --container bad-apples-backend \
  --interactive \
  --command "/bin/bash"
```

---

## Common Issues and Solutions

### Issue 1: Container Keeps Restarting
**Symptoms:** Task stops and restarts repeatedly
**Causes:**
- Application crash on startup
- Failed health checks
- Out of memory

**Solution:**
1. Check CloudWatch logs for errors
2. Verify all environment variables are set correctly
3. Ensure API keys are valid
4. Check Redis connectivity

### Issue 2: Health Check Failures
**Symptoms:** `Task failed ELB health checks in (target-group ...)`
**Causes:**
- App not starting fast enough (< 60 seconds)
- `/health` endpoint not responding
- Port misconfiguration

**Solution:**
1. Increase `startPeriod` in health check (currently 60s)
2. Check if app is binding to correct port (8000)
3. Verify `/health` endpoint returns 200 status

### Issue 3: Out of Memory
**Symptoms:** `OutOfMemory` in task stopped reason
**Current limits:** 2GB memory

**Solution:**
Update `terraform/ecs_variables.tf`:
```hcl
variable "ecs_task_memory" {
  default     = 4096  # Increase to 4GB
}
```

### Issue 4: Redis Connection Failures
**Symptoms:** Logs show Redis connection errors
**Cause:** Redis service not ready or network issues

**Solution:**
1. Check Redis service is running:
```bash
aws ecs list-tasks \
  --cluster bad-apples-cluster \
  --service-name bad-apples-backend-service-redis
```

2. Verify service discovery DNS:
```bash
# The app should connect to: redis.dev.local:6379
# Verify in task environment variable: REDIS_URL
```

### Issue 5: Architecture Mismatch
**Symptoms:** `exec format error` in logs
**Cause:** Docker image built for x86_64 but ECS expects ARM64

**Solution:**
Build multi-architecture image:
```bash
# Build for ARM64 (Graviton)
docker buildx build --platform linux/arm64 -t IMAGE_URI .

# Or build for both architectures
docker buildx build --platform linux/amd64,linux/arm64 -t IMAGE_URI .
```

---

## Immediate Actions to Take

### 1. Rebuild and Deploy
```bash
# Navigate to backend directory
cd backend

# Build Docker image for ARM64
docker buildx build --platform linux/arm64 -t ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/bad-apples-backend:latest .

# Push to ECR
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/bad-apples-backend:latest

# Update ECS service (force new deployment)
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment \
  --region us-east-1
```

### 2. Apply Terraform Changes
```bash
cd terraform
terraform plan
terraform apply
```

### 3. Monitor Deployment
```bash
# Watch service events
aws ecs describe-services \
  --cluster bad-apples-cluster \
  --services bad-apples-backend-service \
  --region us-east-1 \
  --query 'services[0].events[0:5]'

# Watch logs
aws logs tail /ecs/bad-apples-backend-task --follow
```

---

## Additional Configuration Improvements

### 1. Increase Health Check Timeouts (Optional)
If your app needs more time to start, update `terraform/ecs_variables.tf`:
```hcl
variable "health_check_interval" {
  default     = 30  # Check every 30 seconds
}

variable "health_check_timeout" {
  default     = 10  # Increase from 5 to 10 seconds
}

variable "health_check_unhealthy_threshold" {
  default     = 5   # Increase from 3 to 5 (more tolerance)
}
```

### 2. Add CloudWatch Alarms
Monitor service health:
```hcl
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "ecs-backend-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"
  
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.main[0].name
  }
}
```

### 3. Improve Logging
Add more verbose logging in `config.py`:
```python
# Add at the end of Settings class
def validate(self):
    """Validate configuration on startup"""
    errors = []
    
    if not self.REDIS_URL:
        errors.append("REDIS_URL is not set")
    
    if not self.DATABASE_URL:
        errors.append("DATABASE_URL is not set")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")

# Call validation
settings = Settings()
settings.validate()
```

---

## Checklist Before Deploying

- [ ] Fixed missing `settings` import in `main.py`
- [ ] Added container health check to ECS task definition
- [ ] Added health check to Dockerfile
- [ ] Verified Docker image is built for ARM64 (if using Graviton)
- [ ] Checked all required environment variables are set in `ecs.tf`
- [ ] Verified API keys are valid
- [ ] Confirmed Redis service is deployed and running
- [ ] Tested `/health` endpoint responds < 5 seconds
- [ ] Reviewed CloudWatch logs for errors
- [ ] Applied Terraform changes
- [ ] Pushed new Docker image to ECR
- [ ] Forced new deployment of ECS service

---

## Support Resources

- **AWS ECS Documentation:** https://docs.aws.amazon.com/ecs/
- **ECS Troubleshooting Guide:** https://docs.aws.amazon.com/AmazonECS/latest/developerguide/troubleshooting.html
- **CloudWatch Logs Insights:** Use for advanced log analysis

## Quick Diagnostics Commands

```bash
# One-liner to check everything
echo "=== ECS Service Status ===" && \
aws ecs describe-services --cluster bad-apples-cluster --services bad-apples-backend-service --region us-east-1 --query 'services[0].[status,runningCount,desiredCount,deployments[0].status]' && \
echo "\n=== Recent Events ===" && \
aws ecs describe-services --cluster bad-apples-cluster --services bad-apples-backend-service --region us-east-1 --query 'services[0].events[0:3].[createdAt,message]' && \
echo "\n=== Recent Logs ===" && \
aws logs tail /ecs/bad-apples-backend-task --since 10m --region us-east-1
```

---

**Last Updated:** 2024
**Status:** Issues identified and fixes applied

