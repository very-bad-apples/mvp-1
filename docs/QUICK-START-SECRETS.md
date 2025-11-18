# Quick Start: Provide Secret Env Vars to ECS Container

## 🚀 Fastest Method (Using Terraform)

### Step 1: Create `terraform/terraform.tfvars`

```bash
cd terraform
```

Create `terraform.tfvars`:

```hcl
# API Keys
anthropic_api_key  = "sk-ant-api03-..."
openai_api_key     = "sk-..."
replicate_api_key  = "r8_..."
elevenlabs_api_key = "..."
gemini_api_key     = "..."

# Database
database_url = "sqlite:///./video_generator.db"

# CORS
cors_allowed_origins = [
  "http://localhost:3000",
  "https://yourdomain.com"
]
```

### Step 2: Apply Terraform

```bash
terraform init
terraform apply
```

**Done!** Terraform will:
- ✅ Create AWS Secrets Manager secret
- ✅ Store your API keys securely
- ✅ Configure ECS to read secrets
- ✅ Deploy everything

---

## 🔄 Update Secrets Later

### Option 1: Update `terraform.tfvars` and apply
```bash
# Edit terraform.tfvars
vim terraform/terraform.tfvars

# Apply changes
terraform apply

# Force ECS to pick up new secrets
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment \
  --region us-east-1
```

### Option 2: Use AWS CLI directly
```bash
# Update secret in AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string '{
    "ANTHROPIC_API_KEY": "new-key",
    "OPENAI_API_KEY": "new-key"
  }' \
  --region us-east-1

# Force ECS deployment
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

---

## ➕ Add New Secret Variable

### 1. Add to `terraform/variables.tf`:

```hcl
variable "my_new_secret" {
  description = "My new secret"
  type        = string
  default     = ""
  sensitive   = true
}
```

### 2. Add to `terraform/secrets.tf`:

```hcl
secret_string = jsonencode({
  # ... existing keys ...
  MY_NEW_SECRET = var.my_new_secret  # Add this
})
```

### 3. Add to `terraform/ecs.tf`:

```hcl
secrets = [
  # ... existing secrets ...
  {
    name      = "MY_NEW_SECRET"
    valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:MY_NEW_SECRET::"
  }
]
```

### 4. Add to `terraform.tfvars`:

```hcl
my_new_secret = "your-secret-value"
```

### 5. Apply:

```bash
terraform apply
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

---

## ✅ Verify Secrets Are Loaded

```bash
# Check CloudWatch logs for errors
aws logs tail /ecs/bad-apples-backend-task --follow

# Check if service is running
aws ecs describe-services \
  --cluster bad-apples-cluster \
  --services bad-apples-backend-service \
  --query 'services[0].[status,runningCount]'
```

---

## 📚 More Help

- **Full guide:** `docs/ecs-secrets-guide.md`
- **Helper script:** `scripts/setup-secrets.sh`
- **Add new secret:** `scripts/add-secret-env.sh`

---

**That's it!** Your secrets are now securely stored and available to your ECS containers. 🎉

