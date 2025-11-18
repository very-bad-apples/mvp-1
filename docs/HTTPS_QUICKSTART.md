# HTTPS Quick Start Guide

**⏱️ Time Required:** 15-30 minutes  
**💰 Cost:** FREE (ACM certificates are free for AWS-hosted services)

## TL;DR - 4 Steps to HTTPS

```bash
# 1. Request ACM certificate (automated script)
cd terraform
./request-acm-certificate.sh

# 2. Wait for validation (5-30 mins, script will wait for you)

# 3. Apply Terraform changes
terraform plan
terraform apply

# 4. Test HTTPS
curl https://api.yourdomain.com/health
```

## What This Does

✅ **Adds HTTPS (port 443)** to your Application Load Balancer  
✅ **Automatic HTTP → HTTPS redirect** (can be disabled)  
✅ **Free SSL/TLS certificate** from AWS Certificate Manager  
✅ **Auto-renewal** - certificates never expire  
✅ **Better security** - encrypted traffic, secure cookies  

## Prerequisites

- ✅ Domain name you control (e.g., `yourdomain.com`)
- ✅ AWS account with Route 53 or any DNS provider
- ✅ Terraform infrastructure already deployed
- ✅ AWS CLI configured

## Option 1: Automated Setup (Recommended)

### Step 1: Run the Helper Script

```bash
cd terraform
./request-acm-certificate.sh
```

The script will:
1. ✅ Request ACM certificate
2. ✅ Show DNS validation records
3. ✅ Auto-create Route 53 records (if using Route 53)
4. ✅ Wait for validation
5. ✅ Update `terraform.tfvars` with certificate ARN

### Step 2: Apply Terraform

```bash
terraform plan   # Review changes
terraform apply  # Apply changes
```

### Step 3: Update DNS

Point your domain to the ALB:

```bash
# Get ALB DNS name
terraform output alb_dns_name

# Create DNS record:
# Type: CNAME
# Name: api (or your subdomain)
# Value: <alb-dns-name> from output above
```

### Step 4: Test

```bash
# Test HTTPS
curl https://api.yourdomain.com/health

# Test HTTP redirect (should redirect to HTTPS)
curl -I http://api.yourdomain.com/health
```

✅ **Done!** Your API is now secured with HTTPS.

## Option 2: Manual Setup

### Step 1: Request ACM Certificate

**Using AWS Console:**
1. Go to: AWS Console → Certificate Manager
2. Click "Request certificate"
3. Enter domain: `yourdomain.com`
4. Add wildcard: `*.yourdomain.com`
5. Choose "DNS validation"
6. Click "Request"

**Using AWS CLI:**
```bash
aws acm request-certificate \
  --domain-name yourdomain.com \
  --subject-alternative-names *.yourdomain.com \
  --validation-method DNS \
  --region us-east-1
```

### Step 2: Validate Certificate

1. In ACM console, click your certificate
2. Click "Create records in Route 53" (if using Route 53)
   - OR add CNAME records manually to your DNS provider
3. Wait 5-30 minutes for validation
4. Certificate status → "Issued"

### Step 3: Get Certificate ARN

```bash
# List certificates
aws acm list-certificates --region us-east-1

# Find your certificate ARN:
# arn:aws:acm:us-east-1:123456789012:certificate/abc-123-def
```

### Step 4: Update Terraform

Edit `terraform/terraform.tfvars`:

```hcl
# HTTPS Configuration
enable_https             = true
certificate_arn          = "arn:aws:acm:us-east-1:123456789012:certificate/YOUR-CERT-ID"
redirect_http_to_https   = true  # Optional: auto-redirect HTTP to HTTPS
```

### Step 5: Apply Changes

```bash
cd terraform
terraform plan
terraform apply
```

### Step 6: Update DNS & Test

Same as automated option above.

## Configuration Options

### Enable HTTPS (Required)

```hcl
enable_https    = true
certificate_arn = "arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT-ID"
```

### HTTP to HTTPS Redirect (Optional)

```hcl
# Automatically redirect all HTTP traffic to HTTPS
redirect_http_to_https = true  # Default: true

# Or keep HTTP working separately
redirect_http_to_https = false
```

### SSL Policy (Advanced)

The default SSL policy is `ELBSecurityPolicy-2016-08` (recommended).

For stricter security, edit `terraform/ecs.tf`:

```hcl
resource "aws_lb_listener" "https" {
  # ...
  ssl_policy = "ELBSecurityPolicy-TLS-1-2-2017-01"  # TLS 1.2+ only
  # ...
}
```

## Troubleshooting

### Certificate Validation Stuck

**Problem:** Certificate stays "Pending validation" for hours

**Solution:**
```bash
# Check DNS records have propagated
dig _acm-challenge.yourdomain.com CNAME

# If not showing, check:
# 1. DNS records are correct (copy from ACM console)
# 2. Wait for DNS propagation (can take up to 48 hours, usually 5-30 mins)
# 3. Try another DNS provider if stuck
```

### 502 Bad Gateway on HTTPS

**Problem:** HTTPS endpoint returns 502 error

**Solution:**
```bash
# 1. Check ALB health checks
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw target_group_arn)

# 2. Check ECS tasks are running
aws ecs list-tasks --cluster bad-apples-cluster

# 3. Check security groups allow ALB → ECS traffic on port 8000
```

### Browser Certificate Warning

**Problem:** Browser shows "Certificate not valid for domain"

**Solution:**
- Ensure ACM certificate includes the exact domain you're accessing
- If accessing `api.example.com`, certificate must include `api.example.com` OR `*.example.com`

### Terraform Error: Invalid Certificate ARN

**Problem:** `terraform apply` fails with "certificate not found"

**Solution:**
```bash
# Verify certificate exists in correct region
aws acm list-certificates --region us-east-1

# Verify ARN format (no trailing spaces or quotes)
# Correct: arn:aws:acm:us-east-1:123:certificate/abc-123
```

## DNS Configuration Examples

### Route 53 (Recommended)

```bash
# Create alias record (better than CNAME)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.yourdomain.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "bad-apples-alb-123.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": false
        }
      }
    }]
  }'
```

### Cloudflare

1. Go to DNS settings
2. Add record:
   - Type: `CNAME`
   - Name: `api`
   - Target: `<alb-dns-name>`
   - Proxy status: **DNS only** (orange cloud OFF)
   - TTL: Auto

### GoDaddy / Namecheap / Other

1. Go to DNS management
2. Add CNAME record:
   - Host: `api`
   - Points to: `<alb-dns-name>`
   - TTL: 600 seconds

## Testing Your HTTPS Setup

### Basic Test

```bash
# Should return 200 OK
curl https://api.yourdomain.com/health

# Should show certificate details
curl -vI https://api.yourdomain.com/health 2>&1 | grep -i "subject\|issuer\|expire"
```

### Test HTTP Redirect

```bash
# Should return 301 redirect to HTTPS
curl -I http://api.yourdomain.com/health

# Expected output:
HTTP/1.1 301 Moved Permanently
Location: https://api.yourdomain.com/health
```

### Test Certificate

```bash
# Check certificate validity
openssl s_client -connect api.yourdomain.com:443 -servername api.yourdomain.com

# Or use online tools:
# https://www.ssllabs.com/ssltest/
```

### Browser Test

1. Open: `https://api.yourdomain.com/health`
2. Click padlock icon in address bar
3. Should show:
   - ✅ Connection is secure
   - ✅ Certificate valid
   - ✅ Issued by Amazon

## Cost & Maintenance

### Costs

- **ACM Certificate:** FREE ✨
- **ALB HTTPS listener:** No extra cost
- **Data transfer:** Same as HTTP

### Maintenance

- **Certificate renewal:** Automatic (ACM handles it)
- **Monitoring:** Set up CloudWatch alarms for:
  - Certificate expiration (shouldn't happen with DNS validation)
  - 5xx errors
  - Target health

## Security Best Practices

✅ **Enable redirect:** Set `redirect_http_to_https = true`  
✅ **Use strong SSL policy:** Keep default or use TLS 1.2+  
✅ **Monitor certificate:** Set up CloudWatch alarms  
✅ **Update frontend:** Change all API calls to HTTPS  
✅ **Enable HSTS:** Add Strict-Transport-Security headers  

## Next Steps After Enabling HTTPS

### 1. Update Frontend Configuration

```javascript
// Update API endpoint in frontend
const API_BASE_URL = "https://api.yourdomain.com"  // Was: http://...
```

### 2. Update CORS Settings

```python
# backend/main.py - Update allowed origins
origins = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

### 3. Update GitHub Secrets

```bash
# If using GitHub Actions, update API_URL secret
gh secret set API_URL -b "https://api.yourdomain.com"
```

### 4. Enable HSTS (Optional, Advanced)

Add security headers to your FastAPI app:

```python
# backend/main.py
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

## Resources

- 📖 [Full Setup Guide](./setup-acm-https.md) - Detailed instructions
- 🤖 [Helper Script](./request-acm-certificate.sh) - Automated ACM setup
- 📚 [AWS ACM Docs](https://docs.aws.amazon.com/acm/)
- 🔒 [SSL Labs Test](https://www.ssllabs.com/ssltest/) - Test your HTTPS setup

## Common Questions

**Q: Do I need to renew the certificate?**  
A: No! ACM auto-renews certificates with DNS validation.

**Q: Can I use my own certificate?**  
A: Yes, but ACM is easier and free. See [AWS docs for importing certificates](https://docs.aws.amazon.com/acm/latest/userguide/import-certificate.html).

**Q: Does HTTPS cost extra?**  
A: No! ACM certificates are free for ALB/CloudFront.

**Q: Can I use multiple domains?**  
A: Yes! Add them with `--subject-alternative-names` when requesting the certificate.

**Q: What if I don't have a domain?**  
A: You can't use HTTPS without a domain. Consider:
- Buy domain (~$10-15/year)
- Use AWS Route 53 to register domain
- Or continue using HTTP for development

---

**Need Help?** Check the [full guide](./setup-acm-https.md) or open an issue.

