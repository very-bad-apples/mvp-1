# Implementation Notes - v2

## v1 - Multi-Image Character Reference Generation

### Implementation Summary

Successfully implemented batch generation of 1-4 character reference images with UUID-based storage.

### Key Changes

#### Backend

1. **UUID-based Storage**
   - Changed from timestamp-based filenames (`character_ref_YYYYMMDD_HHMMSS.ext`)
   - Now uses UUID filenames (`{uuid}.ext`)
   - Images stored in `backend/mv/outputs/character_reference/`

2. **Batch Generation via Replicate API**
   - Added `number_of_images` parameter to Replicate API call
   - API returns list of FileOutput objects for batch requests
   - Each image processed and saved with unique UUID

3. **Updated Request Model**
   ```python
   class GenerateCharacterReferenceRequest:
       character_description: str  # Required
       num_images: int = 4         # New: 1-4, default 4
       # ... other optional params
   ```

4. **New Response Structure**
   ```python
   class CharacterReferenceImage:
       id: str      # UUID
       path: str    # File path
       base64: str  # Encoded image data

   class GenerateCharacterReferenceResponse:
       images: list[CharacterReferenceImage]  # Changed from single image
       metadata: dict
   ```

5. **New Image Retrieval Endpoint**
   - `GET /api/mv/get_character_reference/{image_id}`
   - Returns image file directly
   - Supports png, jpg, jpeg, webp formats
   - Validates UUID format

6. **Debug Logging**
   - Added `log_batch_image_request()` and `log_batch_image_result()` functions
   - Enhanced logging with num_images_requested, num_images_generated, image_ids

### Deviations from Plan

1. **Parallel API Calls Instead of Batch Parameter**
   - Plan assumed Replicate supports `num_outputs` or `number_of_images` parameter
   - **Reality**: Google Imagen 4 does NOT support batch generation (1 image per call)
   - **Solution**: Implemented parallel API calls using `ThreadPoolExecutor`
   - Each of the N requested images triggers a separate Replicate API call
   - Calls run concurrently for better performance
   - Each call can have unique seed (base_seed + offset) for variation

2. **Frontend Implementation Deferred**
   - Backend-only implementation completed
   - Frontend tasks (grid display, single-select UI) not implemented
   - Frontend team can use the new API structure

3. **No Video Generation Integration Yet**
   - Endpoint returns image ID that can be used with video generation
   - Fetching image by ID available via `/api/mv/get_character_reference/{id}`
   - Frontend must convert to base64 for video generation request (or enhancement could be made to accept ID directly)

### Architecture Decisions

1. **Pydantic ge/le Validation**
   - Used `Field(4, ge=1, le=4)` for automatic range validation
   - Additional manual validation in function for clarity

2. **UUID via Python stdlib**
   - Using `uuid.uuid4()` for standard UUID generation
   - No external dependencies needed

3. **Single Replicate API Call**
   - Batch generation uses single API call with `number_of_images`
   - More cost-efficient than multiple separate calls
   - Single prompt/parameters applied to all images

4. **Backward Incompatibility**
   - Response structure changed (breaking change)
   - Old clients expecting single image will fail
   - Intentional for this version upgrade

### Testing

- 15 unit tests added/updated
- Tests cover:
  - Model validation (including num_images range)
  - Single and batch image generation
  - UUID filename format
  - Custom parameters
  - Error handling

### API Usage Examples

**Request (4 images, default):**
```json
POST /api/mv/generate_character_reference
{
  "character_description": "Silver metallic robot with blue eyes"
}
```

**Request (specific number):**
```json
POST /api/mv/generate_character_reference
{
  "character_description": "Silver metallic robot with blue eyes",
  "num_images": 2
}
```

**Response:**
```json
{
  "images": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "path": "/path/to/a1b2c3d4...png",
      "base64": "iVBORw0KGgoAAAANSUhEUgAA..."
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "path": "/path/to/b2c3d4e5...png",
      "base64": "iVBORw0KGgoAAAANSUhEUgBB..."
    }
  ],
  "metadata": {
    "character_description": "Silver metallic robot with blue eyes",
    "model_used": "google/imagen-4",
    "num_images_requested": 2,
    "num_images_generated": 2,
    "parameters_used": {
      "aspect_ratio": "1:1",
      "safety_filter_level": "block_medium_and_above",
      "person_generation": "allow_adult",
      "output_format": "png",
      "negative_prompt": null,
      "seed": null
    },
    "generation_timestamp": "2025-11-16T21:30:25Z"
  }
}
```

**Retrieve single image:**
```bash
GET /api/mv/get_character_reference/a1b2c3d4-e5f6-7890-abcd-ef1234567890
# Returns: Image file directly
```

### Future Improvements

1. **Frontend Selection UI**
   - 2x2 grid layout for 4 images
   - Single-select with visual feedback
   - Pass selected ID to video generation

2. **Video Generation Integration**
   - Option to accept image ID directly (not just base64)
   - Automatically fetch and convert to base64 server-side

3. **Image Metadata Endpoint**
   - Add `/api/mv/get_character_reference/{id}/info`
   - Return metadata without image data

4. **Partial Success Handling**
   - Handle cases where fewer images than requested are returned
   - Currently assumes all requested images are generated

### Files Modified

- `backend/mv/image_generator.py` - Core batch generation logic
- `backend/routers/mv.py` - Endpoint updates + new retrieval endpoint
- `backend/mv/debug.py` - New batch logging functions
- `backend/mv/test_image_generator.py` - 15 updated tests
- `frontend/src/app/create/page.tsx` - Multi-image handling, grid display, ID tracking
- `.devdocs/v2/tasklist.md` - Task tracking
- `.devdocs/v2/impl-notes.md` - This file


---

## Frontend Implementation

### Changes Made

1. **API Client Update**
   - Request now includes `num_images: 4` parameter
   - Response parsing handles `data.images` array instead of single `data.image_base64`
   - Each image's `id` and `base64` data extracted

2. **State Management**
   - Added `generatedImageIds` state to track UUIDs alongside blob URLs
   - Maintains parallel arrays: `generatedImages` (blob URLs) and `generatedImageIds` (UUIDs)

3. **Loading Skeleton**
   - Updated to show 4 skeleton placeholders in 2x2 grid
   - Message indicates "Generating 4 character images..."

4. **Image Selection**
   - Grid already supported multiple images (2x2 layout)
   - Single-select with blue border and checkmark indicator
   - Selected image ID available via `generatedImageIds[selectedImageIndex]`

5. **Form Submission**
   - Selected image ID appended to FormData as `characterReferenceImageId`
   - Ready for backend integration with video generation

### Frontend File Details

**Location**: `frontend/src/app/create/page.tsx`

**Key State Variables**:
```typescript
const [generatedImages, setGeneratedImages] = useState<string[]>([])        // Blob URLs for display
const [generatedImageIds, setGeneratedImageIds] = useState<string[]>([])    // UUIDs for backend
const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null)
```

**API Call** (lines 172-217):
```typescript
const response = await fetch(`${API_URL}/api/mv/generate_character_reference`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    character_description: characterDescription.trim(),
    num_images: 4,  // NEW: Request 4 images
  }),
})

const data = await response.json()
// Process data.images array (not single image)
for (const image of data.images) {
  // Convert base64 to blob URL
  blobUrls.push(blobUrl)
  imageIds.push(image.id)  // Store UUID
}
```

**Form Submission** (lines 124-127):
```typescript
if (useAICharacter && selectedImageIndex !== null && generatedImageIds[selectedImageIndex]) {
  formData.append('characterReferenceImageId', generatedImageIds[selectedImageIndex])
}
```

### UI Features

- 2x2 grid layout for 4 images
- Blue border + checkmark on selected image
- Ring effect for visual feedback
- "Option 1/2/3/4" labels on each image
- Confirmation message when image selected
- Skeleton loading placeholders during generation

### Not Implemented

1. **Actual Video Generation Integration**
   - Form submission is still mock (uses setTimeout)
   - Need to connect to real `/api/mv/generate_video` endpoint
   - Need to fetch image by ID and convert to base64 for video request

2. **Progressive Loading**
   - All images load at once (as returned by API)
   - Could add individual loading states if backend supports streaming

3. **Partial Failure Handling**
   - If backend returns fewer than 4 images, UI will display what's available
   - No specific error message for partial success

---

## v4 - Video Generation from Scenes

### Implementation Summary

Integrated parallel video generation from generated scenes on `/quick-gen-page`.

### Key Features

1. **Automatic Video Generation**
   - Videos start generating immediately after scenes are created
   - All videos generated in parallel using `Promise.allSettled`
   - Each scene's `description` maps to `prompt`
   - Each scene's `negative_description` maps to `negative_prompt`

2. **Video Cards with Loading States**
   - Cards created immediately with loading spinner
   - Status badge per card (Generating/Ready/Failed)
   - Video ID displayed after completion
   - Configurable expected load time (default: 7 seconds)

3. **Video Playback**
   - HTML5 video player with controls enabled
   - Sound enabled (not muted by default)
   - No autoplay - user must click to play
   - Uses `video_url` from API response directly

4. **Status Summary Bar**
   - Real-time summary: "X loading / Y succeeded / Z failed"
   - Color-coded badges (blue/green/red)
   - Updates dynamically as each video completes

5. **Per-Card Error Handling**
   - Errors isolated to specific cards
   - Shows scene number in error message
   - Other videos unaffected by individual failures

### Limitations

1. **Character Reference Image Not Passed**
   - `reference_image_base64` parameter is omitted from video generation requests
   - Would require fetching character image by ID and converting to base64
   - Documented in code as future enhancement
   - Character reference ID is available but not utilized

2. **No Progress Indicator Per Video**
   - Backend doesn't provide progress status for video generation
   - Only loading/completed/error states available
   - Expected load time shown as placeholder (configurable constant)

3. **No Retry Mechanism**
   - Failed videos cannot be retried without reloading page
   - Future enhancement: add retry button per card

### Configuration

```typescript
// frontend/src/app/quick-gen-page/page.tsx
const VIDEO_EXPECTED_LOAD_TIME_SECONDS = 7 // Configurable expected time
```

### Code Structure

**State Management:**
```typescript
interface VideoState {
  sceneIndex: number
  status: 'loading' | 'completed' | 'error'
  videoId?: string
  videoUrl?: string
  error?: string
}

const [videoStates, setVideoStates] = useState<VideoState[]>([])
```

**Parallel Generation:**
```typescript
const generateVideos = async () => {
  // Initialize all cards as loading
  const initialStates = scenes.map((_, index) => ({
    sceneIndex: index,
    status: 'loading',
  }))
  setVideoStates(initialStates)

  // Fire all requests in parallel
  const videoPromises = scenes.map((scene, index) =>
    generateSingleVideo(scene, index)
  )
  await Promise.allSettled(videoPromises)
}
```

**Status Summary Calculation:**
```typescript
const videoSummary = {
  loading: videoStates.filter(v => v.status === 'loading').length,
  succeeded: videoStates.filter(v => v.status === 'completed').length,
  failed: videoStates.filter(v => v.status === 'error').length,
}
```

### Future Improvements

1. **Character Reference Integration**
   - Fetch character image by ID via `/api/mv/get_character_reference/{id}`
   - Convert to base64 and pass to `generate_video`
   - Ensure consistent character appearance across all videos

2. **Video Download/Export**
   - Add download button per video card
   - Bulk download all videos as ZIP

3. **Retry Failed Videos**
   - Add retry button on error cards
   - Re-trigger single video generation

4. **Video Composition**
   - Stitch all generated videos into single final video
   - Add transitions between scenes

### Files Modified

- `frontend/src/app/quick-gen-page/page.tsx` - Video generation logic and UI
- `.devdocs/v2/tasklist.md` - Task tracking
- `.devdocs/v2/impl-notes.md` - This section

---

## v5 - Dual Storage Backend Support (Local/S3)

### Implementation Summary

Added automatic detection of video URL types to support both local filesystem and S3 cloud storage backends seamlessly.

### Key Changes

1. **URL Resolution Helper Function**
   ```typescript
   const resolveVideoUrl = (videoUrl: string): string => {
     if (videoUrl.startsWith('http://') || videoUrl.startsWith('https://')) {
       // Absolute URL (S3 presigned URL) - use directly
       return videoUrl
     }
     // Relative URL (local backend) - prepend API_URL
     return `${API_URL}${videoUrl}`
   }
   ```

2. **Automatic Backend Detection**
   - Frontend checks if `video_url` from `generate_video` response is absolute or relative
   - SERVE_FROM_CLOUD=true: Backend returns S3 presigned URLs (https://...)
   - SERVE_FROM_CLOUD=false: Backend returns relative paths (/api/mv/get_video/{uuid})
   - No backend changes required - frontend handles both cases

3. **Video Player Integration**
   - Uses resolved URL directly in `<video src={videoUrl}>`
   - Works with both S3 presigned URLs and local backend proxied files
   - No additional API calls needed for S3 mode

### How It Works

**S3 Mode (SERVE_FROM_CLOUD=true):**
```
generate_video response: { video_url: "https://bucket.s3.amazonaws.com/...?AWSAccessKeyId=...&Signature=...&Expires=..." }
↓
resolveVideoUrl detects http/https prefix
↓
Uses URL directly in video player
↓
Browser loads video directly from S3
```

**Local Mode (SERVE_FROM_CLOUD=false):**
```
generate_video response: { video_url: "/api/mv/get_video/uuid-here" }
↓
resolveVideoUrl detects relative path
↓
Prepends API_URL: "http://localhost:8000/api/mv/get_video/uuid-here"
↓
Browser loads video through backend proxy
```

### Benefits

1. **No Backend Changes** - Frontend adapts to whatever URL format the backend provides
2. **Seamless Switching** - Works automatically when backend switches between modes
3. **Efficient S3 Loading** - Videos load directly from S3 without backend proxying
4. **Backward Compatible** - Local mode continues to work as before

### Files Modified

- `frontend/src/app/quick-gen-page/page.tsx` - Added `resolveVideoUrl()` helper function
- `.devdocs/v2/tasklist.md` - v5 task tracking
- `.devdocs/v2/impl-notes.md` - This section

---

## v6 - Video Stitching Endpoint

### Implementation Summary

Added `/api/mv/stitch-videos` endpoint that merges multiple video clips into a single video using MoviePy. Supports both local filesystem and S3 storage backends.

### Key Features

1. **MoviePy Integration**
   - Uses `VideoFileClip` and `concatenate_videoclips` for merging
   - Outputs with libx264 codec and AAC audio
   - Clean resource management with proper clip cleanup

2. **Dual Storage Backend Support**
   - SERVE_FROM_CLOUD=false: Reads from local filesystem, writes locally
   - SERVE_FROM_CLOUD=true: Downloads from S3, merges locally, uploads to S3
   - Returns appropriate URL (relative path or S3 presigned URL)

3. **Error Handling**
   - 400: Empty video_ids list or invalid UUID format
   - 404: Any video not found (fails entire operation)
   - 500: MoviePy processing errors

4. **Debug Logging**
   - Logs request with video IDs
   - Logs storage mode (local vs S3)
   - Logs S3 downloads (when applicable)
   - Logs merge start/completion with timing
   - Logs cleanup of temp files

### Architecture

**Request Flow:**
```
POST /api/mv/stitch-videos
  ↓
Validate video_ids (non-empty, valid UUIDs)
  ↓
Retrieve videos (local path lookup or S3 download)
  ↓
Merge with MoviePy
  ↓
Save to local filesystem
  ↓
Upload to S3 (if configured)
  ↓
Return response with video_id, video_url, metadata
```

**Storage Mode Detection:**
```python
if settings.SERVE_FROM_CLOUD and settings.STORAGE_BUCKET:
    # S3 mode: download → merge → upload
else:
    # Local mode: direct file access
```

### API Usage

**Request:**
```json
POST /api/mv/stitch-videos
{
  "video_ids": [
    "uuid-1",
    "uuid-2",
    "uuid-3"
  ]
}
```

**Response:**
```json
{
  "video_id": "new-uuid",
  "video_path": "/path/to/stitched/video.mp4",
  "video_url": "https://s3.../video.mp4" or "/api/mv/get_video/new-uuid",
  "metadata": {
    "input_video_ids": ["uuid-1", "uuid-2", "uuid-3"],
    "num_videos_stitched": 3,
    "merge_time_seconds": 45.2,
    "total_processing_time_seconds": 120.5,
    "generation_timestamp": "2025-11-17T...",
    "storage_backend": "s3" or "local",
    "cloud_urls": {...}  // if S3
  }
}
```

### Limitations

1. **No Transitions** - Videos are concatenated directly without crossfades or effects
2. **Synchronous Processing** - Can take 30-300+ seconds for multiple large videos
3. **All-or-Nothing** - If any video is missing, entire operation fails
4. **Temporary Storage** - S3 mode downloads all videos to temp directory before merging

### Files Created/Modified

- `backend/mv/video_stitcher.py` - Core stitching logic (NEW)
- `backend/routers/mv.py` - Added `/stitch-videos` endpoint
- `backend/mv/debug.py` - Added stitch-specific logging functions
- `backend/requirements.txt` - Added moviepy==2.0.0
- `.devdocs/v2/tasklist.md` - v6 task tracking
- `.devdocs/v2/impl-notes.md` - This section

### Dependencies Added

- `moviepy==2.0.0` - Video processing and concatenation

### Future Improvements

1. **Add Transitions** - Crossfades, cuts, or other transition effects
2. **Progress Tracking** - Stream progress updates for long operations
3. **Retry Failed Downloads** - Retry S3 downloads on transient failures
4. **Partial Success** - Skip missing videos with warning instead of failing
5. **Audio Normalization** - Normalize audio levels across clips
6. **Video Resolution Matching** - Handle videos with different resolutions
