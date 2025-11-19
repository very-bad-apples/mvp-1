# Test Suite

This directory contains all test files for the backend application, organized to mirror the source code structure.

## Directory Structure

```
tests/
├── __init__.py              # Test package initialization (adds backend to path)
├── test_dynamodb_models.py  # DynamoDB model tests
├── test_endpoints.py        # General API endpoint tests
├── test_mv_endpoints.py     # Music Video API endpoint tests
├── test_e2e_workflow.py     # End-to-end workflow tests
├── test_video_generation_db_integration.py  # Video generation DynamoDB integration tests
├── test_worker.py           # Worker process tests
├── mv/                      # MV module tests
│   ├── __init__.py
│   ├── test_image_generator.py
│   ├── test_mock_video_generator.py
│   ├── test_scene_generator.py
│   └── test_video_generator.py
├── pipeline/                # Pipeline module tests
│   ├── __init__.py
│   ├── test_cta_generator.py
│   ├── test_orchestrator.py
│   ├── test_pipeline.py
│   ├── test_script_generator.py
│   ├── test_video_composer.py
│   ├── test_video_generator.py
│   └── test_voiceover_generator.py
└── services/                # Services module tests
    ├── __init__.py
    ├── test_file_upload.py
    └── test_replicate_client.py
```

## Running Tests

### Run All Tests
```bash
cd backend
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_dynamodb_models.py
pytest tests/mv/test_scene_generator.py
```

### Run Tests with Coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

### Run Integration Tests (Requires Running Backend)
```bash
# Start backend server first
python main.py

# In another terminal, run integration tests
python tests/test_mv_endpoints.py
python tests/test_endpoints.py
```

### Run End-to-End Workflow Tests
```bash
# Prerequisites:
# 1. Backend server running: cd backend && uvicorn main:app --reload
# 2. DynamoDB Local running: docker-compose up -d dynamodb-local
# 3. Redis running: docker-compose up -d redis
# 4. GEMINI_API_KEY set (for scene generation): export GEMINI_API_KEY=your_key

# Run E2E test
cd backend
python tests/test_e2e_workflow.py
```

The E2E test verifies the complete workflow:
1. Create project via POST /api/mv/projects
2. Verify project in DynamoDB
3. Generate scenes via POST /api/mv/create_scenes with project_id
4. Verify scenes in DynamoDB
5. Verify project status updates
6. Test compose endpoint (expected failure - scenes not completed)
7. Test final video endpoint (expected failure - not composed)
8. Cleanup test data

## Import Paths

The `tests/__init__.py` file automatically adds the parent `backend` directory to `sys.path`, allowing tests to import modules using absolute imports:

```python
# ✅ Correct - absolute imports
from mv_models import MVProjectItem
from pipeline.templates import get_scene_template
from services.replicate_client import ReplicateClient

# ❌ Incorrect - relative imports (won't work)
from ..mv_models import MVProjectItem
```

## Test Categories

### Unit Tests
- `test_dynamodb_models.py` - DynamoDB model operations
- `mv/test_*.py` - MV module components
- `pipeline/test_*.py` - Pipeline components
- `services/test_*.py` - Service components

### Integration Tests
- `test_mv_endpoints.py` - MV API endpoint integration tests
- `test_endpoints.py` - General API endpoint integration tests
- `test_worker.py` - Worker process integration tests

### End-to-End Tests
- `test_e2e_workflow.py` - Complete workflow test (create project → generate scenes → verify DB → test compose)

### Integration Tests (DynamoDB)
- `test_video_generation_db_integration.py` - Video generation endpoints DynamoDB integration tests

## Notes

- Integration tests require the backend server to be running on `localhost:8000`
- Some tests require DynamoDB Local to be running (via Docker Compose)
- Some tests require Redis to be running (via Docker Compose)
- E2E tests require GEMINI_API_KEY for scene generation (will skip if not set)
- Mock data and fixtures are typically defined within each test file
- E2E tests automatically clean up test data after execution

