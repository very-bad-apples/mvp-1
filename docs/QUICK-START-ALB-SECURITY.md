# Quick Start: Secure Your ALB Endpoint

## 🚀 Fastest Way: Enable HTTPS

### Step 1: Get an ACM Certificate

```bash
# Request certificate (replace with your domain)
aws acm request-certificate \
  --domain-name api.yourdomain.com \
  --validation-method DNS \
  --region us-east-1

# Note the Certificate ARN from the output
```

### Step 2: Validate Certificate

- Go to AWS Certificate Manager
- Click on your certificate
- Add the DNS validation records to your domain
- Wait for validation (usually 5-30 minutes)

### Step 3: Enable HTTPS in Terraform

Edit `terraform/terraform.tfvars`:
```hcl
enable_https            = true
certificate_arn         = "arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT_ID"
redirect_http_to_https  = true
```

### Step 4: Apply

```bash
cd terraform
terraform apply
```

**Done!** Your ALB now uses HTTPS and redirects HTTP to HTTPS.

---

## 🛡️ Best Security: Enable WAF

### Step 1: Enable WAF

Edit `terraform/terraform.tfvars`:
```hcl
enable_waf      = true
waf_rate_limit  = 2000  # 2000 requests per 5 minutes per IP
```

### Step 2: Optional - Add IP Whitelist

```hcl
waf_allowed_ips = [
  "1.2.3.4/32",      # Your office IP
  "5.6.7.0/24"       # Your office network
]
```

### Step 3: Apply

```bash
terraform apply
```

**WAF Protection Includes:**
- ✅ OWASP Top 10 protection
- ✅ SQL injection protection
- ✅ XSS protection
- ✅ Rate limiting
- ✅ IP whitelisting/blacklisting
- ✅ Bot protection

---

## 📊 Security Comparison

| Feature | HTTPS Only | HTTPS + WAF |
|---------|-----------|-------------|
| Encryption | ✅ | ✅ |
| DDoS Protection | ⚠️ Basic | ✅ Advanced |
| SQL Injection | ❌ | ✅ |
| XSS Protection | ❌ | ✅ |
| Rate Limiting | ❌ | ✅ |
| IP Filtering | ⚠️ Manual | ✅ Easy |
| Cost | Free | ~$5/month |

---

## 🎯 Recommended Setup

### For Production:
```hcl
# terraform/terraform.tfvars
enable_https            = true
certificate_arn         = "arn:aws:acm:..."
redirect_http_to_https  = true
enable_waf              = true
waf_rate_limit          = 2000
```

### For Development:
```hcl
enable_https   = false  # Optional
enable_waf     = false  # Optional
```

---

## 💰 Cost Estimate

- **HTTPS:** Free (ACM certificates are free)
- **WAF:** ~$5/month + $1 per million requests
- **Total:** ~$5-10/month for typical usage

---

## ✅ Quick Checklist

- [ ] Request ACM certificate
- [ ] Validate certificate (DNS records)
- [ ] Set `enable_https = true` in terraform.tfvars
- [ ] Set `certificate_arn` in terraform.tfvars
- [ ] (Optional) Set `enable_waf = true`
- [ ] Run `terraform apply`
- [ ] Test HTTPS endpoint

---

**See `docs/ALB-SECURITY-GUIDE.md` for complete documentation.**

