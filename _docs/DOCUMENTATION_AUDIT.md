# Documentation Audit Report

**Date**: 2025-11-18  
**Scope**: System and architectural level discrepancies between documentation and codebase

## Executive Summary

This audit identified **8 major discrepancies** and **3 minor inaccuracies** between the documentation and the actual codebase implementation. Most issues relate to missing or outdated information about API endpoints, authentication, and router registration.

---

## Critical Discrepancies

### 1. API Authentication Not Documented

**Issue**: All `/api/` routes require API key authentication via `X-API-Key` header or `?api_key=` query parameter, but this is **not mentioned in any documentation**.

**Location**: `backend/main.py:136-184`

**Impact**: HIGH - Users will get 401 errors when trying to use API endpoints without knowing authentication is required.

**Documentation Affected**:
- `README.md` - No mention of API key requirement
- `_docs/architecture.md` - No authentication section for API endpoints
- `backend/_docs/API_ENDPOINTS.md` - No authentication information
- `backend/README.md` - No authentication setup instructions

**Fix Required**: Add authentication documentation to:
1. Root `README.md` - Quick start section
2. `_docs/architecture.md` - API Architecture section
3. `backend/_docs/API_ENDPOINTS.md` - Add authentication section
4. `backend/README.md` - Environment variables section (document `API_KEY`)

---

### 2. Regenerate Router Exists But Not Registered

**Issue**: `backend/routers/regenerate.py` exists with 6 endpoints (`/jobs/{job_id}/regenerate-scene`, `/jobs/{job_id}/regenerate-voiceover`, `/jobs/{job_id}/recompose`, `/jobs/{job_id}/versions`, `/jobs/{job_id}/rollback`), but the router is **NOT registered** in `main.py`.

**Location**: `backend/routers/regenerate.py` (exists) vs `backend/main.py` (not imported/registered)

**Impact**: MEDIUM - Endpoints are implemented but not accessible. This is either:
- Dead code that should be removed, OR
- Missing registration that should be added

**Documentation Affected**:
- No documentation mentions these endpoints (correct, since they're not registered)
- `backend/README.md` - Should clarify if this is intentional

**Fix Required**: 
- **Decision needed**: Are these endpoints intended to be used?
  - If YES: Register router in `main.py`
  - If NO: Remove `regenerate.py` or document as "planned/future"

---

### 3. Projects Router File Exists But Not Used

**Issue**: `backend/routers/projects.py` exists with endpoints, but `main.py` has a comment saying it was "removed" and uses `mv_projects.py` instead. The file still exists.

**Location**: `backend/main.py:267, 276` (comment says removed) vs `backend/routers/projects.py` (file exists)

**Impact**: LOW - Confusing for developers, but doesn't break functionality

**Documentation Affected**:
- `backend/README.md` - Project structure shows `projects.py` but doesn't clarify it's unused

**Fix Required**: 
- Remove `projects.py` if truly unused, OR
- Document why it exists (legacy? future use?)

---

### 4. Missing Endpoint Documentation

**Issue**: Several registered endpoints are not documented in architecture or API docs:

**Missing from `_docs/architecture.md`**:
- `/api/models/*` - Model configuration endpoints (3 endpoints)
- `/api/audio/*` - Audio download endpoints (3 endpoints)
- `/api/regenerate/*` - Regeneration endpoints (if intended to be used)

**Missing from `backend/_docs/API_ENDPOINTS.md`**:
- `/api/mv/projects/*` - MV Project CRUD endpoints (only mentioned as "see main API docs")
- `/api/models/*` - Model configuration
- `/api/audio/*` - Audio download

**Impact**: MEDIUM - Developers can't find documentation for these endpoints

**Fix Required**: 
- Add endpoint documentation to `_docs/architecture.md` API Architecture section
- Add detailed docs to `backend/_docs/API_ENDPOINTS.md` OR link to Swagger UI

---

### 5. Worker Architecture Mismatch

**Issue**: `backend/_docs/WORKER.md` describes a more complex worker architecture than what's actually implemented in `worker_mv.py`.

**Documentation Says**:
- Worker has health checks, graceful shutdown, retry logic, progress updates
- Multiple stages with progress percentages
- Health status endpoint

**Actual Implementation** (`worker_mv.py`):
- Simple async loop with `brpop` for two queues
- No health checks
- No graceful shutdown handling
- No progress updates via pub/sub
- Just calls `process_scene_generation_job` and `process_composition_job`

**Impact**: MEDIUM - Documentation describes features that don't exist

**Documentation Affected**:
- `backend/_docs/WORKER.md` - Describes legacy worker (`worker.py`) features as if they apply to `worker_mv.py`

**Fix Required**: 
- Update `WORKER.md` to clearly separate:
  - Legacy worker (`worker.py`) - Has all the documented features
  - MV worker (`worker_mv.py`) - Simple queue processor (current implementation)
- Document actual MV worker behavior accurately

---

### 6. Status Values ✅ VERIFIED

**Issue**: Status values in documentation appear to match code usage.

**Documentation Lists**:
- Project: `pending`, `generating_scenes`, `processing`, `composing`, `queued`, `completed`, `failed`
- Scene: `pending`, `processing`, `completed`, `failed`

**Actual Usage** (verified via codebase search):
- ✅ `pending` - Used in `mv_models.py`, `mv_projects.py`, `projects.py`
- ✅ `generating_scenes` - Used in `workers/scene_worker.py`
- ✅ `processing` - Used in `routers/mv.py` for scene status
- ✅ `composing` - Used in `workers/compose_worker.py`, `mv_projects.py`
- ✅ `queued` - Used in `mv_projects.py`, `regenerate.py`
- ✅ `completed` - Used in `workers/compose_worker.py`, `routers/mv.py`
- ✅ `failed` - Used in multiple workers and routers

**Impact**: NONE - Status values match documentation

**Fix Required**: None - documentation is accurate

---

### 7. S3 Key Path Patterns Mismatch ✅ VERIFIED

**Issue**: `_docs/database/DYNAMODB_SCHEMA.md` documents S3 key patterns that **DO NOT match** actual implementation.

**Documentation Says**:
- Scene video: `mv/projects/{project_id}/scenes/scene_{sequence:03d}.mp4`
- Scene audio: `mv/projects/{project_id}/scenes/audio_{sequence:03d}.mp3`

**Actual Implementation** (`backend/services/s3_storage.py:266-296`):
- Scene video: `mv/projects/{project_id}/scenes/{sequence:03d}/video.mp4`
- Scene audio: `mv/projects/{project_id}/scenes/{sequence:03d}/audio.mp3`
- Scene lipsynced: `mv/projects/{project_id}/scenes/{sequence:03d}/lipsynced.mp4`

**Impact**: MEDIUM - Documentation shows incorrect paths, could confuse developers

**Fix Required**: 
- Update `_docs/database/DYNAMODB_SCHEMA.md` S3 Key Patterns section to match actual implementation
- Change from `scenes/scene_{sequence:03d}.mp4` to `scenes/{sequence:03d}/video.mp4`

---

### 8. Missing Router Documentation

**Issue**: `README.md` and architecture docs don't list all registered routers.

**Registered Routers** (from `main.py`):
1. `generate.router` - Legacy generation
2. `jobs.router` - Job status
3. `websocket.router` - WebSocket endpoints
4. `models.router` - Model configuration
5. `mv.router` - MV pipeline endpoints
6. `audio.router` - Audio download
7. `mv_projects.router` - MV Project CRUD

**Documentation Coverage**:
- `README.md` - Lists some endpoints but not all routers
- `_docs/architecture.md` - Mentions some but not comprehensive

**Impact**: LOW - Makes it harder to understand system structure

**Fix Required**: 
- Add router overview to `_docs/architecture.md`
- Update `README.md` project structure section

---

## Minor Inaccuracies

### 9. API Endpoint Path Inconsistencies

**Issue**: Some endpoint paths in documentation don't match actual routes.

**Example**: `_docs/architecture.md` shows `/api/mv/projects/{id}/final-video` but need to verify actual route path.

**Impact**: LOW - May cause confusion

**Fix Required**: Audit all endpoint paths in documentation against actual routes

---

### 10. Configuration Flavor Documentation

**Issue**: `README.md` mentions config flavors but doesn't explain how they're discovered or what happens if a flavor doesn't exist.

**Impact**: LOW - Users may be confused about how to use flavors

**Fix Required**: Add more detail about config flavor system

---

### 11. Database Initialization

**Issue**: `README.md` shows `python init_dynamodb.py` but `main.py` shows `init_dynamodb_tables()` is called automatically on startup.

**Impact**: LOW - Redundant step in docs, but doesn't hurt

**Fix Required**: Clarify that initialization happens automatically OR document manual initialization for first-time setup

---

## Recommendations

### Priority 1 (Critical - Fix Immediately)
1. **Add API authentication documentation** - Users can't use API without this
2. **Resolve regenerate router** - Either register it or remove it
3. **Update worker documentation** - Separate legacy vs MV worker clearly

### Priority 2 (Important - Fix Soon)
4. **Document missing endpoints** - Add `/api/models/*` and `/api/audio/*` to architecture docs
5. **Verify status values** - Ensure schema doc matches code
6. **Clean up unused files** - Remove or document `projects.py`

### Priority 3 (Nice to Have)
7. **Add router overview** - Comprehensive list of all routers
8. **Verify S3 key patterns** - Ensure documentation matches implementation
9. **Clarify configuration flavors** - More detailed usage instructions

---

## Files That Need Updates

1. `README.md` - Add authentication, verify endpoint list
2. `_docs/architecture.md` - Add authentication section, complete endpoint list
3. `backend/_docs/API_ENDPOINTS.md` - Add authentication, MV project endpoints
4. `backend/_docs/WORKER.md` - Separate legacy vs MV worker sections
5. `backend/README.md` - Add API_KEY to environment variables
6. `_docs/database/DYNAMODB_SCHEMA.md` - Verify status values and S3 patterns
7. `backend/main.py` - Decision needed on `regenerate.py` router
8. `backend/routers/projects.py` - Remove or document why it exists

---

## Verification Checklist

Before considering this audit complete, verify:

- [ ] All status values in schema doc match code usage
- [ ] All S3 key patterns in schema doc match `s3_storage.py` implementation
- [ ] All endpoint paths in architecture doc match actual routes
- [ ] All registered routers are documented
- [ ] Authentication is documented in all relevant places
- [ ] Worker documentation accurately describes both workers
- [ ] Unused files are removed or documented

---

**Next Steps**: Review this audit, prioritize fixes, and update documentation accordingly.

