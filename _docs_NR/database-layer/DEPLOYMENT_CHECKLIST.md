# MV Database Layer Deployment Checklist

## Pre-Deployment

### 1. AWS Configuration
- [ ] Terraform S3 bucket created and configured
- [ ] IAM user created with S3 access policy
- [ ] Access keys generated and stored securely
- [ ] DynamoDB table created manually in AWS Console
  - Table name: `MVProjects`
  - Partition key: `PK` (String)
  - Sort key: `SK` (String)
  - GSI: `status-created-index` (GSI1PK: status, GSI1SK: createdAt)
  - Provisioned capacity or On-Demand pricing configured

### 2. Environment Variables
- [ ] `.env` file configured with production values
- [ ] `AWS_ACCESS_KEY_ID` set
- [ ] `AWS_SECRET_ACCESS_KEY` set
- [ ] `AWS_REGION` set
- [ ] `STORAGE_BUCKET` set to actual bucket name
- [ ] `DYNAMODB_TABLE_NAME` set to production table
- [ ] `USE_LOCAL_DYNAMODB=false` for production
- [ ] `DYNAMODB_ENDPOINT` removed or empty (uses AWS)

### 3. Dependencies
- [ ] All Python dependencies installed: `pip install -r requirements.txt`
- [ ] PynamoDB version verified: `>= 6.0.0`
- [ ] boto3 version verified: `>= 1.34.0`
- [ ] moviepy installed for video composition

## Deployment Steps

### 1. Backend Deployment
- [ ] Deploy backend to AWS EC2/ECS/Lambda
- [ ] Configure environment variables in deployment platform
- [ ] Verify DynamoDB connectivity: `python -c "from mv_models import MVProjectItem; print(MVProjectItem.exists())"`
- [ ] Verify S3 connectivity: `python -c "from services.s3_storage import get_s3_storage_service; s3 = get_s3_storage_service(); print(s3.bucket_name)"`

### 2. Worker Deployment
- [ ] Deploy worker process separately (or as background task)
- [ ] Configure Redis connection
- [ ] Verify worker can access DynamoDB and S3
- [ ] Start worker: `python worker_mv.py`

### 3. Frontend Deployment
- [ ] Update `NEXT_PUBLIC_API_URL` to production backend URL
- [ ] Deploy to Vercel
- [ ] Test file upload flow

## Post-Deployment Verification

### 1. API Endpoints
- [ ] `POST /api/mv/projects` - Create project
- [ ] `GET /api/mv/projects/{id}` - Get project
- [ ] `PATCH /api/mv/projects/{id}` - Update project
- [ ] `POST /api/mv/projects/{id}/compose` - Queue composition
- [ ] `GET /api/mv/projects/{id}/final-video` - Get final video URL

### 2. End-to-End Test
- [ ] Create project via frontend
- [ ] Verify files uploaded to S3
- [ ] Verify project created in DynamoDB
- [ ] Generate scenes (manual or queued)
- [ ] Verify scenes created in DynamoDB
- [ ] Generate videos for scenes (manual or queued)
- [ ] Compose final video
- [ ] Download final video via presigned URL

### 3. Monitoring
- [ ] CloudWatch metrics configured for DynamoDB
- [ ] S3 bucket size monitoring enabled
- [ ] Application logs configured (CloudWatch Logs)
- [ ] Error alerts configured

## Rollback Plan

If deployment fails:
- [ ] Revert to previous backend version
- [ ] DynamoDB data persists (no migration needed)
- [ ] S3 files remain accessible
- [ ] No data loss

## Production Optimization

### DynamoDB
- [ ] Enable auto-scaling for read/write capacity
- [ ] Configure TTL for old projects (optional)
- [ ] Enable point-in-time recovery (PITR)
- [ ] Set up DynamoDB Streams for audit logging (optional)

### S3
- [ ] Configure lifecycle policies for old videos
- [ ] Enable versioning (already configured via Terraform)
- [ ] Configure CloudFront CDN for video delivery (optional)

### Caching
- [ ] Implement presigned URL caching (optional)
- [ ] Cache project metadata in Redis (optional)

## Local Development Setup

### 1. Start Services
```bash
docker-compose up -d dynamodb-local redis
```

### 2. Initialize DynamoDB
```bash
cd backend
python init_dynamodb.py
```

### 3. Start Backend
```bash
uvicorn main:app --reload
```

### 4. Start Worker (separate terminal)
```bash
cd backend
python worker_mv.py
```

### 5. Verify Setup
```bash
# Test API endpoints
python test_mv_endpoints.py

# Check DynamoDB
python check_database.py dynamodb --list
```

## Environment Variable Reference

### Required for Local Development
```bash
USE_LOCAL_DYNAMODB=true
DYNAMODB_ENDPOINT=http://localhost:8001
DYNAMODB_REGION=us-east-1
DYNAMODB_TABLE_NAME=MVProjects
REDIS_URL=redis://localhost:6379/0
```

### Required for Production
```bash
USE_LOCAL_DYNAMODB=false
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key>
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=MVProjects
STORAGE_BUCKET=<your-s3-bucket>
REDIS_URL=<your-redis-url>
```

## Troubleshooting

### DynamoDB Connection Issues
- Verify `DYNAMODB_ENDPOINT` is correct for local development
- Verify `USE_LOCAL_DYNAMODB=true` for local, `false` for production
- Check DynamoDB Local is running: `curl http://localhost:8001`

### S3 Connection Issues
- Verify AWS credentials are set correctly
- Verify `STORAGE_BUCKET` matches actual bucket name
- Check IAM permissions for S3 access

### Worker Not Processing Jobs
- Verify Redis connection: `redis-cli ping`
- Check worker logs for errors
- Verify queues exist: `redis-cli KEYS "*queue*"`

