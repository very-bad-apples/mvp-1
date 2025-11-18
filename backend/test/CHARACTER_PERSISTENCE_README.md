# Character Reference Image Persistence

## Overview

This document describes the implementation of character reference image persistence in the video generation pipeline. Character reference images are persisted to cloud storage (S3) as part of the job lifecycle, enabling consistent character appearance across video scenes.

## Architecture

### Storage Strategy

Character reference images follow a **job-based workflow** and are stored in cloud storage with the following structure:

```
Cloud Storage Structure:
├── character_references/                    # Standalone images (not yet associated with job)
│   └── {image_id}.{ext}
│
└── videos/                                  # Job-specific images
    └── {job_id}/
        └── intermediate/
            └── character_reference/
                └── {image_id}.{ext}
```

### Key Components

#### 1. AssetPersistenceService

Extended with three new methods for character reference persistence:

**`persist_character_reference(image_id, local_image_path, job_id=None)`**
- Persists a single character reference image to cloud storage
- Supports both standalone images and job-associated images
- Returns cloud URL for the uploaded image

**`associate_character_images_with_job(job_id, image_ids, local_base_path)`**
- Copies character reference images into job directory structure
- Uploads images to cloud under `videos/{job_id}/intermediate/character_reference/`
- Returns list of cloud URLs

**`get_character_reference_url(image_id, job_id=None, extension='png')`**
- Generates presigned URLs (S3)
- Reuses existing storage backend URL generation methods
- Returns None if image doesn't exist

#### 2. API Endpoints

**POST /api/mv/generate_character_reference**
- Generates 1-4 character reference images using Google Imagen 4
- Saves images locally to `mv/outputs/character_reference/`
- Response includes optional `cloud_url` field for each image

**GET /api/mv/get_character_reference/{image_id}**
- Retrieves character reference image by UUID
- Supports both cloud and local serving
- Two response modes:
  - Default: Returns JSON with presigned/public URL
  - Redirect mode (`?redirect=true`): Returns 302 redirect to image

#### 3. Response Models

**CharacterReferenceImage**
```python
class CharacterReferenceImage(BaseModel):
    id: str                      # UUID of the image
    path: str                    # Local file path
    base64: str                  # Base64-encoded image data
    cloud_url: Optional[str]     # Presigned/public URL for cloud access
```

## Usage Examples

### 1. Generate Character Reference Images

```python
import requests

response = requests.post(
    "http://localhost:8000/api/mv/generate_character_reference",
    json={
        "character_description": "A silver metallic humanoid robot with red shield",
        "num_images": 4,
        "aspect_ratio": "1:1"
    }
)

data = response.json()
images = data["images"]

# Access images
for image in images:
    print(f"Image ID: {image['id']}")
    print(f"Local path: {image['path']}")
    print(f"Cloud URL: {image.get('cloud_url', 'Not uploaded yet')}")
```

### 2. Persist Character Image to Cloud

```python
from services.asset_persistence import AssetPersistenceService

service = AssetPersistenceService()

# Persist standalone image
url = await service.persist_character_reference(
    image_id="abc-123",
    local_image_path="/path/to/image.png",
    job_id=None  # Standalone
)
print(f"Uploaded to: {url}")

# Persist as part of job
url = await service.persist_character_reference(
    image_id="abc-123",
    local_image_path="/path/to/image.png",
    job_id="job-456"
)
print(f"Uploaded to: {url}")
```

### 3. Associate Images with Job

```python
# Copy images from standalone storage to job directory and upload
urls = await service.associate_character_images_with_job(
    job_id="job-789",
    image_ids=["abc-123", "def-456"],
    local_base_path="/tmp/video_jobs/job-789"
)

for url in urls:
    print(f"Image URL: {url}")
```

### 4. Get Presigned URL

```python
# Get presigned URL for S3
url = await service.get_character_reference_url(
    image_id="abc-123",
    job_id="job-456",
    extension="png"
)

if url:
    print(f"Access image at: {url}")
else:
    print("Image not found in cloud storage")
```

### 5. Retrieve Image via API

**JSON Response (Default):**
```bash
curl http://localhost:8000/api/mv/get_character_reference/abc-123
```

Response:
```json
{
  "image_id": "abc-123",
  "image_url": "https://s3.amazonaws.com/bucket/character_references/abc-123.png?sig=...",
  "storage_backend": "s3",
  "expires_in_seconds": 3600,
  "cloud_path": "character_references/abc-123.png"
}
```

**Redirect Mode:**
```bash
curl -L http://localhost:8000/api/mv/get_character_reference/abc-123?redirect=true
```

Returns 302 redirect to the actual image URL.

## Configuration

### Environment Variables

```bash
# Cloud Storage Configuration
SERVE_FROM_CLOUD=true                    # Enable cloud serving
STORAGE_BACKEND=s3                       # 's3'
STORAGE_BUCKET=my-bucket                 # Bucket name

# S3-specific
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
PRESIGNED_URL_EXPIRY=3600               # URL expiry in seconds (default: 1 hour)

```

## Integration with Job Lifecycle

### Workflow

1. **Character Generation**
   - User calls `/api/mv/generate_character_reference`
   - Images saved to `mv/outputs/character_reference/`
   - Images returned with UUIDs

2. **Job Creation**
   - When creating a video job, specify character image IDs
   - Call `associate_character_images_with_job()` to copy images to job directory
   - Images uploaded to `videos/{job_id}/intermediate/character_reference/`

3. **Job Persistence**
   - When job completes, call `persist_job_assets()`
   - Character reference images automatically included in upload
   - All job assets backed up to cloud

4. **Job Regeneration**
   - Call `download_job_assets()` to retrieve all job assets
   - Character reference images downloaded along with other assets
   - Ready for regeneration

## Storage Backend Compatibility

### S3 (AWS)
- ✅ Presigned URLs with configurable expiry
- ✅ Time-limited secure access
- ✅ No public bucket access required
- ⚠️ URLs expire after configured time

## Error Handling

### Common Errors

**FileNotFoundError**
```python
# Image file doesn't exist locally
await service.persist_character_reference(
    image_id="abc",
    local_image_path="/nonexistent/image.png"
)
# Raises: FileNotFoundError
```

**Image Not Found in Cloud**
```python
# Image doesn't exist in cloud storage
url = await service.get_character_reference_url(
    image_id="nonexistent"
)
# Returns: None
```

**Cloud Storage Unavailable**
```python
# API endpoint falls back to local serving
GET /api/mv/get_character_reference/{id}
# If cloud fails, serves from local storage
```

## Performance Considerations

### Presigned URL Generation
- **S3**: ~50-100ms per URL (no network call)
- URLs generated locally using credentials

### Image Upload
- Parallel uploads for multiple images
- Uses `asyncio.gather()` for concurrent operations
- Upload speed depends on:
  - Image size
  - Network bandwidth
  - Storage backend performance

### Best Practices

1. **Generate presigned URLs on-demand** - Don't store them in database
2. **Use redirect mode for browsers** - Better UX than JSON response
3. **Set appropriate expiry times** - Balance security and convenience
4. **Monitor cloud storage costs** - Images can accumulate quickly
5. **Implement cleanup policies** - Remove unused standalone images

## Testing

See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for detailed testing instructions.

## Future Enhancements

### Potential Improvements

1. **Lazy Upload**
   - Upload only when image is first accessed
   - Reduce unnecessary cloud storage usage

2. **CDN Integration**
   - Add CloudFront (S3) for faster access
   - Cache images closer to users

3. **Image Optimization**
   - Compress images before upload
   - Generate thumbnails for faster loading

4. **Batch Operations**
   - Upload multiple jobs' images in single operation
   - Bulk presigned URL generation

5. **Metadata Tracking**
   - Store image usage statistics
   - Track which jobs use which images
   - Enable smart cleanup

## Support

For issues or questions:
- Check [TESTING_GUIDE.md](./TESTING_GUIDE.md) for troubleshooting
- Review test files in `backend/test/` for usage examples
- Consult storage backend documentation:
  - [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)

