# Do You Need terraform.tfvars?

## Short Answer: **No, but it's recommended**

Most variables have defaults, so Terraform will work without `terraform.tfvars`. However, you'll likely want to customize some values.

---

## ✅ Variables with Defaults (Work Without tfvars)

These will use defaults if not specified:

- `aws_region` = `"us-east-1"`
- `environment` = `"dev"`
- `bucket_name` = `"video-generator-storage"` ⚠️ **Must be globally unique!**
- `ecs_cluster_name` = `"bad-apples-cluster"`
- `ecs_task_cpu` = `1024` (1 vCPU)
- `ecs_task_memory` = `2048` (2 GB)
- `cors_allowed_origins` = `["http://localhost:3000", "http://localhost:3001", "https://badapples.vercel.app"]`
- All secret variables = `""` (empty - you'll set them in Secrets Manager)

---

## ⚠️ What You Should Override

### 1. **S3 Bucket Name** (Required if default is taken)

```hcl
# terraform.tfvars
bucket_name = "your-unique-bucket-name-12345"
```

**Why:** S3 bucket names must be globally unique. The default might already be taken.

### 2. **CORS Origins** (If you have custom frontend URLs)

```hcl
# terraform.tfvars
cors_allowed_origins = [
  "http://localhost:3000",
  "https://yourdomain.com",
  "https://app.yourdomain.com"
]
```

**Note:** You already have `https://badapples.vercel.app` in the default, so you might be fine!

### 3. **Secrets** (Optional - Can set in Secrets Manager instead)

```hcl
# terraform.tfvars (optional - can skip if using Secrets Manager manually)
anthropic_api_key = "sk-ant-api03-..."
api_key = "your-api-key"
```

**Alternative:** Set these directly in AWS Secrets Manager (no tfvars needed).

---

## 🎯 When You DON'T Need tfvars

### Scenario: Using Defaults + Manual Secrets

**You can skip `terraform.tfvars` if:**
- ✅ Default bucket name is available
- ✅ Default CORS origins work for you
- ✅ You'll set secrets manually in Secrets Manager
- ✅ Default resource sizes (CPU/memory) are fine

**Just run:**
```bash
cd terraform
terraform init
terraform apply
```

---

## 📋 When You DO Need tfvars

### Scenario: Custom Configuration

**Create `terraform.tfvars` if you need to:**
- ✅ Change bucket name (most common)
- ✅ Add custom CORS origins
- ✅ Change resource sizes (CPU/memory)
- ✅ Set environment to `staging` or `prod`
- ✅ Enable HTTPS/WAF/other features

**Example minimal tfvars:**
```hcl
# terraform/terraform.tfvars
bucket_name = "my-unique-bucket-name-12345"
environment = "prod"
```

---

## 🔍 Check If You Need It

### Test Without tfvars:

```bash
cd terraform
terraform init
terraform plan
```

**If you see errors like:**
- `Bucket name already exists` → You need to set `bucket_name` in tfvars
- Otherwise → You're good without tfvars!

---

## 💡 Recommended Approach

### Option 1: Minimal tfvars (Recommended)

Create `terraform/terraform.tfvars` with just essentials:

```hcl
# Only set what you need to change
bucket_name = "your-unique-bucket-name"
```

### Option 2: No tfvars (If defaults work)

Skip tfvars entirely and:
- Use defaults for everything
- Set secrets manually in Secrets Manager
- Update CORS via Terraform variables if needed

---

## 📝 Current Status

Looking at your setup:
- ✅ CORS already includes `https://badapples.vercel.app` (in defaults)
- ✅ Most variables have sensible defaults
- ✅ Secrets can be set manually in Secrets Manager

**You probably DON'T need tfvars unless:**
- The default bucket name is taken
- You want to change resource sizes
- You want to set environment to `prod`

---

## 🚀 Quick Decision Tree

```
Do you need to change bucket name?
├─ YES → Create terraform.tfvars with bucket_name
└─ NO → Continue

Do you need to change CORS origins?
├─ YES → Add cors_allowed_origins to tfvars
└─ NO → Continue

Do you want to set secrets via Terraform?
├─ YES → Add secrets to tfvars
└─ NO → Set in Secrets Manager manually (no tfvars needed)

Do defaults work for everything else?
├─ YES → Skip tfvars!
└─ NO → Create tfvars with custom values
```

---

## ✅ Summary

| Scenario | Need tfvars? |
|----------|--------------|
| Defaults work, secrets in Secrets Manager | ❌ **No** |
| Need unique bucket name | ✅ **Yes** (just bucket_name) |
| Want to customize CORS | ✅ **Yes** (cors_allowed_origins) |
| Want to set secrets via Terraform | ✅ **Yes** (optional) |
| Using production environment | ✅ **Yes** (environment = "prod") |

---

**TL;DR:** You don't NEED it, but you'll probably want it for at least the bucket name. Everything else can use defaults or be set manually in Secrets Manager.

