# Implementation Notes - v1

## `/api/mv/create_scenes` Endpoint

### Current Limitations

#### 1. Synchronous Processing
**Current Implementation**: The endpoint processes requests synchronously, blocking until Gemini generates all scene descriptions.

**Limitation**: For complex prompts or high number of scenes, this could result in long response times (potentially 30+ seconds), which may cause:
- Client timeouts
- Poor user experience
- Resource blocking on the server

**Future Improvement**: Convert to asynchronous job-based processing:
- Accept request and return job ID immediately (202 Accepted)
- Queue scene generation to Redis for worker processing
- Follow same pattern as `/api/generate` endpoint
- Allow progress tracking via WebSocket or polling
- Enable parallel processing of multiple requests

---

#### 2. File-Based Storage
**Current Implementation**: Generated scenes are stored as files (`scenes.json`, `scenes.md`) in the filesystem under `backend/mv/outputs/`.

**Limitation**:
- No database persistence means limited queryability
- No association with user accounts or projects
- Difficult to track generation history
- No metadata indexing or search capabilities
- File cleanup/management becomes manual

**Future Improvement**: Implement database persistence:
- Create `Scene` and `SceneGeneration` database models
- Store scene data in PostgreSQL/SQLite
- Link to user sessions/projects
- Enable versioning and history tracking
- Add search and filtering capabilities
- Implement proper data lifecycle management

---

### Architecture Decisions

1. **Module namespace**: Using `backend/mv/` (music video) to namespace all related functionality
2. **Config management**: YAML files in `backend/mv/configs/` loaded at startup for maintainability
3. **Debug mode**: Environment variable `MV_DEBUG_MODE` for module-wide debug logging
4. **API structure**: Following REST conventions with `/api/mv/` prefix for music video operations

---

### Dependencies Added

- `google-genai`: Google's Generative AI SDK for Gemini model access
- `GEMINI_API_KEY`: Required for scene generation via Gemini 2.5 Pro

---

### Testing Considerations

- Mock Gemini API responses for unit tests to avoid API costs
- Test debug mode output separately
- Validate JSON schema compliance
- Test default parameter injection from config files

---

# Implementation Notes - v2

## `/api/mv/generate_character_reference` Endpoint

### Current Limitations

#### 1. Synchronous Processing
**Current Implementation**: The endpoint processes requests synchronously, blocking until Replicate returns the generated image.

**Limitation**: Image generation via Replicate API typically takes 10-60+ seconds, which may cause:
- Client timeouts (especially with default 30s timeouts)
- Poor user experience with long wait times
- Resource blocking on the server
- Limited scalability for concurrent requests

**Future Improvement**: Convert to asynchronous job-based processing:
- Accept request and return job ID immediately (202 Accepted)
- Queue image generation to Redis for worker processing
- Follow same pattern as `/api/generate` endpoint
- Allow progress tracking via WebSocket or polling
- Enable parallel processing of multiple image requests

---

#### 2. File-Based Storage
**Current Implementation**: Generated images are stored in the filesystem under `backend/mv/outputs/character_reference/` with timestamp-based filenames.

**Limitation**:
- No database persistence means limited queryability
- No association with user accounts or projects
- No metadata indexing (cannot search by character description, params, etc.)
- Difficult to track generation history across sessions
- File cleanup/management becomes manual
- Disk space consumption grows without pruning strategy

**Future Improvement**: Implement database persistence:
- Create `CharacterReference` database model
- Store image metadata in PostgreSQL/SQLite
- Store actual images in object storage (S3, GCS) or keep filesystem with DB references
- Link to user sessions/projects
- Enable versioning and history tracking
- Add search and filtering capabilities
- Implement automatic cleanup policies

---

#### 3. Large Response Payload
**Current Implementation**: The entire image is returned as base64-encoded string in the JSON response.

**Limitation**:
- PNG images at 1024x1024 can be 1-3MB, resulting in 1.3-4MB base64 strings
- Large response payloads increase network transfer time
- May hit API gateway size limits in production
- Memory intensive for both server and client

**Future Improvement**:
- Return only a URL/reference to the stored image
- Implement separate image retrieval endpoint
- Support presigned URLs for cloud storage
- Add image compression/optimization options
- Support progressive loading for large images

---

#### 4. Replicate API Costs and Rate Limits
**Current Implementation**: Direct API calls to Replicate with Google Imagen 4.

**Limitation**:
- Replicate charges per image generation (~$0.01-0.05 per image)
- Rate limits may apply under heavy usage
- No request throttling or cost controls
- API token exposed in environment variable

**Future Improvement**:
- Implement request throttling/rate limiting per user
- Add cost tracking and budgeting
- Cache common character references
- Consider alternative image generation services
- Add usage quotas per project/user

---

### Architecture Decisions

1. **Module namespace**: Using existing `backend/mv/` (music video) namespace for consistency
2. **Config management**: YAML files (`image_params.yaml`, `image_prompts.yaml`) loaded at startup
3. **Debug mode**: Reuses `MV_DEBUG_MODE` for module-wide debug logging
4. **API structure**: Following REST conventions with `/api/mv/` prefix
5. **Timestamp filenames**: Using `character_ref_YYYYMMDD_HHMMSS.ext` pattern for unique, sortable files
6. **Dual storage**: Both file system (for persistence) and base64 return (for immediate use)
7. **API token fallback**: Supports both `REPLICATE_API_TOKEN` and `REPLICATE_API_KEY` for flexibility

---

### Dependencies Added

- `replicate`: Replicate Python SDK for API access (already in requirements.txt)
- `REPLICATE_API_TOKEN`: Required for image generation via Replicate API

---

### Testing Considerations

- Mock Replicate API responses for unit tests to avoid API costs and delays
- Test timestamp filename generation format
- Validate base64 encoding correctness
- Test default parameter injection from config files
- Verify file write operations
- Test with both single output and list outputs from Replicate
- Ensure MV_DEBUG_MODE logging works for image generation

---

# Implementation Notes - v3

## `/api/mv/generate_video` Endpoint

### Current Limitations

#### 1. Synchronous Processing with Long Response Times
**Current Implementation**: The endpoint processes requests synchronously, blocking until Replicate/Gemini returns the generated video.

**Limitation**: Video generation typically takes **20-400+ seconds** (significantly longer than image generation), which causes:
- Very long HTTP request timeouts required (420+ seconds)
- Client connection may drop during long waits
- No progress feedback to user during generation
- Server resources blocked for extended periods
- Poor UX when waiting for multiple concurrent scene generations

**Future Improvement**: Convert to asynchronous job-based processing:
- Accept request and return job ID immediately (202 Accepted)
- Queue video generation to Redis for worker processing
- Follow same pattern as `/api/generate` endpoint
- Allow progress tracking via WebSocket or polling
- Enable parallel processing with worker pool
- Support cancellation of in-progress jobs

---

#### 2. UUID-Based File Storage (No Database)
**Current Implementation**: Generated videos are stored with UUID-based filenames in the filesystem under `backend/mv/outputs/videos/`.

**Limitation**:
- No database persistence means limited queryability
- No association with user accounts or projects
- Videos accessible by anyone who knows the UUID (no auth)
- No expiration/cleanup policy (disk space grows indefinitely)
- Cannot search by prompt, parameters, or metadata
- No tracking of generation history
- No batch operations across videos

**Future Improvement**: Implement database persistence:
- Create `Video` database model linking UUID to metadata
- Store video metadata in PostgreSQL/SQLite
- Link to user sessions/projects
- Implement TTL-based cleanup policies
- Add search and filtering capabilities
- Store generation parameters for reproducibility
- Enable video management (list, delete, rename)

---

#### 3. No Authentication
**Current Implementation**: Videos are accessible to anyone with the UUID via `/api/mv/get_video/{video_id}`.

**Limitation**:
- Security through obscurity only (UUID is hard to guess)
- No user ownership tracking
- Cannot restrict access to specific users
- No audit trail of who accessed videos
- Potential for unauthorized access if UUID is leaked

**Future Improvement**:
- Implement user authentication (JWT, session-based)
- Link videos to authenticated users
- Add access control lists (ACL)
- Generate signed/expiring URLs for sharing
- Audit logging for compliance
- Rate limiting per user

---

#### 4. Base64 Reference Images (Large Payloads)
**Current Implementation**: Reference images are passed as base64-encoded strings in the request body.

**Limitation**:
- Large request payloads (1-4MB+ for base64 images)
- Increased memory usage during request processing
- Slower network transfer times
- May hit API gateway size limits in production
- Not integrated with character reference storage (v2 endpoint)

**Future Improvement**:
- Allow reference to stored character reference by ID (from v2 endpoint)
- Support pre-uploaded images via separate endpoint
- Implement image URL references (presigned URLs)
- Add image compression/optimization
- Cache frequently used reference images

---

#### 5. No Progress Updates
**Current Implementation**: Client blocks and waits for the entire generation to complete.

**Limitation**:
- User has no visibility into generation progress
- Cannot estimate completion time
- No indication if generation is stuck or processing
- Poor user experience for long waits

**Future Improvement**:
- WebSocket connection for real-time status updates
- Server-Sent Events (SSE) for progress streaming
- Polling endpoint for job status
- Estimated time remaining calculation
- Step-by-step progress (e.g., "Generating frame 50/200")

---

#### 6. Client-Side Video Merging
**Current Implementation**: Each call generates a single video clip. Clients must handle merging multiple scene videos themselves.

**Limitation**:
- Frontend must implement video merging logic
- Browser-based video editing can be slow/memory intensive
- No server-side video processing (transitions, effects)
- Inconsistent results based on client capabilities

**Future Improvement**:
- Add `/api/mv/merge_videos` endpoint
- Server-side merging using MoviePy/FFmpeg
- Support transitions between clips
- Audio mixing and normalization
- Final video optimization and compression

---

#### 7. No Rate Limiting or Cost Controls
**Current Implementation**: No throttling on video generation requests.

**Limitation**:
- Each video generation costs API credits (~$0.10-1.00+)
- No protection against accidental overuse
- Potential for API cost runaway
- No usage quotas per user/project
- Could exhaust Replicate rate limits under load

**Future Improvement**:
- Implement per-user rate limiting
- Add cost tracking and budgeting
- Usage quotas per project/user
- Credit system for video generations
- Admin dashboard for monitoring costs

---

#### 8. Limited Gemini Backend Support
**Current Implementation**: Gemini backend is basic and doesn't support all parameters (duration, audio, reference images).

**Limitation**:
- Feature parity not achieved between backends
- Users may not understand which features work with which backend
- Gemini polling implementation may not handle all edge cases
- No automatic failover between backends

**Future Improvement**:
- Document feature matrix clearly
- Implement automatic backend selection based on features needed
- Add failover logic (try Replicate, fall back to Gemini)
- Improve Gemini backend to support more parameters
- Add backend health monitoring

---

### Architecture Decisions

1. **Backend factory pattern**: Clean abstraction for switching between video generation services
2. **UUID-based video IDs**: Unique, URL-safe identifiers for video retrieval
3. **Dual endpoint pattern**: Separate generation and retrieval endpoints for flexibility
4. **Config reuse**: Video parameters stored in same YAML file as image parameters
5. **Debug mode integration**: Reuses `MV_DEBUG_MODE` for consistency across MV module
6. **FileResponse streaming**: Efficient video delivery without loading entire file into memory
7. **Proof-of-concept focus**: Prioritized working implementation over production-ready features

---

### Dependencies Added

- `replicate`: Already present from v2, used for Veo 3.1 video generation
- `google-genai`: Already present from v1, used for Gemini video generation
- `uuid`: Standard library, for unique video identifiers

---

### Testing Considerations

- Mock Replicate and Gemini API responses for unit tests
- Test UUID generation and format validation
- Verify backend factory correctly routes requests
- Test base64 image decoding for reference images
- Validate processing time tracking
- Test video file serving (FileResponse)
- Test info endpoint metadata accuracy
- Verify error handling for various failure modes
- Ensure MV_DEBUG_MODE logging covers all stages

---

# Implementation Notes - v4

## Mock Video Generation Mode

### Purpose

The `MOCK_VID_GENS` environment variable enables a mock mode for video generation endpoints to facilitate frontend development and testing without:
- Consuming Replicate/Gemini API credits
- Waiting 20-400+ seconds for real video generation
- Requiring external API connectivity

### How It Works

When `MOCK_VID_GENS=true`:

1. **Generate Video Endpoint** (`/api/mv/generate_video`):
   - Bypasses real backend calls (Replicate/Gemini)
   - Randomly selects from pre-staged mock videos in `backend/mv/outputs/mock/`
   - Simulates 5-10 second processing delay (random per request)
   - Returns proper response structure with `is_mock: true` in metadata
   - Generates real UUID for video_id

2. **Get Video Endpoint** (`/api/mv/get_video/{video_id}`):
   - Serves videos from mock directory instead of real outputs
   - No additional simulated delay (instant serving)
   - Returns first available mock video for any UUID requested

3. **Get Video Info Endpoint** (`/api/mv/get_video/{video_id}/info`):
   - Returns metadata from mock directory
   - Includes `is_mock: true` in response

### Setup Instructions

1. Enable mock mode:
   ```bash
   # In backend/.env
   MOCK_VID_GENS=true
   ```

2. Add mock videos to `backend/mv/outputs/mock/`:
   - At least 1 MP4 file required
   - Can be any resolution/duration
   - Suggested: Use small file sizes (5-20MB)
   - See `README.txt` in that directory for details

3. Create test videos using ffmpeg:
   ```bash
   # Generate 5-second test pattern video
   ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 \
     -c:v libx264 mock_video_1.mp4
   ```

### Mock Response Structure

```json
{
  "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "video_path": "/path/to/mock/mock_video_1.mp4",
  "video_url": "/api/mv/get_video/a1b2c3d4...",
  "metadata": {
    "prompt": "Original prompt...",
    "backend_used": "mock",
    "model_used": "mock",
    "is_mock": true,
    "mock_video_source": "mock_video_1.mp4",
    "parameters_used": { ... },
    "generation_timestamp": "2025-11-16T10:30:25Z",
    "processing_time_seconds": 7.34  // Actual simulated delay
  }
}
```

### Current Limitations

1. **Manual video setup**: Developers must add their own mock MP4 files (gitignored)
2. **No parameter variation**: Returns same videos regardless of prompt/parameters
3. **Limited video variety**: Only as many mock responses as manually added videos
4. **No reference image validation**: Mock mode ignores reference images
5. **UUID-to-file mapping**: All UUIDs return the same (first) mock video in get_video
6. **No prompt-based selection**: Cannot simulate different videos for different prompts

### Architecture Decisions

1. **Environment variable control**: Simple toggle via `MOCK_VID_GENS` boolean
2. **Early return pattern**: Check mock mode at start of `generate_video()` function
3. **Simulated delay on generation**: Mimics real API behavior (5-10s vs 20-400s)
4. **No delay on serving**: Real video serving is instant, mock matches this
5. **Metadata transparency**: `is_mock: true` clearly indicates mock response
6. **Gitignored mock videos**: Each developer manages their own mock files

### Debug Logging

When `MV_DEBUG_MODE=true`, mock mode logs:
- `mock_mode_enabled`: When mock mode is activated
- `mock_video_selected`: Which mock video was randomly chosen
- `mock_delay`: The simulated processing delay

### Testing Considerations

- 13 unit tests cover mock functionality
- Tests verify delay range (5-10 seconds)
- Tests validate metadata structure includes mock indicators
- Tests ensure proper toggle between mock and real modes
- Tests handle missing mock videos gracefully
