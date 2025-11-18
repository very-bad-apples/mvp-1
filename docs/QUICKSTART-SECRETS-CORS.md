# Quick Start: Secrets & CORS Setup

This is a quick reference for setting up secrets and CORS. For detailed documentation, see [secrets-and-cors-setup.md](./secrets-and-cors-setup.md).

---

## 🚀 5-Minute Setup

### Step 1: Deploy Infrastructure

```bash
cd terraform
terraform init
terraform apply
```

### Step 2: Set Your API Keys

**Option A: Using the helper script (Recommended)**
```bash
cd terraform
chmod +x update-secrets.sh
./update-secrets.sh
```

**Option B: Using AWS CLI**
```bash
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string '{
    "ANTHROPIC_API_KEY": "your-key",
    "OPENAI_API_KEY": "your-key",
    "REPLICATE_API_KEY": "your-key",
    "ELEVENLABS_API_KEY": "your-key",
    "GEMINI_API_KEY": "your-key",
    "DATABASE_URL": "sqlite:///./video_generator.db"
  }' \
  --region us-east-1
```

### Step 3: Deploy with New Secrets

```bash
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment \
  --region us-east-1
```

### Step 4: Configure CORS (Optional)

Edit `terraform/terraform.tfvars`:
```hcl
cors_allowed_origins = [
  "http://localhost:3000",
  "https://yourdomain.com"  # Add your frontend URL
]
```

Apply:
```bash
terraform apply
```

---

## 🔑 Where to Get API Keys

| Service | URL | Required? |
|---------|-----|-----------|
| **Anthropic** | https://console.anthropic.com/settings/keys | For AI generation |
| **OpenAI** | https://platform.openai.com/api-keys | Alternative AI |
| **Replicate** | https://replicate.com/account/api-tokens | For video generation |
| **ElevenLabs** | https://elevenlabs.io/app/settings/api-keys | For audio/voice |
| **Gemini** | https://makersuite.google.com/app/apikey | Optional |

---

## ✅ Verify Setup

### Check if secrets are set:
```bash
aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --region us-east-1 \
  --query SecretString \
  --output text | jq
```

### Check if service is running:
```bash
aws ecs describe-services \
  --cluster bad-apples-cluster \
  --services bad-apples-backend-service \
  --region us-east-1 \
  --query 'services[0].[status,runningCount,desiredCount]'
```

### Test CORS:
```bash
# Get your ALB URL from Terraform output
ALB_URL=$(cd terraform && terraform output -raw alb_url)

# Test CORS
curl -H "Origin: https://yourdomain.com" \
     -X OPTIONS \
     "$ALB_URL/health" \
     -v 2>&1 | grep -i "access-control"
```

---

## 🔄 Common Tasks

### Update a Single Secret
```bash
# Get current secrets
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --query SecretString --output text)

# Update one field (example: Anthropic key)
echo "$CURRENT" | jq '.ANTHROPIC_API_KEY = "new-key"' | \
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string file:///dev/stdin

# Force deployment
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

### Add CORS Origin
1. Edit `terraform/terraform.tfvars`
2. Add URL to `cors_allowed_origins` list
3. Run `terraform apply`

### View Logs
```bash
aws logs tail /ecs/bad-apples-backend-task --follow
```

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Secrets not found" | Run `terraform apply` first to create the secret |
| "Access denied" | Check IAM permissions for secrets access |
| CORS errors | Verify origin is in `cors_allowed_origins` list |
| Secrets not updating | Force new ECS deployment |

---

## 📚 Full Documentation

For comprehensive guides, see:
- [secrets-and-cors-setup.md](./secrets-and-cors-setup.md) - Complete guide
- [ecs-debugging-guide.md](./ecs-debugging-guide.md) - Debugging help

---

**Need Help?** Check CloudWatch Logs:
```bash
aws logs tail /ecs/bad-apples-backend-task --follow --region us-east-1
```

