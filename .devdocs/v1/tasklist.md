# Task List: `/api/mv/create_scenes` Endpoint (v1)

## Overview
Port the `generate_scenes` functionality from `.ref-pipeline/src/main.py` into the backend server as a new endpoint for music video scene generation.

---

## Tasks

### 1. Setup Configuration Infrastructure
- [ ] Create `backend/mv/` directory structure
- [ ] Create `backend/mv/configs/` directory
- [ ] Create `backend/mv/configs/parameters.yaml` with default scene generation parameters
- [ ] Create `backend/mv/configs/scene_prompts.yaml` with prompt templates
- [ ] Add YAML loading utility to load configs at backend startup

### 2. Environment Configuration
- [ ] Add `GEMINI_API_KEY` to `backend/.env`
- [ ] Add `GEMINI_API_KEY` to `backend/config.py` Settings class
- [ ] Add `MV_DEBUG_MODE` environment variable to `backend/.env`
- [ ] Add `MV_DEBUG_MODE` to `backend/config.py` Settings class

### 3. Core Scene Generation Module
- [ ] Create `backend/mv/__init__.py`
- [ ] Create `backend/mv/scene_generator.py` with:
  - [ ] Pydantic models: `Scene`, `SceneResponse`, `CreateScenesRequest`
  - [ ] `generate_scenes()` function ported from reference pipeline
  - [ ] Integration with `google-genai` client
  - [ ] Default parameter handling (load from YAML configs)
  - [ ] Debug mode logging support

### 4. Debug Mode Implementation
- [ ] Create debug logging utilities in `backend/mv/debug.py`
- [ ] Log request arguments received
- [ ] Log default arguments applied
- [ ] Log config parameters loaded
- [ ] Log full prompts sent to Gemini
- [ ] Conditional logging based on `MV_DEBUG_MODE`

### 5. API Endpoint Router
- [ ] Create `backend/routers/mv.py` router file
- [ ] Implement `POST /api/mv/create_scenes` endpoint
- [ ] Define request schema (JSON body with required and optional fields):
  - Required: `idea`, `character_description`
  - Optional with defaults: `character_characteristics`, `number_of_scenes`, `video_type`, `video_characteristics`, `camera_angle`, `output_dir`
- [ ] Return JSON response with generated scenes
- [ ] Add error handling for:
  - Missing Gemini API key
  - Gemini API errors
  - Invalid request parameters

### 6. Backend Integration
- [ ] Import and include `mv` router in `backend/main.py`
- [ ] Update `lifespan` function to load MV configs at startup
- [ ] Store loaded configs in app state or module-level variables

### 7. Package Dependencies
- [ ] Add `google-genai` to backend dependencies (check pyproject.toml/requirements.txt)
- [ ] Add `pyyaml` if not already present
- [ ] Run `pnpm install` or equivalent for Python packages

### 8. File-Based Storage
- [ ] Create output directory for scene data (e.g., `backend/mv/outputs/`)
- [ ] Save `scenes.json` and `scenes.md` to output directory
- [ ] Include file paths in response

### 9. Documentation
- [ ] Create `backend/.devdocs/impl-notes.md` with:
  - [ ] Current limitations (sync processing, file-based storage)
  - [ ] Future improvement plans (async job queue, database persistence)
- [ ] Add endpoint documentation in router docstrings
- [ ] Update root endpoint info in `backend/main.py`

### 10. Testing
- [ ] Create basic test file `backend/mv/test_scene_generator.py`
- [ ] Test endpoint with sample requests
- [ ] Verify debug mode output
- [ ] Validate JSON response structure

---

## Request Schema (Suggested)

```json
{
  "idea": "string (required) - The core concept or topic of the video",
  "character_description": "string (required) - Visual description of main character",
  "character_characteristics": "string (optional) - Personality traits, default: from config",
  "number_of_scenes": "int (optional) - Number of scenes to generate, default: from config",
  "video_type": "string (optional) - Type of video, default: from config",
  "video_characteristics": "string (optional) - Visual style, default: from config",
  "camera_angle": "string (optional) - Camera perspective, default: from config",
  "output_dir": "string (optional) - Directory to save scenes, default: auto-generated"
}
```

## Response Schema (Suggested)

```json
{
  "scenes": [
    {
      "description": "string - Scene description for video generation",
      "negative_description": "string - Elements to exclude"
    }
  ],
  "output_files": {
    "json": "path to scenes.json",
    "markdown": "path to scenes.md"
  },
  "metadata": {
    "idea": "string",
    "number_of_scenes": "int",
    "parameters_used": {}
  }
}
```

---

## Dependencies to Add

- `google-genai` - Google's Generative AI Python SDK
- `pyyaml` - YAML parsing (likely already present)
- `pydantic` - Data validation (likely already present)

## Environment Variables to Add

```bash
# Google AI / Gemini
GEMINI_API_KEY=your_key_here

# Music Video Module Debug Mode
MV_DEBUG_MODE=false
```

# v2 Feature: Generate Character Reference Image Endpoint

## Overview
Port `generate_character_reference_image` from `.ref-pipeline/src/image_generator.py` to `/api/mv/generate_character_reference` endpoint.

---

## Task List

### 1. Environment & Configuration Setup
- [ ] **1.1** Add `REPLICATE_API_TOKEN` to `backend/.env`
- [ ] **1.2** Add `REPLICATE_API_TOKEN` to `backend/config.py` settings
- [ ] **1.3** Create/update `backend/mv/configs/image_params.yaml` with default parameters:
  - `aspect_ratio: "1:1"`
  - `safety_filter_level: "block_medium_and_above"`
  - `person_generation: "allow_adult"`
  - `output_format: "png"`
  - `model: "google/imagen-4"`
- [ ] **1.4** Create/update `backend/mv/configs/image_prompts.yaml` with character reference prompt template:
  - `character_reference_prompt: "A full-body character reference image of {character_description}. Clear, well-lit, neutral background, professional quality, detailed features, front-facing view."`

### 2. Dependencies
- [ ] **2.1** Use Context7 MCP to get latest Replicate Python SDK documentation
- [ ] **2.2** Add `replicate` package to `backend/requirements.txt`
- [ ] **2.3** Install package with `uv pip install replicate`

### 3. Core Module Implementation
- [ ] **3.1** Create `backend/mv/image_generator.py` with:
  - Pydantic models:
    - `GenerateCharacterReferenceRequest` (character_description required, optional: aspect_ratio, safety_filter_level, person_generation, output_format, negative_prompt, seed)
    - `GenerateCharacterReferenceResponse` (image_base64, output_file, metadata)
  - Config loading functions (load from image_params.yaml and image_prompts.yaml)
  - `generate_character_reference_image()` function:
    - Validate `REPLICATE_API_TOKEN` is set
    - Apply defaults from YAML config
    - Format prompt from template
    - Call Replicate API with `google/imagen-4`
    - Save image to `backend/mv/outputs/character_reference/` with timestamp filename (e.g., `character_ref_20251115_143025.png`)
    - Return base64-encoded image data along with file path
- [ ] **3.2** Update `backend/mv/debug.py` to add image generation specific debug logging:
  - `log_image_request_args()`
  - `log_image_defaults_applied()`
  - `log_image_prompt()`
  - `log_replicate_response()`

### 4. Router Integration
- [ ] **4.1** Add endpoint to `backend/routers/mv.py`:
  - `POST /api/mv/generate_character_reference`
  - Request validation (character_description required)
  - Response with base64 image, file path, and metadata
  - Error handling (400 for validation, 500 for API/config errors)
  - OpenAPI documentation with examples

### 5. Startup Integration
- [ ] **5.1** Update `backend/main.py` lifespan to load image configs at startup (if not already handled by existing `load_configs()`)
- [ ] **5.2** Update root endpoint to include new endpoint in available endpoints list

### 6. Testing
- [ ] **6.1** Create `backend/mv/test_image_generator.py` with unit tests:
  - Model validation tests
  - Config loading tests
  - Missing API key error test
  - Successful generation mock test
  - Timestamp filename format test
- [ ] **6.2** Run tests with `uv run pytest backend/mv/test_image_generator.py -v`
- [ ] **6.3** Create `/.devdocs/scripts/test_generate_character_reference.sh` curl script

### 7. Documentation
- [ ] **7.1** Create `.devdocs/v2/impl-notes.md` documenting:
  - Synchronous processing limitation (future: async with job queue)
  - File storage pattern (timestamp-based)
  - Base64 response size considerations
  - Replicate API rate limits and costs

### 8. Git & Cleanup
- [ ] **8.1** Ensure `backend/mv/outputs/character_reference/` is covered by existing gitignore
- [ ] **8.2** Verify no sensitive data in committed configs

---

## API Contract

### Request
```json
POST /api/mv/generate_character_reference
{
  "character_description": "Silver metallic humanoid robot with a red shield",
  "aspect_ratio": "1:1",           // optional, default from config
  "safety_filter_level": "block_medium_and_above",  // optional
  "person_generation": "allow_adult",  // optional
  "output_format": "png",          // optional
  "negative_prompt": "blurry, low quality",  // optional
  "seed": 12345                    // optional, for reproducibility
}
```

### Response
```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "output_file": "/path/to/character_ref_20251115_143025.png",
  "metadata": {
    "character_description": "Silver metallic humanoid robot...",
    "model_used": "google/imagen-4",
    "parameters_used": {
      "aspect_ratio": "1:1",
      "safety_filter_level": "block_medium_and_above",
      ...
    },
    "generation_timestamp": "2025-11-15T14:30:25Z"
  }
}
```

# v3 Feature: Generate Video Endpoint

## Overview
Port `generate_video` from `.ref-pipeline/src/main.py` and video backends from `.ref-pipeline/src/video_backends/` to `/api/mv/generate_video` endpoint for single scene video generation. Clients will call this endpoint multiple times to generate individual scene clips for a music video.

**Key Design Decisions:**
- Synchronous processing (note: 20-400 second response times, multiple concurrent requests expected)
- Default to Replicate backend (Gemini backend available but basic)
- Single video per request (not multi-scene orchestration)
- Base64 encoded reference images in request
- Video served via separate endpoint with UUID-based filenames

---

## Task List

### 1. Environment & Configuration Setup
- [ ] **1.1** Verify `REPLICATE_API_TOKEN` exists in `backend/.env` (from v2)
- [ ] **1.2** Verify `REPLICATE_API_TOKEN` exists in `backend/config.py` (from v2)
- [ ] **1.3** Add `GEMINI_API_KEY` validation for Gemini backend (if not already)
- [ ] **1.4** Update `backend/mv/configs/image_params.yaml` with video defaults:
  - `video_model: "google/veo-3.1"`
  - `video_aspect_ratio: "16:9"`
  - `video_duration: 8`
  - `video_generate_audio: true`
  - `video_person_generation: "allow_all"`

### 2. Core Video Generator Module
- [ ] **2.1** Create `backend/mv/video_generator.py` with:
  - Pydantic models:
    - `GenerateVideoRequest`:
      - Required: `prompt`
      - Optional: `negative_prompt`, `aspect_ratio`, `output_format`, `seed`, `duration`, `generate_audio`, `reference_image_base64`, `video_rules_template`, `backend` (default: "replicate")
    - `GenerateVideoResponse`:
      - `video_id` (UUID for retrieval)
      - `video_path` (filesystem path)
      - `video_url` (URL path to retrieve video)
      - `metadata` (backend used, parameters, generation timestamp, duration)
  - Config loading functions (load video params from existing YAML)
  - `generate_video()` main function:
    - Validate API token for selected backend
    - Apply defaults from YAML config
    - Generate UUID-based filename
    - Call appropriate backend
    - Save video to `backend/mv/outputs/videos/` with UUID filename
    - Return video ID and metadata

### 3. Video Backend Implementation
- [ ] **3.1** Create `backend/mv/video_backends/__init__.py` with backend factory:
  - `get_video_backend(backend_name: str)` factory function
  - Support "replicate" and "gemini" backends
  - Default to "replicate"

- [ ] **3.2** Create `backend/mv/video_backends/replicate_backend.py`:
  - `generate_video_replicate()` function
  - Parameters: prompt, negative_prompt, aspect_ratio, duration, generate_audio, seed, reference_image_base64
  - Handle base64 reference image decoding to temp file
  - Call `replicate.run("google/veo-3.1", ...)`
  - Apply video rules template to prompt
  - Return video binary data
  - Clean up temp files

- [ ] **3.3** Create `backend/mv/video_backends/gemini_backend.py`:
  - `generate_video_gemini()` function (basic implementation)
  - Parameters: prompt, negative_prompt, aspect_ratio (limited support)
  - Initialize `genai.Client()`
  - Call `client.models.generate_videos()` with polling
  - Return video binary data
  - Note: Advanced parameters not prioritized

### 4. Debug Logging
- [ ] **4.1** Update `backend/mv/debug.py` to add video-specific logging:
  - `log_video_request_args()` - log incoming request parameters
  - `log_video_defaults_applied()` - log applied defaults
  - `log_video_prompt()` - log full prompt with rules applied
  - `log_video_backend_selected()` - log which backend is used
  - `log_video_generation_result()` - log generation outcome and timing

### 5. Router Integration - Generate Video
- [ ] **5.1** Add endpoint to `backend/routers/mv.py`:
  - `POST /api/mv/generate_video`
  - Request validation
  - Response with video_id, video_path, video_url, metadata
  - Error handling:
    - 400 for validation errors
    - 500 for API errors (with error codes from video service)
    - 503 for backend unavailable
  - OpenAPI documentation with examples
  - Note: Long timeout needed (420+ seconds for 400s max generation)

### 6. Router Integration - Get Video
- [ ] **6.1** Add endpoint to `backend/routers/mv.py`:
  - `GET /api/mv/get_video/{video_id}`
  - Serve video file directly (streaming bytes)
  - Return 404 if video_id not found
  - Set appropriate Content-Type header (video/mp4)
  - Support HEAD requests for metadata (size, exists)

- [ ] **6.2** Add endpoint to `backend/routers/mv.py`:
  - `GET /api/mv/get_video/{video_id}/info`
  - Return JSON metadata about the video (size, creation time, etc.)
  - Alternative to downloading full video

### 7. Startup Integration
- [ ] **7.1** Update `backend/main.py` lifespan to load video configs at startup
- [ ] **7.2** Create output directories: `backend/mv/outputs/videos/`
- [ ] **7.3** Update root endpoint to include new endpoints:
  - `mv_generate_video`: `/api/mv/generate_video`
  - `mv_get_video`: `/api/mv/get_video/{video_id}`

### 8. Error Handling & Status
- [ ] **8.1** Define error response schema for video generation failures:
  - Status code from video service
  - Error message/description
  - Backend used
  - Timestamp
- [ ] **8.2** Handle timeout scenarios gracefully (20-400s processing time)
- [ ] **8.3** Return meaningful error codes for:
  - Invalid prompt/parameters
  - Backend service errors
  - Rate limiting
  - Content policy violations

### 9. Testing
- [ ] **9.1** Create `backend/mv/test_video_generator.py` with unit tests:
  - Model validation tests
  - Config loading tests
  - Backend factory tests
  - Missing API key error tests
  - Video ID generation tests (UUID format)
- [ ] **9.2** Create `backend/mv/video_backends/test_backends.py`:
  - Mock Replicate API response tests
  - Mock Gemini API response tests
  - Base64 image decoding tests
  - Error handling tests
- [ ] **9.3** Create `/.devdocs/scripts/test_generate_video.sh` curl script
- [ ] **9.4** Run tests with `uv run pytest backend/mv/test_video_generator.py -v`

### 10. Documentation
- [ ] **10.1** Update `.devdocs/v1/impl-notes.md` with v3 section documenting:
  - Synchronous processing limitation (20-400s response times)
  - Multiple concurrent requests pattern from client
  - UUID-based video storage (no database)
  - No authentication (marked for future)
  - File cleanup not automated
  - Proof-of-concept video serving approach
  - Base64 reference image limitation (future: integrate with character reference storage)

- [ ] **10.2** Create/update `.devdocs/v1/client-impl-notes.md` with:
  - How to call `/api/mv/generate_video` for each scene
  - Expected response times (20-400s per video)
  - How to retrieve videos via `/api/mv/get_video/{video_id}`
  - Error handling patterns
  - Example workflow for generating multi-scene music video
  - Request/response examples
  - Video URL construction

### 11. Git & Cleanup
- [ ] **11.1** Ensure `backend/mv/outputs/videos/` is covered by gitignore
- [ ] **11.2** Verify no sensitive data in committed configs
- [ ] **11.3** Clean up any temporary files from base64 decoding

---

## API Contract

### Generate Video Request
```json
POST /api/mv/generate_video
{
  "prompt": "A robot walks through a futuristic city at sunset",  // required
  "negative_prompt": "blurry, low quality, distorted",           // optional
  "aspect_ratio": "16:9",                                         // optional, default from config
  "duration": 8,                                                  // optional, seconds
  "generate_audio": true,                                         // optional, default: true
  "seed": 12345,                                                  // optional, for reproducibility
  "reference_image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",       // optional, base64 encoded image
  "video_rules_template": "Keep it cinematic, no text overlays", // optional, custom rules
  "backend": "replicate"                                          // optional, default: "replicate"
}
```

### Generate Video Response (Success)
```json
{
  "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "video_path": "/home/user/.../backend/mv/outputs/videos/a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp4",
  "video_url": "/api/mv/get_video/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "metadata": {
    "prompt": "A robot walks through a futuristic city at sunset",
    "backend_used": "replicate",
    "model_used": "google/veo-3.1",
    "parameters_used": {
      "aspect_ratio": "16:9",
      "duration": 8,
      "generate_audio": true,
      "seed": 12345
    },
    "generation_timestamp": "2025-11-16T10:30:25Z",
    "processing_time_seconds": 45.7
  }
}
```

### Generate Video Response (Error)
```json
{
  "error": "Video generation failed",
  "error_code": "CONTENT_POLICY_VIOLATION",
  "message": "The prompt violated content safety policies",
  "backend_used": "replicate",
  "timestamp": "2025-11-16T10:30:25Z"
}
```

### Get Video
```
GET /api/mv/get_video/a1b2c3d4-e5f6-7890-abcd-ef1234567890
Content-Type: video/mp4

[binary video data]
```

### Get Video Info
```json
GET /api/mv/get_video/a1b2c3d4-e5f6-7890-abcd-ef1234567890/info
{
  "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "file_size_bytes": 15234567,
  "created_at": "2025-11-16T10:30:25Z",
  "exists": true
}
```

---

## Client Workflow Example

To generate a 4-scene music video, the client would:

1. **Generate scenes** (v1 endpoint):
```bash
POST /api/mv/create_scenes
# Returns 4 scene descriptions
```

2. **Generate character reference** (v2 endpoint):
```bash
POST /api/mv/generate_character_reference
# Returns base64 image of character
```

3. **Generate video for each scene** (v3 endpoint, concurrent requests):
```bash
# Scene 1
POST /api/mv/generate_video
{ "prompt": "Scene 1 description...", "reference_image_base64": "..." }

# Scene 2 (concurrent)
POST /api/mv/generate_video
{ "prompt": "Scene 2 description...", "reference_image_base64": "..." }

# ... etc
```

4. **Retrieve videos**:
```bash
GET /api/mv/get_video/{scene1_video_id}
GET /api/mv/get_video/{scene2_video_id}
# ... etc
```

5. **Client-side video merging** (future: server-side endpoint)

---

## Known Limitations (to document in impl-notes.md)

1. **Synchronous Processing**: 20-400s response times, blocking
2. **No Authentication**: Videos accessible by anyone with UUID
3. **File-based Storage**: No database tracking, manual cleanup needed
4. **Base64 Reference Images**: Large payload size, not integrated with character reference storage
5. **No Job Queue**: Server resources blocked during generation
6. **No Progress Updates**: Client cannot track generation progress
7. **Client-side Merging**: Server doesn't merge multiple scene videos
8. **No Rate Limiting**: Potential for API cost overruns
