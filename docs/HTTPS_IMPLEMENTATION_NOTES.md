# HTTPS Implementation - Technical Notes

## Changes Made

### 1. Terraform Configuration Updates

#### A. HTTP Listener Enhancement (ecs.tf)
**File:** `terraform/ecs.tf` (lines 262-286)

**Before:**
```hcl
resource "aws_lb_listener" "http" {
  # ... basic config ...
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main[0].arn
  }
}
```

**After:**
```hcl
resource "aws_lb_listener" "http" {
  # ... basic config ...
  default_action {
    type = var.enable_https && var.redirect_http_to_https ? "redirect" : "forward"
    
    # Redirect to HTTPS if enabled
    dynamic "redirect" {
      for_each = var.enable_https && var.redirect_http_to_https ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
    
    # Forward to target group if not redirecting
    target_group_arn = var.enable_https && var.redirect_http_to_https ? null : aws_lb_target_group.main[0].arn
  }
}
```

**Key Changes:**
- Dynamic action type based on HTTPS settings
- Conditional HTTP-to-HTTPS redirect (301)
- Maintains backward compatibility
- No breaking changes to existing deployments

#### B. New Variable (ecs_variables.tf)
**File:** `terraform/ecs_variables.tf` (lines 196-200)

```hcl
variable "redirect_http_to_https" {
  description = "Redirect HTTP traffic to HTTPS (only applies when enable_https is true)"
  type        = bool
  default     = true
}
```

**Purpose:**
- Controls HTTP redirect behavior
- Only active when `enable_https = true`
- Default: `true` (automatic redirect)
- Can be disabled for specific use cases

#### C. Enhanced Outputs (ecs_outputs.tf)
**File:** `terraform/ecs_outputs.tf` (lines 70-88, 173-175, 197-214)

**New Outputs:**
```hcl
output "alb_http_url" { ... }      # Explicit HTTP URL
output "alb_https_url" { ... }     # Explicit HTTPS URL
output "https_enabled" { ... }     # Status flag
output "certificate_arn" { ... }   # Certificate reference
```

**Modified Outputs:**
```hcl
output "alb_url" { ... }           # Smart URL selection
output "deployment_url" { ... }    # Smart health check URL
output "quick_start_commands" { ... }  # Smart curl commands
```

**Logic:**
- Automatically uses HTTPS URLs when `enable_https = true`
- Falls back to HTTP when HTTPS disabled
- Provides both HTTP and HTTPS URLs explicitly

#### D. Updated Example Configuration (terraform.tfvars.ecs.example)
**File:** `terraform/terraform.tfvars.ecs.example` (lines 79-82)

```hcl
# HTTPS Configuration (optional)
enable_https             = false
certificate_arn          = ""
redirect_http_to_https   = true
```

### 2. Helper Scripts

#### A. ACM Certificate Request Script
**File:** `terraform/request-acm-certificate.sh`
**Size:** ~250 lines
**Permissions:** Executable (`chmod +x`)

**Features:**
- Interactive certificate request
- DNS validation record display
- Automatic Route 53 record creation
- Certificate validation waiting
- Auto-update terraform.tfvars
- Error handling & validation

**Usage:**
```bash
cd terraform
./request-acm-certificate.sh
```

#### B. HTTPS Validation Script
**File:** `terraform/test-https.sh`
**Size:** ~200 lines
**Permissions:** Executable (`chmod +x`)

**Tests:**
1. DNS resolution
2. HTTP connection & redirect
3. HTTPS connection
4. SSL certificate validation
5. Certificate hostname match
6. API health check
7. TLS protocol support

**Usage:**
```bash
cd terraform
./test-https.sh
# Or specify domain:
./test-https.sh api.yourdomain.com
```

### 3. Documentation

#### A. Quick Start Guide
**File:** `terraform/HTTPS_QUICKSTART.md`
**Purpose:** Fast setup for users (15-30 min guide)
**Sections:**
- TL;DR 4-step setup
- Automated setup option
- Manual setup option
- Configuration reference
- Troubleshooting quick reference
- DNS configuration examples
- Testing instructions

#### B. Detailed Setup Guide
**File:** `terraform/setup-acm-https.md`
**Purpose:** Comprehensive documentation
**Sections:**
- Prerequisites
- Step-by-step ACM setup
- DNS validation methods
- Terraform configuration
- DNS configuration (all providers)
- Security best practices
- Troubleshooting (detailed)
- Cost considerations
- Production deployment advice

#### C. Setup Summary
**File:** `terraform/HTTPS_SETUP_SUMMARY.md`
**Purpose:** Overview of all changes & quick reference
**Sections:**
- What was added
- Quick setup steps
- Configuration reference
- Architecture diagrams
- Testing instructions
- File reference
- Next steps

#### D. Implementation Notes
**File:** `terraform/HTTPS_IMPLEMENTATION_NOTES.md`
**Purpose:** Technical details (this file)

## Terraform Resource Changes

### When HTTPS Disabled (Default)
```
No changes to existing infrastructure
```

### When HTTPS Enabled
```
Terraform will modify:
  ~ aws_lb_listener.http[0]
    - Change action type to "redirect" (if redirect_http_to_https = true)
    - OR keep as "forward" (if redirect_http_to_https = false)

Terraform will create:
  + aws_lb_listener.https[0]
    - Port 443 listener
    - SSL certificate attachment
    - Forward to existing target group

No other resources affected
Zero downtime deployment ✅
```

## Backward Compatibility

### Existing Deployments
✅ **No breaking changes**
- Default behavior unchanged (`enable_https = false`)
- Existing HTTP listeners continue working
- No impact on running services

### Migration Path
1. Request ACM certificate (5-30 mins)
2. Update terraform.tfvars with certificate ARN
3. Run `terraform plan` (review changes)
4. Run `terraform apply` (apply changes)
5. Update DNS (point to ALB)
6. Test HTTPS endpoint

**Rollback:** Set `enable_https = false` and reapply

## Security Considerations

### SSL/TLS Configuration
**Current Policy:** `ELBSecurityPolicy-2016-08`
- ✅ TLS 1.2 supported
- ✅ TLS 1.3 supported
- ✅ Strong cipher suites
- ✅ Compatible with modern browsers

**Alternative (Stricter):** `ELBSecurityPolicy-TLS-1-2-2017-01`
- TLS 1.2+ only
- More restrictive cipher suites
- May block older clients

### Certificate Management
- **Auto-renewal:** DNS-validated certificates auto-renew
- **Expiry monitoring:** ACM sends expiry notices (if renewal fails)
- **No manual intervention:** AWS handles everything
- **Zero cost:** ACM certificates are free for AWS services

### HTTP Redirect Security
- **301 Permanent:** Browsers cache redirect
- **HSTS Ready:** Can add Strict-Transport-Security headers
- **No sensitive data over HTTP:** Immediate redirect before processing

## Testing Strategy

### Pre-Deployment Tests
```bash
# Validate Terraform configuration
terraform validate

# Check plan for unexpected changes
terraform plan

# Review outputs before applying
terraform plan -out=plan.tfplan
terraform show plan.tfplan
```

### Post-Deployment Tests
```bash
# Automated validation
./test-https.sh

# Manual tests
curl -I https://api.yourdomain.com/health
curl -I http://api.yourdomain.com/health  # Should redirect

# Certificate validation
openssl s_client -connect api.yourdomain.com:443

# SSL Labs comprehensive test
# https://www.ssllabs.com/ssltest/analyze.html?d=api.yourdomain.com
```

### Monitoring
```bash
# Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw target_group_arn)

# Check ECS service
aws ecs describe-services \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --services $(terraform output -raw ecs_service_name)

# Check CloudWatch logs
aws logs tail /ecs/$(terraform output -raw ecs_task_definition_family) --follow
```

## Performance Impact

### Latency
- **TLS Handshake:** ~50-100ms (first request only)
- **Session Resumption:** ~5-10ms (subsequent requests)
- **HTTP Redirect:** ~10-20ms (one-time, then cached)
- **Overall Impact:** Negligible (<1% for most use cases)

### Throughput
- **No impact:** ALB handles SSL/TLS offload
- **Same capacity:** HTTP and HTTPS throughput identical
- **Connection reuse:** HTTP/2 improves performance

### Cost
- **ACM Certificate:** $0.00 (FREE)
- **HTTPS Listener:** $0.00 (no additional charge)
- **Data Processing:** Same as HTTP
- **Total Impact:** $0.00

## Known Issues & Limitations

### Issue 1: Certificate Validation Delay
**Problem:** Certificate validation can take 5-30 minutes
**Solution:** Automated in `request-acm-certificate.sh` script
**Workaround:** Run script and wait, or check ACM console

### Issue 2: DNS Propagation
**Problem:** DNS changes can take time to propagate
**Solution:** Use short TTL (300s recommended)
**Workaround:** Test with curl using `--resolve` flag

### Issue 3: Cloudflare Proxy
**Problem:** Cloudflare's orange cloud proxy interferes with ACM validation
**Solution:** Disable proxy (DNS only mode) during validation
**Workaround:** Validate first, then enable proxy

### Issue 4: Multiple Domains
**Problem:** Need separate certificates for different domains
**Solution:** Use wildcard certificates or SANs
**Workaround:** Request multiple domains in single certificate

## Future Enhancements

### Potential Improvements
1. **AWS Secrets Manager Integration**
   - Store certificate ARN in Secrets Manager
   - Automatic rotation support

2. **Certificate Expiry Monitoring**
   - CloudWatch alarm for certificate expiry
   - SNS notification integration

3. **HSTS Support**
   - Add HSTS headers via ALB rules
   - Configurable max-age

4. **HTTP/2 and HTTP/3**
   - Already supported by ALB
   - No changes needed

5. **Custom SSL Policies**
   - Variable for SSL policy selection
   - Easy switching between policies

## Maintenance

### Regular Tasks
- **None** - ACM auto-renews certificates with DNS validation

### Monitoring Checklist
- [ ] Certificate expiry (ACM console)
- [ ] ALB target health (CloudWatch)
- [ ] HTTPS response codes (CloudWatch)
- [ ] SSL Labs score (quarterly)

### Troubleshooting Resources
1. Check `HTTPS_QUICKSTART.md` for quick solutions
2. Review `setup-acm-https.md` for detailed troubleshooting
3. Run `./test-https.sh` for automated diagnostics
4. Check AWS CloudWatch logs
5. Review ALB access logs (if enabled)

## Version Information

**Implementation Date:** 2024
**Terraform Version:** >= 1.0
**AWS Provider Version:** ~> 5.0
**Compatible Regions:** All AWS regions with ELB support

## References

### Internal Documentation
- `HTTPS_QUICKSTART.md` - User quick start guide
- `setup-acm-https.md` - Detailed setup instructions
- `HTTPS_SETUP_SUMMARY.md` - Overview and summary

### Helper Scripts
- `request-acm-certificate.sh` - ACM setup automation
- `test-https.sh` - HTTPS validation script

### Terraform Files
- `ecs.tf` - HTTP listener modifications
- `ecs_variables.tf` - New redirect variable
- `ecs_outputs.tf` - Enhanced HTTPS outputs
- `terraform.tfvars.ecs.example` - Configuration template

### AWS Documentation
- [ACM User Guide](https://docs.aws.amazon.com/acm/latest/userguide/)
- [ALB HTTPS Listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listener.html)
- [DNS Validation](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html)

## Support

For issues or questions:
1. Check troubleshooting sections in documentation
2. Run diagnostic scripts (`test-https.sh`)
3. Review CloudWatch logs
4. Check Terraform state: `terraform show`

---

**Implementation Status:** ✅ Complete and Production-Ready

