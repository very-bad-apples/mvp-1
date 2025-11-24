# Video/Scene Status Management - Quick Reference

## TL;DR

**Status is metadata, not a gate.** Videos are generated based on whether `originalVideoClipUrl` exists, not based on the `status` field.

- If `scene.originalVideoClipUrl` exists → Skip in next generation
- If `scene.originalVideoClipUrl` is missing → Include in next generation
- Status field doesn't prevent anything

---

## Status Values

### Project
- `pending` - Ready (or waiting to start)
- `processing` - Currently generating
- `completed` - Done
- `failed` - Error occurred
- `generating_scenes` - (intermediate, scene phase only)

### Scene  
- `pending` - Ready for video generation
- `processing` - Currently generating video
- `completed` - Video done
- `failed` - Generation failed

---

## Where Status is Set

| Event | Status | File | Line |
|-------|--------|------|------|
| Project created | pending | mv_models.py | 236 |
| Scene generation starts | generating_scenes | scene_worker.py | 50 |
| Scene generation done | pending | scene_worker.py | 140 |
| Video generation starts | processing | routers/mv.py | 819 |
| Video generation done | completed | routers/mv.py | 972 |
| Generation fails | failed | routers/mv.py | 2089 |

---

## Where Status is Checked

| Purpose | Code Location | What's Checked |
|---------|---------------|-----------------|
| **Filtering scenes for generation** | edit/[id]/page.tsx:211-214 | `originalVideoClipUrl` only |
| **Backend accepts request** | routers/mv.py:750-821 | None (accepts all) |
| **Orchestration decides** | orchestration.ts:285-319 | None (attempts all) |
| **UI display** | ScenesPanel.tsx | Status for badge |
| **Project counters** | mv_models.py:331-552 | Count by status |

---

## The Real Decision Maker: Video URLs

```javascript
// Frontend decides to skip generation if:
if (scene.originalVideoClipUrl) {
  // Skip - video exists
} else {
  // Include - video missing
}
```

**This is the only true gate.** Status is just recording what happened.

---

## Key File Locations

### Database & Models
- `/backend/mv_models.py` - PynamoDB models, status field, counter functions
- `/backend/mv_schemas.py` - Status validation schema

### API Endpoints  
- `/backend/routers/mv.py:750-821` - generate_scene_video() - no status checks
- `/backend/routers/mv.py:940-972` - DB update logic after generation

### Frontend Logic
- `/frontend/src/app/edit/[id]/page.tsx:211-224` - Scene filtering (checks URL only)
- `/frontend/src/lib/orchestration.ts:205-413` - Generation workflow (no status checks)

### Scene Auto-generation
- `/backend/workers/scene_worker.py:18-180` - Automatic scene generation on project creation

---

## Common Scenarios

### Scenario: Scene has video URL
```
status: "completed"
originalVideoClipUrl: "https://..."

Result: Will NOT regenerate (URL exists)
```

### Scenario: Scene status failed but URL exists  
```
status: "failed"
originalVideoClipUrl: "https://..."

Result: Will NOT regenerate (URL exists, status ignored)
```

### Scenario: Scene status completed but URL missing
```
status: "completed"
originalVideoClipUrl: null

Result: WILL regenerate (URL missing)
Logic: Frontend sees no URL → includes in generation
Note: Status is wrong but behavior is correct
```

### Scenario: Scene status processing
```
status: "processing"
originalVideoClipUrl: null

Result: WILL regenerate when user clicks button
Note: Normal state during generation
```

---

## Database Schema (Simplified)

```
DynamoDB Table: music_video_projects

Project Item:
  PK: PROJECT#{uuid}
  SK: METADATA
  status: "pending" | "processing" | "completed" | "failed"
  GSI1PK: (mirrors status for queries)

Scene Item:
  PK: PROJECT#{uuid}
  SK: SCENE#{sequence:03d}
  status: "pending" | "processing" | "completed" | "failed"
  originalVideoClipS3Key: S3 path or null
  workingVideoClipS3Key: S3 path or null
```

---

## Tracing Generation Decision

**User clicks "Generate Videos":**

1. **Edit page calculates:**
   ```typescript
   scenesWithoutVideos = project.scenes.filter(
     s => !s.originalVideoClipUrl
   )
   ```
   *(Status not checked)*

2. **Frontend calls orchestration:**
   ```typescript
   startFullGeneration(projectId)
   ```

3. **Orchestration maps scenes:**
   ```typescript
   videoPromises = project.scenes.map(scene => 
     generateVideo({...})
   )
   ```
   *(Attempts ALL scenes, backend will handle failures)*

4. **Backend endpoint accepts any scene:**
   - Sets status = "processing"
   - Generates video
   - Uploads to S3
   - If successful: originalVideoClipS3Key = path, status = "completed"
   - If fails: status = "failed"

5. **Next time user clicks generate:**
   - Scenes WITH originalVideoClipUrl are filtered out
   - Scenes WITHOUT originalVideoClipUrl are retried

---

## Status Updates During Generation

```
Timeline of a Video Generation:

T0: User clicks "Generate Videos"
    scene.status = "pending"
    scene.originalVideoClipUrl = null

T1: Backend starts processing
    scene.status = "processing"

T2: Video generated successfully
    [In DynamoDB as video object]

T3: Uploaded to S3
    scene.originalVideoClipS3Key = "mv/projects/.../video.mp4"

T4: DB updated
    scene.status = "completed"
    [Both status and URL updated]

T5: Frontend refetches
    Sees originalVideoClipUrl 
    Won't regenerate next time
```

---

## Important Note: URL Is Primary

If status and URL disagree:
- **Frontend filtering uses URL** → correct behavior
- **UI display uses status** → might be stale
- **Project counts use status** → might be inaccurate

The URL-based filtering saves the system from inconsistent status.

---

## Testing/Debugging

### Check if scene will regenerate:
```python
# In Python backend
scene = get_scene(project_id, sequence)
will_regenerate = not scene.originalVideoClipS3Key
print(f"Will regenerate: {will_regenerate}")
print(f"Status: {scene.status}")
print(f"URL: {scene.originalVideoClipS3Key}")
```

### Force regeneration:
```python
# Manually clear the URL
scene.originalVideoClipS3Key = None
scene.save()
# Next generation attempt will include this scene
```

### Check project counters:
```python
# These are idempotent - recalculate if suspected bad state
from mv_models import recalculate_scene_counters
recalculate_scene_counters(project_id)
```

---

## Related Files Saved

1. `VIDEO_STATUS_INVESTIGATION.md` - Full detailed analysis with code excerpts
2. `DETAILED_STATUS_ANALYSIS.md` - Complete workflow documentation
3. `STATUS_FLOW_DIAGRAM.txt` - ASCII flow diagrams
4. `STATUS_QUICK_REFERENCE.md` - This file

