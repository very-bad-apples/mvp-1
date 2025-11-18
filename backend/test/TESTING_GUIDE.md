# Character Reference Image Persistence - Testing Guide

## Overview

This guide provides instructions for testing the character reference image persistence implementation, including unit tests, integration tests, and manual testing procedures.

## Test Files

```
backend/test/
├── conftest.py                        # Pytest configuration and fixtures
├── pytest.ini                         # Pytest settings and markers
├── test_character_persistence.py      # Unit tests for AssetPersistenceService
├── test_character_api.py              # Integration tests for API endpoints
├── test_presigned_urls.py             # Tests for URL generation
├── CHARACTER_PERSISTENCE_README.md    # Implementation documentation
└── TESTING_GUIDE.md                   # This file
```

## Prerequisites

### Install Test Dependencies

```bash
cd backend
pip install pytest pytest-asyncio pytest-mock httpx
```

### Python Path Setup

The tests require the `backend/` directory to be in the Python path. This is handled automatically in three ways:

1. **pytest with conftest.py**: The `backend/test/conftest.py` file automatically adds the backend directory to `sys.path`
2. **Individual test files**: Each test file has its own `sys.path.insert()` for direct execution
3. **PYTHONPATH environment variable**: You can manually set it if needed

```bash
# Option 1: Run from backend directory (recommended)
cd backend
pytest test/ -v

# Option 2: Set PYTHONPATH explicitly
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest test/ -v

# Option 3: Use python -m pytest
cd backend
python -m pytest test/ -v
```

### Environment Setup

Create a `.env.test` file for testing:

```bash
# Local Testing (No Cloud)
SERVE_FROM_CLOUD=false
REPLICATE_API_TOKEN=your_token_here

# S3 Testing
SERVE_FROM_CLOUD=true
STORAGE_BACKEND=s3
STORAGE_BUCKET=test-bucket
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
PRESIGNED_URL_EXPIRY=3600

```

## Running Tests

### Run All Tests

```bash
cd backend
pytest test/ -v
```

### Run Specific Test Files

```bash
# Unit tests
pytest test/test_character_persistence.py -v

# API tests
pytest test/test_character_api.py -v

# Presigned URL tests
pytest test/test_presigned_urls.py -v
```

### Run Specific Test Cases

```bash
# Run a single test
pytest test/test_character_persistence.py::test_persist_character_reference_standalone -v

# Run tests matching pattern
pytest test/ -k "presigned" -v

# Skip integration tests (default - they require real credentials)
pytest test/ -v -m "not integration"

# Run ONLY integration tests (requires real AWS credentials)
pytest test/ -v -m "integration"
```

### Run with Coverage

```bash
pytest test/ --cov=services.asset_persistence --cov=routers.mv --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
```

## Manual Testing

### 1. Test Character Reference Generation

**Generate Images:**
```bash
curl -X POST http://localhost:8000/api/mv/generate_character_reference \
  -H "Content-Type: application/json" \
  -d '{
    "character_description": "A silver metallic humanoid robot with red shield",
    "num_images": 4,
    "aspect_ratio": "1:1"
  }'
```

**Expected Response:**
```json
{
  "images": [
    {
      "id": "abc-123...",
      "path": "/path/to/image.png",
      "base64": "iVBORw0KGgo...",
      "cloud_url": null
    }
  ],
  "metadata": {
    "character_description": "...",
    "num_images_generated": 4
  }
}
```

### 2. Test Image Retrieval (Local)

**Get Image:**
```bash
# Get image by ID (replace with actual ID from step 1)
curl http://localhost:8000/api/mv/get_character_reference/abc-123-456...
```

**Expected:** Image file or JSON with URL

### 3. Test Image Persistence

**Create Python Test Script:**
```python
# test_manual_persistence.py
import asyncio
from services.asset_persistence import AssetPersistenceService

async def test_persistence():
    service = AssetPersistenceService()
    
    # Test standalone persistence
    url = await service.persist_character_reference(
        image_id="test-image-id",
        local_image_path="mv/outputs/character_reference/abc-123.png",
        job_id=None
    )
    print(f"Uploaded to: {url}")
    
    # Test job-associated persistence
    url = await service.persist_character_reference(
        image_id="test-image-id",
        local_image_path="mv/outputs/character_reference/abc-123.png",
        job_id="test-job-123"
    )
    print(f"Uploaded to job: {url}")

if __name__ == "__main__":
    asyncio.run(test_persistence())
```

Run:
```bash
python test_manual_persistence.py
```

### 4. Test Cloud Serving (S3)

**Configure S3:**
```bash
export SERVE_FROM_CLOUD=true
export STORAGE_BACKEND=s3
export STORAGE_BUCKET=your-bucket
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
```

**Test Presigned URL:**
```bash
# Generate image first, then get with cloud serving
curl http://localhost:8000/api/mv/get_character_reference/abc-123
```

**Expected Response:**
```json
{
  "image_id": "abc-123",
  "image_url": "https://your-bucket.s3.us-east-1.amazonaws.com/...?X-Amz-Signature=...",
  "storage_backend": "s3",
  "expires_in_seconds": 3600,
  "cloud_path": "character_references/abc-123.png"
}
```

**Test Redirect Mode:**
```bash
curl -L http://localhost:8000/api/mv/get_character_reference/abc-123?redirect=true
```

### 5. Test Associate Images with Job

**Create Test Script:**
```python
# test_associate_images.py
import asyncio
from pathlib import Path
from services.asset_persistence import AssetPersistenceService

async def test_associate():
    service = AssetPersistenceService()
    
    # Create job directory
    job_dir = Path("/tmp/test_job_123")
    job_dir.mkdir(exist_ok=True)
    
    # Associate images (replace with actual image IDs)
    urls = await service.associate_character_images_with_job(
        job_id="test-job-123",
        image_ids=["abc-123", "def-456"],
        local_base_path=str(job_dir)
    )
    
    for url in urls:
        print(f"Image associated: {url}")

if __name__ == "__main__":
    asyncio.run(test_associate())
```

### 6. Test Complete Job Workflow

**Full Integration Test:**
```python
# test_full_workflow.py
import asyncio
import tempfile
from pathlib import Path
from services.asset_persistence import AssetPersistenceService

async def test_full_workflow():
    service = AssetPersistenceService()
    
    # 1. Generate character images (via API)
    print("Step 1: Generate character reference images")
    # (Use curl or requests to call /api/mv/generate_character_reference)
    
    # 2. Create job directory with character references
    print("Step 2: Create job directory")
    with tempfile.TemporaryDirectory() as job_dir:
        job_path = Path(job_dir)
        char_ref_dir = job_path / "character_reference"
        char_ref_dir.mkdir()
        
        # Copy test image
        # (Simulate having character reference images)
        
        # 3. Persist job assets (includes character references)
        print("Step 3: Persist job assets")
        result = await service.persist_job_assets(
            job_id="test-job-789",
            local_base_path=str(job_path)
        )
        
        print(f"Character references uploaded: {len(result['character_references'])}")
        for url in result['character_references']:
            print(f"  - {url}")
        
        # 4. Download job assets
        print("Step 4: Download job assets")
        with tempfile.TemporaryDirectory() as download_dir:
            await service.download_job_assets(
                job_id="test-job-789",
                local_base_path=download_dir
            )
            
            # Verify character references downloaded
            downloaded_refs = list(Path(download_dir).glob("character_reference/*"))
            print(f"Downloaded {len(downloaded_refs)} character references")

if __name__ == "__main__":
    asyncio.run(test_full_workflow())
```

## Troubleshooting

### Common Issues

#### 1. Import/Module Errors

**Problem:**
```
ModuleNotFoundError: No module named 'services'
```

**Solution:**

The tests need to import from the backend directory. Make sure you're running tests correctly:

```bash
# ✅ Correct - Run from backend directory
cd backend
pytest test/ -v

# ✅ Also correct - Use python -m pytest
cd backend
python -m pytest test/ -v

# ❌ Wrong - Running from test directory
cd backend/test
pytest test_character_api.py  # Will fail with import errors
```

If you still get import errors:
```bash
# Manually set PYTHONPATH
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest test/ -v
```

The `conftest.py` file in the test directory automatically handles path setup when using pytest.

#### 2. AWS Credentials Not Found

**Problem:**
```
ClientError: Unable to locate credentials
```

**Solution:**
```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1

# Or use AWS CLI to configure
aws configure
```

#### 3. Replicate API Token Missing

**Problem:**
```
ValueError: REPLICATE_API_TOKEN is not configured
```

**Solution:**
```bash
export REPLICATE_API_TOKEN=your_token_here
```

#### 4. Image Not Found

**Problem:**
```
404: Character reference image with ID xxx not found
```

**Solution:**
- Verify image was actually generated
- Check `backend/mv/outputs/character_reference/` for files
- Ensure image ID matches file name (UUID)

#### 5. Cloud Storage Connection Failed

**Problem:**
```
Error: Failed to connect to storage backend
```

**Solution:**
- Verify STORAGE_BACKEND is set correctly ('s3')
- Check STORAGE_BUCKET is valid
- Verify credentials are correct
- Test network connectivity

#### 6. Mock/Patch Errors

**Problem:**
```
AttributeError: <module 'routers.mv'> does not have the attribute 'get_storage_backend'
```

**Solution:**
When patching imports that happen inside functions, patch at the source module:
```python
# ❌ Wrong - trying to patch where it's imported
with patch('routers.mv.get_storage_backend') as mock:
    pass

# ✅ Correct - patch at the source
with patch('services.storage_backend.get_storage_backend') as mock:
    pass
```

### Debugging Tips

**Enable Debug Logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check File Existence:**
```bash
# List character reference images
ls -la backend/mv/outputs/character_reference/

# Check cloud storage (S3)
aws s3 ls s3://your-bucket/character_references/

```

**Verify Configuration:**
```bash
curl http://localhost:8000/api/mv/config/debug
```

## Test Coverage Goals

### Unit Tests
- ✅ persist_character_reference() - standalone
- ✅ persist_character_reference() - with job
- ✅ associate_character_images_with_job()
- ✅ get_character_reference_url() - S3
- ✅ persist_job_assets() includes character_references

### Integration Tests
- ✅ POST /api/mv/generate_character_reference
- ✅ GET /api/mv/get_character_reference/{id} - local
- ✅ GET /api/mv/get_character_reference/{id} - S3
- ✅ GET /api/mv/get_character_reference/{id} - redirect mode
- ✅ Cloud fallback to local serving

### Presigned URL Tests
- ✅ S3 presigned URL generation
- ✅ URL expiry configuration
- ✅ Different file extensions
- ✅ URL uniqueness

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Character Persistence

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-mock
    
    - name: Run tests
      env:
        SERVE_FROM_CLOUD: false
        REPLICATE_API_TOKEN: ${{ secrets.REPLICATE_API_TOKEN }}
      run: |
        cd backend
        pytest test/ -v --cov=services.asset_persistence
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Performance Testing

### Benchmark Script

```python
# benchmark_persistence.py
import asyncio
import time
from services.asset_persistence import AssetPersistenceService

async def benchmark():
    service = AssetPersistenceService()
    
    # Test presigned URL generation speed
    start = time.time()
    for i in range(100):
        await service.get_character_reference_url(
            image_id=f"test-{i}",
            extension="png"
        )
    elapsed = time.time() - start
    print(f"100 URL generations: {elapsed:.2f}s ({elapsed/100*1000:.2f}ms each)")

if __name__ == "__main__":
    asyncio.run(benchmark())
```

## Next Steps

1. ✅ Run all unit tests
2. ✅ Run integration tests with local storage
3. ✅ Run integration tests with S3
4. ✅ Perform manual end-to-end test
5. ✅ Check test coverage (aim for >80%)
6. ✅ Review and fix any failing tests
7. ✅ Document any additional edge cases

## Support

For issues or questions:
- Review [CHARACTER_PERSISTENCE_README.md](./CHARACTER_PERSISTENCE_README.md)
- Check test file comments for usage examples
- Consult pytest documentation: https://docs.pytest.org/

