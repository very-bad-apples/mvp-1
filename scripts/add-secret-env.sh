#!/bin/bash

# =============================================================================
# Add New Secret Environment Variable to ECS Container
# =============================================================================
# This script helps you add a new secret environment variable to your ECS task
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SECRET_NAME="bad-apples-backend-task-secrets"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}          Add New Secret Environment Variable to ECS                ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed${NC}"
    echo "Install with: brew install jq (Mac) or apt-get install jq (Linux)"
    exit 1
fi

# Get secret name
read -p "Enter the environment variable name (e.g., MY_API_KEY): " ENV_NAME

if [ -z "$ENV_NAME" ]; then
    echo -e "${RED}Error: Environment variable name is required${NC}"
    exit 1
fi

# Validate name (uppercase, alphanumeric and underscores only)
if [[ ! "$ENV_NAME" =~ ^[A-Z][A-Z0-9_]*$ ]]; then
    echo -e "${YELLOW}Warning: Environment variable names should be UPPERCASE${NC}"
    read -p "Continue anyway? (y/N): " CONTINUE
    if [[ ! $CONTINUE =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Get secret value
read -sp "Enter the secret value: " SECRET_VALUE
echo ""

if [ -z "$SECRET_VALUE" ]; then
    echo -e "${RED}Error: Secret value is required${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Updating AWS Secrets Manager...${NC}"

# Get current secret
CURRENT_SECRET=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$AWS_REGION" \
    --query SecretString \
    --output text 2>/dev/null || echo '{}')

# Add new key to secret
UPDATED_SECRET=$(echo "$CURRENT_SECRET" | jq --arg key "$ENV_NAME" --arg value "$SECRET_VALUE" '. + {($key): $value}')

# Update secret
aws secretsmanager update-secret \
    --secret-id "$SECRET_NAME" \
    --secret-string "$UPDATED_SECRET" \
    --region "$AWS_REGION" \
    > /dev/null

echo -e "${GREEN}✓ Secret updated in AWS Secrets Manager${NC}"
echo ""

# Now update Terraform files
echo -e "${BLUE}Updating Terraform configuration...${NC}"

TERRAFORM_DIR="terraform"

# Check if we're in the right directory
if [ ! -d "$TERRAFORM_DIR" ]; then
    if [ -d "../terraform" ]; then
        TERRAFORM_DIR="../terraform"
    else
        echo -e "${YELLOW}Warning: Could not find terraform directory${NC}"
        echo "Please run this script from the project root or terraform directory"
        exit 1
    fi
fi

# 1. Add to secrets.tf (if it exists)
if [ -f "$TERRAFORM_DIR/secrets.tf" ]; then
    echo -e "${CYAN}→ Updating secrets.tf${NC}"
    
    # Check if variable already exists
    if grep -q "variable \"${ENV_NAME,,}\"" "$TERRAFORM_DIR/secrets.tf" 2>/dev/null; then
        echo -e "${YELLOW}  Variable already exists in secrets.tf${NC}"
    else
        # Add variable (we'll need to add it manually or use a template)
        echo -e "${YELLOW}  Note: You may need to add variable definition manually${NC}"
    fi
    
    # Update the secret_string in secrets.tf
    # This is complex, so we'll just show what needs to be added
    echo -e "${CYAN}  Add to secret_string in secrets.tf:${NC}"
    echo -e "${YELLOW}    ${ENV_NAME} = var.${ENV_NAME,,}${NC}"
fi

# 2. Add to ecs.tf
if [ -f "$TERRAFORM_DIR/ecs.tf" ]; then
    echo -e "${CYAN}→ Updating ecs.tf${NC}"
    
    # Check if already in secrets array
    if grep -q "\"${ENV_NAME}\"" "$TERRAFORM_DIR/ecs.tf"; then
        echo -e "${YELLOW}  Secret already configured in ecs.tf${NC}"
    else
        # Show what needs to be added
        echo -e "${CYAN}  Add to secrets array in ecs.tf:${NC}"
        echo -e "${YELLOW}    {${NC}"
        echo -e "${YELLOW}      name      = \"${ENV_NAME}\"${NC}"
        echo -e "${YELLOW}      valueFrom = \"\${aws_secretsmanager_secret.app_secrets.arn}:${ENV_NAME}::\"${NC}"
        echo -e "${YELLOW}    },${NC}"
    fi
fi

# 3. Add to variables.tf
if [ -f "$TERRAFORM_DIR/variables.tf" ]; then
    echo -e "${CYAN}→ Checking variables.tf${NC}"
    
    VAR_NAME=$(echo "$ENV_NAME" | tr '[:upper:]' '[:lower:]' | tr '_' '_')
    
    if grep -q "variable \"${VAR_NAME}\"" "$TERRAFORM_DIR/variables.tf" 2>/dev/null; then
        echo -e "${YELLOW}  Variable already exists in variables.tf${NC}"
    else
        echo -e "${CYAN}  Add to variables.tf:${NC}"
        cat <<EOF | sed 's/^/  /'
variable "${VAR_NAME}" {
  description = "${ENV_NAME} secret"
  type        = string
  default     = ""
  sensitive   = true
}
EOF
    fi
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Secret added to AWS Secrets Manager${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "1. Update Terraform files (see above for what to add)"
echo "2. Apply Terraform changes:"
echo "   ${CYAN}cd $TERRAFORM_DIR${NC}"
echo "   ${CYAN}terraform apply${NC}"
echo ""
echo "3. Force new ECS deployment to pick up the secret:"
echo "   ${CYAN}aws ecs update-service \\${NC}"
echo "     ${CYAN}--cluster bad-apples-cluster \\${NC}"
echo "     ${CYAN}--service bad-apples-backend-service \\${NC}"
echo "     ${CYAN}--force-new-deployment \\${NC}"
echo "     ${CYAN}--region $AWS_REGION${NC}"
echo ""
echo -e "${GREEN}Done! 🎉${NC}"

