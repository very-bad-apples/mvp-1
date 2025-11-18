#!/bin/bash
# Script to request and configure ACM certificate for ALB HTTPS

set -e

echo "=========================================="
echo "ACM Certificate Request Helper"
echo "=========================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    echo "   https://aws.amazon.com/cli/"
    exit 1
fi

# Check if jq is installed (for JSON parsing)
if ! command -v jq &> /dev/null; then
    echo "⚠️  jq is not installed. Installing..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install -y jq
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install jq
    else
        echo "Please install jq manually: https://stedolan.github.io/jq/"
        exit 1
    fi
fi

# Get AWS region
echo "Step 1: AWS Configuration"
echo "=========================="
read -p "Enter AWS region (default: us-east-1): " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

# Verify AWS credentials
echo ""
echo "Verifying AWS credentials..."
if ! aws sts get-caller-identity --region $AWS_REGION &> /dev/null; then
    echo "❌ AWS credentials not configured or invalid"
    echo "   Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✅ Authenticated as AWS Account: $ACCOUNT_ID"
echo ""

# Get domain name
echo "Step 2: Domain Configuration"
echo "============================="
read -p "Enter your domain name (e.g., example.com): " DOMAIN_NAME

if [ -z "$DOMAIN_NAME" ]; then
    echo "❌ Domain name is required"
    exit 1
fi

# Ask about wildcard
read -p "Include wildcard subdomain (*.$DOMAIN_NAME)? (y/n, default: y): " INCLUDE_WILDCARD
INCLUDE_WILDCARD=${INCLUDE_WILDCARD:-y}

# Ask about subdomain
read -p "Add specific subdomain (e.g., api)? (press Enter to skip): " SUBDOMAIN

# Build subject alternative names
SAN_ARGS=""
if [[ "$INCLUDE_WILDCARD" == "y" ]]; then
    SAN_ARGS="--subject-alternative-names *.$DOMAIN_NAME"
fi

if [ ! -z "$SUBDOMAIN" ]; then
    FULL_SUBDOMAIN="$SUBDOMAIN.$DOMAIN_NAME"
    if [ -z "$SAN_ARGS" ]; then
        SAN_ARGS="--subject-alternative-names $FULL_SUBDOMAIN"
    else
        SAN_ARGS="$SAN_ARGS $FULL_SUBDOMAIN"
    fi
fi

echo ""
echo "Certificate will cover:"
echo "  - $DOMAIN_NAME"
if [[ "$INCLUDE_WILDCARD" == "y" ]]; then
    echo "  - *.$DOMAIN_NAME"
fi
if [ ! -z "$SUBDOMAIN" ]; then
    echo "  - $FULL_SUBDOMAIN"
fi

echo ""
read -p "Proceed with certificate request? (y/n): " PROCEED
if [[ "$PROCEED" != "y" ]]; then
    echo "Aborted."
    exit 0
fi

# Request certificate
echo ""
echo "Step 3: Requesting ACM Certificate"
echo "==================================="
echo "Requesting certificate..."

CERT_ARN=$(aws acm request-certificate \
    --domain-name "$DOMAIN_NAME" \
    $SAN_ARGS \
    --validation-method DNS \
    --region $AWS_REGION \
    --tags Key=Name,Value="$DOMAIN_NAME" Key=ManagedBy,Value=Terraform Key=Project,Value=bad-apples-mvp \
    --query CertificateArn \
    --output text)

if [ -z "$CERT_ARN" ]; then
    echo "❌ Failed to request certificate"
    exit 1
fi

echo "✅ Certificate requested successfully!"
echo "   ARN: $CERT_ARN"
echo ""

# Wait a moment for AWS to process
echo "Waiting for certificate details..."
sleep 3

# Get validation records
echo ""
echo "Step 4: DNS Validation Records"
echo "==============================="
echo "Retrieving DNS validation records..."

CERT_DETAILS=$(aws acm describe-certificate \
    --certificate-arn "$CERT_ARN" \
    --region $AWS_REGION \
    --output json)

echo ""
echo "DNS Validation Records (add these to your DNS):"
echo "================================================"
echo ""

# Parse and display validation records
echo "$CERT_DETAILS" | jq -r '.Certificate.DomainValidationOptions[] | 
    "Domain: \(.DomainName)\n" +
    "Record Name: \(.ResourceRecord.Name)\n" +
    "Record Type: \(.ResourceRecord.Type)\n" +
    "Record Value: \(.ResourceRecord.Value)\n" +
    "----------------------------------------"'

# Check if using Route 53
echo ""
read -p "Are you using Route 53 for DNS? (y/n): " USING_ROUTE53

if [[ "$USING_ROUTE53" == "y" ]]; then
    echo ""
    echo "Step 5: Automatic Route 53 Validation"
    echo "======================================"
    
    # List hosted zones
    echo "Finding Route 53 hosted zones..."
    HOSTED_ZONES=$(aws route53 list-hosted-zones --output json)
    
    echo ""
    echo "Available hosted zones:"
    echo "$HOSTED_ZONES" | jq -r '.HostedZones[] | "\(.Name) - \(.Id)"'
    
    echo ""
    read -p "Create validation records automatically in Route 53? (y/n): " AUTO_VALIDATE
    
    if [[ "$AUTO_VALIDATE" == "y" ]]; then
        # Extract validation records and create Route 53 records
        VALIDATION_OPTIONS=$(echo "$CERT_DETAILS" | jq -r '.Certificate.DomainValidationOptions[0].ResourceRecord')
        
        RECORD_NAME=$(echo "$VALIDATION_OPTIONS" | jq -r '.Name')
        RECORD_VALUE=$(echo "$VALIDATION_OPTIONS" | jq -r '.Value')
        
        # Find the hosted zone ID for the domain
        ZONE_ID=$(aws route53 list-hosted-zones --output json | \
            jq -r --arg domain "$DOMAIN_NAME." '.HostedZones[] | select(.Name == $domain) | .Id' | \
            cut -d'/' -f3)
        
        if [ -z "$ZONE_ID" ]; then
            echo "❌ Could not find hosted zone for $DOMAIN_NAME"
            echo "   Please create DNS records manually"
        else
            echo "Creating DNS validation records in Route 53..."
            
            # Create change batch JSON
            CHANGE_BATCH=$(cat <<EOF
{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "$RECORD_NAME",
      "Type": "CNAME",
      "TTL": 300,
      "ResourceRecords": [{"Value": "$RECORD_VALUE"}]
    }
  }]
}
EOF
)
            
            aws route53 change-resource-record-sets \
                --hosted-zone-id "$ZONE_ID" \
                --change-batch "$CHANGE_BATCH" \
                --output json > /dev/null
            
            echo "✅ DNS validation records created in Route 53!"
        fi
    fi
else
    echo ""
    echo "Manual DNS Configuration Required:"
    echo "=================================="
    echo "1. Log in to your DNS provider"
    echo "2. Add the CNAME records shown above"
    echo "3. Wait for DNS propagation (5-30 minutes)"
    echo ""
fi

# Wait for validation
echo ""
echo "Step 6: Waiting for Certificate Validation"
echo "==========================================="
echo "This may take 5-30 minutes..."
echo ""
read -p "Wait for validation now? (y/n): " WAIT_VALIDATION

if [[ "$WAIT_VALIDATION" == "y" ]]; then
    echo "Checking validation status (will timeout after 30 minutes)..."
    
    aws acm wait certificate-validated \
        --certificate-arn "$CERT_ARN" \
        --region $AWS_REGION \
        && echo "✅ Certificate validated successfully!" \
        || echo "⚠️  Validation timeout. Check ACM console for status."
fi

# Update Terraform configuration
echo ""
echo "Step 7: Update Terraform Configuration"
echo "======================================="
echo ""
echo "Add these lines to your terraform/terraform.tfvars file:"
echo ""
echo "# HTTPS Configuration"
echo "enable_https    = true"
echo "certificate_arn = \"$CERT_ARN\""
echo ""

# Offer to update tfvars automatically
if [ -f "terraform.tfvars" ]; then
    read -p "Update terraform.tfvars automatically? (y/n): " UPDATE_TFVARS
    
    if [[ "$UPDATE_TFVARS" == "y" ]]; then
        # Backup existing file
        cp terraform.tfvars terraform.tfvars.backup
        
        # Remove old HTTPS config if exists
        sed -i '/^enable_https/d' terraform.tfvars
        sed -i '/^certificate_arn/d' terraform.tfvars
        
        # Add new HTTPS config
        echo "" >> terraform.tfvars
        echo "# HTTPS Configuration (added by request-acm-certificate.sh)" >> terraform.tfvars
        echo "enable_https    = true" >> terraform.tfvars
        echo "certificate_arn = \"$CERT_ARN\"" >> terraform.tfvars
        
        echo "✅ terraform.tfvars updated!"
        echo "   Backup saved to: terraform.tfvars.backup"
    fi
fi

# Next steps
echo ""
echo "=========================================="
echo "🎉 Setup Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Verify certificate is validated in ACM console"
echo "2. Apply Terraform changes:"
echo "   cd terraform"
echo "   terraform plan"
echo "   terraform apply"
echo ""
echo "3. Update DNS to point to your ALB:"
echo "   Get ALB DNS: terraform output alb_dns_name"
echo "   Create CNAME: api.$DOMAIN_NAME -> <alb-dns-name>"
echo ""
echo "4. Test HTTPS access:"
echo "   curl https://api.$DOMAIN_NAME/health"
echo ""
echo "Certificate ARN: $CERT_ARN"
echo ""
echo "For detailed instructions, see: terraform/setup-acm-https.md"
echo ""

