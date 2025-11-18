# ALB Security Guide

This guide covers multiple ways to secure your Application Load Balancer endpoint.

---

## 🔒 Security Options Available

### 1. ✅ HTTPS/TLS Encryption (Recommended)
**Status:** Already configured, but optional

### 2. 🛡️ AWS WAF (Web Application Firewall)
**Status:** Not configured - **Best for production**

### 3. 🔐 ALB Authentication (Cognito/OIDC)
**Status:** Not configured - **For user authentication**

### 4. 🌐 IP Whitelisting
**Status:** Can be configured via Security Groups

### 5. 📊 Rate Limiting
**Status:** Can be configured via WAF

### 6. 🔒 Security Headers
**Status:** Can be configured via WAF or ALB

---

## 1. HTTPS/TLS Encryption

### Current Status
- ✅ HTTPS listener is configured but disabled by default
- ✅ HTTP to HTTPS redirect is available
- ⚠️ Requires ACM certificate

### Enable HTTPS

**Step 1: Request ACM Certificate**

```bash
# Request certificate for your domain
aws acm request-certificate \
  --domain-name api.yourdomain.com \
  --validation-method DNS \
  --region us-east-1

# Or use the helper script
cd terraform
./request-acm-certificate.sh
```

**Step 2: Update Terraform**

Edit `terraform/terraform.tfvars`:
```hcl
enable_https            = true
certificate_arn         = "arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT_ID"
redirect_http_to_https  = true
```

**Step 3: Apply**

```bash
terraform apply
```

**Benefits:**
- ✅ Encrypts traffic in transit
- ✅ Prevents man-in-the-middle attacks
- ✅ Required for production
- ✅ Free SSL certificates via ACM

---

## 2. AWS WAF (Web Application Firewall) - **RECOMMENDED**

WAF provides:
- ✅ Protection against common web exploits (OWASP Top 10)
- ✅ Rate limiting
- ✅ IP whitelisting/blacklisting
- ✅ Geographic restrictions
- ✅ Bot protection
- ✅ SQL injection protection
- ✅ XSS protection

### Implementation

I'll create a WAF configuration file for you. This is the **most comprehensive** security option.

---

## 3. ALB Authentication (Cognito/OIDC)

For user authentication at the ALB level:

**Use Cases:**
- Admin endpoints
- Internal APIs
- Multi-tenant applications

**Implementation:**
- Configure Cognito User Pool
- Add authentication action to ALB listener rules

---

## 4. IP Whitelisting

Restrict access to specific IP addresses:

**Via Security Groups:**
```hcl
# In terraform/ecs.tf
ingress {
  description = "HTTPS from specific IPs only"
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = ["1.2.3.4/32", "5.6.7.8/32"]  # Your IPs
}
```

**Via WAF:**
- More flexible
- Can whitelist by IP ranges
- Can combine with other rules

---

## 5. Rate Limiting

Protect against DDoS and abuse:

**Via WAF:**
- Rate-based rules
- Limit requests per IP
- Custom rate limits

**Example:** Limit to 2000 requests per 5 minutes per IP

---

## 6. Security Headers

Add security headers to responses:

**Via WAF:**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy`

---

## 🎯 Recommended Security Stack

### For Development:
1. ✅ HTTPS (optional)
2. ✅ Security Groups (already configured)

### For Production:
1. ✅ **HTTPS** (required)
2. ✅ **AWS WAF** (highly recommended)
3. ✅ Rate limiting
4. ✅ Security headers
5. ⚠️ IP whitelisting (if needed)

---

## 📋 Quick Start: Enable HTTPS

**Fastest way to secure your ALB:**

1. Get a domain (or use existing)
2. Request ACM certificate
3. Update Terraform:
   ```hcl
   enable_https = true
   certificate_arn = "arn:aws:acm:..."
   ```
4. Apply: `terraform apply`

---

## 🛡️ Next Steps

Would you like me to:
1. ✅ **Add AWS WAF configuration** (recommended for production)
2. ✅ **Set up HTTPS with ACM certificate**
3. ✅ **Add IP whitelisting**
4. ✅ **Configure rate limiting**
5. ✅ **Add security headers**

Let me know which security features you'd like to implement!

