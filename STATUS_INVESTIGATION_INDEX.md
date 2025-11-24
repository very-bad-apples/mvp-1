# Video/Scene Status Management - Investigation Index

## Overview

This investigation examined how video and scene status is managed in the Bad Apple video generation system. It revealed that **status is metadata for tracking, not a mechanism to prevent generation**. The actual gate for generation is the presence or absence of video URLs.

**Investigation Date:** November 24, 2025  
**Scope:** Backend (Python/FastAPI), Frontend (Next.js), Database (DynamoDB)  
**Key Files Analyzed:** 40+ source files

---

## Documents in This Investigation

### 1. **STATUS_QUICK_REFERENCE.md** ⭐ START HERE
**Purpose:** TL;DR summary with essential facts  
**Length:** 262 lines  
**Best for:** Quick lookup, understanding the core concept

**Contains:**
- Status values (pending, processing, completed, failed)
- Where status is set and checked
- Common scenarios
- Testing/debugging tips

**Key Finding:** Frontend filtering uses `originalVideoClipUrl`, not status.

---

### 2. **VIDEO_STATUS_INVESTIGATION.md** 
**Purpose:** Comprehensive analysis with code architecture  
**Length:** 455 lines  
**Best for:** Understanding the complete system design

**Contains:**
- Status enum validation
- DynamoDB schema with examples
- Complete lifecycle workflows (2 phases)
- Frontend filtering logic
- Backend endpoint behavior
- Orchestration layer
- Counter management strategy
- Three-tier consistency model

**Key Finding:** URLs are primary source of truth; status lags behind.

---

### 3. **DETAILED_STATUS_ANALYSIS.md**
**Purpose:** Executive summary with deep technical details  
**Length:** 293 lines  
**Best for:** Communicating findings to stakeholders, understanding design decisions

**Contains:**
- Executive summary
- Status values (enum, validation)
- Database schema and models
- Status transitions and workflows
- How generation is triggered (frontend, backend, orchestration)
- Counter management (idempotent recounting)
- What status does/doesn't control
- Edge cases and potential issues
- Code references with line numbers

**Key Finding:** System uses three tiers of consistency (URL > Status > Counters).

---

### 4. **STATUS_FLOW_DIAGRAM.txt**
**Purpose:** Visual representation of system flows  
**Length:** 191 lines  
**Best for:** Understanding state transitions, decision points

**Contains:**
- Project lifecycle flow chart
- Scene status state diagram
- Two key decision points (should generate? can accept?)
- Counter management flow
- Data consistency tiers
- Potential inconsistencies (3 cases)

**Key Finding:** Status has no explicit checks; backend accepts all generation requests.

---

## At a Glance

### Status Values

#### Project
```
pending  ──→  processing  ──→  completed
  ↑                                 │
  └───────────────── failed ←───────┘
```

- `generating_scenes` (intermediate during scene generation)
- Set by: Backend endpoints during operations
- Checked by: UI display, counters, database queries
- Prevents generation: **NO**

#### Scene
```
pending  ──→  processing  ──→  completed
  ↑                                 │
  └───────────────── failed ←───────┘
```

### Generation Decision Logic

```
Frontend:
  scene.originalVideoClipUrl exists?
    YES → Skip
    NO  → Include
  
Backend:
  Accept (no status check)
  
Orchestration:
  Attempt all scenes
```

### Key Metrics

| Aspect | Finding |
|--------|---------|
| **Status prevents regeneration?** | No |
| **URL-based filtering** | Yes |
| **Backend status checks** | None |
| **Frontend status filters** | None |
| **Source of truth** | Video URL (primary), Status (metadata) |
| **Counter strategy** | Idempotent recounting |

---

## Investigation Results

### What Status Controls
✓ Metadata tracking  
✓ GSI queries by status  
✓ UI badge display  
✓ Project completion metrics  

### What Status Does NOT Control
✗ Preventing regeneration  
✗ Blocking scene edits  
✗ Enforcing sequence  
✗ Preventing concurrent generation  
✗ Rate limiting  

### The Core Finding

**The system uses video URLs as the decision gate for generation, not the status field.**

```python
# What the code actually does (simplified):

# Frontend:
if not scene.originalVideoClipUrl:
    include_in_generation()

# Backend:
accept_all_generation_requests()

# Update:
scene.status = "completed"
scene.originalVideoClipS3Key = url
```

---

## Code References Quick Index

### Database & Models
- `/backend/mv_models.py:79` - Status field definition
- `/backend/mv_models.py:129-141` - update_status() method
- `/backend/mv_models.py:302` - Scene creation (status="pending")
- `/backend/mv_models.py:331-552` - Counter functions (idempotent)

### API Endpoints
- `/backend/routers/mv.py:750-821` - generate_scene_video() (no status checks!)
- `/backend/routers/mv.py:819` - Sets status to "processing"
- `/backend/routers/mv.py:972` - Sets status to "completed"
- `/backend/routers/mv.py:2089` - Sets status to "failed"

### Frontend Logic
- `/frontend/src/app/edit/[id]/page.tsx:211-214` - Scene filtering (checks URL only)
- `/frontend/src/app/edit/[id]/page.tsx:216-258` - Generation handler
- `/frontend/src/lib/orchestration.ts:205-413` - Full workflow (no status checks)
- `/frontend/src/lib/orchestration.ts:281-319` - Video generation phase

### Schemas
- `/backend/mv_schemas.py:264-266` - Status validation (pending, processing, completed, failed)
- `/backend/mv_schemas.py:10-62` - SceneResponse schema

### Workers
- `/backend/workers/scene_worker.py:18-180` - Scene generation worker (automatic)

---

## Key Files Analyzed (Complete List)

### Backend (Python)
- ✓ mv_models.py - Database models, status fields, counters
- ✓ mv_schemas.py - API schemas with status validation
- ✓ routers/mv.py - Main endpoint with status transitions
- ✓ workers/scene_worker.py - Automatic scene generation
- ✓ workers/compose_worker.py - Video composition
- ✓ config.py - Configuration
- ✓ schemas.py - Schema definitions

### Frontend (Next.js/TypeScript)
- ✓ app/edit/[id]/page.tsx - Edit page with filtering logic
- ✓ lib/orchestration.ts - Generation orchestration
- ✓ lib/api/client.ts - API client
- ✓ components/ScenesPanel.tsx - Scene list display
- ✓ components/SceneDetailPanel.tsx - Scene detail view
- ✓ hooks/useProjectPolling.ts - Project polling

### Tests
- ✓ test_delete_scene.py - Scene deletion with status
- ✓ test_add_scene.py - Scene addition tests
- ✓ test_mv_endpoints.py - Endpoint tests
- ✓ test_scene_insertion_deletion_flow.py - Flow tests

---

## Potential Issues Found

### 1. Orphaned Status
**Scenario:** Status updated but S3 upload fails

- Status says "completed"
- URL says "not started"
- Result: Works correctly (URL precedence) but status is stale

### 2. Silent Failures  
**Scenario:** S3 upload succeeds but status update fails

- Status says "processing"
- URL is set correctly
- Result: Works correctly (frontend won't regenerate) but status is stale

### 3. No Manual Regeneration UI
**Scenario:** User wants to regenerate a completed video

- No button/UI to reset URL
- No admin interface to force regeneration
- Workaround: Directly reset `originalVideoClipS3Key` in DB

---

## Recommendations

### For Reliability
1. Wrap status + URL updates in atomic transaction
2. Add background task to detect/fix inconsistencies
3. Store generation timestamps separately
4. Monitor for orphaned status situations

### For Maintainability
1. Document that URLs are the source of truth
2. Add explicit status checks if needed in future
3. Consider state machine validation layer
4. Keep counter recalculation as safety valve

### For Features
1. Add admin UI to reset/retry scenes
2. Add generation history tracking
3. Consider explicit "locked" state for in-progress
4. Add webhook/event system for status changes

---

## How to Use These Documents

### If you need to understand...

**...how status works** → Read STATUS_QUICK_REFERENCE.md

**...why videos regenerate** → Read STATUS_QUICK_REFERENCE.md + VIDEO_STATUS_INVESTIGATION.md

**...the complete architecture** → Read all four documents in order

**...specific code locations** → See "Code References Quick Index" above

**...design decisions** → Read DETAILED_STATUS_ANALYSIS.md

**...state transitions visually** → See STATUS_FLOW_DIAGRAM.txt

---

## File Statistics

| Document | Lines | Focus |
|----------|-------|-------|
| STATUS_QUICK_REFERENCE.md | 262 | TL;DR reference |
| VIDEO_STATUS_INVESTIGATION.md | 455 | Complete analysis |
| DETAILED_STATUS_ANALYSIS.md | 293 | Executive + technical |
| STATUS_FLOW_DIAGRAM.txt | 191 | Visual flows |
| **Total** | **1,201** | Full investigation |

---

## Investigation Methodology

1. **Database exploration** - Examined DynamoDB schema, models, status fields
2. **Code flow tracing** - Followed status updates through backend
3. **Frontend filtering** - Analyzed scene selection logic
4. **Orchestration layer** - Reviewed generation workflow
5. **Edge case analysis** - Identified consistency issues
6. **Reference verification** - Validated all findings with code references

---

## Key Takeaway

> **Status is metadata describing what happened during generation, not a gate that prevents generation. Video URLs are the actual source of truth for what needs to be generated.**

This design works well because:
- URLs are only set after successful S3 upload (reliable)
- Frontend filters based on URL presence (foolproof)
- Status is eventually consistent with actual state
- Idempotent counters catch inconsistencies

---

## Next Steps

If you need to:

1. **Fix regeneration issues** - Check `originalVideoClipUrl` presence
2. **Debug status inconsistencies** - Run `recalculate_scene_counters()`
3. **Implement status-based prevention** - Add checks in backend endpoint
4. **Add manual regeneration** - Create endpoint to reset video URLs
5. **Improve reliability** - Implement atomic status + URL updates

---

**Generated:** November 24, 2025  
**Investigation Scope:** Complete video status management system  
**Status of Findings:** Verified with code references
