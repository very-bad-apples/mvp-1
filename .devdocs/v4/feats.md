## v1: Auto-Delete Local Media Files After S3 Upload

**Feature**: Delete media files saved to children directories of backend/mv/outputs (e.g. audio/ videos/ jobs/ etc) once the upload to S3 is complete.

**Status**: ✅ Implemented

**Task List**: See `.devdocs/v4/tasklist.md` for detailed implementation plan

**Requirements**:
- Delete files immediately after successful S3 upload
- Keep files locally if upload fails (for retry purposes)
- Preserve existing tempfile cleanup in finally blocks
- Only delete successfully uploaded files

**Benefits**:
- Prevents disk space accumulation from generated media files
- Automatic cleanup without manual intervention
- Reduces storage costs on backend servers
- Improves long-term system stability

**Affected Components**:
- `backend/mv/video_generator.py` - Video generation uploads
- `backend/routers/mv_projects.py` - Scene video and trim uploads
- `backend/workers/compose_worker.py` - Final composition uploads
- `backend/mv/lipsync.py` - Lipsync video uploads
- `backend/services/s3_storage.py` - Cleanup utility function

**Implementation Priority**: High (prevents disk space issues in production)

## v2: Port Lipsync Route to Project-Based Endpoint

**Feature**: Create a new project-based lipsync endpoint at `/api/mv/projects/{project_id}/lipsync/{sequence}` that integrates with the existing project/scene database structure and adds lipsync functionality to the scene options menu in the frontend.

**Status**: 📋 Planned

**Task List**: See `.devdocs/v4/tasklist.md` section "v2: Port Lipsync Route to Project-Based Endpoint" for detailed implementation plan

**Requirements**:
- Port the `/api/mv/lipsync` route logic to the new project-based endpoint (keep original route)
- Calculate audio timing automatically from database based on scene sequence and cumulative duration of previous scenes
- Pull video and audio URLs from S3 via database records (project's audioBackingTrackS3Key and scene's videoClipUrl)
- Update scene record with lipsynced video URL (replace existing videoClipUrl, preserve originalVideoClipUrl)
- Add "Add Lipsync" option to scene options menu in UI (three-dot menu on /edit/<project-id> page)
- Support client-provided parameters: temperature, active_speaker_detection, occlusion_detection_enabled
- Display errors gracefully in UI while preserving original video on failure

**Benefits**:
- Enables per-scene lipsync within project workflow
- Automated audio timing calculation eliminates manual timing configuration
- Seamless integration with existing scene management and video regeneration
- User-friendly UI for lipsync operations with parameter control
- Improved video quality with lip-sync capabilities for talking scenes

**Affected Components**:
- `backend/routers/mv_projects.py` - New lipsync endpoint with audio timing calculation
- `backend/mv/lipsync.py` - Audio clipping and lipsync logic (reused from existing route)
- `frontend/src/components/ProjectSceneCard.tsx` - UI for "Add Lipsync" option in three-dot menu
- `frontend/src/components/LipsyncOptionsModal.tsx` - New modal for lipsync parameter inputs
- `frontend/src/app/project/[id]/ProjectPageClient.tsx` - API integration and state management
- `backend/mv_schemas.py` - Response schema for lipsync endpoint

**Implementation Priority**: High (enables key feature for music video generation with talking characters)

**Key Technical Details**:
- Audio timing: `start_time` = sum of all previous scenes' `videoDuration`, `end_time` = start_time + current scene's `videoDuration`
- Scene update: Replace `videoClipUrl` with lipsynced video S3 key, preserve `originalVideoClipUrl` for rollback
- UI location: Three-dot menu in scene card (alongside "Regenerate Image", "Regenerate Video", "Regenerate Lip-Sync")
- Error handling: Preserve original video on failure, display error in UI and console
- Additive approach: Original `/api/mv/lipsync` route remains unchanged