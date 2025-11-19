# Test Suite

This directory contains all test files for the backend application, organized to mirror the source code structure.

## Directory Structure

```
tests/
├── __init__.py              # Test package initialization (adds backend to path)
├── test_dynamodb_models.py  # DynamoDB model tests
├── test_endpoints.py        # General API endpoint tests
├── test_mv_endpoints.py     # Music Video API endpoint tests
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

## Notes

- Integration tests require the backend server to be running on `localhost:8000`
- Some tests require DynamoDB Local to be running (via Docker Compose)
- Some tests require Redis to be running (via Docker Compose)
- Mock data and fixtures are typically defined within each test file

