# Secrets Management Explained

## ✅ Yes, but with an important caveat!

You can **update secret VALUES manually** without touching Terraform, but you **MUST** have the secret key referenced in `ecs.tf` for ECS to pick it up.

---

## How It Works

### Two Parts:

1. **`terraform/secrets.tf`** - Creates the secret and defines its structure
2. **`terraform/ecs.tf`** - Tells ECS which secret keys to inject into containers

### The Flow:

```
┌─────────────────────────────────┐
│  AWS Secrets Manager            │
│  ┌───────────────────────────┐ │
│  │ Secret: app-secrets       │ │
│  │ {                         │ │
│  │   "ANTHROPIC_API_KEY":    │ │
│  │   "OPENAI_API_KEY":       │ │
│  │   "NEW_SECRET": "value"   │ │ ← You can add this manually
│  │ }                         │ │
│  └───────────────────────────┘ │
└─────────────────────────────────┘
              │
              │ ECS reads only keys listed in ecs.tf
              ▼
┌─────────────────────────────────┐
│  terraform/ecs.tf               │
│  secrets = [                    │
│    { name = "ANTHROPIC_API_KEY" }│
│    { name = "OPENAI_API_KEY" }  │
│    # NEW_SECRET not listed!     │ ← Won't be injected
│  ]                              │
└─────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  ECS Container                  │
│  Environment Variables:         │
│  • ANTHROPIC_API_KEY ✅         │
│  • OPENAI_API_KEY ✅            │
│  • NEW_SECRET ❌ (not injected) │
└─────────────────────────────────┘
```

---

## ✅ What You CAN Do Manually

### 1. Update Existing Secret Values

**YES!** You can update values without touching Terraform:

```bash
# Update ANTHROPIC_API_KEY value
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string '{
    "ANTHROPIC_API_KEY": "new-value-here",
    "OPENAI_API_KEY": "existing-value",
    ...
  }'
```

**ECS will pick it up** after you force a new deployment:
```bash
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

**Why this works:**
- The key `ANTHROPIC_API_KEY` is already listed in `ecs.tf`
- Terraform has `ignore_changes = [secret_string]` so it won't overwrite your manual changes
- ECS reads the latest value from Secrets Manager when containers start

---

## ❌ What You CANNOT Do Manually

### 2. Add NEW Secret Keys Without Updating Terraform

**NO!** If you add a new key that's not in `ecs.tf`, ECS won't inject it:

```bash
# You add NEW_SECRET manually
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string '{
    "ANTHROPIC_API_KEY": "...",
    "NEW_SECRET": "my-value"  ← New key
  }'
```

**ECS won't inject `NEW_SECRET`** because it's not listed in `ecs.tf`!

**To fix:** You must add it to `ecs.tf`:

```hcl
# terraform/ecs.tf
secrets = [
  # ... existing secrets ...
  {
    name      = "NEW_SECRET"
    valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:NEW_SECRET::"
  }
]
```

Then run `terraform apply` and redeploy ECS.

---

## 📋 Summary

| Action | Can Do Manually? | ECS Picks It Up? |
|--------|------------------|------------------|
| **Update existing secret value** | ✅ Yes | ✅ Yes (after redeploy) |
| **Add new secret key** | ⚠️ Can add to Secrets Manager | ❌ No (must update `ecs.tf`) |
| **Delete secret key** | ✅ Yes | ✅ Yes (env var won't exist) |
| **Change secret structure** | ✅ Yes | ⚠️ Only if keys match `ecs.tf` |

---

## 🔍 How to Verify

### Check What's in Secrets Manager:

```bash
aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --query SecretString \
  --output text | jq 'keys'
```

### Check What ECS Will Inject:

```bash
aws ecs describe-task-definition \
  --task-definition bad-apples-backend-task \
  --query 'taskDefinition.containerDefinitions[0].secrets[*].name' \
  --output json
```

**Only secrets listed in the ECS task definition will be injected!**

---

## 💡 Best Practice

### For Existing Secrets (Updating Values):
1. ✅ Update manually in Secrets Manager
2. ✅ Force new ECS deployment
3. ✅ No Terraform changes needed

### For New Secrets (Adding Keys):
1. ✅ Add key to Secrets Manager manually (optional, can do via Terraform)
2. ✅ **MUST** add to `terraform/ecs.tf` secrets array
3. ✅ Run `terraform apply`
4. ✅ ECS will automatically redeploy with new secret

---

## 🎯 Example Workflow

### Scenario: Update API Key Value

**Step 1:** Update secret manually
```bash
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string '{"ANTHROPIC_API_KEY": "new-key"}'
```

**Step 2:** Force ECS deployment
```bash
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

**Done!** ✅ No Terraform changes needed.

---

### Scenario: Add New Secret Key

**Step 1:** Add to Secrets Manager
```bash
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string '{"ANTHROPIC_API_KEY": "...", "NEW_KEY": "value"}'
```

**Step 2:** **MUST** add to `terraform/ecs.tf`:
```hcl
secrets = [
  # ... existing ...
  {
    name      = "NEW_KEY"
    valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:NEW_KEY::"
  }
]
```

**Step 3:** Apply Terraform
```bash
terraform apply
```

**Step 4:** ECS automatically redeploys with new secret

---

## 🔒 Important Notes

1. **`lifecycle { ignore_changes = [secret_string] }`** in `secrets.tf`
   - This prevents Terraform from overwriting manual changes
   - You can safely update values manually

2. **ECS reads secrets at container startup**
   - Secrets are injected when the container starts
   - To pick up new values, force a new deployment

3. **Secret keys must match exactly**
   - Key name in Secrets Manager must match key name in `ecs.tf`
   - Case-sensitive!

---

**TL;DR:** You can update VALUES manually, but you MUST have the key listed in `ecs.tf` for ECS to inject it. Adding new keys requires updating `ecs.tf`.

