# Quick Start: API Authentication

## 🚀 Enable API Key Authentication

### Step 1: Generate API Key

```bash
# Generate a secure random API key
openssl rand -hex 32
```

### Step 2: Add to Secrets Manager

```bash
# Get current secret
CURRENT=$(aws secretsmanager get-secret-value \
  --secret-id bad-apples-backend-task-secrets \
  --query SecretString --output text)

# Add API_KEY
echo "$CURRENT" | jq '.API_KEY = "your-generated-key-here"' | \
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string file:///dev/stdin \
  --region us-east-1
```

### Step 3: Apply Terraform

```bash
cd terraform
terraform apply
```

### Step 4: Protect Your Endpoints

In your FastAPI routes, add authentication:

```python
from fastapi import Depends
from auth import verify_api_key

@app.post("/api/generate")
async def generate_video(
    # ... your existing parameters ...
    api_key: str = Depends(verify_api_key)  # Add this line
):
    # Your endpoint logic
    return {"job_id": "123"}
```

### Step 5: Test

```bash
# Without API key (will fail with 401)
curl https://your-alb-url/api/generate

# With API key (success)
curl -H "X-API-Key: your-generated-key-here" \
     https://your-alb-url/api/generate
```

**Done!** ✅

---

## 📋 Example: Protect Your Endpoints

### Before (No Auth)

```python
# routers/generate.py
@app.post("/api/generate")
async def generate_video(
    product_name: str = Form(...),
    style: str = Form(...)
):
    # Generate video
    return {"job_id": "123"}
```

### After (With Auth)

```python
# routers/generate.py
from auth import verify_api_key

@app.post("/api/generate")
async def generate_video(
    product_name: str = Form(...),
    style: str = Form(...),
    api_key: str = Depends(verify_api_key)  # Add this
):
    # Generate video
    return {"job_id": "123"}
```

---

## 🔒 Keep Health Check Public

```python
# main.py
@app.get("/health")
async def health_check():
    # No auth required - public endpoint
    return {"status": "healthy"}

# routers/generate.py
from auth import verify_api_key

@app.post("/api/generate")
async def generate_video(
    api_key: str = Depends(verify_api_key)  # Protected
):
    return {"job_id": "123"}
```

---

## 📱 Client Usage

### JavaScript/Fetch

```javascript
fetch('https://your-alb-url/api/generate', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key-here',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({...})
})
```

### cURL

```bash
curl -H "X-API-Key: your-api-key-here" \
     -H "Content-Type: application/json" \
     -X POST \
     https://your-alb-url/api/generate \
     -d '{"product_name": "Test"}'
```

### Python Requests

```python
import requests

headers = {
    'X-API-Key': 'your-api-key-here',
    'Content-Type': 'application/json'
}

response = requests.post(
    'https://your-alb-url/api/generate',
    headers=headers,
    json={'product_name': 'Test'}
)
```

---

## ✅ Checklist

- [ ] Generate secure API key
- [ ] Add `API_KEY` to Secrets Manager
- [ ] Update `terraform/ecs.tf` (already done)
- [ ] Apply Terraform changes
- [ ] Add `Depends(verify_api_key)` to protected endpoints
- [ ] Test authentication
- [ ] Update client applications with API keys

---

**See `docs/API-AUTHENTICATION-GUIDE.md` for complete documentation.**

