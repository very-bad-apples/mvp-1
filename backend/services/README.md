# Backend Services

This directory contains business logic services for the AI Video Generator backend.

## File Upload Service

The `FileUploadService` handles file uploads with comprehensive validation, thumbnail generation, and temporary storage management.

### Features

1. **File Format Validation** (Subtask 11.1)
   - Supports PNG, JPG/JPEG, and WebP formats
   - Validates both file extension and actual image format
   - Detects corrupted or invalid images

2. **Thumbnail Generation** (Subtask 11.2)
   - Automatically generates 300x300 thumbnails
   - Maintains aspect ratio
   - Converts RGBA/transparency to RGB with white background
   - Outputs optimized JPEG thumbnails

3. **File Size Validation** (Subtask 11.3)
   - Enforces 10MB maximum file size
   - Rejects empty files
   - Provides detailed error messages

4. **Temporary Storage Management** (Subtask 11.4)
   - Session-based file organization
   - Automatic directory creation
   - Filename sanitization for security
   - Session cleanup capabilities

### Installation

Required packages (already in requirements.txt):
```bash
pip install Pillow python-multipart aiohttp aiofiles
```

### Usage Example

```python
from services.file_upload import FileUploadService

# Initialize service
upload_service = FileUploadService(upload_dir="/tmp/uploads")

# Process file upload
async def handle_upload(file_bytes: bytes, filename: str):
    result = await upload_service.process_upload(
        file_content=file_bytes,
        filename=filename,
        session_id="user_session_123",
        generate_thumbnail=True
    )

    if result["success"]:
        print(f"File uploaded: {result['file_path']}")
        print(f"Thumbnail: {result['thumbnail_path']}")
        print(f"Format: {result['format']}")
        print(f"Size: {result['size_bytes']} bytes")
    else:
        print(f"Upload failed: {result['error']}")

    return result
```

### FastAPI Integration Example

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from services.file_upload import FileUploadService

app = FastAPI()
upload_service = FileUploadService()

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """Upload product image with validation"""

    # Read file content
    content = await file.read()

    # Process upload
    result = await upload_service.process_upload(
        file_content=content,
        filename=file.filename,
        generate_thumbnail=True
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "message": "File uploaded successfully",
        "file_path": result["file_path"],
        "thumbnail_path": result["thumbnail_path"],
        "session_id": result["session_id"],
        "format": result["format"],
        "size_bytes": result["size_bytes"]
    }

@app.delete("/upload/{session_id}")
async def cleanup_upload(session_id: str):
    """Clean up uploaded files for a session"""
    await upload_service.cleanup_session(session_id)
    return {"message": "Session cleaned up successfully"}
```

### API Reference

#### FileUploadService

**Constructor:**
```python
FileUploadService(upload_dir: str = "/tmp/uploads")
```

**Main Methods:**

- `process_upload(file_content, filename, session_id=None, generate_thumbnail=True)` - Complete upload processing
- `validate_format(file_content, filename)` - Validate image format
- `validate_size(file_content, filename)` - Validate file size
- `generate_thumbnail(file_content, thumbnail_path, size=(300, 300))` - Generate thumbnail
- `save_to_storage(file_content, filename, session_id=None)` - Save to temporary storage
- `cleanup_session(session_id)` - Remove all session files
- `get_session_files(session_id)` - List files in session

**Configuration:**

```python
# Supported formats
SUPPORTED_FORMATS = {"PNG", "JPEG", "WEBP"}
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# File size limit
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Thumbnail settings
THUMBNAIL_SIZE = (300, 300)
THUMBNAIL_QUALITY = 85
```

### Testing

Run the comprehensive test suite:

```bash
cd backend
pytest services/test_file_upload.py -v
```

Test coverage includes:
- 27 test cases covering all 4 subtasks
- Format validation (6 tests)
- Thumbnail generation (5 tests)
- Size validation (4 tests)
- Storage management (6 tests)
- Integration tests (6 tests)

### Error Handling

The service provides detailed error messages for:
- Unsupported file formats
- Files exceeding size limits
- Corrupted or invalid images
- Empty files
- Storage failures

Example error response:
```python
{
    "success": False,
    "error": "File size (12.45MB) exceeds maximum allowed size (10.00MB)",
    "file_path": None,
    "thumbnail_path": None
}
```

### Security Features

- Filename sanitization prevents directory traversal attacks
- File format verification (not just extension checking)
- Size limits prevent DoS attacks
- Session-based isolation
- Safe file handling with proper cleanup

### Integration with Asset Manager

The FileUploadService complements the existing `AssetManager` in `pipeline/asset_manager.py`:

- **FileUploadService**: Handles user uploads, validation, thumbnails
- **AssetManager**: Manages job-specific assets during video generation

They can work together:

```python
from services.file_upload import FileUploadService
from pipeline.asset_manager import AssetManager

# User uploads product image
upload_result = await upload_service.process_upload(...)

# Later, use in video generation job
asset_manager = AssetManager(job_id="job-123")
await asset_manager.create_job_directory()

# Copy uploaded file to job directory
import shutil
shutil.copy(
    upload_result["file_path"],
    asset_manager.job_dir / "product.jpg"
)
```

### Performance

- Asynchronous I/O for non-blocking uploads
- Efficient streaming with aiofiles
- Pillow optimization for thumbnails
- Memory-efficient image processing

### Future Enhancements

Potential improvements:
- Support for additional image formats (GIF, TIFF)
- Multiple thumbnail sizes
- Image compression/optimization
- S3/cloud storage integration
- Virus scanning integration
- Rate limiting per session
