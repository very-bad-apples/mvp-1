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
