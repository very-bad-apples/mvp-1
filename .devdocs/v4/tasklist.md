# Task List - Video Generation Backend

## v1: Auto-Delete Local Media Files After S3 Upload

**Goal**: Delete media files from `backend/mv/outputs/*` directories immediately after successful S3 upload to save disk space and prevent accumulation.

**Requirements**:
- Delete files immediately after successful upload
- Keep files locally if upload fails (for retry purposes)
- Do NOT modify existing tempfile cleanup in finally blocks
- Only delete files that were successfully uploaded

---

### Tasks

#### 1. Create Utility Function for Post-Upload Cleanup
**Location**: `backend/services/s3_storage.py`

- [ ] Add `delete_local_file_after_upload(file_path: str) -> None` utility function
  - Takes absolute file path as input
  - Safely deletes file with error handling
  - Logs deletion success/failure
  - Handles edge cases (file doesn't exist, permissions, etc.)

**Implementation notes**:
```python
def delete_local_file_after_upload(file_path: str) -> None:
    """
    Delete local file after successful S3 upload.

    Args:
        file_path: Absolute path to file to delete
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info("local_file_deleted", file_path=file_path)
        else:
            logger.warning("local_file_not_found", file_path=file_path)
    except Exception as e:
        logger.error("failed_to_delete_local_file", file_path=file_path, error=str(e))
```

---

#### 2. Update Video Generator Cleanup
**Location**: `backend/mv/video_generator.py`

- [ ] Find all `storage.upload_file()` calls (around lines 417-434)
- [ ] Add cleanup after each successful upload:
  - Video file deletion after `urls["video"]` upload succeeds
  - Metadata file deletion after `urls["metadata"]` upload succeeds
  - Reference image deletion after `urls["reference_image"]` upload succeeds (if exists)

**Code location**: `backend/mv/video_generator.py:417-434`

**Implementation pattern**:
```python
# After successful upload
urls["video"] = await storage.upload_file(
    str(video_path),
    f"mv/jobs/{video_id}/video.mp4"
)
# Add cleanup
delete_local_file_after_upload(str(video_path))
```

---

#### 3. Update Scene Video Upload Cleanup
**Location**: `backend/routers/mv_projects.py`

- [ ] Find scene video upload in `generate_scene_video_background()` (around lines 347-359)
- [ ] Add cleanup after successful `s3_service.upload_file_from_path()` call
- [ ] Delete `video_path` local file after upload succeeds and before updating scene record

**Code location**: `backend/routers/mv_projects.py:347-359`

---

#### 4. Update Lipsync Upload Cleanup
**Location**: `backend/mv/lipsync.py`

- [ ] Find S3 upload calls in lipsync processing
- [ ] Add cleanup after successful upload
- [ ] Delete local lipsynced video file after S3 upload

**Note**: Need to verify exact location in `lipsync.py`

---

#### 5. Update Compose Worker Cleanup
**Location**: `backend/workers/compose_worker.py`

- [ ] Find final video upload in `process_composition_job()` (around lines 130-134)
- [ ] Add cleanup after successful `s3_service.upload_file_from_path()` call
- [ ] Delete `output_path` (final composed video) after upload succeeds

**Code location**: `backend/workers/compose_worker.py:130-134`

**Note**: Temp directory cleanup already handled by finally block (lines 180-187) - leave as is

---

#### 6. Update Character Reference Upload Cleanup
**Location**: `backend/routers/mv.py` or `backend/routers/projects.py`

- [ ] Find character reference image upload calls
- [ ] Add cleanup after successful upload to S3
- [ ] Delete local reference image files

**Note**: Need to identify exact location

---

#### 7. Update Trim Video Upload Cleanup
**Location**: `backend/routers/mv_projects.py`

- [ ] Find trimmed video upload in `trim_scene_video()` (around lines 1617-1621)
- [ ] Add cleanup after successful upload
- [ ] Delete `trimmed_video_path` after S3 upload succeeds

**Code location**: `backend/routers/mv_projects.py:1617-1621`

**Note**: Temp directory cleanup already handled by finally block (lines 1642-1646) - leave as is

---

#### 8. Testing & Validation

- [ ] Test video generation flow - verify files deleted after upload
- [ ] Test scene generation - verify scene videos deleted after upload
- [ ] Test lipsync processing - verify lipsynced videos deleted after upload
- [ ] Test final composition - verify final video deleted after upload
- [ ] Test trim functionality - verify trimmed videos deleted after upload
- [ ] Test upload failure scenarios - verify files kept locally when upload fails
- [ ] Check disk usage before/after implementation
- [ ] Monitor logs for deletion errors

---

### Implementation Order (Recommended)

1. **Start**: Task 1 - Create utility function
2. **High Priority**: Task 2 - Video generator (most frequently used)
3. **High Priority**: Task 3 - Scene video uploads (most frequently used)
4. **Medium Priority**: Task 5 - Compose worker (runs less frequently)
5. **Medium Priority**: Task 7 - Trim video uploads (user-triggered)
6. **Low Priority**: Task 4 - Lipsync cleanup
7. **Low Priority**: Task 6 - Character reference cleanup
8. **Final**: Task 8 - Testing

---

### Success Criteria

 No media files accumulate in `backend/mv/outputs/*` directories after successful uploads
 Files are deleted immediately after each successful S3 upload
 Files are preserved locally if S3 upload fails
 No errors in deletion logging
 Existing tempfile cleanup (finally blocks) unchanged
 All file paths correctly identified and deleted
 No impact on retry mechanisms

---

### Edge Cases to Handle

1. **Concurrent uploads**: Multiple processes uploading same file (unlikely but possible)
2. **Permission errors**: File locked or permission denied
3. **Symbolic links**: Should we follow/delete symlinks?
4. **Partial uploads**: S3 upload succeeds but file metadata update fails
5. **Directory cleanup**: Should we also remove empty directories in `outputs/*`?

---

### Monitoring & Debugging

Add structured logging for:
- `local_file_deleted` - File successfully deleted
- `local_file_not_found` - File missing when attempting deletion (warning)
- `failed_to_delete_local_file` - Deletion failed (error)
- Track file sizes deleted (for metrics)

---

### Future Enhancements (Optional)

- Add periodic cleanup job to remove orphaned files (files older than X hours)
- Add metrics tracking (disk space saved)
- Add configuration option to disable auto-cleanup (for debugging)
- Add cleanup API endpoint for manual triggering

---

## v2: Port Lipsync Route to Project-Based Endpoint

**Goal**: Create a new project-based lipsync endpoint at `/api/mv/projects/{project_id}/lipsync/{sequence}` that integrates with the existing project/scene database structure and adds lipsync functionality to the scene options menu in the frontend.

**Requirements**:
- Port the `/api/mv/lipsync` route logic to the new project-based endpoint
- Calculate audio timing from database based on scene sequence and cumulative duration
- Pull video and audio URLs from S3 via database records
- Update scene record with lipsynced video URL (replace existing video_url)
- Add "Add Lipsync" option to scene options menu in UI (three-dot menu)
- Support client-provided parameters: temperature, active_speaker_detection
- Display errors gracefully in UI while preserving original video on failure
- Keep original `/api/mv/lipsync` route unchanged (additive approach)

**Benefits**:
- Enables per-scene lipsync within project workflow
- Automated audio timing calculation from database
- Seamless integration with existing scene management
- User-friendly UI for lipsync operations
- Improved video quality with lip-sync capabilities

**Affected Components**:
- `backend/routers/mv_projects.py` - New lipsync endpoint
- `backend/mv/lipsync.py` - Audio clipping and lipsync logic (reused)
- `frontend/src/components/ProjectSceneCard.tsx` - UI for "Add Lipsync" option
- `frontend/src/app/project/[id]/ProjectPageClient.tsx` - API integration
- `backend/mv_models.py` - Scene model (video_url update)

**Implementation Priority**: High (enables key feature for music video generation)

---

### Tasks

#### 1. Backend: Create Project-Based Lipsync Endpoint
**Location**: `backend/routers/mv_projects.py`

- [ ] Create new POST endpoint: `/api/mv/projects/{project_id}/lipsync/{sequence}`
  - Accept path parameters: `project_id` (UUID), `sequence` (int)
  - Accept optional body parameters:
    - `temperature: Optional[float]` (0.0-1.0, controls lip movement expressiveness)
    - `active_speaker_detection: Optional[bool]` (auto-detect speaker in multi-person videos)
    - `occlusion_detection_enabled: Optional[bool]` (handle face obstructions)
  - Return lipsynced video URL and updated scene data

- [ ] Implement database lookups:
  - Fetch project metadata to get `audioBackingTrackS3Key`
  - Fetch target scene by sequence number to get `videoClipUrl` or `originalVideoClipUrl`
  - Validate project and scene exist (raise 404 if not found)
  - Generate presigned URLs for video and audio from S3 keys

- [ ] Implement audio timing calculation:
  - Query all scenes for the project with `sequence < target_sequence`
  - Sum `videoDuration` of all previous scenes to get cumulative duration
  - Calculate `start_time` = cumulative duration
  - Calculate `end_time` = cumulative duration + target scene's `videoDuration`
  - Handle edge cases (missing duration values, first scene, etc.)

- [ ] Call lipsync processing:
  - Use `generate_lipsync()` from `mv.lipsync` module
  - Pass video URL (from scene), audio URL (from project), start/end times, and optional parameters
  - Handle temp file upload to S3
  - Get back S3 URL for lipsynced video

- [ ] Update scene record:
  - Update scene's `videoClipUrl` with new lipsynced video S3 key
  - Preserve `originalVideoClipUrl` if not already set (for rollback)
  - Update `updatedAt` timestamp
  - Save to DynamoDB

- [ ] Error handling:
  - Return proper HTTP status codes (400, 404, 500)
  - Log errors with structured logging
  - Return detailed error messages for debugging
  - Preserve scene's original video on any failure

**Implementation notes**:
```python
@router.post("/projects/{project_id}/lipsync/{sequence}")
async def add_scene_lipsync(
    project_id: str,
    sequence: int,
    temperature: Optional[float] = None,
    active_speaker_detection: Optional[bool] = None,
    occlusion_detection_enabled: Optional[bool] = None
):
    """
    Add lipsync to a specific scene in a project.

    Automatically calculates audio timing based on scene sequence
    and previous scene durations.
    """
    # 1. Validate and fetch project metadata
    # 2. Fetch target scene
    # 3. Calculate audio timing from previous scenes
    # 4. Generate presigned URLs for video/audio
    # 5. Call lipsync processing
    # 6. Update scene with lipsynced video
    # 7. Return updated scene data
```

---

#### 2. Backend: Audio Timing Calculation Logic
**Location**: `backend/routers/mv_projects.py` (helper function)

- [ ] Create helper function: `calculate_audio_timing_for_scene(project_id: str, sequence: int)`
  - Query all scenes with `PK = PROJECT#{project_id}` and `SK` starting with `SCENE#`
  - Filter scenes where sequence < target sequence
  - Sort by sequence number
  - Sum `videoDuration` values (handle None/null values gracefully)
  - Return `(start_time, end_time)` tuple

- [ ] Handle edge cases:
  - First scene (sequence=1): start_time=0.0
  - Missing `videoDuration` on previous scenes: log warning, skip or use default
  - No previous scenes: start_time=0.0
  - Target scene has no duration: use remaining audio or default duration

**Implementation notes**:
```python
def calculate_audio_timing_for_scene(project_id: str, sequence: int) -> tuple[float, float]:
    """
    Calculate audio start_time and end_time for a scene based on cumulative duration.

    Returns:
        (start_time, end_time) in seconds
    """
    cumulative_duration = 0.0

    # Query all scenes before target sequence
    previous_scenes = MVProjectItem.query(
        f"PROJECT#{project_id}",
        MVProjectItem.SK.startswith("SCENE#") & (MVProjectItem.sequence < sequence)
    )

    for scene in previous_scenes:
        if scene.videoDuration:
            cumulative_duration += scene.videoDuration

    # Fetch target scene to get its duration
    target_scene = get_scene(project_id, sequence)
    scene_duration = target_scene.videoDuration or 5.0  # default fallback

    return (cumulative_duration, cumulative_duration + scene_duration)
```

---

#### 3. Backend: Integrate with Existing Lipsync Logic
**Location**: `backend/mv/lipsync.py` (review and reuse)

- [ ] Review `generate_lipsync()` function for compatibility
  - Ensure it accepts video_url, audio_url, start_time, end_time
  - Ensure it handles optional parameters (temperature, active_speaker, etc.)
  - Verify it returns S3 URL for lipsynced video

- [ ] Verify audio clipping functionality:
  - Confirm `ffmpeg` command for extracting audio segment (start_time to end_time)
  - Ensure temp file cleanup is handled properly
  - Test with various audio formats (mp3, wav, etc.)

- [ ] Ensure temp file upload to S3:
  - Lipsynced video should be uploaded to S3 with proper key structure
  - Suggested key: `mv/projects/{project_id}/scenes/{sequence}/lipsync_{timestamp}.mp4`
  - Clean up local temp files after upload (leverage v1 cleanup logic)

**Note**: Most logic already exists in `generate_lipsync()`, just need to ensure it works with project-based parameters.

---

#### 4. Frontend: Add "Add Lipsync" to Scene Options Menu
**Location**: `frontend/src/components/ProjectSceneCard.tsx`

- [ ] Add new dropdown menu item in existing three-dot menu:
  - Label: "Add Lipsync"
  - Icon: `<Mic />` (already imported)
  - Position: After "Regenerate Video" option
  - Enable when scene has video (check `scene.videoClipUrl` or `scene.originalVideoClipUrl`)

- [ ] Add callback prop: `onAddLipsync?: (sequence: number) => void`
  - Call when "Add Lipsync" is clicked
  - Pass scene sequence number to parent component

- [ ] Update menu rendering logic:
  - Only show "Add Lipsync" for completed scenes with video
  - Disable if scene is currently processing
  - Add hover/focus states matching existing menu items

**Implementation notes**:
```tsx
<DropdownMenuItem
  onClick={() => onAddLipsync?.(scene.sequence)}
  disabled={!scene.videoClipUrl && !scene.originalVideoClipUrl}
  className="text-white hover:bg-slate-700 focus:bg-slate-700"
>
  <Mic className="h-4 w-4 mr-2" />
  Add Lipsync
</DropdownMenuItem>
```

---

#### 5. Frontend: Create Lipsync Modal/Dialog for Parameters
**Location**: `frontend/src/components/LipsyncOptionsModal.tsx` (new file)

- [ ] Create new modal component for lipsync options:
  - Modal title: "Add Lipsync to Scene {sequence}"
  - Input fields:
    - Temperature slider (0.0 - 1.0, default 0.5)
      - Label: "Lip Movement Expressiveness"
      - Help text: "0.0 = subtle, 1.0 = exaggerated"
    - Active Speaker Detection checkbox (default: false)
      - Label: "Active Speaker Detection"
      - Help text: "Auto-detect speaker in multi-person videos"
    - Occlusion Detection checkbox (default: false)
      - Label: "Occlusion Detection"
      - Help text: "Handle face obstructions (slower processing)"

- [ ] Add submit/cancel buttons:
  - "Add Lipsync" primary button (calls API)
  - "Cancel" secondary button (closes modal)

- [ ] Handle loading state:
  - Show spinner during API call
  - Disable inputs while processing
  - Display progress message

**Implementation notes**:
```tsx
interface LipsyncOptionsModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (options: LipsyncOptions) => void
  sceneSequence: number
}

interface LipsyncOptions {
  temperature?: number
  active_speaker_detection?: boolean
  occlusion_detection_enabled?: boolean
}
```

---

#### 6. Frontend: Integrate Lipsync API Call
**Location**: `frontend/src/app/project/[id]/ProjectPageClient.tsx`

- [ ] Add API integration function:
  - Create `addSceneLipsync(projectId, sequence, options)` function
  - Call POST `/api/mv/projects/{project_id}/lipsync/{sequence}`
  - Pass optional parameters in request body
  - Handle response and update scene state

- [ ] Update scene state management:
  - Set scene status to "processing" during lipsync
  - Update scene video URL on success
  - Preserve original video URL on failure
  - Refresh scene data after completion

- [ ] Error handling:
  - Display error toast/notification on failure
  - Log detailed error to console
  - Keep scene in original state (don't replace video)
  - Show retry option if needed

**Implementation notes**:
```typescript
const addSceneLipsync = async (
  projectId: string,
  sequence: number,
  options: LipsyncOptions
) => {
  try {
    // Set scene to processing state
    updateSceneStatus(sequence, 'generating-lipsync')

    const response = await fetch(
      `/api/mv/projects/${projectId}/lipsync/${sequence}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(options)
      }
    )

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail?.message || 'Lipsync failed')
    }

    const data = await response.json()

    // Update scene with new video URL
    updateSceneVideo(sequence, data.video_url)
    updateSceneStatus(sequence, 'completed')

    showSuccessToast('Lipsync added successfully!')
  } catch (error) {
    console.error('Lipsync error:', error)

    // Preserve original video, just update status
    updateSceneStatus(sequence, 'error')

    showErrorToast(`Lipsync failed: ${error.message}`)
  }
}
```

---

#### 7. Frontend: UI State Management for Lipsync
**Location**: `frontend/src/components/ProjectSceneCard.tsx`

- [ ] Add new status type: `'generating-lipsync'`
  - Already exists in `SceneGenerationStatus` type (line 32)
  - Update status badge text and styling

- [ ] Update progress indicator:
  - Show "Generating Lip-Sync" message
  - Display progress bar or spinner
  - Show estimated time if available

- [ ] Handle error display:
  - Show error badge with brief message in UI
  - Log detailed error to console
  - Preserve and display original video
  - Show retry button or option to re-open lipsync modal

**Implementation notes**:
```tsx
// Status badge text already handled in getStatusText() (line 134-148)
case 'generating-lipsync':
  return 'Generating Lip-Sync'

// Error display
{scene.status === 'error' && scene.errorMessage && (
  <Alert variant="destructive" className="mt-2">
    <AlertCircle className="h-4 w-4" />
    <AlertDescription>{scene.errorMessage}</AlertDescription>
  </Alert>
)}
```

---

#### 8. Backend: Response Schema for Lipsync Endpoint
**Location**: `backend/mv_schemas.py` (add new schema)

- [ ] Create response schema: `LipsyncSceneResponse`
  - Include updated scene data (sequence, video_url, status, etc.)
  - Include lipsync metadata (processing time, parameters used, etc.)
  - Follow existing response schema patterns

**Implementation notes**:
```python
class LipsyncSceneResponse(BaseModel):
    """Response for scene lipsync operation."""

    project_id: str
    sequence: int
    video_url: str  # New lipsynced video URL
    original_video_url: Optional[str]  # Preserved original
    audio_segment: dict  # start_time, end_time
    lipsync_params: dict  # temperature, active_speaker, etc.
    status: str
    processing_time_seconds: Optional[float]
    updated_at: datetime
```

---

#### 9. Testing: Backend API Testing
**Location**: Manual testing / future automated tests

- [ ] Test lipsync endpoint with valid project and scene:
  - Create project with audio track
  - Generate scenes with videos
  - Call lipsync endpoint for scene 2, 3, etc.
  - Verify audio timing calculation is correct
  - Verify video URL is updated in database

- [ ] Test audio timing edge cases:
  - First scene (sequence=1): start_time should be 0.0
  - Scene with missing videoDuration in previous scenes
  - Project with only one scene

- [ ] Test error scenarios:
  - Invalid project_id (should return 404)
  - Invalid sequence (should return 404)
  - Missing audio track (should return 400)
  - Scene without video (should return 400)
  - Lipsync API failure (should preserve original video)

- [ ] Test parameter validation:
  - Temperature out of range (0.0-1.0)
  - Invalid boolean values
  - Missing optional parameters (should use defaults)

---

#### 10. Testing: Frontend UI Testing
**Location**: Manual testing in browser

- [ ] Test "Add Lipsync" menu option:
  - Verify menu appears on scene cards with videos
  - Verify menu is disabled for scenes without videos
  - Verify menu is disabled during processing

- [ ] Test lipsync modal:
  - Verify modal opens when "Add Lipsync" is clicked
  - Verify parameter inputs work correctly
  - Verify form validation
  - Verify cancel button closes modal

- [ ] Test lipsync API integration:
  - Verify scene status changes to "generating-lipsync"
  - Verify video updates after successful lipsync
  - Verify original video preserved on error
  - Verify error message displays in UI

- [ ] Test error scenarios in UI:
  - API returns 404 (project/scene not found)
  - API returns 400 (validation error)
  - API returns 500 (server error)
  - Network timeout or connection error

---

#### 11. Documentation: Update API Documentation
**Location**: `backend/routers/mv_projects.py` (endpoint docstring)

- [ ] Add comprehensive docstring to lipsync endpoint:
  - Describe endpoint purpose and behavior
  - Document path parameters (project_id, sequence)
  - Document body parameters (temperature, active_speaker, etc.)
  - Provide example request and response
  - Document error codes and messages
  - Note audio timing calculation behavior

- [ ] Update OpenAPI/Swagger documentation:
  - Verify endpoint appears in generated API docs
  - Ensure parameter descriptions are clear
  - Add example values for better UX

---

#### 12. Code Cleanup and Optimization
**Location**: All affected files

- [ ] Add structured logging:
  - Log lipsync request received (project_id, sequence, params)
  - Log audio timing calculation results
  - Log lipsync processing start/complete
  - Log errors with full context

- [ ] Optimize database queries:
  - Use query pagination if needed for large projects
  - Consider caching cumulative durations if performance issue
  - Add database indexes if needed (check existing GSIs)

- [ ] Reuse existing code patterns:
  - Follow same error handling as other endpoints in mv_projects.py
  - Use same S3 URL generation utilities
  - Match response schema patterns for consistency

- [ ] Clean up temp files:
  - Leverage v1 auto-delete logic for uploaded lipsync videos
  - Ensure no orphaned files in backend/mv/outputs/

---

### Implementation Order (Recommended)

1. **Start**: Task 2 - Audio timing calculation logic (foundational)
2. **Backend Core**: Task 1 - Create lipsync endpoint
3. **Backend Integration**: Task 3 - Integrate with existing lipsync logic
4. **Backend Schema**: Task 8 - Response schema definition
5. **Frontend UI**: Task 4 - Add menu option to scene card
6. **Frontend Modal**: Task 5 - Create lipsync options modal
7. **Frontend Integration**: Task 6 - API integration in ProjectPageClient
8. **Frontend State**: Task 7 - UI state management
9. **Backend Testing**: Task 9 - Backend API testing
10. **Frontend Testing**: Task 10 - Frontend UI testing
11. **Documentation**: Task 11 - API documentation
12. **Final**: Task 12 - Code cleanup and optimization

---

### Success Criteria

✓ New endpoint `/api/mv/projects/{project_id}/lipsync/{sequence}` works correctly
✓ Audio timing is calculated automatically from database (cumulative scene durations)
✓ Scene video_url is updated with lipsynced video after successful processing
✓ Original video_url is preserved in originalVideoClipUrl for rollback
✓ "Add Lipsync" option appears in scene three-dot menu
✓ Lipsync modal allows user to set temperature and active_speaker parameters
✓ UI displays "generating-lipsync" status during processing
✓ Errors are handled gracefully with preserved original video
✓ Original `/api/mv/lipsync` route remains unchanged (additive)
✓ Lipsync videos are auto-deleted after S3 upload (v1 cleanup logic)
✓ All structured logging in place for debugging
✓ API documentation is complete and accurate

---

### Edge Cases to Handle

1. **First scene (sequence=1)**: start_time=0.0, no previous scenes to sum
2. **Missing videoDuration**: Log warning, skip scene or use default duration
3. **Lipsync failure**: Preserve original video, display error, allow retry
4. **Concurrent lipsync requests**: Handle with scene status locking (status="processing")
5. **Audio track missing from project**: Return 400 error with clear message
6. **Scene without video**: Return 400 error or disable UI option
7. **Audio shorter than cumulative duration**: Handle gracefully (trim end_time)
8. **Very long audio timing calculation**: Optimize query or add caching

---

### Monitoring & Debugging

Add structured logging for:
- `lipsync_request_received` - Endpoint called with params
- `audio_timing_calculated` - start_time, end_time, scene count
- `lipsync_processing_started` - video/audio URLs, parameters
- `lipsync_processing_completed` - processing time, output size
- `lipsync_scene_updated` - scene updated with new video URL
- `lipsync_error` - Error details, stack trace, scene preserved
- Track processing times and success/failure rates

---

### Future Enhancements (Optional)

- Add batch lipsync for multiple scenes
- Support custom audio file upload per scene (override project audio)
- Add preview mode (show lipsynced clip before committing)
- Add undo/revert to original video option
- Cache cumulative duration calculations for performance
- Add queue system for long-running lipsync jobs
- Support different lipsync models/providers
