# Video/Scene Status Management Investigation

## Status Values Used

### Project Status Values
- `pending` - Project created, waiting for scene generation or video generation
- `processing` - Currently generating scenes, images, videos, or composing
- `generating_scenes` - Intermediate state during scene generation (worker-only)
- `completed` - All videos generated successfully
- `failed` - Generation failed at some stage

**File:** `/backend/mv_models.py:79` - Status attribute definition
**Status validation:** `/backend/mv_schemas.py:264-266` - Only accepts: pending, processing, completed, failed

### Scene Status Values
- `pending` - Scene created, waiting for video generation
- `processing` - Currently generating video
- `completed` - Video generated successfully
- `failed` - Video generation failed

**File:** `/backend/mv_models.py:302` - Scene creation initializes status as "pending"

## Database Schema

### DynamoDB Single-Table Design
**File:** `/backend/mv_models.py` (PynamoDB model)

**Primary Keys:**
- **PK (Partition Key):** `PROJECT#{projectId}` - Groups all items for a project
- **SK (Range Key):** 
  - `METADATA` for project metadata
  - `SCENE#{sequence:03d}` for scene items (e.g., `SCENE#001`)

**Status Attributes:**
- `status` (UnicodeAttribute) - Current status
- `GSI1PK` (UnicodeAttribute, null=True) - Global Secondary Index partition key (mirrors status for project items)
- `GSI1SK` (UnicodeAttribute, null=True) - Global Secondary Index sort key (createdAt timestamp)

**Status Index:** `status-created-index` - Allows querying projects by status

### Status Update Method
**File:** `/backend/mv_models.py:129-141` - `update_status()` method

```python
def update_status(self, new_status: str) -> None:
    """Update status and GSI fields atomically"""
    self.status = new_status
    if self.entityType == "project":
        self.GSI1PK = new_status  # Keep GSI in sync
    self.updatedAt = datetime.now(timezone.utc)
    self.save()
```

**Key Point:** GSI is only updated for project items (entityType="project"), not for scenes.

## Status Transitions & Workflow

### Complete Generation Workflow

#### Phase 1: Scene Generation (Automatic on project creation)
**File:** `/backend/workers/scene_worker.py`

```
pending (initial)
    ↓
generating_scenes (worker sets this)
    ↓
pending (after scenes generated, ready for video generation)
    or
failed (if scene generation fails)
```

1. Project created with status `pending` (line 236)
2. Worker sets status to `generating_scenes` (line 50)
3. Scenes are generated using Gemini API
4. Status updated to `pending` (line 140) - ready for video generation
5. If error, status set to `failed` (line 107)

#### Phase 2: Video Generation (Manual via "Generate Videos" button)
**File:** `/backend/routers/mv.py` - `generate_scene_video()` endpoint

```
pending
    ↓
processing (when generation starts, line 819)
    ↓
completed (when video successfully generated, line 972)
    or
failed (on error, line 2089)
```

1. User clicks "Generate Videos" button in frontend
2. Frontend calls `startFullGeneration()` orchestration (orchestration.ts)
3. Backend `/api/mv/generate_scene_video` endpoint sets scene status to `processing` (line 819)
4. Video is generated via Gemini or Replicate backend
5. Video uploaded to S3
6. Scene status set to `completed` (line 972)
7. Project metadata updated with video counts

**Key Logic:** `/backend/routers/mv.py:941-943`
```python
if write_to_db:
    # Track if scene was already completed
    was_completed = scene_item.status == "completed"
```

This checks if a scene WAS completed before regeneration.

### Frontend Logic - What Triggers Generation

**File:** `/frontend/src/app/edit/[id]/page.tsx`

#### Auto-trigger Scene Generation (Lines 146-208)
```typescript
// Only auto-trigger for projects with no scenes
if (project.scenes.length === 0 && !isGeneratingScenes) {
  // Calls generateScenes()
}
```

**Condition:** Project has 0 scenes AND scene generation not already triggered

#### Manual Video Generation (Lines 216-224)
```typescript
const scenesWithoutVideos = useMemo(() => {
  if (!project?.scenes) return []
  return project.scenes.filter(scene => !scene.originalVideoClipUrl)
}, [project?.scenes])

// In handleGenerateVideos:
if (scenesWithoutVideos.length === 0) {
  toast("All Videos Complete")
  return
}
```

**Key Filter:** Scenes are included in generation if they DON'T have `originalVideoClipUrl`

**Critical Finding:** The filter only checks for presence of `originalVideoClipUrl`. It does NOT check scene status (pending, processing, completed, failed).

### How Status Prevents Regeneration

#### Indirect Prevention - Frontend Level
1. **Edit page** calculates `scenesWithoutVideos` by checking for `originalVideoClipUrl` only
2. No status-based filtering on the frontend
3. Users CAN manually trigger regeneration if they delete videos or somehow reset the URL

#### Backend Endpoint - Accepts All Requests
**File:** `/backend/routers/mv.py:750-821`

The `generate_scene_video()` endpoint:
1. Accepts any project/scene combination
2. Clears old video clip fields (lines 816-818)
3. Sets status to `processing` (line 819)
4. Proceeds with generation regardless of previous status

**NO explicit status check that blocks regeneration**

#### Database Update Logic
**File:** `/backend/routers/mv.py:940-972`

When writing to DB after video generation:
```python
if write_to_db:
    was_completed = scene_item.status == "completed"
    
    # ... generate video ...
    
    # Update scene
    scene_item.originalVideoClipS3Key = video_s3_key
    scene_item.workingVideoClipS3Key = video_s3_key
    scene_item.status = "completed"
    scene_item.save()
    
    if was_completed:
        decrement_completed_scene(project_id)
```

**Interesting Logic:** If a scene WAS already completed, it decrements the counter. This allows for regeneration without counter corruption.

## Project Status Update Counters

**Files:**
- `/backend/mv_models.py:331-370` - `increment_completed_scene()`
- `/backend/mv_models.py:373-412` - `increment_failed_scene()`
- `/backend/mv_models.py:415-430` - `decrement_completed_scene()`

**Key Pattern:** Counters are idempotent - they RECOUNT from actual scene statuses rather than incrementing/decrementing

```python
# Count scenes with status="completed"
completed_count = sum(1 for scene in scenes if scene.status == "completed")

# Update project metadata
project_item.completedScenes = completed_count
```

**Why:** Prevents counter inconsistencies if operations fail or are retried

## Orchestration - What Checks Status

**File:** `/frontend/src/lib/orchestration.ts:205-413` - `startFullGeneration()`

#### Scene Phase (Lines 224-252)
```typescript
if (project.scenes.length === 0) {
  // Generate scenes via API
} else {
  opts.onProgress('scenes', 1, 1, `Using existing ${project.scenes.length} scenes`)
}
```

**Check:** Only checks if scenes exist (length), not their status

#### Video Phase (Lines 281-319)
```typescript
// Generate all videos in parallel
const videoPromises = project.scenes.map((scene, index) =>
  // ... calls generateVideo for EACH scene without filtering ...
)

await Promise.all(videoPromises)
```

**Check:** NO filtering - attempts to generate ALL scenes

#### Lip-sync Phase (Lines 321-366)
```typescript
if (!scene.originalVideoClipUrl && !scene.videoClipUrl) {
  console.warn(`Scene ${index + 1} missing video, skipping lip-sync`)
  return null
}
```

**Check:** Skips if video URL missing (not based on status)

## Summary: How Status Manages Generation

### What Status Controls
1. **Metadata in database** - Tracks what's been done
2. **Project-level counters** - How many scenes completed/failed
3. **GSI queries** - Can find projects by status
4. **UI display** - Shows in badge/progress indicators

### What Status Does NOT Control
1. **Preventing regeneration** - Backend doesn't reject requests based on status
2. **Selective generation** - Frontend generates based on URL presence, not status
3. **Blocking scene updates** - Prompts can be updated regardless of status
4. **Enforcing sequence** - Videos can be generated in any order

### The Core Issue

**The system uses URLs as the "source of truth" for completion, not status.**

If `scene.originalVideoClipUrl` exists:
- Scene is considered "done" and skipped in generation
- Status is likely `completed` but not validated

If `scene.originalVideoClipUrl` is missing/null:
- Scene will be regenerated regardless of what the status field says
- Can be in `failed`, `pending`, or even `completed` state

**Prevention Mechanism:** The only thing that stops regeneration is checking for video URL presence, which happens at the frontend filtering level.

## Potential Issues

1. **Orphaned Status Values:** A scene could have `status="completed"` but no video URL if there's an error between status update and S3 upload
2. **Manual Regeneration:** No way to prevent regeneration if someone manually clears S3 keys
3. **Counter Inconsistencies:** If many operations fail/retry, counts could diverge from actual scene statuses
   - *Mitigation:* Idempotent recounting methods exist and should be called after failures

## References

**Backend Models:** `/backend/mv_models.py`
- Status attribute: Line 79
- Scene creation: Lines 262-328
- Update method: Lines 129-141

**Backend Routers:** `/backend/routers/mv.py`
- Generate video endpoint: Lines 750-1000
- Status transitions: Lines 819, 943, 972, 2089

**Frontend Logic:** `/frontend/src/app/edit/[id]/page.tsx`
- Scene filtering: Lines 211-214
- Video generation trigger: Lines 216-258

**Orchestration:** `/frontend/src/lib/orchestration.ts`
- Full generation flow: Lines 205-413
- Video phase: Lines 281-319

**Database:** `/backend/mv_models.py`
- Counters: Lines 331-552
- Status index: Lines 29-42
