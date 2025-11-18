# Continuous Deployment Approaches for AWS

This document explains the different CD (Continuous Deployment) approaches for deploying your backend application on AWS.

## Implemented Solution: AWS ECS Fargate ⭐

We've implemented **AWS ECS Fargate** with GitHub Actions for fully automated deployments.

### Why ECS Fargate?

✅ **Serverless** - No server management  
✅ **Auto-scaling** - Scales from 1-4 tasks based on CPU/memory  
✅ **Zero-downtime deployments** - Rolling updates with health checks  
✅ **Cost-effective** - Pay only for running tasks (~$97/month)  
✅ **Production-ready** - Load balancer, monitoring, logging included  

### What Was Implemented

#### 1. GitHub Actions CI/CD Pipeline
- **File**: `.github/workflows/deploy-backend.yml`
- **Triggers**: Automatic on push to `main` branch
- **Process**:
  1. Builds Docker image from `backend/Dockerfile`
  2. Pushes to AWS ECR (container registry)
  3. Updates ECS service with new image
  4. Waits for deployment to complete

#### 2. AWS Infrastructure (Terraform)
- **ECR Repository** - Stores Docker images
- **ECS Cluster** - Runs containers
- **ECS Service** - Manages task lifecycle
- **Application Load Balancer** - Distributes traffic
- **Auto-scaling** - Scales 1-4 tasks based on load
- **VPC & Networking** - Private/public subnets, NAT gateways
- **IAM Roles** - Security and permissions
- **CloudWatch Logs** - Application logging

#### 3. Features
- **1 vCPU / 2 GB RAM** per task (optimal for Python FastAPI + Uvicorn)
- **Auto-scaling** on 70% CPU or 80% memory
- **Health checks** on `/health` endpoint
- **Rolling deployments** with circuit breaker (auto-rollback on failure)
- **Zero-downtime** deployments (200% max, 100% min healthy)
- **Logs retained** for 7 days in CloudWatch

### Deployment Flow

```
Developer Push → GitHub Actions → Build Docker → Push to ECR
                                         ↓
                      Update ECS Task Definition
                                         ↓
                      Deploy New Tasks → Health Check
                                         ↓
                      Remove Old Tasks (zero-downtime)
```

### Cost Breakdown

**Monthly costs (us-east-1)**:
- Fargate (1 task): ~$14.40
- ALB: ~$16.20
- NAT Gateway (2 AZs): ~$64.80
- CloudWatch Logs: ~$0.50
- ECR Storage: ~$0.50
- **Total**: ~$97/month

Scales to ~$150-200/month under heavy load (4 tasks).

---

## Alternative CD Approaches (Not Implemented)

Here are other deployment approaches you could consider:

### 2. AWS App Runner

**Simplest option - fully managed container service**

#### Pros
- ✅ Easiest to set up (minimal configuration)
- ✅ Automatic HTTPS and custom domains
- ✅ Built-in auto-scaling
- ✅ Direct from ECR or GitHub
- ✅ No load balancer needed

#### Cons
- ❌ Less control over infrastructure
- ❌ Limited networking options (no VPC customization)
- ❌ More expensive for consistent workloads
- ❌ Less suitable for complex microservices

#### When to Use
- Small to medium APIs
- Want simplest deployment
- Don't need VPC customization
- Unpredictable traffic patterns

#### Cost
~$60-100/month for similar specs

#### Implementation
Would require:
- App Runner service configuration
- IAM role for ECR access
- GitHub Actions to push to ECR
- App Runner auto-deploys on new images

---

### 3. AWS ECS on EC2

**More control, cost-effective for consistent workloads**

#### Pros
- ✅ More control over instances
- ✅ Cost-effective for steady traffic
- ✅ Can use spot instances (70% discount)
- ✅ Better for GPU/special hardware needs

#### Cons
- ❌ Manage EC2 instances (patching, scaling)
- ❌ More complex auto-scaling setup
- ❌ Capacity planning required
- ❌ Instance failures affect containers

#### When to Use
- Consistent high traffic
- Need specific instance types
- Want to optimize costs
- Have DevOps expertise

#### Cost
~$30-50/month (t3.small) + ALB costs

#### Implementation
Would require:
- EC2 instances with ECS agent
- Auto-scaling groups for instances
- Container-level auto-scaling
- More complex Terraform configuration

---

### 4. AWS Lambda + API Gateway

**Serverless functions (alternative architecture)**

#### Pros
- ✅ Pay per request (ultra cost-effective)
- ✅ Infinite auto-scaling
- ✅ No server management
- ✅ Best for sporadic traffic

#### Cons
- ❌ 15-minute execution limit
- ❌ Cold start latency (3-5 seconds)
- ❌ Requires refactoring FastAPI app
- ❌ Limited to 10GB RAM
- ❌ Not suitable for long-running video processing

#### When to Use
- Sporadic traffic patterns
- Simple API endpoints
- Short execution times (<15 min)
- Very low traffic (cost optimization)

#### Cost
~$0-10/month for low traffic

#### Implementation
Would require:
- Refactor FastAPI to Lambda handlers
- API Gateway configuration
- Lambda layers for dependencies
- S3 for video processing results

---

### 5. Direct EC2 with Docker Compose

**Simplest for MVPs, single instance**

#### Pros
- ✅ Very simple to understand
- ✅ Lowest cost for single instance
- ✅ Full SSH access for debugging
- ✅ Quick to set up

#### Cons
- ❌ No auto-scaling
- ❌ Manual deployments
- ❌ Single point of failure
- ❌ Manual SSL/HTTPS setup
- ❌ Not production-ready

#### When to Use
- MVP/proof of concept
- Very low budget
- Learning/development
- Single user or low traffic

#### Cost
~$10-30/month (t3.micro to t3.small)

#### Implementation
Would require:
- Single EC2 instance
- Docker Compose file
- GitHub Actions SSH deployment
- Nginx for reverse proxy
- Manual setup of SSL certificates

---

### 6. AWS Elastic Beanstalk

**Platform-as-a-Service (middle ground)**

#### Pros
- ✅ Manages infrastructure automatically
- ✅ Auto-scaling included
- ✅ Multiple environments (dev/staging/prod)
- ✅ Rolling deployments built-in

#### Cons
- ❌ Abstraction can be limiting
- ❌ More expensive than ECS
- ❌ Less flexibility
- ❌ Harder to debug issues

#### When to Use
- Want managed platform
- Multiple environments needed
- Standard web application
- Team prefers simplicity over control

#### Cost
~$80-150/month

#### Implementation
Would require:
- Elastic Beanstalk application
- Environment configuration
- GitHub Actions deployment
- Less Terraform needed (EB manages infra)

---

## Comparison Matrix

| Approach | Cost/Month | Complexity | Auto-Scale | Production Ready | Setup Time |
|----------|------------|------------|------------|------------------|------------|
| **ECS Fargate** ⭐ | $97-200 | Medium | Yes | ✅ Yes | 30 min |
| App Runner | $60-100 | Low | Yes | ✅ Yes | 15 min |
| ECS on EC2 | $30-100 | High | Yes | ✅ Yes | 60 min |
| Lambda | $0-10 | Medium | Yes | ⚠️ Limited | 45 min |
| EC2 + Docker | $10-30 | Low | No | ❌ No | 20 min |
| Elastic Beanstalk | $80-150 | Low | Yes | ✅ Yes | 30 min |

---

## Why We Chose ECS Fargate

Given your requirements:
1. ✅ Production deployment
2. ✅ Auto-scaling needed (video processing can spike)
3. ✅ Zero-downtime deployments
4. ✅ Cost-effective for variable workloads
5. ✅ Uvicorn + FastAPI (runs well in containers)

**ECS Fargate** provides the best balance of:
- Production-readiness
- Auto-scaling capability
- Cost optimization
- Operational simplicity
- Full control when needed

---

## Migration Paths

### From Fargate to Other Services

If you need to migrate later:

**To App Runner** (simpler):
```bash
# Already using ECR, just point App Runner to it
# Minimal changes needed
```

**To ECS on EC2** (cost optimization):
```bash
# Reuse existing ECS task definitions
# Add EC2 launch configuration
# Update service to use EC2 launch type
```

**To Lambda** (extreme cost optimization):
```bash
# Refactor application code
# Use AWS Lambda Web Adapter
# Still use ECR for container images
```

---

## Getting Started

Your deployment is already set up! Here's what to do:

1. **Deploy Infrastructure**: `cd terraform && terraform apply`
2. **Configure GitHub Secrets**: Add AWS credentials
3. **Push to Main**: Application deploys automatically
4. **Monitor**: Check CloudWatch logs and metrics

See [QUICKSTART.md](./QUICKSTART.md) for step-by-step guide.

---

## Questions?

- **Cost too high?** Reduce task size or min capacity
- **Need more performance?** Increase task CPU/memory
- **Want simpler?** Consider App Runner (requires migration)
- **Need GPU?** Consider ECS on EC2 with GPU instances
- **Very low traffic?** Consider Lambda (requires refactoring)

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed documentation.

