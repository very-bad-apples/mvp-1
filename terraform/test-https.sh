#!/bin/bash
# Script to test HTTPS configuration for ALB

set -e

echo "=========================================="
echo "HTTPS Configuration Test"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get domain from user or use ALB DNS
read -p "Enter your domain (e.g., api.yourdomain.com) or press Enter to use ALB DNS: " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "Getting ALB DNS from Terraform..."
    if command -v terraform &> /dev/null; then
        cd "$(dirname "$0")"
        DOMAIN=$(terraform output -raw alb_dns_name 2>/dev/null || echo "")
        if [ -z "$DOMAIN" ]; then
            echo -e "${RED}❌ Could not get ALB DNS from Terraform${NC}"
            echo "   Please enter domain manually or deploy infrastructure first"
            exit 1
        fi
        echo "Using ALB DNS: $DOMAIN"
    else
        echo -e "${RED}❌ Terraform not found and no domain provided${NC}"
        exit 1
    fi
fi

echo ""
echo "Testing domain: $DOMAIN"
echo "=========================================="
echo ""

# Test 1: DNS Resolution
echo "Test 1: DNS Resolution"
echo "----------------------"
if host "$DOMAIN" &> /dev/null; then
    DNS_IP=$(host "$DOMAIN" | grep "has address" | head -1 | awk '{print $4}')
    echo -e "${GREEN}✅ DNS resolves to: $DNS_IP${NC}"
else
    echo -e "${RED}❌ DNS does not resolve${NC}"
    echo "   Fix: Update DNS records to point to ALB"
    exit 1
fi

# Test 2: HTTP Connection
echo ""
echo "Test 2: HTTP Connection (Port 80)"
echo "---------------------------------"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -m 10 "http://$DOMAIN/health" 2>/dev/null || echo "000")

if [ "$HTTP_STATUS" = "301" ] || [ "$HTTP_STATUS" = "302" ]; then
    REDIRECT_URL=$(curl -s -I -m 10 "http://$DOMAIN/health" 2>/dev/null | grep -i "location:" | awk '{print $2}' | tr -d '\r')
    echo -e "${GREEN}✅ HTTP redirects to HTTPS (Status: $HTTP_STATUS)${NC}"
    echo "   Redirect URL: $REDIRECT_URL"
elif [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${YELLOW}⚠️  HTTP works but doesn't redirect to HTTPS (Status: 200)${NC}"
    echo "   Consider enabling: redirect_http_to_https = true"
elif [ "$HTTP_STATUS" = "000" ]; then
    echo -e "${RED}❌ HTTP connection failed (timeout or refused)${NC}"
    echo "   Check: ALB security group allows port 80"
else
    echo -e "${YELLOW}⚠️  HTTP returned status: $HTTP_STATUS${NC}"
fi

# Test 3: HTTPS Connection
echo ""
echo "Test 3: HTTPS Connection (Port 443)"
echo "-----------------------------------"
if curl -k -s -m 10 "https://$DOMAIN/health" &> /dev/null; then
    HTTPS_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" -m 10 "https://$DOMAIN/health")
    
    if [ "$HTTPS_STATUS" = "200" ]; then
        echo -e "${GREEN}✅ HTTPS connection successful (Status: 200)${NC}"
    else
        echo -e "${YELLOW}⚠️  HTTPS connected but returned status: $HTTPS_STATUS${NC}"
    fi
else
    echo -e "${RED}❌ HTTPS connection failed${NC}"
    echo "   Check:"
    echo "   - enable_https = true in terraform.tfvars"
    echo "   - Valid certificate_arn configured"
    echo "   - ALB security group allows port 443"
    exit 1
fi

# Test 4: SSL Certificate Validation
echo ""
echo "Test 4: SSL Certificate Validation"
echo "-----------------------------------"
if command -v openssl &> /dev/null; then
    CERT_INFO=$(echo | openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null)
    
    if [ ! -z "$CERT_INFO" ]; then
        echo -e "${GREEN}✅ SSL certificate is valid${NC}"
        echo ""
        echo "$CERT_INFO" | while IFS= read -r line; do
            echo "   $line"
        done
        
        # Check certificate expiry
        EXPIRY_DATE=$(echo "$CERT_INFO" | grep "notAfter" | cut -d'=' -f2)
        echo ""
        echo "   Certificate expires: $EXPIRY_DATE"
        
        # Check issuer
        ISSUER=$(echo "$CERT_INFO" | grep "issuer" | grep -o "O = [^,]*" | cut -d'=' -f2 | xargs)
        if [[ "$ISSUER" == *"Amazon"* ]]; then
            echo -e "   ${GREEN}Issued by: Amazon (ACM)${NC}"
        else
            echo "   Issued by: $ISSUER"
        fi
    else
        echo -e "${RED}❌ Could not retrieve certificate information${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  OpenSSL not found, skipping certificate validation${NC}"
    echo "   Install: apt-get install openssl"
fi

# Test 5: Certificate Hostname Match
echo ""
echo "Test 5: Certificate Hostname Match"
echo "-----------------------------------"
CERT_VERIFY=$(curl -s -o /dev/null -w "%{http_code}" -m 10 "https://$DOMAIN/health" 2>&1)

if [ "$CERT_VERIFY" = "200" ]; then
    echo -e "${GREEN}✅ Certificate matches hostname${NC}"
elif [[ "$CERT_VERIFY" == *"certificate"* ]] || [[ "$CERT_VERIFY" == *"SSL"* ]]; then
    echo -e "${RED}❌ Certificate hostname mismatch or invalid${NC}"
    echo "   Ensure ACM certificate includes: $DOMAIN"
else
    echo -e "${GREEN}✅ Certificate appears valid${NC}"
fi

# Test 6: API Health Endpoint
echo ""
echo "Test 6: API Health Check Response"
echo "----------------------------------"
HEALTH_RESPONSE=$(curl -s -m 10 "https://$DOMAIN/health" 2>/dev/null || echo "")

if [ ! -z "$HEALTH_RESPONSE" ]; then
    echo -e "${GREEN}✅ API responding${NC}"
    echo "   Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}❌ API not responding${NC}"
    echo "   Check:"
    echo "   - ECS tasks are running"
    echo "   - Target group health checks passing"
    echo "   - Backend /health endpoint works"
fi

# Test 7: TLS Version Support
echo ""
echo "Test 7: TLS Protocol Support"
echo "-----------------------------"
if command -v openssl &> /dev/null; then
    # Test TLS 1.2
    if openssl s_client -connect "$DOMAIN:443" -tls1_2 -servername "$DOMAIN" </dev/null 2>&1 | grep -q "Protocol.*TLSv1.2"; then
        echo -e "${GREEN}✅ TLS 1.2 supported${NC}"
    else
        echo -e "${YELLOW}⚠️  TLS 1.2 not available${NC}"
    fi
    
    # Test TLS 1.3
    if openssl s_client -connect "$DOMAIN:443" -tls1_3 -servername "$DOMAIN" </dev/null 2>&1 | grep -q "Protocol.*TLSv1.3"; then
        echo -e "${GREEN}✅ TLS 1.3 supported${NC}"
    fi
fi

# Summary
echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="

# Check overall status
OVERALL_STATUS="pass"

if [ "$HTTPS_STATUS" != "200" ]; then
    OVERALL_STATUS="fail"
fi

if [ "$OVERALL_STATUS" = "pass" ]; then
    echo -e "${GREEN}✅ HTTPS is configured correctly!${NC}"
    echo ""
    echo "Your API is accessible at: https://$DOMAIN"
    echo ""
    echo "Next steps:"
    echo "1. Update frontend to use HTTPS endpoint"
    echo "2. Update CORS settings for HTTPS domain"
    echo "3. Update any API documentation"
else
    echo -e "${RED}❌ HTTPS configuration has issues${NC}"
    echo ""
    echo "Review the errors above and check:"
    echo "1. Terraform configuration (enable_https, certificate_arn)"
    echo "2. ACM certificate is validated and issued"
    echo "3. Security groups allow ports 80 and 443"
    echo "4. DNS points to ALB"
    echo ""
    echo "See: terraform/HTTPS_QUICKSTART.md for troubleshooting"
fi

echo ""
echo "For detailed testing, visit:"
echo "  https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo ""

