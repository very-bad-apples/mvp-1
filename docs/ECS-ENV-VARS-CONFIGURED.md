# ECS Environment Variables Configuration

## ✅ All Environment Variables Configured

All requested environment variables have been added to the ECS task definition.

### Environment Variables Set

| Variable | Value | Notes |
|----------|-------|-------|
| `AWS_REGION` | `us-east-1` | ✅ Set from `var.aws_region` |
| `SERVE_FROM_CLOUD` | `true` | ✅ Added |
| `MOCK_VID_GENS` | `false` | ✅ Added |
| `DATABASE_URL` | `sqlite:///./video_generator.db` | ✅ Added (moved from secrets) |
| `REDIS_URL` | `redis://redis.dev.local:6379/0` | ✅ Uses service discovery (not localhost) |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001,https://badapples.vercel.app` | ✅ From `var.cors_allowed_origins` |
| `DEBUG` | `true` | ✅ Added |
| `API_HOST` | `0.0.0.0` | ✅ Added |
| `API_PORT` | `8000` | ✅ Added (also `PORT=8000`) |
| `MV_DEBUG_MODE` | `false` | ✅ Added |
| `STORAGE_BACKEND` | `s3` | ✅ Already set |
| `STORAGE_BUCKET` | `video-generator-storage` | ✅ From `var.bucket_name` |

### Additional Environment Variables (Already Set)

- `ENVIRONMENT` - Environment name (dev/staging/prod)
- `PORT` - Container port (8000)

---

## ⚠️ Important Notes

### REDIS_URL
**Note:** You requested `redis://localhost:6379/0`, but in ECS Fargate, Redis runs as a separate service. The configuration uses **service discovery**:
- **Set to:** `redis://redis.dev.local:6379/0`
- This automatically resolves to the Redis container's IP address
- **Do not change to localhost** - it won't work in ECS

### CORS_ORIGINS
- Already includes `https://badapples.vercel.app` (from your `variables.tf` update)
- Trailing slashes are automatically handled by FastAPI CORS middleware

### DATABASE_URL
- **Moved from Secrets Manager to environment variable**
- Now set directly in the task definition
- Removed from secrets array to avoid conflicts

---

## 📋 Complete List of Environment Variables

Your ECS container now has **22 environment variables**:

### Regular Environment Variables (13)
1. `ENVIRONMENT`
2. `AWS_REGION` ✅
3. `STORAGE_BACKEND` ✅
4. `STORAGE_BUCKET` ✅
5. `PORT`
6. `API_PORT` ✅
7. `API_HOST` ✅
8. `REDIS_URL` ✅
9. `CORS_ORIGINS` ✅
10. `SERVE_FROM_CLOUD` ✅
11. `MOCK_VID_GENS` ✅
12. `DEBUG` ✅
13. `MV_DEBUG_MODE` ✅
14. `DATABASE_URL` ✅

### Secrets from AWS Secrets Manager (8)
15. `ANTHROPIC_API_KEY`
16. `OPENAI_API_KEY`
17. `REPLICATE_API_KEY`
18. `REPLICATE_API_TOKEN`
19. `ELEVENLABS_API_KEY`
20. `GEMINI_API_KEY`
21. `AWS_ACCESS_KEY_ID`
22. `AWS_SECRET_ACCESS_KEY`

---

## 🚀 Deploy Changes

### Step 1: Apply Terraform

```bash
cd terraform
terraform plan  # Review changes
terraform apply
```

### Step 2: Force New ECS Deployment

```bash
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment \
  --region us-east-1
```

### Step 3: Verify

```bash
# Check task definition
aws ecs describe-task-definition \
  --task-definition bad-apples-backend-task \
  --query 'taskDefinition.containerDefinitions[0].environment[*].[name,value]' \
  --region us-east-1 \
  --output table

# Check logs
aws logs tail /ecs/bad-apples-backend-task --follow
```

---

## 🔍 Verify Environment Variables

### Check in Running Container (if ECS Exec enabled)

```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster bad-apples-cluster \
  --service-name bad-apples-backend-service \
  --query 'taskArns[0]' \
  --output text)

# Execute command to see env vars
aws ecs execute-command \
  --cluster bad-apples-cluster \
  --task $TASK_ARN \
  --container bad-apples-backend \
  --interactive \
  --command "env | grep -E '(AWS_REGION|SERVE_FROM_CLOUD|MOCK_VID_GENS|DATABASE_URL|REDIS_URL|CORS_ORIGINS|DEBUG|API_HOST|API_PORT|MV_DEBUG_MODE|STORAGE)' | sort"
```

---

## 📝 Changes Made

### Files Updated
- ✅ `terraform/ecs.tf` - Added all new environment variables
- ✅ `terraform/ecs.tf` - Removed `DATABASE_URL` from secrets (now env var)

### Variables Added
- `API_PORT` - Set to container port (8000)
- `API_HOST` - Set to 0.0.0.0
- `SERVE_FROM_CLOUD` - Set to true
- `MOCK_VID_GENS` - Set to false
- `DEBUG` - Set to true
- `MV_DEBUG_MODE` - Set to false
- `DATABASE_URL` - Set to sqlite:///./video_generator.db (moved from secrets)

---

**Configuration Complete!** ✅

All environment variables are now configured and ready to deploy.

