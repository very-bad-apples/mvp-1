## v1: Auto-Delete Local Media Files After S3 Upload

**Feature**: Delete media files saved to children directories of backend/mv/outputs (e.g. audio/ videos/ jobs/ etc) once the upload to S3 is complete.

**Status**: 📋 Planned

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