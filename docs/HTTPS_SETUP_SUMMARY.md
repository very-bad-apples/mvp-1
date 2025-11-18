# HTTPS Setup - Complete Summary

## What Was Added

✅ **HTTP-to-HTTPS Redirect Support**
- Automatically redirect HTTP traffic to HTTPS when enabled
- Configurable via `redirect_http_to_https` variable

✅ **Enhanced Terraform Outputs**
- `alb_https_url` - Direct HTTPS URL
- `https_enabled` - Status check
- `certificate_arn` - Certificate reference
- All URLs now use HTTPS when enabled

✅ **Helper Scripts**
- `request-acm-certificate.sh` - Automated ACM certificate setup
- `test-https.sh` - Validate HTTPS configuration

✅ **Documentation**
- `HTTPS_QUICKSTART.md` - Quick setup guide (15-30 mins)
- `setup-acm-https.md` - Detailed instructions & troubleshooting

## Quick Setup (3 Simple Steps)

### Step 1: Request ACM Certificate (~5 mins)

```bash
cd terraform
./request-acm-certificate.sh
```

The script will:
- Request certificate from AWS ACM
- Show DNS validation records
- Auto-create Route 53 records (if applicable)
- Wait for validation
- Update `terraform.tfvars` automatically

### Step 2: Apply Terraform Changes (~2 mins)

```bash
terraform plan    # Review changes
terraform apply   # Apply (type 'yes')
```

### Step 3: Point Your Domain to ALB (~5 mins)

```bash
# Get ALB DNS name
terraform output alb_dns_name

# Create DNS CNAME record:
# api.yourdomain.com → <alb-dns-name>
```

**Done! 🎉** Test with: `curl https://api.yourdomain.com/health`

## Configuration Reference

### Required Variables

Add to `terraform/terraform.tfvars`:

```hcl
enable_https    = true
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/YOUR-CERT-ID"
```

### Optional Variables

```hcl
# Automatically redirect HTTP → HTTPS (recommended)
redirect_http_to_https = true  # Default: true

# Keep HTTP working separately
redirect_http_to_https = false
```

## How It Works

### Before (HTTP Only)

```
User → HTTP (80) → ALB → ECS Tasks
```

### After (HTTPS Enabled)

```
User → HTTP (80)  → ALB → 301 Redirect to HTTPS
User → HTTPS (443) → ALB → ECS Tasks
                     ↓
                  SSL/TLS
                 Termination
```

## New Terraform Resources

### Modified Resources

**1. HTTP Listener (ecs.tf:262-286)**
- Now supports conditional redirect
- Uses dynamic block for HTTPS redirect
- Maintains backward compatibility

**2. Variables (ecs_variables.tf:196-200)**
- Added `redirect_http_to_https` variable
- Controls HTTP redirect behavior

**3. Outputs (ecs_outputs.tf:70-88)**
- Added `alb_https_url` output
- Added `https_enabled` status
- Added `certificate_arn` reference
- Updated `deployment_url` to use HTTPS

### New Features

**Automatic HTTP Redirect**
```hcl
# When enable_https = true and redirect_http_to_https = true
# HTTP requests get 301 redirected to HTTPS
```

**Smart URL Selection**
```hcl
# Terraform outputs automatically use HTTPS URLs when enabled
terraform output deployment_url
# Returns: https://... (if HTTPS enabled)
# Returns: http://...  (if HTTPS disabled)
```

## Testing Your Setup

### Automated Test

```bash
cd terraform
./test-https.sh
```

Tests:
- ✅ DNS resolution
- ✅ HTTP connection & redirect
- ✅ HTTPS connection
- ✅ SSL certificate validation
- ✅ Certificate hostname match
- ✅ API health check
- ✅ TLS protocol support

### Manual Tests

```bash
# Test HTTPS endpoint
curl https://api.yourdomain.com/health

# Test HTTP redirect
curl -I http://api.yourdomain.com/health
# Should return: HTTP/1.1 301 Moved Permanently

# Check certificate
openssl s_client -connect api.yourdomain.com:443 -servername api.yourdomain.com

# View Terraform outputs
terraform output alb_https_url
terraform output https_enabled
```

## Cost Impact

| Item | Cost |
|------|------|
| ACM Certificate | **FREE** ✨ |
| HTTPS Listener | **$0** (same as HTTP) |
| Data Transfer | Same rates |
| **Total Additional Cost** | **$0** |

## Security Improvements

✅ **Encrypted Traffic** - All data encrypted in transit  
✅ **HTTPS-Only Mode** - Automatic HTTP redirect  
✅ **Strong SSL/TLS** - Modern security protocols  
✅ **Auto-Renewal** - Certificates never expire (DNS validated)  
✅ **No Maintenance** - AWS handles everything  

## Terraform State Changes

When you enable HTTPS, Terraform will:

**Modify:**
- `aws_lb_listener.http` - Add redirect logic
- `aws_security_group.alb` - Already allows 443 (conditional)

**Create:**
- `aws_lb_listener.https` - New HTTPS listener

**No Changes:**
- S3 buckets
- ECS services
- Task definitions
- IAM roles

**Zero Downtime** ✅ - Services remain running during update

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| Certificate stuck "Pending" | Check DNS records, wait 30 mins |
| 502 Bad Gateway | Check ECS health, security groups |
| Certificate mismatch | Ensure cert includes your domain |
| HTTP not redirecting | Set `redirect_http_to_https = true` |
| Can't find cert ARN | `aws acm list-certificates` |

**Full troubleshooting:** See `setup-acm-https.md`

## File Reference

```
terraform/
├── ecs.tf                          # Modified HTTP listener
├── ecs_variables.tf                # Added redirect variable
├── ecs_outputs.tf                  # Added HTTPS outputs
├── terraform.tfvars.ecs.example    # Updated with HTTPS config
├── request-acm-certificate.sh      # NEW: ACM setup script
├── test-https.sh                   # NEW: Validation script
├── HTTPS_QUICKSTART.md             # NEW: Quick guide
├── setup-acm-https.md              # NEW: Detailed guide
└── HTTPS_SETUP_SUMMARY.md          # NEW: This file
```

## Next Steps After Enabling HTTPS

### 1. Update Your Frontend

```javascript
// Old
const API_URL = "http://your-alb-dns.amazonaws.com"

// New
const API_URL = "https://api.yourdomain.com"
```

### 2. Update CORS Settings

```python
# backend/main.py
origins = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

### 3. Update Environment Variables

```bash
# .env files, GitHub Secrets, etc.
API_URL=https://api.yourdomain.com
```

### 4. Enable HSTS (Optional, Advanced)

```python
# backend/main.py - Add security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
```

## Rollback Instructions

If you need to disable HTTPS:

```bash
# Edit terraform.tfvars
enable_https = false

# Apply changes
terraform apply

# Certificate remains in ACM (no cost)
# Can re-enable anytime
```

## Support & Resources

📖 **Documentation:**
- Quick Start: `HTTPS_QUICKSTART.md`
- Detailed Guide: `setup-acm-https.md`

🛠️ **Scripts:**
- Setup: `./request-acm-certificate.sh`
- Test: `./test-https.sh`

🌐 **External Resources:**
- [AWS ACM Documentation](https://docs.aws.amazon.com/acm/)
- [SSL Labs Test](https://www.ssllabs.com/ssltest/)
- [ALB HTTPS Listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listener.html)

## Summary

**What changed:**
- ✅ Added HTTPS listener support to ALB
- ✅ Added automatic HTTP-to-HTTPS redirect
- ✅ Added helper scripts for setup & testing
- ✅ Enhanced Terraform outputs for HTTPS
- ✅ Created comprehensive documentation

**What you need:**
- A domain name you control
- 15-30 minutes for setup
- AWS CLI & Terraform installed

**Benefits:**
- 🔒 Secure, encrypted traffic
- 💰 Zero additional cost
- 🤖 Fully automated (no manual renewal)
- 🚀 Better SEO & user trust
- ✅ Production-ready security

**Getting started:**
```bash
cd terraform
./request-acm-certificate.sh
```

That's it! 🎉

