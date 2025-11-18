#!/bin/bash

# Verify ECS Fargate Deployment Script
# This script verifies that the deployment is working correctly

set -e

echo "========================================"
echo "ECS Fargate Deployment Verification"
echo "========================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters for summary
PASSED=0
FAILED=0
WARNINGS=0

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    FAILED=$((FAILED + 1))
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASSED=$((PASSED + 1))
}

print_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Check required tools
command -v aws >/dev/null 2>&1 || {
    print_error "AWS CLI is not installed. Please install AWS CLI first."
    exit 1
}

command -v curl >/dev/null 2>&1 || {
    print_error "curl is not installed. Please install curl first."
    exit 1
}

# Get configuration
if [ -d "terraform" ] && [ -f "terraform/terraform.tfstate" ]; then
    cd terraform
    ALB_URL=$(tofu output -raw alb_url 2>/dev/null || echo "")
    ALB_DNS=$(tofu output -raw alb_dns_name 2>/dev/null || echo "")
    ECS_CLUSTER=$(tofu output -raw ecs_cluster_name 2>/dev/null || echo "bad-apples-cluster")
    ECS_SERVICE=$(tofu output -raw ecs_service_name 2>/dev/null || echo "bad-apples-backend-service")
    AWS_REGION=$(tofu output -raw aws_region 2>/dev/null || echo "us-east-1")
    ECR_REPO=$(tofu output -raw ecr_repository_name 2>/dev/null || echo "bad-apples-backend")
    cd ..
else
    # Use defaults if OpenTofu state not found
    ECS_CLUSTER="bad-apples-cluster"
    ECS_SERVICE="bad-apples-backend-service"
    AWS_REGION="us-east-1"
    ECR_REPO="bad-apples-backend"
    ALB_URL=""
fi

# If ALB URL not found, ask user
if [ -z "$ALB_URL" ]; then
    echo ""
    read -p "Enter your ALB URL (or press Enter to skip HTTP tests): " ALB_URL
fi

print_info "Configuration:"
print_info "  AWS Region: $AWS_REGION"
print_info "  ECS Cluster: $ECS_CLUSTER"
print_info "  ECS Service: $ECS_SERVICE"
print_info "  ECR Repository: $ECR_REPO"
print_info "  ALB URL: ${ALB_URL:-Not provided}"

# Test 1: Check AWS CLI authentication
print_section "1. AWS Authentication"

if aws sts get-caller-identity > /dev/null 2>&1; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
    print_success "AWS CLI authenticated"
    print_info "  Account ID: $ACCOUNT_ID"
    print_info "  User/Role: $USER_ARN"
else
    print_error "AWS CLI not authenticated. Run: aws configure"
fi

# Test 2: Check ECR repository
print_section "2. ECR Repository"

if aws ecr describe-repositories --repository-names $ECR_REPO --region $AWS_REGION > /dev/null 2>&1; then
    IMAGE_COUNT=$(aws ecr list-images --repository-name $ECR_REPO --region $AWS_REGION --query 'length(imageIds)' --output text)
    print_success "ECR repository exists: $ECR_REPO"
    print_info "  Image count: $IMAGE_COUNT"
    
    if [ "$IMAGE_COUNT" -eq 0 ]; then
        print_warning "No images in repository. Push an image first."
    fi
    
    # Get latest image
    LATEST_IMAGE=$(aws ecr describe-images --repository-name $ECR_REPO --region $AWS_REGION \
        --query 'sort_by(imageDetails,& imagePushedAt)[-1].imageTags[0]' --output text 2>/dev/null || echo "")
    
    if [ -n "$LATEST_IMAGE" ] && [ "$LATEST_IMAGE" != "None" ]; then
        print_info "  Latest image tag: $LATEST_IMAGE"
    fi
else
    print_error "ECR repository not found: $ECR_REPO"
fi

# Test 3: Check ECS cluster
print_section "3. ECS Cluster"

if aws ecs describe-clusters --clusters $ECS_CLUSTER --region $AWS_REGION > /dev/null 2>&1; then
    CLUSTER_STATUS=$(aws ecs describe-clusters --clusters $ECS_CLUSTER --region $AWS_REGION \
        --query 'clusters[0].status' --output text)
    TASK_COUNT=$(aws ecs describe-clusters --clusters $ECS_CLUSTER --region $AWS_REGION \
        --query 'clusters[0].runningTasksCount' --output text)
    
    if [ "$CLUSTER_STATUS" == "ACTIVE" ]; then
        print_success "ECS cluster is active: $ECS_CLUSTER"
        print_info "  Running tasks: $TASK_COUNT"
    else
        print_error "ECS cluster status: $CLUSTER_STATUS"
    fi
else
    print_error "ECS cluster not found: $ECS_CLUSTER"
fi

# Test 4: Check ECS service
print_section "4. ECS Service"

SERVICE_INFO=$(aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE \
    --region $AWS_REGION 2>/dev/null)

if [ $? -eq 0 ]; then
    SERVICE_STATUS=$(echo $SERVICE_INFO | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
    DESIRED_COUNT=$(echo $SERVICE_INFO | grep -o '"desiredCount":[0-9]*' | head -1 | cut -d':' -f2)
    RUNNING_COUNT=$(echo $SERVICE_INFO | grep -o '"runningCount":[0-9]*' | head -1 | cut -d':' -f2)
    PENDING_COUNT=$(echo $SERVICE_INFO | grep -o '"pendingCount":[0-9]*' | head -1 | cut -d':' -f2)
    
    if [ "$SERVICE_STATUS" == "ACTIVE" ]; then
        print_success "ECS service is active: $ECS_SERVICE"
        print_info "  Desired tasks: $DESIRED_COUNT"
        print_info "  Running tasks: $RUNNING_COUNT"
        print_info "  Pending tasks: $PENDING_COUNT"
        
        if [ "$RUNNING_COUNT" -lt "$DESIRED_COUNT" ]; then
            print_warning "Not all tasks are running ($RUNNING_COUNT/$DESIRED_COUNT)"
        fi
        
        if [ "$RUNNING_COUNT" -eq 0 ]; then
            print_error "No tasks are running!"
        fi
    else
        print_error "ECS service status: $SERVICE_STATUS"
    fi
    
    # Check recent events
    print_info "Recent service events:"
    aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION \
        --query 'services[0].events[0:3].[createdAt,message]' --output text | while read line; do
        print_info "    $line"
    done
else
    print_error "ECS service not found: $ECS_SERVICE"
fi

# Test 5: Check running tasks
print_section "5. Running Tasks"

TASK_ARNS=$(aws ecs list-tasks --cluster $ECS_CLUSTER --service-name $ECS_SERVICE \
    --region $AWS_REGION --query 'taskArns[*]' --output text)

if [ -n "$TASK_ARNS" ]; then
    TASK_COUNT=$(echo $TASK_ARNS | wc -w)
    print_success "Found $TASK_COUNT running task(s)"
    
    # Get details of first task
    FIRST_TASK=$(echo $TASK_ARNS | awk '{print $1}')
    TASK_DETAILS=$(aws ecs describe-tasks --cluster $ECS_CLUSTER --tasks $FIRST_TASK \
        --region $AWS_REGION 2>/dev/null)
    
    TASK_STATUS=$(echo $TASK_DETAILS | grep -o '"lastStatus":"[^"]*"' | head -1 | cut -d'"' -f4)
    HEALTH_STATUS=$(echo $TASK_DETAILS | grep -o '"healthStatus":"[^"]*"' | head -1 | cut -d'"' -f4)
    
    print_info "  Task status: $TASK_STATUS"
    
    if [ -n "$HEALTH_STATUS" ]; then
        if [ "$HEALTH_STATUS" == "HEALTHY" ]; then
            print_success "  Task is healthy"
        else
            print_warning "  Task health: $HEALTH_STATUS"
        fi
    fi
else
    print_error "No running tasks found"
fi

# Test 6: Check ALB target health
print_section "6. Load Balancer Health"

# Find target group
TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups --region $AWS_REGION \
    --query "TargetGroups[?contains(TargetGroupName, '$ECS_CLUSTER')].TargetGroupArn" \
    --output text 2>/dev/null)

if [ -n "$TARGET_GROUP_ARN" ]; then
    print_success "Target group found"
    
    # Check target health
    TARGET_HEALTH=$(aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN \
        --region $AWS_REGION 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        HEALTHY_COUNT=$(echo $TARGET_HEALTH | grep -o '"State":"healthy"' | wc -l)
        UNHEALTHY_COUNT=$(echo $TARGET_HEALTH | grep -o '"State":"unhealthy"' | wc -l)
        DRAINING_COUNT=$(echo $TARGET_HEALTH | grep -o '"State":"draining"' | wc -l)
        
        print_info "  Healthy targets: $HEALTHY_COUNT"
        
        if [ "$UNHEALTHY_COUNT" -gt 0 ]; then
            print_warning "  Unhealthy targets: $UNHEALTHY_COUNT"
        fi
        
        if [ "$DRAINING_COUNT" -gt 0 ]; then
            print_info "  Draining targets: $DRAINING_COUNT"
        fi
        
        if [ "$HEALTHY_COUNT" -eq 0 ]; then
            print_error "No healthy targets!"
            print_info "  Target health details:"
            echo $TARGET_HEALTH | grep -o '"Reason":"[^"]*"' | while read reason; do
                print_info "    $reason"
            done
        fi
    fi
else
    print_warning "Could not find target group"
fi

# Test 7: HTTP Health Check
print_section "7. HTTP Health Check"

if [ -n "$ALB_URL" ]; then
    # Remove trailing slash
    ALB_URL=${ALB_URL%/}
    
    print_info "Testing: $ALB_URL/health"
    
    # Test with timeout
    HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" --connect-timeout 10 --max-time 30 "$ALB_URL/health" 2>/dev/null)
    HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -n1)
    HTTP_BODY=$(echo "$HTTP_RESPONSE" | head -n-1)
    
    if [ "$HTTP_CODE" == "200" ]; then
        print_success "Health check passed (HTTP $HTTP_CODE)"
        print_info "  Response: $HTTP_BODY"
    elif [ -z "$HTTP_CODE" ]; then
        print_error "Could not connect to ALB (connection timeout)"
    else
        print_error "Health check failed (HTTP $HTTP_CODE)"
        print_info "  Response: $HTTP_BODY"
    fi
    
    # Test root endpoint
    print_info "Testing: $ALB_URL/"
    ROOT_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$ALB_URL/" 2>/dev/null)
    
    if [ -n "$ROOT_CODE" ]; then
        print_info "  Root endpoint HTTP code: $ROOT_CODE"
    fi
else
    print_warning "ALB URL not provided, skipping HTTP tests"
fi

# Test 8: Check CloudWatch Logs
print_section "8. CloudWatch Logs"

LOG_GROUP="/ecs/bad-apples-backend-task"

if aws logs describe-log-groups --log-group-name-prefix $LOG_GROUP --region $AWS_REGION > /dev/null 2>&1; then
    print_success "CloudWatch log group exists: $LOG_GROUP"
    
    # Get recent log streams
    STREAM_COUNT=$(aws logs describe-log-streams --log-group-name $LOG_GROUP --region $AWS_REGION \
        --order-by LastEventTime --descending --max-items 5 \
        --query 'length(logStreams)' --output text 2>/dev/null)
    
    print_info "  Recent log streams: $STREAM_COUNT"
    
    # Check for recent errors
    print_info "  Checking for recent errors..."
    ERROR_COUNT=$(aws logs filter-log-events --log-group-name $LOG_GROUP --region $AWS_REGION \
        --start-time $(($(date +%s) - 3600))000 \
        --filter-pattern "ERROR" --max-items 10 \
        --query 'length(events)' --output text 2>/dev/null || echo "0")
    
    if [ "$ERROR_COUNT" -gt 0 ]; then
        print_warning "Found $ERROR_COUNT error(s) in last hour"
        print_info "View logs: aws logs tail $LOG_GROUP --follow"
    else
        print_success "No errors found in last hour"
    fi
else
    print_error "CloudWatch log group not found: $LOG_GROUP"
fi

# Test 9: Check Auto-scaling
print_section "9. Auto-scaling Configuration"

SCALING_TARGET=$(aws application-autoscaling describe-scalable-targets \
    --service-namespace ecs \
    --resource-ids "service/$ECS_CLUSTER/$ECS_SERVICE" \
    --region $AWS_REGION 2>/dev/null)

if [ $? -eq 0 ]; then
    MIN_CAPACITY=$(echo $SCALING_TARGET | grep -o '"MinCapacity":[0-9]*' | cut -d':' -f2)
    MAX_CAPACITY=$(echo $SCALING_TARGET | grep -o '"MaxCapacity":[0-9]*' | cut -d':' -f2)
    
    if [ -n "$MIN_CAPACITY" ] && [ -n "$MAX_CAPACITY" ]; then
        print_success "Auto-scaling configured"
        print_info "  Min capacity: $MIN_CAPACITY"
        print_info "  Max capacity: $MAX_CAPACITY"
    fi
    
    # Check scaling policies
    POLICY_COUNT=$(aws application-autoscaling describe-scaling-policies \
        --service-namespace ecs \
        --resource-id "service/$ECS_CLUSTER/$ECS_SERVICE" \
        --region $AWS_REGION \
        --query 'length(ScalingPolicies)' --output text 2>/dev/null)
    
    print_info "  Scaling policies: $POLICY_COUNT"
else
    print_warning "Auto-scaling not configured"
fi

# Summary
print_section "Verification Summary"

echo ""
echo -e "${GREEN}Passed:   $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed:   $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    print_success "All checks passed! Deployment is healthy. ✅"
    exit 0
elif [ $FAILED -eq 0 ]; then
    print_warning "Deployment is working but has some warnings. ⚠️"
    exit 0
else
    print_error "Deployment has failures that need attention. ❌"
    echo ""
    print_info "Troubleshooting steps:"
    print_info "  1. Check logs: aws logs tail $LOG_GROUP --follow"
    print_info "  2. Check service events: aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE"
    print_info "  3. Check task details: aws ecs describe-tasks --cluster $ECS_CLUSTER --tasks <task-id>"
    print_info "  4. Review deployment guide: docs/DEPLOYMENT.md"
    exit 1
fi

