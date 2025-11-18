# Backend Deployment Documentation

Complete documentation for deploying the backend application to AWS ECS Fargate.

## 📁 Documentation Files

### Quick Start
- **[QUICKSTART.md](./QUICKSTART.md)** - Deploy in 15 minutes (start here!)

### Detailed Guides
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete deployment guide with troubleshooting
- **[CD-APPROACHES.md](./CD-APPROACHES.md)** - Comparison of deployment approaches and why we chose Fargate

### Scripts
- **[test-deployment.sh](./test-deployment.sh)** - Test Docker image locally before deploying
- **[verify-deployment.sh](./verify-deployment.sh)** - Verify live deployment health

## 🚀 Quick Deploy

```bash
# 1. Deploy infrastructure
cd terraform
terraform init
terraform apply

# 2. Configure GitHub Secrets
# AWS_ACCESS_KEY_ID: [from terraform output]
# AWS_SECRET_ACCESS_KEY: [from terraform output]
# AWS_REGION: us-east-1

# 3. Push to main branch
git push origin main

# 4. Verify deployment
bash ../docs/verify-deployment.sh
```

## 🏗️ What Gets Deployed

### Infrastructure
- **AWS ECR** - Docker container registry
- **ECS Cluster** - Fargate cluster for running containers
- **ECS Service** - Manages 1-4 tasks with auto-scaling
- **Application Load Balancer** - Distributes traffic with health checks
- **VPC** - Private/public subnets, NAT gateways, security groups
- **CloudWatch** - Logs and metrics
- **IAM** - Roles and policies for security

### Features
- ✅ **Auto-scaling** - 1-4 tasks based on CPU (70%) and memory (80%)
- ✅ **Zero-downtime** - Rolling deployments with health checks
- ✅ **Auto-rollback** - Circuit breaker reverts failed deployments
- ✅ **Load balancing** - ALB distributes traffic across tasks
- ✅ **Monitoring** - CloudWatch logs and Container Insights
- ✅ **Security** - Private subnets, security groups, IAM roles

### GitHub Actions CI/CD
- Automatic deployment on push to `main`
- Builds Docker image
- Pushes to ECR
- Updates ECS service
- Waits for healthy deployment

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Actions                         │
│  (Build Docker → Push to ECR → Deploy to ECS)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │      Amazon ECR               │
         │  (Container Registry)         │
         └───────────────┬───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │      ECS Cluster              │
         │  ┌─────────────────────────┐  │
         │  │ ECS Service             │  │
         │  │ - Auto-scaling (1-4)    │  │
         │  │ - Health checks         │  │
         │  │ - Rolling updates       │  │
         │  └─────────────────────────┘  │
         └───────────────┬───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │  Application Load Balancer    │
         │  - HTTP/HTTPS                 │
         │  - Health checks              │
         │  - SSL termination            │
         └───────────────┬───────────────┘
                         │
                         ▼
                   ┌──────────┐
                   │ Internet │
                   └──────────┘
```

## 💰 Cost Estimate

### Minimal Usage (1 task)
- Fargate: $14.40/month
- ALB: $16.20/month
- NAT Gateway: $64.80/month
- Other: $2/month
- **Total**: ~$97/month

### High Usage (4 tasks)
- Fargate: $57.60/month
- ALB: $25/month
- NAT Gateway: $64.80/month
- Other: $5/month
- **Total**: ~$150-200/month

## 🎯 Use Cases

### ✅ This Deployment Is Perfect For:
- Production web APIs
- Variable traffic patterns
- Need for auto-scaling
- Zero-downtime requirements
- Video processing workloads
- FastAPI + Uvicorn applications

### ⚠️ Consider Alternatives For:
- **Very low traffic** → AWS Lambda (cheaper)
- **Consistent high traffic** → ECS on EC2 (cost-effective)
- **Maximum simplicity** → AWS App Runner
- **Learning/MVP** → Single EC2 with Docker

See [CD-APPROACHES.md](./CD-APPROACHES.md) for detailed comparison.

## 📝 Files Created

### GitHub Actions
```
.github/workflows/
└── deploy-backend.yml          # CI/CD pipeline
```

### Terraform Infrastructure
```
terraform/
├── ecs.tf                      # ECS Fargate resources
├── ecs_variables.tf            # Configuration variables
├── ecs_outputs.tf              # Deployment outputs
├── terraform.tfvars.ecs.example # Configuration template
└── main.tf                     # Updated with IAM for GitHub Actions
```

### Documentation
```
docs/
├── README.md                   # This file
├── QUICKSTART.md               # 15-minute deployment guide
├── DEPLOYMENT.md               # Complete deployment guide
├── CD-APPROACHES.md            # Deployment options comparison
├── test-deployment.sh          # Local testing script
└── verify-deployment.sh        # Deployment verification script
```

## 🔧 Configuration

### Customize Deployment

Edit `terraform/terraform.tfvars`:

```hcl
# Basic configuration
aws_region = "us-east-1"
environment = "prod"
bucket_name = "your-unique-bucket-name"

# Resource sizing
ecs_task_cpu = 1024      # 1 vCPU
ecs_task_memory = 2048   # 2 GB RAM

# Auto-scaling
ecs_min_capacity = 1
ecs_max_capacity = 4
autoscaling_target_cpu = 70
```

See `terraform/terraform.tfvars.ecs.example` for all options.

## 🐛 Troubleshooting

### Quick Checks

```bash
# Run verification script
bash docs/verify-deployment.sh

# Check logs
aws logs tail /ecs/bad-apples-backend-task --follow

# Check service status
aws ecs describe-services \
  --cluster bad-apples-cluster \
  --services bad-apples-backend-service
```

### Common Issues

1. **Health checks failing**
   - Verify `/health` endpoint exists in your app
   - Check container logs for errors
   - Ensure port 8000 is exposed

2. **Deployment timeout**
   - Check ECS service events
   - Verify security groups allow ALB → ECS traffic
   - Review CloudWatch logs for app errors

3. **High costs**
   - Reduce task size (512 CPU / 1024 MB)
   - Lower max_capacity
   - Reduce log retention period

See [DEPLOYMENT.md](./DEPLOYMENT.md#troubleshooting) for detailed troubleshooting.

## 🔄 Update Application

### Automatic (Recommended)
```bash
git add .
git commit -m "Update feature"
git push origin main
```

GitHub Actions automatically deploys with zero downtime.

### Manual
```bash
# Build and push image
bash docs/test-deployment.sh

# Force new deployment
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

## 📈 Monitoring

### CloudWatch Logs
```bash
# Tail logs
aws logs tail /ecs/bad-apples-backend-task --follow

# Search logs
aws logs filter-log-events \
  --log-group-name /ecs/bad-apples-backend-task \
  --filter-pattern "ERROR"
```

### Metrics to Watch
- **CPUUtilization** - Should stay below 70%
- **MemoryUtilization** - Should stay below 80%
- **TargetResponseTime** - Request latency
- **HealthyHostCount** - Number of healthy tasks
- **RequestCount** - Total requests

### AWS Console
- [ECS Console](https://console.aws.amazon.com/ecs/) - Service status
- [CloudWatch Console](https://console.aws.amazon.com/cloudwatch/) - Logs and metrics
- [Load Balancer Console](https://console.aws.amazon.com/ec2/v2/home#LoadBalancers) - ALB health

## 🔐 Security

### Best Practices Implemented
- ✅ Private subnets for ECS tasks
- ✅ Security groups with least privilege
- ✅ IAM roles with specific permissions
- ✅ No hardcoded credentials
- ✅ Encrypted container images
- ✅ VPC isolation

### Recommendations
- Move API keys to AWS Secrets Manager (production)
- Enable HTTPS with ACM certificate
- Set up AWS WAF for DDoS protection
- Enable VPC Flow Logs
- Implement AWS GuardDuty

## 🚀 Next Steps

### Production Readiness
1. **Custom Domain** - Set up Route53 + ACM certificate
2. **HTTPS** - Enable ALB HTTPS listener
3. **Secrets Management** - Move to AWS Secrets Manager
4. **Monitoring** - Set up CloudWatch alarms
5. **Backups** - Configure database backups

### Scale Up
1. Increase task size (2 vCPU / 4 GB)
2. Increase max capacity (8+ tasks)
3. Add Redis for caching
4. Add RDS for database
5. Add CloudFront CDN

### CI/CD Enhancements
1. Add staging environment
2. Add manual approval for prod
3. Add automated tests
4. Add canary deployments
5. Add rollback automation

## 📚 Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [GitHub Actions Documentation](https://docs.github.com/actions)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)

## 🆘 Support

### Documentation Order
1. Start with [QUICKSTART.md](./QUICKSTART.md) - Fast deployment
2. Read [DEPLOYMENT.md](./DEPLOYMENT.md) - Detailed guide
3. Check [CD-APPROACHES.md](./CD-APPROACHES.md) - Understand alternatives
4. Run [verify-deployment.sh](./verify-deployment.sh) - Check health

### Getting Help
- Check CloudWatch logs first
- Review ECS service events
- Run verification script
- Check troubleshooting section in DEPLOYMENT.md

---

**Ready to deploy?** → [QUICKSTART.md](./QUICKSTART.md)

**Need details?** → [DEPLOYMENT.md](./DEPLOYMENT.md)

**Want alternatives?** → [CD-APPROACHES.md](./CD-APPROACHES.md)

---

**Last Updated**: November 2024  
**Deployment Type**: AWS ECS Fargate with GitHub Actions  
**Estimated Cost**: $97-200/month  
**Setup Time**: 15-30 minutes

