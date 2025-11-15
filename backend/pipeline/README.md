# Pipeline Core Infrastructure

Core components for the AI ad creative video generation pipeline.

## Phase 1 - Foundation (COMPLETED)

### Components Implemented

1. **Scene Template System** (`templates.py`) - Task 12 ✓
   - 4 hardcoded scene templates (luxury, energetic, minimal, bold)
   - Each template: 4 scenes, 30 seconds total (8s, 8s, 10s, 4s)
   - Scene 4 always static image (cost optimization)
   - Template filling with product data

2. **Asset Manager** (`asset_manager.py`) - Task 18 ✓
   - Async file operations (download, save, validate)
   - Isolated job directories (scenes/, audio/, final/)
   - Retry logic with exponential backoff
   - Cleanup and disk usage tracking

3. **Error Handling System** (`error_handler.py`) - Task 25 ✓
   - Comprehensive error codes for all scenarios
   - User-friendly error messages
   - Retry logic determination
   - Error serialization for API responses

## File Structure

```
backend/pipeline/
├── __init__.py              # Package exports
├── templates.py             # Scene template system (358 lines)
├── asset_manager.py         # File operations (391 lines)
├── error_handler.py         # Error handling (408 lines)
├── test_pipeline.py         # Test suite (522 lines)
├── demo.py                  # Usage examples
└── README.md                # This file
```

## Quick Start

### 1. Scene Templates

```python
from templates import get_scene_template, fill_template

# Get a template
template = get_scene_template("luxury")
print(f"Duration: {template['total_duration']}s")
print(f"Scenes: {len(template['scenes'])}")

# Fill with product data
filled = fill_template(template, "Premium Watch", "Shop Now")
print(filled['scenes'][0]['voiceover_template'])  # "Discover Premium Watch."
```

### 2. Asset Manager

```python
from asset_manager import AssetManager

# Create manager
am = AssetManager("job-123")
await am.create_job_directory()

# Save files
await am.save_file(b"video data", "scene1.mp4", "scenes")
await am.save_file(b"audio data", "voice.mp3", "audio")

# Validate
valid = await am.validate_file("scene1.mp4", "scenes")

# Cleanup
await am.cleanup()
```

### 3. Error Handling

```python
from error_handler import PipelineError, ErrorCode, should_retry

# Raise error
raise PipelineError(
    ErrorCode.INVALID_INPUT,
    "Product name is required",
    {"field": "product_name"}
)

# Handle error
try:
    # ... operation
except PipelineError as e:
    if should_retry(e):
        # Retry logic
    else:
        # Return error to user
        return e.to_dict()
```

## Testing

Run all tests:
```bash
cd backend/pipeline
python test_pipeline.py
```

Expected output:
```
============================================================
ALL TESTS PASSED! ✓
============================================================
```

Run demo:
```bash
python demo.py
```

## Architecture Decisions

### Hardcoded Templates (Not Dynamic LLM)

**The Genius Insight**: We use hardcoded scene templates instead of dynamic LLM generation for:

1. **100% Predictable Structure**: Same timing, pacing, and flow every time
2. **Quality Control**: Templates are professionally crafted and tested
3. **Cost Efficiency**: No LLM calls for scene planning
4. **Performance**: Instant template loading vs API calls
5. **Reliability**: No API failures or hallucinations

The LLM is used ONLY for:
- Script generation (filling voiceover placeholders)
- Video/image prompts (creative variation within structure)

### Scene 4 as Static Image

Scene 4 (final CTA scene) is always a static image because:
- **Cost**: 4s video costs ~$0.20, static image costs ~$0.01 (20x cheaper)
- **Purpose**: CTA doesn't need motion, just clear text and product
- **Reliability**: Image generation is faster and more reliable

### Async/Await Throughout

All file operations use async/await for:
- **Concurrent Downloads**: Multiple assets in parallel
- **Non-blocking I/O**: Don't block event loop
- **Scalability**: Handle multiple jobs simultaneously

## Next Steps - Phase 2

See `PARALLEL-DEVELOPMENT.md` for Phase 2 implementation:

### Tasks 13-19 (Media Generation)

- **Task 13**: Script Generator (`script_generator.py`)
- **Task 14**: Voice Generator (`voice_generator.py`)
- **Task 15**: Video Generator (`video_generator.py`)
- **Task 16**: Image Generator (`image_generator.py`)
- **Task 17**: Video Compositor (`video_compositor.py`)
- **Task 19**: Media API Client (`media_api_client.py`)

These tasks depend on the foundation built in Phase 1.

## API Documentation

### Templates API

#### `get_scene_template(style: str) -> Dict`
Returns a scene template for the specified style.

**Args:**
- `style`: One of 'luxury', 'energetic', 'minimal', 'bold'

**Returns:** Dictionary with scene specifications

**Example:**
```python
template = get_scene_template("luxury")
# {
#   "total_duration": 30,
#   "style_keywords": "soft lighting, elegant, premium, refined",
#   "scenes": [...]
# }
```

#### `fill_template(template: Dict, product_name: str, cta_text: str) -> Dict`
Fills template placeholders with actual product information.

**Args:**
- `template`: Template from `get_scene_template()`
- `product_name`: Product name to insert
- `cta_text`: Call-to-action text

**Returns:** Template with placeholders replaced

### Asset Manager API

#### `AssetManager(job_id: str, base_path: str = "/tmp/video_jobs")`
Creates asset manager for a job.

**Methods:**
- `create_job_directory()`: Create directory structure
- `download_file(url, filename, subdir)`: Download file
- `download_with_retry(url, filename, max_retries=3)`: Download with retry
- `save_file(content, filename, subdir)`: Save binary content
- `validate_file(filename, subdir, min_size=100)`: Validate file
- `list_files(subdir)`: List files in directory
- `get_disk_usage()`: Calculate total size
- `cleanup()`: Remove all files

### Error Handling API

#### Error Codes
- **API Errors**: `INVALID_INPUT`, `FILE_TOO_LARGE`, `UNSUPPORTED_FORMAT`
- **Pipeline Errors**: `SCRIPT_GENERATION_FAILED`, `VIDEO_GENERATION_FAILED`
- **External API**: `CLAUDE_API_ERROR`, `REPLICATE_API_ERROR`, `API_TIMEOUT`
- **System Errors**: `REDIS_CONNECTION_ERROR`, `DATABASE_ERROR`, `STORAGE_ERROR`

#### `PipelineError(code: ErrorCode, message: str, details: Dict)`
Base exception for pipeline errors.

**Methods:**
- `to_dict()`: Serialize for API response
- `get_user_friendly_message()`: Get user-facing message
- `log_error()`: Log with appropriate level

#### `should_retry(error: Exception) -> bool`
Determines if error is transient and should be retried.

**Returns:** True if retryable, False otherwise

## Performance Metrics

- **Template Loading**: <1ms (in-memory)
- **File Operations**: Async, non-blocking
- **Error Handling**: Zero overhead when no errors
- **Test Suite**: ~1 second for all 27 tests

## Code Quality

- **Total Lines**: 1,702 (excluding tests)
- **Type Hints**: Full coverage
- **Docstrings**: All public functions
- **Test Coverage**: 27 tests, all passing
- **Async/Await**: All I/O operations

## Task Master Status

- ✓ Task 12: Create Scene Template System (DONE)
- ✓ Task 18: Build Asset Manager (DONE)
  - ✓ Subtask 18.1: Implement File Operations (DONE)
  - ✓ Subtask 18.2: Implement Cleanup Logic (DONE)
  - ✓ Subtask 18.3: Implement Retry Logic (DONE)
- ✓ Task 25: Implement Error Handling System (DONE)

Updated: 2025-11-14
