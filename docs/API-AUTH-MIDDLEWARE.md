# API Authentication Middleware - All /api/ Routes Protected

## ✅ What Was Done

Added a middleware in `backend/main.py` that **automatically protects all `/api/` routes** with API key authentication.

---

## 🔒 How It Works

### Protected Routes
- ✅ **All routes starting with `/api/`** require authentication
- Examples:
  - `/api/generate` ✅ Protected
  - `/api/jobs/{job_id}` ✅ Protected
  - `/api/mv/create_scenes` ✅ Protected
  - `/api/audio/download` ✅ Protected

### Public Routes (No Auth Required)
- ✅ `/health` - Health check
- ✅ `/` - Root endpoint
- ✅ `/docs` - Swagger documentation
- ✅ `/redoc` - ReDoc documentation
- ✅ `/openapi.json` - OpenAPI schema
- ✅ `/ws/*` - WebSocket endpoints (if any)

---

## 📋 Implementation Details

### Middleware Location
`backend/main.py` - `api_authentication_middleware()`

### How It Works
1. Checks if path starts with `/api/`
2. Extracts API key from:
   - Header: `X-API-Key: your-key`
   - Query parameter: `?api_key=your-key`
3. Verifies key against `API_KEY` environment variable
4. Returns 401 if missing or invalid
5. Allows request to continue if valid

---

## 🚀 Usage

### No Changes Needed in Your Endpoints!

All `/api/` routes are automatically protected. You don't need to add `Depends(verify_api_key)` to individual endpoints.

### Example: Your Existing Endpoints

```python
# routers/generate.py
@app.post("/api/generate")  # ← Automatically protected!
async def generate_video(...):
    return {"job_id": "123"}
```

**No changes needed!** The middleware handles it.

---

## 🧪 Testing

### Without API Key (Will Fail)
```bash
curl https://your-alb-url/api/generate
# Returns: 401 Unauthorized
```

### With API Key (Will Succeed)
```bash
# Using header
curl -H "X-API-Key: your-key" \
     https://your-alb-url/api/generate

# Using query parameter
curl https://your-alb-url/api/generate?api_key=your-key
```

### Public Endpoints (No Auth Needed)
```bash
curl https://your-alb-url/health
# Returns: {"status": "healthy"}
```

---

## ⚙️ Configuration

### Set API Key

**Option 1: Via Secrets Manager**
```bash
aws secretsmanager update-secret \
  --secret-id bad-apples-backend-task-secrets \
  --secret-string '{"API_KEY": "your-key"}'
```

**Option 2: Via Terraform**
```hcl
# terraform.tfvars
api_key = "your-key"
```

### Development Mode

If `API_KEY` is not set (empty), **all requests are allowed**. This is useful for development.

---

## 🔍 What Routes Are Protected?

### Protected (Require API Key)
- ✅ `/api/generate`
- ✅ `/api/jobs/{job_id}`
- ✅ `/api/mv/*` (all MV endpoints)
- ✅ `/api/audio/*` (all audio endpoints)
- ✅ Any route starting with `/api/`

### Public (No Auth Required)
- ✅ `/health`
- ✅ `/`
- ✅ `/docs`
- ✅ `/redoc`
- ✅ `/openapi.json`
- ✅ `/ws/*` (WebSocket)

---

## 🎯 Benefits

1. ✅ **Automatic Protection** - No need to modify individual endpoints
2. ✅ **Consistent Security** - All API routes protected uniformly
3. ✅ **Easy to Maintain** - One place to manage authentication
4. ✅ **Flexible** - Supports header or query parameter
5. ✅ **Development Friendly** - Works without API key in dev mode

---

## 📝 Code Changes

### Modified Files
- ✅ `backend/main.py` - Added authentication middleware
- ✅ `backend/auth.py` - Renamed `verify_api_key()` function to `check_api_key()` to avoid naming conflict

### No Changes Needed
- ✅ All router files (`routers/*.py`) - No changes needed!
- ✅ All endpoint functions - No changes needed!

---

## 🔄 How to Disable (If Needed)

To temporarily disable authentication, comment out the middleware:

```python
# @app.middleware("http")
# async def api_authentication_middleware(request: Request, call_next):
#     ...
```

Or set `API_KEY=""` in environment variables (development mode).

---

## ✅ Summary

**All `/api/` routes are now automatically protected!**

- ✅ No code changes needed in your endpoints
- ✅ Works with header: `X-API-Key`
- ✅ Works with query: `?api_key=...`
- ✅ Public routes remain public
- ✅ Development mode if no API key set

**Just set `API_KEY` in Secrets Manager and you're done!** 🎉

