# Quick Start: ALB Authentication

## 🚀 Enable Cognito Authentication (Easiest)

### Step 1: Configure Terraform

Edit `terraform/terraform.tfvars`:

```hcl
# Enable ALB authentication
enable_alb_auth = true
alb_auth_type   = "cognito"

# Cognito settings
cognito_user_pool_name   = "bad-apples-users"
cognito_user_pool_domain = "bad-apples-auth"  # Must be globally unique!

# Optional: Protect only specific paths
# alb_auth_paths = ["/admin/*", "/api/secure/*"]
# Leave empty to protect all paths
```

### Step 2: Apply

```bash
cd terraform
terraform apply
```

### Step 3: Create Your First User

```bash
# Get User Pool ID
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 10 --query 'UserPools[?Name==`bad-apples-users`].Id' --output text --region us-east-1)

# Create user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com \
  --message-action SUPPRESS \
  --region us-east-1

# Set password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --password "SecurePassword123!" \
  --permanent \
  --region us-east-1
```

### Step 4: Test

1. Visit your ALB URL
2. You'll be redirected to Cognito login
3. Sign in with your credentials
4. You'll be redirected back to your app

**Done!** ✅

---

## 🌐 Enable OIDC Authentication (Google, Auth0, etc.)

### Step 1: Get OIDC Credentials

**For Google:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 Client ID
3. Add redirect URI: `https://your-alb-url/oauth2/idpresponse`

### Step 2: Configure Terraform

Edit `terraform/terraform.tfvars`:

```hcl
enable_alb_auth = true
alb_auth_type   = "oidc"

# Google OIDC Configuration
oidc_issuer                = "https://accounts.google.com"
oidc_authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
oidc_token_endpoint        = "https://oauth2.googleapis.com/token"
oidc_user_info_endpoint    = "https://openidconnect.googleapis.com/v1/userinfo"
oidc_client_id            = "your-google-client-id"
oidc_client_secret        = "your-google-client-secret"
```

### Step 3: Apply

```bash
terraform apply
```

**Done!** ✅

---

## 🎯 Protect Specific Paths Only

To protect only certain routes (e.g., `/admin/*`):

```hcl
enable_alb_auth = true
alb_auth_type   = "cognito"
alb_auth_paths  = ["/admin/*", "/api/secure/*"]
```

All other paths will be public.

---

## 📋 Configuration Examples

### Example 1: Protect Everything

```hcl
enable_alb_auth = true
alb_auth_type   = "cognito"
alb_auth_paths  = []  # Empty = all paths
```

### Example 2: Protect Admin Only

```hcl
enable_alb_auth = true
alb_auth_type   = "cognito"
alb_auth_paths  = ["/admin/*"]
```

### Example 3: Public API with Admin Auth

```hcl
enable_alb_auth = true
alb_auth_type   = "cognito"
alb_auth_paths  = ["/admin/*", "/api/admin/*"]

# Health check stays public (no auth rule)
```

---

## 🔒 Security Best Practices

1. ✅ **Always use HTTPS** when enabling authentication
2. ✅ **Enable MFA** for Cognito (set `cognito_enable_mfa = true`)
3. ✅ **Set strong password policy** (already configured)
4. ✅ **Use secure session timeouts**
5. ✅ **Combine with WAF** for additional protection

---

## 💰 Cost

- **Cognito:** Free for first 50,000 MAUs, then $0.0055 per MAU
- **OIDC:** Free (uses external provider)

---

## 🆘 Troubleshooting

### "Domain already exists"
Change `cognito_user_pool_domain` to something unique.

### "Redirect loop"
Make sure HTTPS is enabled and certificate is valid.

### "Invalid client"
Check OIDC client ID and secret are correct.

---

**See `docs/ALB-AUTHENTICATION-GUIDE.md` for complete documentation.**

