# AWS ECS Fargate Deployment - Quick Start

Fast-track guide to deploy your backend to AWS ECS Fargate in under 15 minutes.

## Prerequisites

- AWS Account with billing enabled
- AWS CLI configured (`aws configure`)
- Terraform installed
- Docker installed (for local testing)
- Git repository with backend code

## Step 1: Deploy Infrastructure (5 minutes)

```bash
cd terraform

# Initialize Terraform
terraform init

# Review what will be created
terraform plan

# Create infrastructure
terraform apply
# Type 'yes' when prompted

# Save the outputs
terraform output > deployment-info.txt
```

## Step 2: Configure GitHub Secrets (2 minutes)

Get your GitHub Actions credentials:

```bash
terraform output github_actions_access_key_id
terraform output -raw github_actions_secret_access_key
```

Add to GitHub repository:
1. Go to: Repository → Settings → Secrets and variables → Actions
2. Add these secrets:
   - `AWS_ACCESS_KEY_ID`: [from output above]
   - `AWS_SECRET_ACCESS_KEY`: [from output above]
   - `AWS_REGION`: `us-east-1` (or your region)

## Step 3: Deploy Application (5-10 minutes)

```bash
# Push to main branch
git checkout main
git add .
git commit -m "Deploy to AWS ECS Fargate"
git push origin main
```

GitHub Actions will automatically build and deploy.

## Step 4: Verify Deployment (2 minutes)

```bash
# Get your application URL
cd terraform
export APP_URL=$(terraform output -raw alb_url)

# Test health endpoint
curl $APP_URL/health

# Or run verification script
bash ../docs/verify-deployment.sh
```

Expected response: `{"status": "healthy"}`

## That's It! 🎉

Your backend is now running on AWS ECS Fargate with:
- ✅ Auto-scaling (1-4 tasks)
- ✅ Load balancing
- ✅ Zero-downtime deployments
- ✅ CloudWatch logging
- ✅ Automatic CI/CD

## View Your Deployment

```bash
# Application URL
echo $APP_URL

# CloudWatch logs
aws logs tail /ecs/bad-apples-backend-task --follow

# ECS service status
aws ecs describe-services \
  --cluster bad-apples-cluster \
  --services bad-apples-backend-service
```

## Update Your Application

Just push to main:

```bash
git add .
git commit -m "Update feature"
git push origin main
```

GitHub Actions automatically deploys with zero downtime.

## Troubleshooting

If something goes wrong:

```bash
# Run verification script
bash docs/verify-deployment.sh

# Check logs
aws logs tail /ecs/bad-apples-backend-task --since 10m

# Check service status
aws ecs describe-services \
  --cluster bad-apples-cluster \
  --services bad-apples-backend-service
```

## Cost

Estimated monthly cost: **$30-50** for minimal usage
- Fargate: ~$14/month (1 task)
- ALB: ~$16/month
- NAT Gateway: ~$65/month (2 AZs)
- Other: ~$2/month

**Total**: ~$97/month for production-ready setup

## Clean Up

To destroy everything:

```bash
cd terraform
terraform destroy
```

## Next Steps

- [Full Deployment Guide](./DEPLOYMENT.md) - Detailed documentation
- [Test Deployment Script](./test-deployment.sh) - Test locally before deploying
- [Verify Deployment Script](./verify-deployment.sh) - Check deployment health

## Architecture

```
GitHub → ECR → ECS Fargate → ALB → Internet
         ↓      ↓
    CloudWatch  Auto-scaling (1-4 tasks)
```

## Files Created

- `.github/workflows/deploy-backend.yml` - CI/CD pipeline
- `terraform/ecs.tf` - ECS infrastructure
- `terraform/ecs_variables.tf` - Configuration variables
- `terraform/ecs_outputs.tf` - Deployment outputs
- `docs/DEPLOYMENT.md` - Full documentation
- `docs/test-deployment.sh` - Local testing script
- `docs/verify-deployment.sh` - Deployment verification

## Support

For detailed information, see [DEPLOYMENT.md](./DEPLOYMENT.md)

---

**Ready to deploy?** Run `terraform apply` in the terraform directory!

