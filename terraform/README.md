# Terraform Configuration for AI Video Generator S3 Storage

This Terraform configuration creates all the AWS infrastructure needed for the cloud storage persistence feature.

## What This Creates

✅ **S3 Bucket** with:
- Versioning enabled
- Server-side encryption (AES256)
- CORS configuration for web access
- Lifecycle policies for cleanup
- Public access blocked (secure)

✅ **IAM User** with:
- Least privilege access policy
- Permissions for upload/download/delete/copy
- Access keys for application use

✅ **CloudWatch Monitoring** (optional):
- Bucket size alerts
- Usage metrics

## Prerequisites

1. **AWS Account** - You need an AWS account
2. **AWS CLI** - Install from https://aws.amazon.com/cli/
3. **Terraform** - Install from https://www.terraform.io/downloads

### Install Terraform (WSL/Linux)

```bash
# Download and install Terraform
wget https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip
unzip terraform_1.7.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
terraform version
```

### Configure AWS CLI

```bash
# Configure your AWS credentials
aws configure

# You'll be prompted for:
# AWS Access Key ID: (your root/admin account key)
# AWS Secret Access Key: (your secret key)
# Default region: us-east-1
# Default output format: json
```

## Quick Start

### 1. Customize Configuration

```bash
cd terraform

# Copy the example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars  # or vim, code, etc.
```

**Important:** Change `bucket_name` to something unique! S3 bucket names must be globally unique across all AWS accounts.

Suggestions:
- `yourname-video-generator`
- `company-video-gen-dev`
- `mvp1-video-storage-2024`

### 2. Initialize Terraform

```bash
terraform init
```

This downloads the AWS provider plugin.

### 3. Preview Changes

```bash
terraform plan
```

Review what will be created. You should see:
- 1 S3 bucket
- 1 IAM user
- 1 IAM policy
- 1 policy attachment
- 1 access key
- Several bucket configurations

### 4. Create Infrastructure

```bash
terraform apply
```

Type `yes` when prompted.

This takes about 30-60 seconds.

### 5. Get Your Credentials

```bash
# View all outputs (credentials hidden)
terraform output

# Get credentials for .env file
terraform output -raw env_file_config

# Or get individual values
terraform output bucket_name
terraform output access_key_id
terraform output -raw secret_access_key  # Secret key (sensitive)
```

### 6. Update Your .env File

Copy the output and add to `backend/.env`:

```bash
# Get the formatted configuration
terraform output -raw env_file_config > temp_config.txt

# Then copy the contents to backend/.env
cat temp_config.txt
rm temp_config.txt
```

Or manually:

```bash
STORAGE_BACKEND=s3
STORAGE_BUCKET=your-bucket-name-here
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

### 7. Test Connection

```bash
cd ../backend
python test_s3_connection.py
```

You should see: ✅ ALL S3 TESTS PASSED!

## Configuration Options

### Variables

Edit `terraform.tfvars` to customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS region | `us-east-1` |
| `bucket_name` | S3 bucket name (must be unique!) | `video-generator-storage` |
| `environment` | Environment name | `dev` |
| `iam_user_name` | IAM user name | `video-generator-app` |
| `cors_allowed_origins` | CORS origins for web access | `["http://localhost:3000", ...]` |
| `asset_retention_days` | Days before auto-deletion (0=never) | `0` |
| `enable_monitoring` | Enable CloudWatch alarms | `false` |

### Cost Optimization

**Lifecycle Rules:**
- Old versions deleted after 30 days
- Incomplete uploads cleaned after 7 days
- Optional: Auto-delete videos after X days

**To enable auto-deletion:**
```hcl
asset_retention_days = 90  # Delete videos after 90 days
```

## Managing Infrastructure

### View Current State

```bash
terraform show
```

### Update Configuration

1. Edit `terraform.tfvars`
2. Run `terraform plan` to preview changes
3. Run `terraform apply` to apply changes

### Rotate Access Keys

```bash
# Force recreation of access key
terraform taint aws_iam_access_key.video_generator_app
terraform apply
```

**Important:** Update your `.env` file with new keys immediately!

### Destroy Everything

```bash
terraform destroy
```

⚠️ **Warning:** This deletes the bucket and ALL videos! Use with caution.

To keep videos but destroy other resources:
```bash
# Remove the bucket from state (keeps it in AWS)
terraform state rm aws_s3_bucket.video_storage
terraform destroy  # Destroys IAM user/policies but keeps bucket
```

## Security Best Practices

### ✅ Do This:

1. **Store credentials securely**
   - Never commit `.env` file
   - Use AWS Secrets Manager for production
   - Rotate keys regularly

2. **Bucket security**
   - Public access is blocked by default
   - Encryption is enabled
   - Versioning protects against accidental deletion

3. **IAM least privilege**
   - User only has access to this bucket
   - No console access
   - Limited to required operations

### ❌ Don't Do This:

1. Don't commit `terraform.tfstate` (contains secrets!)
2. Don't use root AWS credentials
3. Don't disable encryption
4. Don't make bucket public

## Troubleshooting

### "Bucket name already exists"

S3 bucket names are globally unique. Change `bucket_name` in `terraform.tfvars`.

### "Access Denied" when running terraform

Your AWS CLI credentials don't have sufficient permissions. You need:
- `s3:*` permissions
- `iam:CreateUser`, `iam:CreatePolicy`, `iam:AttachUserPolicy`

### "Invalid credentials" in test

1. Check credentials with: `terraform output -raw secret_access_key`
2. Verify they match your `.env` file
3. Ensure no extra spaces or quotes

### Terraform state locked

```bash
# Force unlock (use with caution)
terraform force-unlock <lock-id>
```

## Cost Estimate

**Storage:**
- First 50 TB: $0.023/GB/month
- Example: 100GB = ~$2.30/month

**Requests:**
- PUT/COPY: $0.005 per 1,000 requests
- GET: $0.0004 per 1,000 requests

**Data Transfer:**
- IN: Free
- OUT: First 100GB/month free, then $0.09/GB

**Typical Cost:** $5-20/month for moderate usage

## Production Deployment

For production, consider:

1. **Enable Monitoring:**
   ```hcl
   enable_monitoring = true
   ```

2. **Set up State Backend:**
   ```hcl
   # In main.tf
   terraform {
     backend "s3" {
       bucket = "your-terraform-state-bucket"
       key    = "video-generator/terraform.tfstate"
       region = "us-east-1"
     }
   }
   ```

3. **Use AWS Secrets Manager:**
   - Store access keys in Secrets Manager
   - Reference from application instead of .env

4. **Enable CloudTrail:**
   - Audit all S3 access
   - Track who accessed what

5. **Set up Backups:**
   - Enable S3 Cross-Region Replication
   - Use AWS Backup for additional protection

## Support

If you encounter issues:

1. Check Terraform logs: `TF_LOG=DEBUG terraform apply`
2. Validate AWS permissions: `aws sts get-caller-identity`
3. Test S3 access: `aws s3 ls s3://your-bucket-name/`

## Clean Up

To remove all resources:

```bash
# Backup important videos first!
aws s3 sync s3://your-bucket-name/ ./backup/

# Then destroy
terraform destroy
```

---

**Created for:** Gauntlet MVP-1 AI Video Generator  
**Managed by:** Terraform  
**Last Updated:** 2024

