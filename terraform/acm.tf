# =============================================================================
# ACM Certificate for HTTPS
# =============================================================================
# This creates an SSL/TLS certificate for your domain using AWS Certificate Manager
# After running terraform apply, you'll need to add the DNS validation records to Cloudflare
# =============================================================================

# ACM Certificate for bigbadapples.com and *.bigbadapples.com
resource "aws_acm_certificate" "main" {
  domain_name               = "bigbadapples.com"
  subject_alternative_names = ["*.bigbadapples.com"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name        = "bigbadapples.com"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "bad-apples-mvp"
  }
}

# Certificate Validation is handled manually
# After adding DNS records to Cloudflare, the certificate will auto-validate
# Check status in AWS Certificate Manager console or run:
# aws acm describe-certificate --certificate-arn <arn>

# Output the DNS validation records
output "certificate_validation_records" {
  description = "DNS records to add to Cloudflare for certificate validation"
  value = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      value  = dvo.resource_record_value
      domain = dvo.domain_name
    }
  }
}
