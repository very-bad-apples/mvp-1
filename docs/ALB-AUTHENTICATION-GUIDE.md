# ALB Authentication Configuration Guide

This guide shows you how to add authentication to your ALB using AWS Cognito or OIDC providers.

---

## 🔐 Authentication Options

### Option 1: AWS Cognito (Recommended)
- ✅ Fully managed by AWS
- ✅ Easy to set up
- ✅ User management built-in
- ✅ Social login support (Google, Facebook, etc.)

### Option 2: OIDC Provider
- ✅ Works with any OIDC-compliant provider
- ✅ Google, Auth0, Okta, etc.
- ⚠️ Requires external provider setup

---

## 🚀 Quick Start: AWS Cognito Authentication

### Step 1: Create Cognito User Pool

The Terraform configuration will create this automatically, or you can create it manually:

```bash
aws cognito-idp create-user-pool \
  --pool-name bad-apples-users \
  --region us-east-1
```

### Step 2: Configure Terraform

Edit `terraform/terraform.tfvars`:

```hcl
# Enable ALB authentication
enable_alb_auth     = true
alb_auth_type       = "cognito"  # or "oidc"

# Cognito configuration (if using Cognito)
cognito_user_pool_name = "bad-apples-users"
cognito_user_pool_domain = "bad-apples-auth"  # Must be globally unique
```

### Step 3: Apply Terraform

```bash
cd terraform
terraform apply
```

### Step 4: Test Authentication

1. Visit your ALB URL
2. You'll be redirected to Cognito login page
3. Sign up/Sign in
4. After authentication, you'll be redirected back to your app

---

## 📋 Complete Setup: Cognito User Pool

### Manual Setup (Alternative)

**Step 1: Create User Pool**

```bash
aws cognito-idp create-user-pool \
  --pool-name bad-apples-users \
  --auto-verified-attributes email \
  --region us-east-1
```

**Step 2: Create User Pool Client**

```bash
# Get User Pool ID from previous command
USER_POOL_ID="us-east-1_XXXXXXXXX"

aws cognito-idp create-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-name bad-apples-client \
  --generate-secret \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --region us-east-1
```

**Step 3: Create User Pool Domain**

```bash
aws cognito-idp create-user-pool-domain \
  --domain bad-apples-auth \
  --user-pool-id $USER_POOL_ID \
  --region us-east-1
```

**Step 4: Update ALB Listener**

The Terraform configuration will handle this automatically.

---

## 🔧 Configuration Options

### Authentication Scope

You can apply authentication to:
- ✅ **All paths** (entire API)
- ✅ **Specific paths** (e.g., `/admin/*`, `/api/secure/*`)
- ✅ **All paths except** (e.g., exclude `/health`, `/public/*`)

### Example: Protect Only Admin Routes

```hcl
# In terraform/ecs.tf listener rules
resource "aws_lb_listener_rule" "admin_auth" {
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 100

  action {
    type = "authenticate-cognito"
    authenticate_cognito {
      user_pool_arn       = aws_cognito_user_pool.main.arn
      user_pool_client_id = aws_cognito_user_pool_client.main.id
      user_pool_domain    = aws_cognito_user_pool_domain.main.domain
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main[0].arn
  }

  condition {
    path_pattern {
      values = ["/admin/*", "/api/secure/*"]
    }
  }
}
```

---

## 🌐 OIDC Provider Setup

### Using Google OAuth

**Step 1: Create Google OAuth Credentials**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 Client ID
3. Add authorized redirect URI: `https://your-alb-url/oauth2/idpresponse`

**Step 2: Configure Terraform**

```hcl
enable_alb_auth = true
alb_auth_type   = "oidc"

# OIDC Configuration
oidc_issuer                = "https://accounts.google.com"
oidc_authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
oidc_token_endpoint        = "https://oauth2.googleapis.com/token"
oidc_user_info_endpoint    = "https://openidconnect.googleapis.com/v1/userinfo"
oidc_client_id            = "your-google-client-id"
oidc_client_secret         = "your-google-client-secret"
```

**Step 3: Apply**

```bash
terraform apply
```

---

## 🔍 How It Works

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │ 1. Request to ALB
       ▼
┌─────────────────┐
│   ALB           │
│   (with auth)   │
└──────┬──────────┘
       │ 2. Check if authenticated
       │
       ├─ Not authenticated → Redirect to Cognito/OIDC
       │                        ↓
       │                    ┌──────────────┐
       │                    │  Cognito/    │
       │                    │  OIDC Login   │
       │                    └──────┬───────┘
       │                           │ 3. User logs in
       │                           │ 4. Redirect back with token
       │                           ▼
       └─ Authenticated → Forward to ECS
                            ↓
                    ┌──────────────┐
                    │  Your App    │
                    └──────────────┘
```

---

## 📝 User Management (Cognito)

### Create User

```bash
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com \
  --message-action SUPPRESS \
  --region us-east-1
```

### Set User Password

```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --password "SecurePassword123!" \
  --permanent \
  --region us-east-1
```

### List Users

```bash
aws cognito-idp list-users \
  --user-pool-id $USER_POOL_ID \
  --region us-east-1
```

---

## 🎯 Use Cases

### 1. Protect Entire API

Apply authentication to all routes - all users must log in.

### 2. Protect Admin Routes Only

Only `/admin/*` and `/api/secure/*` require authentication.

### 3. Public API with Optional Auth

Most routes are public, but authenticated users get additional features.

---

## ⚙️ Advanced Configuration

### Custom Authentication Scopes

```hcl
authenticate_cognito {
  user_pool_arn       = aws_cognito_user_pool.main.arn
  user_pool_client_id = aws_cognito_user_pool_client.main.id
  user_pool_domain    = aws_cognito_user_pool_domain.main.domain
  scope               = "openid email profile"
  session_cookie_name = "AWSELBAuthSessionCookie"
  session_timeout     = 604800  # 7 days
}
```

### Multiple Authentication Rules

You can have different authentication for different paths:

```hcl
# Public health check (no auth)
resource "aws_lb_listener_rule" "health" {
  priority = 1
  # No authentication action
}

# Admin routes (Cognito auth)
resource "aws_lb_listener_rule" "admin" {
  priority = 100
  # Cognito authentication
}

# API routes (OIDC auth)
resource "aws_lb_listener_rule" "api" {
  priority = 200
  # OIDC authentication
}
```

---

## 🔒 Security Best Practices

1. ✅ **Use HTTPS** - Always enable HTTPS when using authentication
2. ✅ **Secure Cookies** - Use secure, HTTP-only cookies
3. ✅ **Session Timeout** - Set appropriate session timeouts
4. ✅ **MFA** - Enable Multi-Factor Authentication in Cognito
5. ✅ **Password Policy** - Enforce strong password policies
6. ✅ **Rate Limiting** - Combine with WAF for rate limiting

---

## 🆘 Troubleshooting

### Issue: "Redirect loop"

**Cause:** Authentication rule conflicts

**Solution:** Check listener rule priorities and conditions

### Issue: "Invalid client"

**Cause:** OIDC client ID/secret incorrect

**Solution:** Verify credentials in Terraform variables

### Issue: "User pool not found"

**Cause:** Cognito User Pool ARN incorrect

**Solution:** Check User Pool ID and region

---

## 📊 Cost

- **Cognito:** 
  - Free tier: 50,000 MAUs (Monthly Active Users)
  - After: $0.0055 per MAU
- **OIDC:** Free (uses external provider)

---

## 🎓 Next Steps

1. ✅ Choose authentication type (Cognito or OIDC)
2. ✅ Configure in `terraform.tfvars`
3. ✅ Apply Terraform changes
4. ✅ Test authentication flow
5. ✅ Configure user management (if using Cognito)

---

**See the Terraform configuration files for implementation details.**

