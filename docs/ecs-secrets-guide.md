# ECS Container Secrets Guide

This guide shows you how to provide secret environment variables to your ECS Fargate containers.

---

## 🎯 Two Methods

### Method 1: AWS Secrets Manager (Recommended) ✅
- ✅ Secrets encrypted at rest
- ✅ Not stored in Terraform state
- ✅ Can be updated without Terraform
- ✅ Audit trail via CloudTrail

### Method 2: Terraform Variables (Simple)
- ✅ Easy to set up
- ⚠️ Secrets stored in Terraform state
- ⚠️ Need Terraform to update

---

## 🔐 Method 1: Using AWS Secrets Manager

### Step 1: Create/Update Secrets

**Option A: Using AWS CLI (Recommended)**

```bash
# Create or update the secret
aws secretsmanager put-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string '{
    "ANTHROPIC_API_KEY": "sk-ant-api03-...",
    "OPENAI_API_KEY": "sk-...",
    "REPLICATE_API_KEY": "r8_...",
    "ELEVENLABS_API_KEY": "...",
    "GEMINI_API_KEY": "...",
    "DATABASE_URL": "sqlite:///./video_generator.db"
  }' \
  --region us-east-1
```

**Option B: Using the Helper Script**

```bash
cd terraform
chmod +x update-secrets.sh
./update-secrets.sh
```

**Option C: Using AWS Console**
1. Go to AWS Secrets Manager
2. Find: `bad-apples-backend-task-secrets`
3. Click "Retrieve secret value" → "Edit"
4. Update JSON and save

### Step 2: Deploy Infrastructure (if not done)

```bash
cd terraform
terraform init
terraform apply
```

This will:
- Create the Secrets Manager secret (if it doesn't exist)
- Configure ECS task to read from Secrets Manager
- Set up IAM permissions

### Step 3: Force ECS to Pick Up New Secrets

```bash
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment \
  --region us-east-1
```

---

## 📝 Method 2: Using Terraform Variables

### Step 1: Create `terraform.tfvars`

```hcl
# terraform/terraform.tfvars
anthropic_api_key  = "sk-ant-api03-..."
openai_api_key     = "sk-..."
replicate_api_key  = "r8_..."
elevenlabs_api_key = "..."
gemini_api_key     = "..."
database_url       = "sqlite:///./video_generator.db"
```

### Step 2: Apply Terraform

```bash
cd terraform
terraform apply
```

**Note:** Secrets will be stored in Terraform state. Make sure:
- `terraform.tfvars` is in `.gitignore`
- Terraform state is stored securely (S3 with encryption)

---

## ➕ Adding New Secret Environment Variables

### For Secrets Manager:

**Step 1:** Update the secret in AWS Secrets Manager:

```bash
# Get current secret
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --query SecretString --output text)

# Add new key
echo "$CURRENT" | jq '.NEW_SECRET_KEY = "value"' | \
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string file:///dev/stdin
```

**Step 2:** Update `terraform/secrets.tf`:

```hcl
resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id

  secret_string = jsonencode({
    ANTHROPIC_API_KEY  = var.anthropic_api_key
    OPENAI_API_KEY     = var.openai_api_key
    # ... existing keys ...
    NEW_SECRET_KEY     = var.new_secret_key  # Add this
  })
}
```

**Step 3:** Update `terraform/ecs.tf`:

```hcl
secrets = [
  # ... existing secrets ...
  {
    name      = "NEW_SECRET_KEY"
    valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:NEW_SECRET_KEY::"
  }
]
```

**Step 4:** Add variable to `terraform/variables.tf`:

```hcl
variable "new_secret_key" {
  description = "New secret key"
  type        = string
  default     = ""
  sensitive   = true
}
```

**Step 5:** Apply and deploy:

```bash
terraform apply
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

---

## 🔍 Verify Secrets Are Loaded

### Check Container Environment Variables

```bash
# Get a running task
TASK_ARN=$(aws ecs list-tasks \
  --cluster bad-apples-cluster \
  --service-name bad-apples-backend-service \
  --query 'taskArns[0]' \
  --output text)

# Check environment variables (if ECS Exec enabled)
aws ecs execute-command \
  --cluster bad-apples-cluster \
  --task $TASK_ARN \
  --container bad-apples-backend \
  --interactive \
  --command "env | grep -E '(ANTHROPIC|OPENAI|REPLICATE|ELEVENLABS|GEMINI|DATABASE)'"
```

### Check CloudWatch Logs

```bash
# Look for errors related to missing secrets
aws logs tail /ecs/bad-apples-backend-task --follow | grep -i "secret\|key\|env"
```

---

## 🛠️ Quick Reference Commands

### Update All Secrets at Once

```bash
# Using helper script
cd terraform
./update-secrets.sh

# Or manually with AWS CLI
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string file://secrets.json
```

### Update Single Secret

```bash
# Get current
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --query SecretString --output text)

# Update one field
echo "$CURRENT" | jq '.ANTHROPIC_API_KEY = "new-value"' | \
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string file:///dev/stdin

# Force deployment
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

### View Current Secrets (Names Only)

```bash
aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --query SecretString \
  --output text | jq 'keys'
```

---

## 🔒 Security Best Practices

1. ✅ **Never commit secrets to Git**
   - Add `terraform.tfvars` to `.gitignore`
   - Use environment variables or Secrets Manager

2. ✅ **Use Secrets Manager for production**
   - More secure than Terraform variables
   - Better audit trail

3. ✅ **Rotate secrets regularly**
   - Update in Secrets Manager
   - Force new ECS deployment

4. ✅ **Limit IAM permissions**
   - Only ECS execution role can read secrets
   - Use least privilege principle

5. ✅ **Monitor secret access**
   ```bash
   # View CloudTrail logs
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=ResourceName,AttributeValue=bad-apples-backend-task-secrets
   ```

---

## 🆘 Troubleshooting

### Issue: "Secrets not found"

**Solution:**
```bash
# Check if secret exists
aws secretsmanager describe-secret \
  --secret-id bad-apples-backend-task-secrets

# If not, create it first
terraform apply -target=aws_secretsmanager_secret.app_secrets
```

### Issue: "Access denied" when reading secrets

**Solution:**
```bash
# Check IAM permissions
aws iam get-role-policy \
  --role-name bad-apples-backend-task-execution-role \
  --policy-name bad-apples-backend-task-secrets-policy

# Verify policy includes secretsmanager:GetSecretValue
```

### Issue: Secrets not updating in container

**Solution:**
```bash
# Force new deployment (secrets are loaded at container startup)
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

---

## 📚 Related Files

- `terraform/secrets.tf` - Secrets Manager configuration
- `terraform/ecs.tf` - ECS task definition with secrets
- `terraform/update-secrets.sh` - Helper script for updating secrets
- `terraform/variables.tf` - Terraform variable definitions

---

**Last Updated:** 2024

