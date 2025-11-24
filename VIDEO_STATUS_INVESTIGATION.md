# Video/Scene Status Management - Complete Investigation

## Executive Summary

The video/scene generation system uses **status fields for tracking and counters**, but **URLs as the actual "source of truth"** for what needs to be generated. The status field is metadata about what happened, not a mechanism to prevent regeneration.

### Key Finding
**Status does NOT prevent generation from being triggered.** Only the presence or absence of video URLs (`originalVideoClipUrl`) determines whether a scene will be included in the next generation run.

---

## Status Values

### Project Status Enum
Located: `/backend/mv_schemas.py:264-266`

```python
if v not in ['pending', 'processing', 'completed', 'failed']:
    raise ValueError("Invalid status value")
```

**Values:**
- `pending` - Waiting for generation (initial state)
- `processing` - Currently generating
- `completed` - All videos generated
- `failed` - Generation failed somewhere
- `generating_scenes` - Intermediate state (scene generation phase only)

### Scene Status Values
Located: `/backend/mv_models.py:302` (creation)

**Values:**
- `pending` - Waiting for video generation
- `processing` - Currently generating video
- `completed` - Video generated and saved
- `failed` - Video generation failed

---

## Database Schema

### DynamoDB Single-Table Design
**File:** `/backend/mv_models.py:45-127`

#### Structure
```
Partition Key (PK): PROJECT#{projectId}
Sort Key (SK):     METADATA | SCENE#{sequence:03d}

Examples:
  PROJECT#550e8400-e29b-41d4-a716-446655440000  METADATA
  PROJECT#550e8400-e29b-41d4-a716-446655440000  SCENE#001
  PROJECT#550e8400-e29b-41d4-a716-446655440000  SCENE#002
```

#### Status Fields
| Field | Type | Used For |
|-------|------|----------|
| `status` | UnicodeAttribute | Current status (pending/processing/completed/failed) |
| `GSI1PK` | UnicodeAttribute | Global Secondary Index - query by status (project only) |
| `GSI1SK` | UnicodeAttribute | GSI range key - createdAt timestamp |

#### Video URL Fields (The Real Source of Truth)
| Field | Type | Purpose |
|-------|------|---------|
| `originalVideoClipS3Key` | String | Unmodified Veo/Gemini output |
| `workingVideoClipS3Key` | String | Trimmed/edited version |
| `lipSyncedVideoClipS3Key` | String | Lip-synced version |

### Key Method: update_status()
```python
# /backend/mv_models.py:129-141
def update_status(self, new_status: str) -> None:
    self.status = new_status
    if self.entityType == "project":
        self.GSI1PK = new_status  # Keep GSI in sync
    self.updatedAt = datetime.now(timezone.utc)
    self.save()
```

**Note:** GSI only updated for project metadata, not scene items

---

## Status Transition Logic

### Complete Workflow

#### Phase 1: Scene Generation (Automatic)
**File:** `/backend/workers/scene_worker.py:18-180`

```
1. Project Created
   └─ status = "pending"

2. Worker Triggered (if no scenes)
   └─ Project status = "generating_scenes"

3. Scenes Generated via Gemini API
   └─ Project status = "pending" (ready for videos)
   └─ Each scene: status = "pending"

4. On Error
   └─ Project status = "failed"
```

#### Phase 2: Video Generation (Manual)
**File:** `/backend/routers/mv.py:750-1010`

```
1. User clicks "Generate Videos" button
   └─ Filters scenes WITHOUT originalVideoClipUrl
   └─ Calls backend for each scene

2. Backend processes each scene
   └─ Scene status = "processing"
   └─ Generate video (Gemini/Replicate)
   └─ Upload to S3
   └─ Scene status = "completed"
   └─ Update project counters

3. On Error
   └─ Scene status = "failed"
   └─ Project status = "failed"
```

### Status Transitions Diagram

```
PENDING ──────→ PROCESSING ──────→ COMPLETED
  ↑                                    │
  │                  ↓                 │
  └──────────────── FAILED ←──────────┘
```

**Key Point:** Transitions happen automatically during generation, not as explicit state machine checks.

---

## How Generation is Triggered

### Frontend Filtering Logic
**File:** `/frontend/src/app/edit/[id]/page.tsx:211-224`

```typescript
// Calculate scenes missing videos
const scenesWithoutVideos = useMemo(() => {
  if (!project?.scenes) return []
  return project.scenes.filter(scene => !scene.originalVideoClipUrl)
}, [project?.scenes])

// Prevent generation if all have videos
const handleGenerateVideos = async () => {
  if (scenesWithoutVideos.length === 0) {
    toast("All Videos Complete")
    return
  }
  // ... start generation ...
}
```

**What it checks:**
- ✓ Is `originalVideoClipUrl` missing?
- ✗ What is the scene status?
- ✗ Has generation been attempted before?
- ✗ Is there an error message?

**Result:** Generation ONLY blocked by missing URL, not by status

### Backend Endpoint
**File:** `/backend/routers/mv.py:750-821`

```python
# Get scene from database
scene_item = MVProjectItem.get(f"PROJECT#{project_id}", scene_sk)

# Verify it's a scene item
if scene_item.entityType != "scene":
    raise HTTPException(...)

# Get project metadata
project_item = MVProjectItem.get(f"PROJECT#{project_id}", "METADATA")

# NO STATUS CHECK HERE - just proceeds
scene_item.status = "processing"  # Set to processing
scene_item.save()

# Generate video...
# Upload to S3...
# Update status to "completed"
```

**Backend behavior:**
- ✓ Accepts generation requests for any scene
- ✓ Allows regeneration of completed scenes
- ✗ No status-based rejection logic
- ✗ No rate limiting by status

### Orchestration Layer
**File:** `/frontend/src/lib/orchestration.ts:205-413`

```typescript
// Phase: Generate videos
const videoPromises = project.scenes.map((scene, index) =>
  retryWithBackoff(
    async () => {
      const videoRequest = {
        prompt: scene.prompt,
        negative_prompt: scene.negativePrompt || undefined,
        project_id: projectId,
        sequence: scene.sequence,
      }
      const videoResponse = await generateVideo(videoRequest)
      return videoResponse
    },
    `Generate video for scene ${index + 1}`,
    opts,
    'videos',
    index
  )
)

await Promise.all(videoPromises)
```

**What it does:**
- ✓ Attempts to generate ALL scenes
- ✓ Retries with exponential backoff (3x)
- ✗ No filtering based on status
- ✗ No skipping of completed scenes

---

## Counter Management

### Project Counters
**File:** `/backend/mv_models.py:331-552`

Project metadata maintains:
- `sceneCount` - Total number of scenes
- `completedScenes` - Scenes with status="completed"
- `failedScenes` - Scenes with status="failed"

### Update Strategy: IDEMPOTENT
**Not increment/decrement** - Always **recount**

```python
# /backend/mv_models.py:331-370
def increment_completed_scene(project_id: str) -> None:
    scenes = MVProjectItem.query(pk, MVProjectItem.SK.startswith("SCENE#"))
    
    # RECOUNT, don't increment
    completed_count = sum(1 for scene in scenes if scene.status == "completed")
    
    project_item.completedScenes = completed_count  # SET, not +=
    project_item.save()
```

**Why:** Prevents double-counting on retries and failed operations

### When Counters Update
1. After scene video generation completes
2. After scene video generation fails  
3. After scene deletion
4. On explicit counter recalculation

---

## What Status Actually Controls

### What Status DOES
1. ✓ Tracks metadata about what happened
2. ✓ Enables GSI queries to find projects by status
3. ✓ Used in UI badges/progress indicators
4. ✓ Counted for project completion metrics

### What Status DOES NOT
1. ✗ Prevent regeneration requests
2. ✗ Block scene updates/edits
3. ✗ Enforce sequence of operations
4. ✗ Prevent concurrent generation
5. ✗ Provide rate limiting

---

## The Real Source of Truth

### Three-Tier Consistency Model

#### Tier 1: Video URL Fields (PRIMARY)
- Stored in DynamoDB as S3 keys
- Only set after successful S3 upload
- **Most reliable** - used for critical decisions
- Set in: `/backend/routers/mv.py:925-933`

```python
s3_storage.upload_file(
    file_data=video_file,
    s3_key=video_s3_key,
    content_type="video/mp4"
)

scene_item.originalVideoClipS3Key = video_s3_key
scene_item.save()
```

#### Tier 2: Status Field (METADATA)
- Tracks generation state
- Lags behind actual completion (set before S3 upload)
- Used for display, not decisions
- Good but not definitive

#### Tier 3: Project Counters (DERIVED)
- Calculated by recounting scenes
- Always accurate because they're recalculated
- Used for progress indicators

### Decision Making
```
Frontend Filtering:
  if scene.originalVideoClipUrl → Skip generation
  else                           → Include in generation

Backend Acceptance:
  No status checks - always accept

Orchestration:
  Attempts ALL scenes (rely on frontend filtering)
```

---

## Potential Issues & Edge Cases

### Issue 1: Orphaned Status
**Scenario:** Status updated to "completed" but S3 upload fails

```
After Status Update:  scene.status = "completed"
Before S3 Upload:     scene.originalVideoClipS3Key = null

Result:
  - Status says "completed"
  - URL says "not started"
  - Frontend sees no URL → will regenerate
  - But status metadata is incorrect
```

**Current handling:** Works because of URL precedence

### Issue 2: Silent Failures
**Scenario:** S3 upload succeeds but status update fails

```
After S3 Upload:      scene.originalVideoClipS3Key = "mv/projects/..."
Before Status Update: scene.status = "processing"

Result:
  - URL is set (correct)
  - Status still "processing" (incorrect)
  - Frontend won't regenerate (correct behavior)
  - But status is stale
```

**Current handling:** Works due to URL-based filtering

### Issue 3: Manual Regeneration
**Scenario:** User/admin wants to regenerate a completed video

```
Scenario A - Reset in Frontend:
  Can't - no UI to reset URL
  
Scenario B - Reset in Database:
  Could manually delete originalVideoClipS3Key
  Next generation would regenerate
  No status check prevents this
  
Scenario C - Status says "failed" but URL exists:
  Frontend sees URL → won't regenerate
  Status-based decision would fail here
```

**Current handling:** URL-based filtering works but status-based checks would fail

---

## Code References

### Database Model
- **File:** `/backend/mv_models.py`
- Status field: Line 79
- Status update method: Lines 129-141
- Scene creation: Lines 262-328
- Counter methods: Lines 331-552

### Backend Routing
- **File:** `/backend/routers/mv.py`
- Generate video endpoint: Lines 750-1010
- Status transitions: Lines 819, 943, 972, 2089
- Counter updates: Throughout endpoint

### Frontend Logic
- **File:** `/frontend/src/app/edit/[id]/page.tsx`
- Scene filtering: Lines 211-214
- Video generation trigger: Lines 216-258
- Auto-scene-generation: Lines 146-208

### Orchestration
- **File:** `/frontend/src/lib/orchestration.ts`
- Main workflow: Lines 205-413
- Video phase: Lines 281-319
- No status-based filtering

### Schemas & Validation
- **File:** `/backend/mv_schemas.py`
- Status validation: Lines 264-266
- Scene response: Lines 10-62
- Project response: Lines 208-253

---

## Summary Table

| Aspect | Status Field | URL Field | Counter |
|--------|--------------|-----------|---------|
| **Storage** | DynamoDB | DynamoDB | DynamoDB |
| **Set When** | Start of operation | After S3 success | After count |
| **Checked By** | UI, counters | Filtering | Display |
| **Reliable** | Medium | High | High |
| **Prevents Regen** | No | Yes | No |
| **Can Be Stale** | Yes | Rare | No |

---

## Recommendations

### If Implementation Needs Status-Based Prevention
1. Add explicit status check in backend endpoint
2. Validate status before accepting generation
3. Update status atomically with video URL
4. Consider state machine validation

### If URL-Based System is Sufficient
1. Document that URLs are source of truth
2. Add method to reset URLs for regeneration
3. Monitor for orphaned status situations
4. Keep counter recalculation as safety valve

### To Improve Reliability
1. Wrap status + URL updates in transaction
2. Add background task to detect/fix inconsistencies
3. Store generation timestamps separately
4. Consider explicit "locked" state for in-progress

