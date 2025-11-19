# Documentation Review Report

**Date**: 2025-11-18  
**Scope**: System-level and architectural documentation review  
**Files Reviewed**: `_docs/`, `backend/_docs/`, all README.md files

---

## Executive Summary

This review identified **8 critical discrepancies** and **5 minor inconsistencies** between documentation and codebase implementation. The discrepancies primarily affect:

1. **Technology Stack Versions** (Next.js version mismatch)
2. **API Endpoint Paths** (naming inconsistencies)
3. **Worker System Documentation** (two different workers documented)
4. **Database Status Values** (missing status values in docs)
5. **Architecture Diagrams** (outdated component references)

---

## Critical Discrepancies

### 1. Next.js Version Mismatch ⚠️ **CRITICAL**

**Location**: `_docs/architecture.md:131`, `README.md:32`

**Documentation States**:
- `Framework: Next.js 15 (App Router)`
- `Next.js 15` mentioned in multiple places

**Actual Implementation**:
- `frontend/package.json:29`: `"next": "^14.2.18"`

**Impact**: High - Misleading for developers setting up the project

**Recommendation**: Update all documentation to reflect Next.js 14.2.18

---

### 2. API Endpoint Path Inconsistency ⚠️ **CRITICAL**

**Location**: `backend/_docs/API_ENDPOINTS.md:528`, `_docs/architecture.md:529`

**Documentation States**:
- `GET /api/mv/config-flavors` (with hyphen)

**Actual Implementation**:
- `backend/routers/mv.py:61`: `@router.get("/get_config_flavors")` (with underscore, different prefix)

**Impact**: High - API calls will fail if using documented path

**Recommendation**: 
- Update documentation to use `/api/mv/get_config_flavors` OR
- Rename endpoint to match documentation `/api/mv/config-flavors`

---

### 3. Worker System Documentation Confusion ⚠️ **CRITICAL**

**Location**: `backend/_docs/WORKER.md`

**Documentation States**:
- Documents `worker.py` (legacy ad-creative worker)
- Describes SQLAlchemy database integration
- Mentions `video_generation_queue`

**Actual Implementation**:
- Two separate workers exist:
  - `backend/worker.py` - Legacy ad-creative worker (SQLAlchemy)
  - `backend/worker_mv.py` - MV pipeline worker (DynamoDB)
- MV worker uses different queues: `scene_generation_queue`, `video_composition_queue`

**Impact**: High - Developers may use wrong worker or queue names

**Recommendation**: 
- Split `WORKER.md` into two documents:
  - `WORKER_LEGACY.md` - For `worker.py` (ad-creative)
  - `WORKER_MV.md` - For `worker_mv.py` (MV pipeline)
- Or clearly distinguish sections in single document

---

### 4. Missing Project Status Values ⚠️ **CRITICAL**

**Location**: `_docs/database/DYNAMODB_SCHEMA.md:248-255`

**Documentation States**:
- Project status: `pending`, `generating_scenes`, `processing`, `composing`, `completed`, `failed`

**Actual Implementation**:
- `backend/mv_models.py:79`: Status field allows any string
- `backend/routers/mv.py` uses `"processing"` status before video generation/lipsync
- Architecture doc mentions `"composing"` but code may use different values

**Impact**: Medium - Status transitions may not match documentation

**Recommendation**: 
- Audit all status values used in codebase
- Document complete state machine with transitions
- Add validation to ensure only documented statuses are used

---

### 5. Duplicate Router Documentation ⚠️ **CRITICAL**

**Location**: `backend/routers/projects.py` vs `backend/routers/mv_projects.py`

**Documentation States**:
- `backend/_docs/API_ENDPOINTS.md` mentions MV endpoints
- `_docs/architecture.md` lists `/api/mv/projects/*` endpoints

**Actual Implementation**:
- Two routers exist:
  - `backend/routers/projects.py` - Appears to be duplicate/alternative
  - `backend/routers/mv_projects.py` - Active MV projects router
- Both registered in `main.py:276-277`

**Impact**: High - Confusion about which router is active

**Recommendation**: 
- Determine if `projects.py` is legacy/unused
- Remove or clearly mark as deprecated
- Update documentation to reflect active router only

---

### 6. Configuration Flavor Endpoint Path ⚠️ **MEDIUM**

**Location**: `backend/_docs/API_ENDPOINTS.md:528-538`

**Documentation States**:
- `GET /api/mv/config-flavors`

**Actual Implementation**:
- `backend/routers/mv.py:61`: `/api/mv/get_config_flavors`

**Impact**: Medium - API calls will fail

**Recommendation**: Update documentation to match implementation

---

### 7. Frontend Architecture Description ⚠️ **MEDIUM**

**Location**: `_docs/architecture.md:79-87`, `README.md:32-37`

**Documentation States**:
- "Direct Backend Communication: Removed Next.js API route layer"
- "Type-Safe API Client: Centralized `lib/api/client.ts`"

**Actual Implementation**:
- Need to verify `frontend/src/lib/api/client.ts` exists
- Documentation may be aspirational vs. actual

**Impact**: Medium - Misleading if not implemented

**Recommendation**: Verify implementation exists or mark as "planned"

---

### 8. Database Model Primary Key Description ⚠️ **MEDIUM**

**Location**: `_docs/database/DYNAMODB_SCHEMA.md:13-19`

**Documentation States**:
- Partition Key: `PROJECT#{uuid}` format

**Actual Implementation**:
- `backend/mv_models.py:73`: `PK = UnicodeAttribute(hash_key=True)`
- Code uses `f"PROJECT#{project_id}"` pattern
- Documentation is correct but could be more explicit about format

**Impact**: Low - Documentation is accurate but could be clearer

**Recommendation**: Add explicit format validation examples

---

## Minor Inconsistencies

### 9. Python Version Specification

**Location**: `_docs/architecture.md:152`, `README.md:41`

**Documentation States**: `Python 3.12`

**Actual Implementation**: Need to verify `requirements.txt` or `pyproject.toml`

**Recommendation**: Verify and update if incorrect

---

### 10. Redis Queue Names

**Location**: `backend/_docs/WORKER.md:453-456`

**Documentation States**: 
- Queue: `video_generation_queue`

**Actual Implementation**:
- `backend/worker_mv.py:26-27`: Uses `scene_generation_queue`, `video_composition_queue`

**Impact**: Low - Only affects MV worker (legacy worker uses different queue)

**Recommendation**: Document both queue systems clearly

---

### 11. S3 Key Pattern Documentation

**Location**: `_docs/database/DYNAMODB_SCHEMA.md:189-195`

**Documentation States**:
- Scene video: `mv/projects/{project_id}/scenes/scene_{sequence:03d}.mp4`

**Actual Implementation**:
- `backend/services/s3_storage.py` may use different pattern
- Need to verify actual key generation

**Impact**: Low - Pattern may vary but should be documented accurately

**Recommendation**: Verify actual S3 key patterns in code

---

### 12. Worker Process Description

**Location**: `_docs/architecture.md:114-118`

**Documentation States**:
- "Worker Process: Background job processor, Scene prompt generation, Video clip stitching, Asset management"

**Actual Implementation**:
- `backend/worker_mv.py` is async and handles scene generation and composition
- Separate workers: `scene_worker.py`, `compose_worker.py`

**Impact**: Low - Description is accurate but could mention separation

**Recommendation**: Clarify worker architecture (main worker + specialized workers)

---

### 13. Configuration Flavor Discovery

**Location**: `README.md:260-265`, `_docs/architecture.md:162-172`

**Documentation States**:
- Flavors auto-discovered at startup
- Example shows `cinematic` flavor

**Actual Implementation**:
- `backend/mv/configs/` contains: `default/`, `example/`
- No `cinematic` flavor exists

**Impact**: Low - Example is aspirational

**Recommendation**: Update examples to use actual flavors (`default`, `example`)

---

## Architecture-Level Issues

### 14. Dual Database System Clarity

**Location**: Multiple files

**Documentation States**:
- DynamoDB for MV projects
- SQLite for legacy jobs
- "Independent" systems

**Actual Implementation**:
- Both systems active
- Some confusion about which endpoints use which

**Impact**: Medium - Developers may use wrong database

**Recommendation**: 
- Create clear mapping: Endpoint → Database
- Add architecture diagram showing separation
- Document migration path (if any)

---

### 15. Missing Router Registration Documentation

**Location**: `backend/main.py:270-277`

**Actual Implementation**:
- 8 routers registered:
  - `generate.router` (legacy)
  - `jobs.router` (legacy)
  - `websocket.router`
  - `models.router`
  - `mv.router` (MV pipeline)
  - `audio.router`
  - `projects.router` (duplicate?)
  - `mv_projects.router` (MV projects)

**Documentation**: Not clearly documented which routers are active

**Recommendation**: Add router registration documentation to `backend/README.md`

---

## Recommendations Summary

### Immediate Actions (Critical)

1. ✅ **Update Next.js version** in all documentation (14.2.18, not 15)
2. ✅ **Fix API endpoint paths** - Standardize on `/api/mv/get_config_flavors` or rename endpoint
3. ✅ **Split worker documentation** - Separate legacy vs MV worker docs
4. ✅ **Resolve duplicate routers** - Document which `projects.py` router is active
5. ✅ **Audit status values** - Document complete state machine

### Short-Term Actions (Medium Priority)

6. ✅ **Verify frontend API client** - Confirm `lib/api/client.ts` exists and matches docs
7. ✅ **Document router registration** - Add to `backend/README.md`
8. ✅ **Clarify database separation** - Create endpoint → database mapping
9. ✅ **Update configuration flavor examples** - Use actual flavors

### Long-Term Actions (Low Priority)

10. ✅ **Add architecture diagrams** - Visual representation of system
11. ✅ **Document S3 key patterns** - Verify and document actual patterns
12. ✅ **Add API versioning strategy** - If applicable

---

## Files Requiring Updates

### High Priority
- `_docs/architecture.md` - Next.js version, endpoint paths
- `README.md` - Next.js version, endpoint examples
- `backend/_docs/API_ENDPOINTS.md` - Endpoint paths, worker info
- `backend/_docs/WORKER.md` - Split or clearly separate sections
- `backend/README.md` - Router registration, worker clarification

### Medium Priority
- `_docs/database/DYNAMODB_SCHEMA.md` - Status values, S3 patterns
- `_docs/key-insights.md` - Verify examples match implementation

### Low Priority
- All README.md files - Minor consistency updates

---

## Verification Checklist

Before considering this review complete, verify:

- [ ] Next.js version updated in all docs
- [ ] API endpoint paths match implementation
- [ ] Worker documentation clearly separates legacy vs MV
- [ ] Duplicate router situation resolved
- [ ] Status values documented completely
- [ ] Frontend API client implementation verified
- [ ] Configuration flavor examples use actual flavors
- [ ] Router registration documented
- [ ] Database separation clearly documented

---

**Review Completed**: 2025-11-18  
**Next Review Recommended**: After implementing critical fixes

