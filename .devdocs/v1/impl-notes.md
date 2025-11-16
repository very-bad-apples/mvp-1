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
