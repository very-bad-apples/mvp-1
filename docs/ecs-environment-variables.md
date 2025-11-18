# ECS Container Environment Variables

This document lists all environment variables that are **actually set** in your ECS Fargate container.

---

## ✅ Environment Variables Set in ECS Container

### Regular Environment Variables (from `terraform/ecs.tf`)

These are set directly in the task definition:

| Variable | Value | Source | Description |
|----------|-------|--------|-------------|
| `ENVIRONMENT` | `dev` / `staging` / `prod` | `var.environment` | Environment name |
| `AWS_REGION` | `us-east-1` | `var.aws_region` | AWS region |
| `STORAGE_BACKEND` | `s3` | Hardcoded | Storage backend type |
| `STORAGE_BUCKET` | `bad-apples-video-storage` | `var.bucket_name` | S3 bucket name |
| `PORT` | `8000` | `var.container_port` | Container port |
| `REDIS_URL` | `redis://redis.dev.local:6379/0` | Service discovery | Redis connection URL |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | `var.cors_allowed_origins` | CORS allowed origins (comma-separated) |

### Secrets from AWS Secrets Manager

These are loaded from Secrets Manager at container startup:

| Variable | Secret Key | Description |
|----------|------------|-------------|
| `ANTHROPIC_API_KEY` | `ANTHROPIC_API_KEY` | Anthropic Claude API key |
| `OPENAI_API_KEY` | `OPENAI_API_KEY` | OpenAI API key |
| `REPLICATE_API_KEY` | `REPLICATE_API_KEY` | Replicate API token |
| `REPLICATE_API_TOKEN` | `REPLICATE_API_KEY` | Same as REPLICATE_API_KEY (alias) |
| `ELEVENLABS_API_KEY` | `ELEVENLABS_API_KEY` | ElevenLabs API key |
| `GEMINI_API_KEY` | `GEMINI_API_KEY` | Google Gemini API key |
| `DATABASE_URL` | `DATABASE_URL` | Database connection URL |

---

## 📊 Summary

**Total Environment Variables Set:** 14
- **7 regular** environment variables
- **7 secrets** from Secrets Manager

---

## 🔍 How to Verify

### Option 1: Check Task Definition

```bash
aws ecs describe-task-definition \
  --task-definition bad-apples-backend-task \
  --query 'taskDefinition.containerDefinitions[0].[environment,secrets]' \
  --region us-east-1
```

### Option 2: Check Running Container (if ECS Exec enabled)

```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster bad-apples-cluster \
  --service-name bad-apples-backend-service \
  --query 'taskArns[0]' \
  --output text)

# Execute command to see environment variables
aws ecs execute-command \
  --cluster bad-apples-cluster \
  --task $TASK_ARN \
  --container bad-apples-backend \
  --interactive \
  --command "env | sort"
```

### Option 3: Check CloudWatch Logs

```bash
# Look for environment variable usage in logs
aws logs tail /ecs/bad-apples-backend-task --follow | grep -i "env\|config"
```

---

## ⚠️ Variables Your App Expects But Are NOT Set

Your `backend/config.py` expects these, but they're **NOT** set in ECS (they use defaults):

| Variable | Default Value | Status |
|----------|---------------|--------|
| `REDIS_MAX_CONNECTIONS` | `50` | ❌ Not set (uses default) |
| `REDIS_SOCKET_TIMEOUT` | `5` | ❌ Not set (uses default) |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | `5` | ❌ Not set (uses default) |
| `REDIS_RETRY_ON_TIMEOUT` | `true` | ❌ Not set (uses default) |
| `REDIS_HEALTH_CHECK_INTERVAL` | `30` | ❌ Not set (uses default) |
| `DEBUG` | `false` | ❌ Not set (uses default) |
| `API_HOST` | `0.0.0.0` | ❌ Not set (uses default) |
| `API_PORT` | `8000` | ❌ Not set (uses default) |
| `MV_DEBUG_MODE` | `false` | ❌ Not set (uses default) |
| `MOCK_VID_GENS` | `false` | ❌ Not set (uses default) |
| `ELEVENLABS_VOICE_ID` | `EXAVITQu4vr4xnSDxMaL` | ❌ Not set (uses default) |
| `REPLICATE_MAX_RETRIES` | `3` | ❌ Not set (uses default) |
| `REPLICATE_TIMEOUT` | `600` | ❌ Not set (uses default) |
| `FIREBASE_CREDENTIALS_PATH` | `""` | ❌ Not set (uses default) |
| `AWS_ACCESS_KEY_ID` | `""` | ❌ Not set (uses default) |
| `AWS_SECRET_ACCESS_KEY` | `""` | ❌ Not set (uses default) |
| `PRESIGNED_URL_EXPIRY` | `3600` | ❌ Not set (uses default) |
| `SERVE_FROM_CLOUD` | `false` | ❌ Not set (uses default) |
| `KEEP_INTERMEDIATE_ASSETS` | `true` | ❌ Not set (uses default) |
| `ASSET_BACKUP_LIMIT` | `1` | ❌ Not set (uses default) |
| `FFMPEG_PATH` | `None` | ❌ Not set (uses default) |
| `JOB_TIMEOUT` | `3600` | ❌ Not set (uses default) |
| `JOB_RESULT_TTL` | `86400` | ❌ Not set (uses default) |

**Note:** These use defaults from `config.py`, which is fine for most cases. Add them to ECS if you need to override defaults.

---

## 🔧 How to Add Missing Environment Variables

### Add Regular Environment Variable

Edit `terraform/ecs.tf`:

```hcl
environment = [
  # ... existing variables ...
  {
    name  = "DEBUG"
    value = "true"  # or var.debug_mode
  },
  {
    name  = "API_PORT"
    value = "8000"
  }
]
```

### Add Secret Environment Variable

**Step 1:** Add to Secrets Manager:

```bash
# Get current secret
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --query SecretString --output text)

# Add new key
echo "$CURRENT" | jq '.AWS_ACCESS_KEY_ID = "your-key"' | \
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string file:///dev/stdin
```

**Step 2:** Update `terraform/secrets.tf`:

```hcl
secret_string = jsonencode({
  # ... existing keys ...
  AWS_ACCESS_KEY_ID = var.aws_access_key_id
})
```

**Step 3:** Update `terraform/ecs.tf`:

```hcl
secrets = [
  # ... existing secrets ...
  {
    name      = "AWS_ACCESS_KEY_ID"
    valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:AWS_ACCESS_KEY_ID::"
  }
]
```

**Step 4:** Apply and deploy:

```bash
terraform apply
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

---

## 📋 Complete List (What's Actually Set)

Here's the complete list of environment variables **actually set** in your ECS container:

```bash
# Regular environment variables
ENVIRONMENT=dev
AWS_REGION=us-east-1
STORAGE_BACKEND=s3
STORAGE_BUCKET=bad-apples-video-storage
PORT=8000
REDIS_URL=redis://redis.dev.local:6379/0
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Secrets (from Secrets Manager)
ANTHROPIC_API_KEY=<from-secrets-manager>
OPENAI_API_KEY=<from-secrets-manager>
REPLICATE_API_KEY=<from-secrets-manager>
REPLICATE_API_TOKEN=<from-secrets-manager>
ELEVENLABS_API_KEY=<from-secrets-manager>
GEMINI_API_KEY=<from-secrets-manager>
DATABASE_URL=<from-secrets-manager>
```

---

## 🎯 Quick Reference

**To see what's actually set:**
```bash
# View task definition
aws ecs describe-task-definition \
  --task-definition bad-apples-backend-task \
  --query 'taskDefinition.containerDefinitions[0]' \
  --region us-east-1 | jq '{environment, secrets}'
```

**To see what your app reads:**
```bash
# Check config.py
cat backend/config.py | grep "os.getenv"
```

---

**Last Updated:** 2024

