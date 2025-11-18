# Secrets Configuration Summary

## ✅ Configured Secrets in AWS Secrets Manager

All of the following secrets are now configured to be stored in AWS Secrets Manager and automatically injected into your ECS containers:

### API Keys
1. ✅ **ANTHROPIC_API_KEY** - Anthropic Claude API key
2. ✅ **OPENAI_API_KEY** - OpenAI API key
3. ✅ **REPLICATE_API_KEY** - Replicate API token
4. ✅ **ELEVENLABS_API_KEY** - ElevenLabs API key
5. ✅ **GEMINI_API_KEY** - Google Gemini API key

### AWS Credentials
6. ✅ **AWS_ACCESS_KEY_ID** - AWS Access Key ID for S3 access
7. ✅ **AWS_SECRET_ACCESS_KEY** - AWS Secret Access Key for S3 access

### Additional
8. ✅ **DATABASE_URL** - Database connection URL (also in secrets)

---

## 📋 Files Updated

### Terraform Configuration
- ✅ `terraform/variables.tf` - Added `aws_access_key_id` and `aws_secret_access_key` variables
- ✅ `terraform/secrets.tf` - Added AWS credentials to secret string
- ✅ `terraform/ecs.tf` - Added AWS credentials to secrets array

### Helper Scripts
- ✅ `terraform/update-secrets.sh` - Updated to include AWS credentials
- ✅ `terraform/create-secret.sh` - Updated to include AWS credentials
- ✅ `scripts/setup-secrets.sh` - Updated to include AWS credentials
- ✅ `terraform/terraform.tfvars.example` - Added AWS credentials example

---

## 🚀 Next Steps

### Step 1: Set Your Secrets

**Option A: Using Terraform Variables**

Create `terraform/terraform.tfvars`:

```hcl
anthropic_api_key    = "sk-ant-api03-..."
openai_api_key       = "sk-..."
replicate_api_key    = "r8_..."
elevenlabs_api_key   = "..."
gemini_api_key       = "..."
aws_access_key_id    = "AKIA..."
aws_secret_access_key = "..."
database_url         = "sqlite:///./video_generator.db"
```

Then apply:
```bash
cd terraform
terraform apply
```

**Option B: Using Helper Script**

```bash
cd terraform
./update-secrets.sh
```

**Option C: Using AWS CLI Directly**

```bash
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string '{
    "ANTHROPIC_API_KEY": "sk-ant-api03-...",
    "OPENAI_API_KEY": "sk-...",
    "REPLICATE_API_KEY": "r8_...",
    "ELEVENLABS_API_KEY": "...",
    "GEMINI_API_KEY": "...",
    "AWS_ACCESS_KEY_ID": "AKIA...",
    "AWS_SECRET_ACCESS_KEY": "...",
    "DATABASE_URL": "sqlite:///./video_generator.db"
  }' \
  --region us-east-1
```

### Step 2: Deploy to ECS

After setting secrets, force a new deployment:

```bash
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment \
  --region us-east-1
```

---

## 🔍 Verify Secrets Are Set

### Check Secrets Manager

```bash
aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --query SecretString \
  --output text | jq 'keys'
```

Should show:
```json
[
  "ANTHROPIC_API_KEY",
  "AWS_ACCESS_KEY_ID",
  "AWS_SECRET_ACCESS_KEY",
  "DATABASE_URL",
  "ELEVENLABS_API_KEY",
  "GEMINI_API_KEY",
  "OPENAI_API_KEY",
  "REPLICATE_API_KEY"
]
```

### Check ECS Task Definition

```bash
aws ecs describe-task-definition \
  --task-definition bad-apples-backend-task \
  --query 'taskDefinition.containerDefinitions[0].secrets[*].name' \
  --region us-east-1
```

Should show all 8 secrets (including REPLICATE_API_TOKEN which uses REPLICATE_API_KEY).

---

## 📝 Environment Variables in Container

After deployment, your ECS container will have these environment variables:

### Regular Environment Variables (7)
- `ENVIRONMENT`
- `AWS_REGION`
- `STORAGE_BACKEND`
- `STORAGE_BUCKET`
- `PORT`
- `REDIS_URL`
- `CORS_ORIGINS`

### Secrets from Secrets Manager (9)
- `ANTHROPIC_API_KEY` ✅
- `OPENAI_API_KEY` ✅
- `REPLICATE_API_KEY` ✅
- `REPLICATE_API_TOKEN` ✅ (same as REPLICATE_API_KEY)
- `ELEVENLABS_API_KEY` ✅
- `GEMINI_API_KEY` ✅
- `AWS_ACCESS_KEY_ID` ✅
- `AWS_SECRET_ACCESS_KEY` ✅
- `DATABASE_URL` ✅

**Total: 16 environment variables**

---

## ⚠️ Important Notes

### AWS Credentials vs IAM Roles

Your ECS tasks already have an IAM role (`ecs_task_role`) that can access S3. You may not need AWS access keys if:

- ✅ Your S3 bucket is in the same AWS account
- ✅ The IAM role has S3 permissions
- ✅ You're using AWS SDK with default credential chain

**Recommendation:** If your IAM role already has S3 access, you can leave `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` empty. The AWS SDK will automatically use the IAM role.

### Security Best Practices

1. ✅ Never commit `terraform.tfvars` to Git
2. ✅ Rotate secrets regularly
3. ✅ Use IAM roles instead of access keys when possible
4. ✅ Monitor secret access via CloudTrail
5. ✅ Use least privilege for IAM permissions

---

## 🔄 Updating Secrets

To update any secret:

```bash
# Update via helper script
cd terraform
./update-secrets.sh

# Or update directly
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string file://secrets.json

# Force new deployment
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

---

**Configuration Complete!** ✅

All requested secrets are now configured in AWS Secrets Manager and will be automatically injected into your ECS containers.

