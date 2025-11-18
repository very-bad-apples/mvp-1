# API Authentication Guide

This guide shows you how to secure your FastAPI endpoints with API key authentication.

---

## 🔐 Authentication Methods

### Option 1: API Key Authentication (Recommended for APIs)
- ✅ Simple to implement
- ✅ Works with any client (browser, mobile, scripts)
- ✅ No redirects (perfect for APIs)
- ✅ Fast and lightweight

### Option 2: JWT Tokens (For user authentication)
- ✅ More secure
- ✅ Supports user sessions
- ✅ Token expiration
- ⚠️ More complex setup

---

## 🚀 Quick Start: API Key Authentication

### Step 1: Set API Key in Secrets Manager

Add `API_KEY` to your secrets:

```bash
# Get current secret
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --query SecretString --output text)

# Add API_KEY
echo "$CURRENT" | jq '.API_KEY = "your-secret-api-key-here"' | \
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string file:///dev/stdin
```

### Step 2: Add API_KEY to ECS Environment

Update `terraform/ecs.tf` to include API_KEY in secrets:

```hcl
secrets = [
  # ... existing secrets ...
  {
    name      = "API_KEY"
    valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:API_KEY::"
  }
]
```

### Step 3: Protect Your Endpoints

In your FastAPI routes:

```python
from auth import verify_api_key

@app.post("/api/generate")
async def generate_video(
    # ... your parameters ...
    api_key: str = Depends(verify_api_key)  # Add this
):
    # Your endpoint logic
    return {"message": "Success"}
```

### Step 4: Test

```bash
# Without API key (will fail)
curl https://your-alb-url/api/generate

# With API key in header
curl -H "X-API-Key: your-secret-api-key-here" \
     https://your-alb-url/api/generate

# With API key in query parameter
curl https://your-alb-url/api/generate?api_key=your-secret-api-key-here
```

---

## 📋 Implementation Examples

### Protect All Endpoints

```python
# In main.py
from fastapi import Depends
from auth import verify_api_key

# Apply to all routes
app = FastAPI(
    dependencies=[Depends(verify_api_key)]  # All routes require auth
)
```

### Protect Specific Endpoints

```python
from fastapi import Depends
from auth import verify_api_key

@app.get("/health")
async def health_check():
    # Public endpoint - no auth required
    return {"status": "healthy"}

@app.post("/api/generate")
async def generate_video(
    # ... parameters ...
    api_key: str = Depends(verify_api_key)  # Protected
):
    return {"message": "Success"}
```

### Optional Authentication

```python
from auth import verify_api_key_optional

@app.get("/api/data")
async def get_data(
    api_key: Optional[str] = Depends(verify_api_key_optional)
):
    if api_key:
        # Return premium data
        return {"data": "premium"}
    else:
        # Return basic data
        return {"data": "basic"}
```

---

## 🔒 Security Best Practices

### 1. Use Strong API Keys

Generate secure keys:
```bash
# Generate a secure random key
openssl rand -hex 32
```

### 2. Store Keys Securely

- ✅ Store in AWS Secrets Manager
- ✅ Never commit to Git
- ✅ Rotate keys regularly

### 3. Use HTTPS

Always use HTTPS in production to prevent key interception.

### 4. Rate Limiting

Combine with WAF rate limiting to prevent abuse.

### 5. Multiple Keys

Support multiple API keys for different clients:

```bash
# Set multiple keys (comma-separated)
API_KEY="key1,key2,key3"
```

---

## 🎯 Use Cases

### 1. Protect All API Endpoints

```python
# main.py
app = FastAPI(
    dependencies=[Depends(verify_api_key)]
)
```

### 2. Public Health Check, Protected API

```python
@app.get("/health")
async def health():
    return {"status": "ok"}  # Public

@app.post("/api/generate")
async def generate(api_key: str = Depends(verify_api_key)):
    return {"job_id": "123"}  # Protected
```

### 3. Different Keys for Different Clients

```python
# In auth.py, verify_api_key can check multiple keys
# Set API_KEY="client1-key,client2-key,admin-key"
```

---

## 🔄 Key Rotation

### Rotate API Key

1. Generate new key:
```bash
NEW_KEY=$(openssl rand -hex 32)
```

2. Update secret:
```bash
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string '{"API_KEY": "'$NEW_KEY'", ...}'
```

3. Force ECS deployment:
```bash
aws ecs update-service \
  --cluster bad-apples-cluster \
  --service bad-apples-backend-service \
  --force-new-deployment
```

4. Update clients with new key

---

## 📊 Monitoring

### Log Authentication Failures

The auth module logs failed attempts. Check CloudWatch:

```bash
aws logs tail /ecs/bad-apples-backend-task --follow | grep "401"
```

### Track API Key Usage

Add logging in `auth.py`:

```python
logger.info("api_key_used", key_prefix=api_key[:8])
```

---

## 🆘 Troubleshooting

### "API key missing"

**Cause:** Client not sending API key

**Solution:** 
- Check header name: `X-API-Key`
- Or use query parameter: `?api_key=YOUR_KEY`

### "Invalid API key"

**Cause:** Key doesn't match configured key

**Solution:**
- Verify key in Secrets Manager
- Check for typos
- Ensure ECS has latest secrets (force deployment)

### "No API key configured"

**Cause:** `API_KEY` environment variable not set

**Solution:**
- Development: All requests allowed (by design)
- Production: Set `API_KEY` in Secrets Manager

---

## 💡 Advanced: JWT Token Authentication

For user-based authentication, consider JWT tokens:

```python
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

security = HTTPBearer()

async def verify_token(token: str = Depends(security)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## 📚 Next Steps

1. ✅ Add `API_KEY` to Secrets Manager
2. ✅ Update `terraform/ecs.tf` to include API_KEY
3. ✅ Add `Depends(verify_api_key)` to protected endpoints
4. ✅ Test authentication
5. ✅ Update client applications with API keys

---

**See `backend/auth.py` for implementation details.**

