# Enabling HTTPS with ACM Certificate for ALB

This guide walks you through setting up HTTPS for your Application Load Balancer using AWS Certificate Manager (ACM).

## Prerequisites

1. **Domain name**: You need a domain that you control
2. **Route 53 (recommended)** or access to your domain's DNS settings
3. **AWS CLI configured** with appropriate permissions
4. **Terraform already deployed** (VPC, ALB, ECS service)

## Step 1: Request an ACM Certificate

### Option A: Using AWS Console

1. Go to AWS Certificate Manager in your AWS region (e.g., us-east-1)
2. Click "Request a certificate"
3. Choose "Request a public certificate"
4. Enter your domain name(s):
   - `example.com`
   - `*.example.com` (wildcard for subdomains)
5. Choose validation method:
   - **DNS validation** (recommended - faster, can be automated)
   - **Email validation** (requires email access)
6. Add tags if needed
7. Click "Request"

### Option B: Using AWS CLI

```bash
# Request certificate for your domain
aws acm request-certificate \
  --domain-name yourdomain.com \
  --subject-alternative-names *.yourdomain.com \
  --validation-method DNS \
  --region us-east-1

# Note the CertificateArn from the output
```

## Step 2: Validate the Certificate

### DNS Validation (Recommended)

After requesting the certificate, ACM will provide CNAME records to add to your DNS:

1. In ACM console, click on your certificate
2. Under "Domains", click "Create records in Route 53" (if using Route 53)
   - OR manually add the CNAME records to your DNS provider
3. Wait for validation (usually 5-30 minutes)
4. Certificate status will change to "Issued"

### Email Validation

If you chose email validation, check the email addresses for your domain and click the validation link.

## Step 3: Get Your Certificate ARN

Once the certificate is issued:

```bash
# List certificates and find your ARN
aws acm list-certificates --region us-east-1

# Or describe a specific certificate
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT-ID \
  --region us-east-1
```

The ARN will look like:
```
arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012
```

## Step 4: Update Terraform Configuration

Create or update your `terraform/terraform.tfvars` file:

```hcl
# Enable HTTPS
enable_https    = true
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/YOUR-CERT-ID"
```

## Step 5: Apply Terraform Changes

```bash
cd terraform

# Review the changes
terraform plan

# Apply the changes
terraform apply
```

This will:
- Add HTTPS listener (port 443) to your ALB
- Update ALB security group to allow port 443
- Configure SSL/TLS termination

## Step 6: Update DNS to Point to ALB

Get your ALB DNS name:

```bash
# From Terraform output
terraform output alb_dns_name

# Or from AWS CLI
aws elbv2 describe-load-balancers \
  --names bad-apples-cluster-alb \
  --region us-east-1 \
  --query 'LoadBalancers[0].DNSName' \
  --output text
```

### Create DNS Record

#### Using Route 53:

```bash
# Create an A record (alias) pointing to ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR-ZONE-ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.yourdomain.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "YOUR-ALB-HOSTED-ZONE-ID",
          "DNSName": "your-alb-dns-name.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": false
        }
      }
    }]
  }'
```

#### Using Other DNS Providers:

Create a CNAME record:
- **Name**: `api` (or your subdomain)
- **Type**: CNAME
- **Value**: Your ALB DNS name (e.g., `bad-apples-cluster-alb-123456789.us-east-1.elb.amazonaws.com`)
- **TTL**: 300 seconds

## Step 7: Test HTTPS Access

```bash
# Test HTTPS endpoint
curl https://api.yourdomain.com/health

# Check certificate details
curl -vI https://api.yourdomain.com/health 2>&1 | grep -i "subject\|issuer\|expire"

# Or use openssl
openssl s_client -connect api.yourdomain.com:443 -servername api.yourdomain.com
```

## Optional: Redirect HTTP to HTTPS

If you want to automatically redirect HTTP traffic to HTTPS, you'll need to update the Terraform configuration.

Add to `terraform/ecs.tf` after the HTTP listener (around line 274):

```hcl
# HTTP Listener - Redirect to HTTPS
resource "aws_lb_listener" "http" {
  count = var.create_vpc ? 1 : 0

  load_balancer_arn = aws_lb.main[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = var.enable_https ? "redirect" : "forward"
    
    # Redirect to HTTPS if enabled
    dynamic "redirect" {
      for_each = var.enable_https ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
    
    # Forward to target group if HTTPS not enabled
    target_group_arn = var.enable_https ? null : aws_lb_target_group.main[0].arn
  }
}
```

## Common Issues & Troubleshooting

### Certificate Validation Stuck

- **Issue**: Certificate stays in "Pending validation" status
- **Solution**: 
  - Verify DNS records are correct
  - Check that DNS changes have propagated (use `dig` or `nslookup`)
  - Wait up to 30 minutes for validation

### SSL Certificate Error in Browser

- **Issue**: Browser shows "Certificate name mismatch"
- **Solution**: Ensure your ACM certificate includes all domains/subdomains you're using

### 502 Bad Gateway

- **Issue**: HTTPS endpoint returns 502 error
- **Solution**: 
  - Check that ALB target group health checks are passing
  - Verify ECS tasks are running
  - Check security group rules allow ALB → ECS traffic

### Cost Considerations

- **ACM Certificates**: FREE for public certificates
- **ALB with HTTPS**: No additional cost (same as HTTP)
- **Data transfer**: Standard AWS data transfer rates apply

## Security Best Practices

1. **Use DNS validation**: Faster and more secure than email validation
2. **Enable deletion protection**: Set `enable_deletion_protection = true` in production
3. **Use strong SSL policy**: The default `ELBSecurityPolicy-2016-08` is good, but consider `ELBSecurityPolicy-TLS-1-2-2017-01` for stricter security
4. **Monitor certificate expiration**: ACM auto-renews certificates validated via DNS
5. **Use HTTPS only**: Consider redirecting all HTTP traffic to HTTPS

## Next Steps

1. **Update your frontend**: Change API endpoint from HTTP to HTTPS
2. **Update GitHub Actions**: Update deployment workflow with new endpoint
3. **Configure CORS**: Ensure CORS settings allow your HTTPS domain
4. **Test thoroughly**: Verify all API endpoints work over HTTPS

## Resources

- [AWS ACM Documentation](https://docs.aws.amazon.com/acm/)
- [ALB HTTPS Listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listener.html)
- [DNS Validation Guide](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html)

