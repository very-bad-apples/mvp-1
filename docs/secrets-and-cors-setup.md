# Secrets and CORS Configuration Guide

This guide explains how to securely configure API keys and CORS settings for your ECS Fargate deployment.

---

## 🔐 Secrets Management with AWS Secrets Manager

### Why Use AWS Secrets Manager?

✅ **Secure**: Secrets are encrypted at rest and in transit  
✅ **No exposure**: Secrets don't appear in Terraform state or logs  
✅ **Rotation**: Supports automatic secret rotation  
✅ **Audit**: CloudTrail logs all secret access  
✅ **Cost-effective**: $0.40/month per secret + $0.05 per 10,000 API calls

### Architecture

```
┌─────────────────┐
│  ECS Task       │
│  (Container)    │
└────────┬────────┘
         │ Read secrets on startup
         ▼
┌─────────────────────────┐
│ AWS Secrets Manager     │
│ ┌─────────────────────┐ │
│ │ API Keys:           │ │
│ │ - Anthropic         │ │
│ │ - OpenAI            │ │
│ │ - Replicate         │ │
│ │ - ElevenLabs        │ │
│ │ - Gemini            │ │
│ │ - Database URL      │ │
│ └─────────────────────┘ │
└─────────────────────────┘
```

---

## 📋 Setup Methods

### Method 1: Using the Helper Script (Recommended)

**Step 1:** Deploy the infrastructure first
```bash
cd terraform
terraform init
terraform apply
```

**Step 2:** Update secrets using the helper script
```bash
chmod +x update-secrets.sh
./update-secrets.sh
```

The script will:
- Prompt you for each API key
- Keep existing values if you press Enter
- Update AWS Secrets Manager securely
- Show you commands to deploy the changes

**Step 3:** Force ECS to pick up new secrets
```bash
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment \
  --region us-east-1
```

---

### Method 2: Using AWS CLI Directly

```bash
# Create the secret JSON
cat > secrets.json <<EOF
{
  "ANTHROPIC_API_KEY": "your-anthropic-key",
  "OPENAI_API_KEY": "your-openai-key",
  "REPLICATE_API_KEY": "your-replicate-key",
  "ELEVENLABS_API_KEY": "your-elevenlabs-key",
  "GEMINI_API_KEY": "your-gemini-key",
  "DATABASE_URL": "sqlite:///./video_generator.db"
}
EOF

# Update the secret
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string file://secrets.json \
  --region us-east-1

# Clean up the file (important!)
rm secrets.json

# Force new deployment
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment \
  --region us-east-1
```

---

### Method 3: Using AWS Console

1. Go to **AWS Secrets Manager** in the AWS Console
2. Find the secret: `bad-apples-backend-task-secrets`
3. Click **"Retrieve secret value"**
4. Click **"Edit"**
5. Update the JSON with your API keys
6. Click **"Save"**
7. Force new ECS deployment (see commands above)

---

### Method 4: Using Terraform Variables (Less Secure)

**⚠️ Not recommended for production** - Secrets may appear in Terraform state and logs.

```bash
# Create terraform.tfvars
cat > terraform/terraform.tfvars <<EOF
anthropic_api_key  = "your-key"
openai_api_key     = "your-key"
replicate_api_key  = "your-key"
elevenlabs_api_key = "your-key"
gemini_api_key     = "your-key"
database_url       = "sqlite:///./video_generator.db"
EOF

# Apply
cd terraform
terraform apply
```

**Important:** Add `terraform.tfvars` to `.gitignore`!

---

## 🔑 Getting API Keys

### Anthropic (Claude)
- **URL:** https://console.anthropic.com/settings/keys
- **Purpose:** AI text generation, script writing
- **Pricing:** Pay per token
- **Required for:** Scene generation, content creation

### OpenAI (GPT)
- **URL:** https://platform.openai.com/api-keys
- **Purpose:** Alternative AI text generation
- **Pricing:** Pay per token
- **Required for:** Alternative to Anthropic

### Replicate
- **URL:** https://replicate.com/account/api-tokens
- **Purpose:** Video generation models (Stable Video Diffusion, etc.)
- **Pricing:** Pay per second of inference
- **Required for:** Video generation

### ElevenLabs
- **URL:** https://elevenlabs.io/app/settings/api-keys
- **Purpose:** Voice synthesis, text-to-speech
- **Pricing:** Character-based pricing
- **Required for:** Audio generation, voiceovers

### Google Gemini
- **URL:** https://makersuite.google.com/app/apikey
- **Purpose:** Alternative AI text/vision generation
- **Pricing:** Free tier available
- **Required for:** Optional alternative AI provider

---

## 🌐 CORS Configuration

### What is CORS?

CORS (Cross-Origin Resource Sharing) controls which websites can make requests to your API.

### Default Configuration

By default, these origins are allowed:
- `http://localhost:3000` - Local development (React/Next.js default)
- `http://localhost:3001` - Alternative local port

### Adding Production Frontend URLs

**Option 1: Using Terraform Variables**

Edit `terraform/terraform.tfvars`:
```hcl
cors_allowed_origins = [
  "http://localhost:3000",
  "http://localhost:3001",
  "https://yourdomain.com",
  "https://www.yourdomain.com",
  "https://app.yourdomain.com"
]
```

Then apply:
```bash
cd terraform
terraform apply
```

**Option 2: Using Environment Variables**

```bash
export TF_VAR_cors_allowed_origins='["http://localhost:3000","https://yourdomain.com"]'
terraform apply
```

### CORS Testing

Test if CORS is working:
```bash
# Replace with your ALB DNS
ALB_URL="http://bad-apples-alb-123456789.us-east-1.elb.amazonaws.com"

# Test from your frontend origin
curl -H "Origin: https://yourdomain.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     -v \
     "$ALB_URL/health"

# Should see:
# Access-Control-Allow-Origin: https://yourdomain.com
# Access-Control-Allow-Methods: *
# Access-Control-Allow-Headers: *
```

### CORS Security Best Practices

✅ **DO:**
- List specific domains (e.g., `https://yourdomain.com`)
- Use HTTPS in production
- Keep the list minimal (only domains you control)

❌ **DON'T:**
- Use `*` (wildcard) in production
- Allow `http://` origins in production (use HTTPS)
- Allow origins you don't control

### Dynamic CORS (Advanced)

If you need dynamic CORS (based on subdomain patterns, etc.), you can modify the FastAPI CORS middleware in `backend/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware
import re

def is_allowed_origin(origin: str) -> bool:
    """Check if origin is allowed based on pattern"""
    allowed_patterns = [
        r"^https://.*\.yourdomain\.com$",  # Any subdomain
        r"^http://localhost:\d+$",          # Any localhost port
    ]
    return any(re.match(pattern, origin) for pattern in allowed_patterns)

# In middleware setup:
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https://.*\.yourdomain\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🔄 Updating Secrets and CORS

### Updating Secrets (No Downtime)

1. Update the secret in AWS Secrets Manager
2. Force new ECS deployment
3. ECS will start new tasks with new secrets
4. Old tasks are terminated once new tasks are healthy

```bash
# Update secret (using any method above)
./update-secrets.sh

# Force deployment
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment \
  --region us-east-1

# Watch deployment (optional)
watch -n 5 'aws ecs describe-services \
  --cluster bad-apples-cluster \
  --services bad-apples-backend-service \
  --region us-east-1 \
  --query "services[0].[runningCount,desiredCount,deployments[*].[status,desiredCount,runningCount]]"'
```

### Updating CORS (No Downtime)

1. Update `cors_allowed_origins` in `terraform.tfvars`
2. Apply Terraform changes
3. Terraform will update the task definition
4. ECS will automatically deploy new tasks

```bash
cd terraform
terraform apply
```

---

## 🔍 Troubleshooting

### Issue: Secrets Not Loading

**Symptoms:** Container crashes with "API key not found" errors

**Solution:**
```bash
# Check if secret exists
aws secretsmanager describe-secret \
  --secret-id bad-apples-backend-task-secrets \
  --region us-east-1

# Verify IAM permissions
aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --region us-east-1

# Check CloudWatch logs for permission errors
aws logs tail /ecs/bad-apples-backend-task --follow
```

### Issue: CORS Errors in Browser

**Symptoms:** Browser console shows CORS errors

**Check:**
1. Verify origin is in the allowed list
2. Check CORS headers in response
3. Ensure using correct protocol (http vs https)

**Debug:**
```bash
# Check current CORS config
aws ecs describe-task-definition \
  --task-definition bad-apples-backend-task \
  --query 'taskDefinition.containerDefinitions[0].environment[?name==`CORS_ORIGINS`]'

# Test CORS preflight
curl -H "Origin: https://yourdomain.com" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     -v \
     "http://your-alb-url/health"
```

### Issue: Secret Updates Not Applied

**Cause:** ECS tasks use secrets from when they started

**Solution:** Force new deployment
```bash
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment \
  --region us-east-1
```

---

## 📊 Monitoring

### Check Secret Access Logs

```bash
# View CloudTrail logs for secret access
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=bad-apples-backend-task-secrets \
  --max-results 10 \
  --region us-east-1
```

### Monitor Costs

Secrets Manager costs approximately:
- **$0.40/month** per secret
- **$0.05 per 10,000 API calls**

For 1 secret accessed on container startup:
- 1 secret × $0.40 = $0.40/month
- ~1,000 task starts/month × $0.05/10,000 = $0.005/month
- **Total: ~$0.41/month**

---

## 🎯 Quick Reference

### Commands Cheat Sheet

```bash
# Update secrets interactively
./update-secrets.sh

# Update secrets from file
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string file://secrets.json \
  --region us-east-1

# Force new deployment
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment \
  --region us-east-1

# View secrets (requires permissions)
aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --region us-east-1

# Update CORS
vim terraform/terraform.tfvars  # Edit cors_allowed_origins
terraform apply

# Test CORS
curl -H "Origin: https://yourdomain.com" -X OPTIONS -v http://your-alb/health
```

---

## 🔒 Security Checklist

- [ ] Secrets stored in AWS Secrets Manager (not in code)
- [ ] Terraform state stored securely (S3 with encryption)
- [ ] `terraform.tfvars` in `.gitignore`
- [ ] CORS limited to specific domains (no wildcards)
- [ ] HTTPS enabled for production
- [ ] CloudTrail logging enabled for secret access
- [ ] IAM permissions follow least privilege
- [ ] Secrets rotated periodically
- [ ] API keys have spending limits (where supported)

---

**Last Updated:** 2024  
**Related Files:**
- `terraform/secrets.tf` - Secrets Manager configuration
- `terraform/update-secrets.sh` - Helper script
- `terraform/ecs.tf` - Task definition with secrets
- `backend/config.py` - Application configuration

