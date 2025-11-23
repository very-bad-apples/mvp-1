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
