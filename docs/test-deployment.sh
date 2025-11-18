#!/bin/bash

# Test Deployment Script for AWS ECS Fargate
# This script helps test the Docker image locally before deploying to ECS

set -e

echo "=================================="
echo "ECS Fargate Deployment Test Script"
echo "=================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running from project root
if [ ! -d "backend" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Check required tools
print_info "Checking required tools..."

command -v docker >/dev/null 2>&1 || {
    print_error "Docker is not installed. Please install Docker first."
    exit 1
}

command -v aws >/dev/null 2>&1 || {
    print_error "AWS CLI is not installed. Please install AWS CLI first."
    exit 1
}

command -v tofu >/dev/null 2>&1 || {
    print_warning "OpenTofu is not installed. Some features may not work."
}

print_info "✓ All required tools are installed"
echo ""

# Get configuration from OpenTofu outputs
print_info "Getting deployment configuration..."

cd terraform 2>/dev/null || {
    print_error "terraform directory not found"
    exit 1
}

# Check if OpenTofu state exists (we're already in terraform/ directory)
if [ ! -f "terraform.tfstate" ]; then
    print_warning "OpenTofu state not found. Using default values."
    ECR_REPO="bad-apples-backend"
    AWS_REGION="us-east-1"
else
    ECR_REPO=$(tofu output -raw ecr_repository_url 2>/dev/null || echo "")
    AWS_REGION=$(tofu output -raw aws_region 2>/dev/null || echo "us-east-1")
    
    if [ -z "$ECR_REPO" ]; then
        print_warning "Could not get ECR repository URL from OpenTofu. Using default."
        ECR_REPO="bad-apples-backend"
    fi
fi

cd ..

print_info "AWS Region: $AWS_REGION"
print_info "ECR Repository: $ECR_REPO"
echo ""

# Test 1: Build Docker image locally
print_info "Test 1: Building Docker image locally..."

cd backend

# Build Docker image - try ARM64 first (for Graviton), fallback to native
print_info "Building Docker image..."

# Check if buildx is available
if docker buildx version >/dev/null 2>&1; then
    print_info "Attempting ARM64 build (for AWS Graviton compatibility)..."
    if docker buildx build --platform linux/arm64 -t bad-apples-backend:test --load . 2>/dev/null; then
        print_info "✓ Docker image built successfully (ARM64)"
        BUILD_SUCCESS=true
    else
        print_warning "ARM64 build not available, using native architecture..."
        BUILD_SUCCESS=false
    fi
else
    print_warning "Docker buildx not available, using standard build..."
    BUILD_SUCCESS=false
fi

# Fallback to native build if ARM64 failed
if [ "$BUILD_SUCCESS" != "true" ]; then
    print_info "Building for native architecture..."
    if docker build -t bad-apples-backend:test .; then
        print_info "✓ Docker image built successfully (native x86/AMD64)"
    else
        print_error "✗ Docker build failed"
        exit 1
    fi
fi

cd ..
echo ""

# Test 2: Run container locally
print_info "Test 2: Running container locally..."

# Stop any existing test container
docker stop bad-apples-backend-test 2>/dev/null || true
docker rm bad-apples-backend-test 2>/dev/null || true

# Run container
if docker run -d \
    --name bad-apples-backend-test \
    -p 8000:8000 \
    -e ENVIRONMENT=test \
    -e PORT=8000 \
    bad-apples-backend:test; then
    print_info "✓ Container started successfully"
else
    print_error "✗ Failed to start container"
    exit 1
fi

# Wait for container to be ready
print_info "Waiting for container to be ready..."
sleep 5

# Test 3: Check health endpoint
print_info "Test 3: Testing health endpoint..."

for i in {1..10}; do
    if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        print_info "✓ Health check passed"
        HEALTH_CHECK_PASSED=true
        break
    else
        if [ $i -eq 10 ]; then
            print_error "✗ Health check failed after 10 attempts"
            print_info "Container logs:"
            docker logs bad-apples-backend-test
            docker stop bad-apples-backend-test
            docker rm bad-apples-backend-test
            exit 1
        fi
        print_warning "Health check attempt $i failed, retrying..."
        sleep 2
    fi
done

# Get health response
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
print_info "Health response: $HEALTH_RESPONSE"
echo ""

# Test 4: Check container logs
print_info "Test 4: Checking container logs for errors..."

if docker logs bad-apples-backend-test 2>&1 | grep -i "error" > /dev/null; then
    print_warning "Found errors in container logs:"
    docker logs bad-apples-backend-test 2>&1 | grep -i "error"
else
    print_info "✓ No errors found in logs"
fi
echo ""

# Test 5: Test API endpoints (if available)
print_info "Test 5: Testing API endpoints..."

# Test root endpoint
if curl -f -s http://localhost:8000/ > /dev/null 2>&1; then
    print_info "✓ Root endpoint accessible"
else
    print_warning "Root endpoint not accessible (this may be normal)"
fi

# Test docs endpoint
if curl -f -s http://localhost:8000/docs > /dev/null 2>&1; then
    print_info "✓ API docs endpoint accessible at http://localhost:8000/docs"
else
    print_warning "API docs endpoint not accessible"
fi

echo ""

# Cleanup local test
print_info "Cleaning up local test container..."
docker stop bad-apples-backend-test
docker rm bad-apples-backend-test
print_info "✓ Cleanup complete"
echo ""

# Optional: Push to ECR
read -p "Do you want to push this image to ECR? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Logging in to ECR..."
    
    # Check if ECR_REPO contains full URL or just repository name
    if [[ $ECR_REPO == *".dkr.ecr."* ]]; then
        # Full URL provided
        ECR_URL=$ECR_REPO
    else
        # Just repository name, need to construct URL
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
    fi
    
    if aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL; then
        print_info "✓ Logged in to ECR"
    else
        print_error "✗ Failed to login to ECR"
        exit 1
    fi
    
    print_info "Tagging image for ECR..."
    docker tag bad-apples-backend:test $ECR_URL:latest
    docker tag bad-apples-backend:test $ECR_URL:manual-$(date +%Y%m%d-%H%M%S)
    
    print_info "Pushing image to ECR..."
    if docker push $ECR_URL:latest && docker push $ECR_URL:manual-$(date +%Y%m%d-%H%M%S); then
        print_info "✓ Image pushed to ECR successfully"
        
        print_info ""
        print_info "To deploy this image to ECS, run:"
        print_info "  aws ecs update-service --cluster bad-apples-cluster --service bad-apples-backend-service --force-new-deployment"
    else
        print_error "✗ Failed to push image to ECR"
        exit 1
    fi
fi

echo ""
print_info "=================================="
print_info "All tests completed successfully!"
print_info "=================================="
echo ""
print_info "Next steps:"
print_info "  1. Push code to GitHub main branch for automatic deployment"
print_info "  2. Or run: aws ecs update-service --cluster bad-apples-cluster --service bad-apples-backend-service --force-new-deployment"
print_info "  3. Monitor deployment: aws ecs describe-services --cluster bad-apples-cluster --services bad-apples-backend-service"
echo ""

