#!/bin/bash

# =============================================================================
# Interactive Setup Script for API Keys and Secrets
# =============================================================================
# This script helps you create a terraform.tfvars file with your API keys
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

clear

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                    ║${NC}"
echo -e "${BLUE}║          Bad Apples MVP - Secrets Configuration Setup             ║${NC}"
echo -e "${BLUE}║                                                                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if terraform.tfvars already exists
if [ -f "terraform/terraform.tfvars" ]; then
    echo -e "${YELLOW}⚠️  Warning: terraform/terraform.tfvars already exists!${NC}"
    echo ""
    read -p "Do you want to overwrite it? (y/N): " OVERWRITE
    if [[ ! $OVERWRITE =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Keeping existing file. Exiting.${NC}"
        exit 0
    fi
fi

echo -e "${CYAN}This script will help you configure:${NC}"
echo "  • API keys for AI services"
echo "  • CORS origins for your frontend"
echo "  • Database configuration"
echo ""
echo -e "${YELLOW}Note: You can press Enter to skip any API key you don't have yet${NC}"
echo ""

read -p "Press Enter to continue..."
clear

# =============================================================================
# API Keys
# =============================================================================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                        API Keys Setup                              ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# Anthropic
echo -e "${GREEN}1. Anthropic Claude API Key${NC}"
echo "   Used for: AI text generation, scene creation"
echo "   Get from: ${CYAN}https://console.anthropic.com/settings/keys${NC}"
echo "   Format: sk-ant-api03-..."
echo ""
read -p "Enter Anthropic API Key (or press Enter to skip): " ANTHROPIC_KEY
echo ""

# OpenAI
echo -e "${GREEN}2. OpenAI API Key${NC}"
echo "   Used for: Alternative AI provider"
echo "   Get from: ${CYAN}https://platform.openai.com/api-keys${NC}"
echo "   Format: sk-..."
echo ""
read -p "Enter OpenAI API Key (or press Enter to skip): " OPENAI_KEY
echo ""

# Replicate
echo -e "${GREEN}3. Replicate API Token${NC}"
echo "   Used for: Video generation (REQUIRED for video features)"
echo "   Get from: ${CYAN}https://replicate.com/account/api-tokens${NC}"
echo "   Format: r8_..."
echo ""
read -p "Enter Replicate API Token (or press Enter to skip): " REPLICATE_KEY
echo ""

# ElevenLabs
echo -e "${GREEN}4. ElevenLabs API Key${NC}"
echo "   Used for: Voice synthesis, audio generation"
echo "   Get from: ${CYAN}https://elevenlabs.io/app/settings/api-keys${NC}"
echo ""
read -p "Enter ElevenLabs API Key (or press Enter to skip): " ELEVENLABS_KEY
echo ""

# Gemini
echo -e "${GREEN}5. Google Gemini API Key${NC}"
echo "   Used for: Optional alternative AI provider"
echo "   Get from: ${CYAN}https://makersuite.google.com/app/apikey${NC}"
echo "   Format: AIza..."
echo ""
read -p "Enter Gemini API Key (or press Enter to skip): " GEMINI_KEY
echo ""

# AWS Credentials
echo -e "${GREEN}6. AWS Access Key ID${NC}"
echo "   Used for: S3 access (if not using IAM roles)"
echo "   Get from: ${CYAN}AWS IAM Console${NC}"
echo ""
read -p "Enter AWS Access Key ID (or press Enter to skip): " AWS_ACCESS_KEY
echo ""

echo -e "${GREEN}7. AWS Secret Access Key${NC}"
echo "   Used for: S3 access (if not using IAM roles)"
echo "   Get from: ${CYAN}AWS IAM Console${NC}"
echo ""
read -sp "Enter AWS Secret Access Key (or press Enter to skip): " AWS_SECRET_KEY
echo ""

# =============================================================================
# CORS Configuration
# =============================================================================

clear
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                      CORS Configuration                            ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Configure which domains can access your API"
echo ""
echo -e "${YELLOW}Default origins:${NC}"
echo "  • http://localhost:3000"
echo "  • http://localhost:3001"
echo ""
echo "Add your production frontend URLs (comma-separated)"
echo "Example: https://yourdomain.com,https://app.yourdomain.com"
echo ""
read -p "Additional CORS origins (or press Enter for defaults): " CORS_EXTRA
echo ""

# Build CORS list
CORS_ORIGINS='  "http://localhost:3000",\n  "http://localhost:3001"'
if [ -n "$CORS_EXTRA" ]; then
    IFS=',' read -ra ORIGINS <<< "$CORS_EXTRA"
    for origin in "${ORIGINS[@]}"; do
        origin=$(echo "$origin" | xargs)  # Trim whitespace
        CORS_ORIGINS="${CORS_ORIGINS},\n  \"${origin}\""
    done
fi

# Count configured keys for summary
KEY_COUNT=0
[ -n "$ANTHROPIC_KEY" ] && ((KEY_COUNT++))
[ -n "$OPENAI_KEY" ] && ((KEY_COUNT++))
[ -n "$REPLICATE_KEY" ] && ((KEY_COUNT++))
[ -n "$ELEVENLABS_KEY" ] && ((KEY_COUNT++))
[ -n "$GEMINI_KEY" ] && ((KEY_COUNT++))
[ -n "$AWS_ACCESS_KEY" ] && ((KEY_COUNT++))
[ -n "$AWS_SECRET_KEY" ] && ((KEY_COUNT++))

# =============================================================================
# AWS Configuration
# =============================================================================

clear
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                      AWS Configuration                             ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

read -p "AWS Region [us-east-1]: " AWS_REGION
AWS_REGION="${AWS_REGION:-us-east-1}"

read -p "Environment (dev/staging/prod) [dev]: " ENVIRONMENT
ENVIRONMENT="${ENVIRONMENT:-dev}"

read -p "S3 Bucket Name [bad-apples-video-storage-${ENVIRONMENT}]: " BUCKET_NAME
BUCKET_NAME="${BUCKET_NAME:-bad-apples-video-storage-${ENVIRONMENT}}"

# =============================================================================
# Generate terraform.tfvars
# =============================================================================

clear
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    Generating Configuration                        ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

cat > terraform/terraform.tfvars <<EOF
# =============================================================================
# Terraform Variables - Auto-generated by setup-secrets.sh
# =============================================================================
# DO NOT COMMIT THIS FILE TO GIT!
# Generated on: $(date)
# =============================================================================

# =============================================================================
# AWS Configuration
# =============================================================================

aws_region  = "${AWS_REGION}"
environment = "${ENVIRONMENT}"
bucket_name = "${BUCKET_NAME}"

# =============================================================================
# API Keys
# =============================================================================

anthropic_api_key    = "${ANTHROPIC_KEY}"
openai_api_key       = "${OPENAI_KEY}"
replicate_api_key    = "${REPLICATE_KEY}"
elevenlabs_api_key   = "${ELEVENLABS_KEY}"
gemini_api_key       = "${GEMINI_KEY}"
aws_access_key_id    = "${AWS_ACCESS_KEY}"
aws_secret_access_key = "${AWS_SECRET_KEY}"

database_url = "sqlite:///./video_generator.db"

# =============================================================================
# CORS Configuration
# =============================================================================

cors_allowed_origins = [
$(echo -e "$CORS_ORIGINS")
]

# =============================================================================
# ECS Configuration (defaults from variables)
# =============================================================================

ecs_cluster_name    = "bad-apples-cluster"
ecs_service_name    = "bad-apples-backend-service"
ecs_task_family     = "bad-apples-backend-task"
ecr_repository_name = "bad-apples-backend"

# Task Resources
ecs_task_cpu    = 1024  # 1 vCPU
ecs_task_memory = 2048  # 2 GB

# Auto-scaling
ecs_desired_count = 1
ecs_min_capacity  = 1
ecs_max_capacity  = 4

# =============================================================================
# Generated by setup-secrets.sh
# =============================================================================
EOF

echo -e "${GREEN}✓ Created terraform/terraform.tfvars${NC}"
echo ""

# Check .gitignore
if ! grep -q "terraform.tfvars" .gitignore 2>/dev/null; then
    echo "terraform/terraform.tfvars" >> .gitignore
    echo -e "${GREEN}✓ Added terraform.tfvars to .gitignore${NC}"
else
    echo -e "${GREEN}✓ terraform.tfvars already in .gitignore${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                         Summary                                    ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# Show configured keys
[ -n "$ANTHROPIC_KEY" ] && echo -e "${GREEN}✓${NC} Anthropic API Key configured"
[ -n "$OPENAI_KEY" ] && echo -e "${GREEN}✓${NC} OpenAI API Key configured"
[ -n "$REPLICATE_KEY" ] && echo -e "${GREEN}✓${NC} Replicate API Token configured"
[ -n "$ELEVENLABS_KEY" ] && echo -e "${GREEN}✓${NC} ElevenLabs API Key configured"
[ -n "$GEMINI_KEY" ] && echo -e "${GREEN}✓${NC} Gemini API Key configured"
[ -n "$AWS_ACCESS_KEY" ] && echo -e "${GREEN}✓${NC} AWS Access Key ID configured"
[ -n "$AWS_SECRET_KEY" ] && echo -e "${GREEN}✓${NC} AWS Secret Access Key configured"

if [ $KEY_COUNT -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No secrets configured${NC}"
    echo "   You can add them later by editing terraform/terraform.tfvars"
else
    echo ""
    echo -e "${GREEN}✓ ${KEY_COUNT} secret(s) configured${NC}"
fi

echo ""
echo -e "${CYAN}Configuration saved to:${NC} terraform/terraform.tfvars"
echo ""

# =============================================================================
# Next Steps
# =============================================================================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                       Next Steps                                   ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "1. Review the configuration:"
echo "   ${CYAN}cat terraform/terraform.tfvars${NC}"
echo ""
echo "2. Deploy to AWS:"
echo "   ${CYAN}cd terraform${NC}"
echo "   ${CYAN}terraform init${NC}"
echo "   ${CYAN}terraform plan${NC}"
echo "   ${CYAN}terraform apply${NC}"
echo ""
echo "3. Get the deployment URL:"
echo "   ${CYAN}terraform output -raw alb_url${NC}"
echo ""
echo "4. View logs:"
echo "   ${CYAN}aws logs tail /ecs/bad-apples-backend-task --follow${NC}"
echo ""
echo -e "${GREEN}Setup complete! 🚀${NC}"
echo ""

