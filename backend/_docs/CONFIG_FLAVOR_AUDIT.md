# Config Flavor Usage Audit

**Created:** 2025-11-21  
**Purpose:** Document all places where `config_flavor` and related parameters are used before refactoring

---

## Summary

**Total Files with config_flavor references:** 8  
**Total References:** 68+ lines

**Impact Assessment:**
- **High Impact:** Core scene generation, video generation, image generation
- **Medium Impact:** API endpoints, frontend UI
- **Low Impact:** Documentation, tests

---

## Backend Files

### 1. `backend/mv/scene_generator.py`

**References:** 10 lines

**Functions:**
- `get_default_parameters(config_flavor: Optional[str] = None)` - Line 77
  - **Usage:** Loads default parameters from config flavor
  - **Impact:** HIGH - Core parameter resolution
  - **Action:** Replace with template_loader

- `get_prompt_template(config_flavor: Optional[str] = None)` - Line 104
  - **Usage:** Loads prompt template from config flavor
  - **Impact:** HIGH - Core prompt generation
  - **Action:** Replace with template_loader

- `generate_scenes(..., config_flavor: Optional[str] = None, ...)` - Line 178
  - **Usage:** Passes config_flavor to helper functions
  - **Impact:** HIGH - Main scene generation function
  - **Action:** Remove parameter, use mode-based templates

**Comments:**
- Line 29: Comment about config_flavor parameter
- Line 74: Deprecation comment

**Status:** ✅ Will be refactored in Phase 2

---

### 2. `backend/mv/config_manager.py`

**References:** 15+ lines

**Purpose:** Core config flavor management system

**Functions:**
- `get_config(flavor: Optional[str], config_type: str, ...)` - Line 133
  - **Usage:** Retrieves config for a flavor
  - **Impact:** HIGH - Used throughout codebase
  - **Action:** Mark as deprecated, maintain for legacy support

- `initialize_config_flavors()` - Line 223
  - **Usage:** Loads all flavors at startup
  - **Impact:** MEDIUM - Startup initialization
  - **Action:** Keep for legacy projects, add deprecation warning

**Status:** ✅ Will be deprecated in Phase 5

---

### 3. `backend/routers/mv.py`

**References:** 6 lines

**Endpoints:**
- `GET /api/mv/get_config_flavors` - Line 61
  - **Usage:** Returns list of available config flavors
  - **Impact:** MEDIUM - Frontend uses this
  - **Action:** Remove endpoint (no longer needed)

- `POST /api/mv/create_scenes` - Line 305
  - **Usage:** Accepts config_flavor query parameter
  - **Impact:** MEDIUM - API contract
  - **Action:** Remove parameter

- `POST /api/mv/generate_video` - Line 568
  - **Usage:** Accepts config_flavor query parameter
  - **Impact:** MEDIUM - API contract
  - **Action:** Remove parameter

- `POST /api/mv/generate_image` - Line 1009
  - **Usage:** Accepts config_flavor query parameter
  - **Impact:** MEDIUM - API contract
  - **Action:** Remove parameter

**Status:** ✅ Will be updated in Phase 4

---

### 4. `backend/routers/mv_projects.py`

**References:** 0 direct references (uses generate_scenes which has config_flavor)

**Functions:**
- `generate_scenes_and_videos_background()` - Line 45
  - **Usage:** Calls generate_scenes() (which accepts config_flavor)
  - **Impact:** HIGH - Background task for project generation
  - **Action:** Update to use new generate_scenes signature

**Status:** ✅ Will be updated in Phase 4 (Task 4.2)

---

### 5. `backend/mv/video_generator.py`

**References:** 8+ lines

**Functions:**
- `get_default_video_parameters(config_flavor: Optional[str] = None)` - Line 130
  - **Usage:** Loads video generation parameters
  - **Impact:** MEDIUM - Video generation uses config
  - **Action:** Note: Video generator refactor is out of scope for this migration
  - **Note:** Video generator may need separate refactor later

- `generate_video(..., config_flavor: Optional[str] = None, ...)` - Line 188
  - **Usage:** Video generation endpoint
  - **Impact:** MEDIUM - API contract
  - **Action:** Out of scope for this migration (scene generation only)

**Status:** ⚠️ Out of scope - Video generator refactor is separate

---

### 6. `backend/mv/image_generator.py`

**References:** 6+ lines

**Functions:**
- `get_default_image_parameters(config_flavor: Optional[str] = None)` - Line 65
- `get_character_reference_prompt_template(config_flavor: Optional[str] = None)` - Line 88
- `generate_character_reference_image(..., config_flavor: Optional[str] = None, ...)` - Line 117

**Status:** ⚠️ Out of scope - Image generator refactor is separate

---

### 7. `backend/workers/scene_worker.py`

**References:** 3 lines

**Usage:**
- Line 56: Comment about config_flavor
- Line 57: Hardcoded `config_flavor = "default"`
- Line 60: Uses `get_config(config_flavor, "parameters")`

**Impact:** MEDIUM - Worker process
**Action:** Update to use mode-based templates

**Status:** ✅ Will be updated in Phase 4

---

### 8. `backend/main.py`

**References:** 3 lines

**Usage:**
- Line 67-68: Calls `initialize_config_flavors()` at startup
- Line 69: Log message

**Impact:** LOW - Startup initialization
**Action:** Keep for legacy support, add deprecation comment

**Status:** ✅ Will be updated in Phase 5

---

### 9. `backend/tests/mv/test_scene_generator.py`

**References:** 2 lines

**Tests:**
- `test_generate_scenes_with_config_flavor_and_director()` - Line 290
  - **Usage:** Tests config_flavor parameter
  - **Impact:** LOW - Test code
  - **Action:** Update test to use mode instead

- `test_get_default_parameters_fallback()` - Line 71
  - **Usage:** Tests get_default_parameters function
  - **Impact:** LOW - Test code
  - **Action:** Update or remove test

**Status:** ✅ Will be updated in Phase 6

---

## Frontend Files

### 1. `frontend/src/app/create/page.tsx`

**References:** 6 lines

**Usage:**
- Line 49: State declaration `const [configFlavor, setConfigFlavor] = useState<string>('default')`
- Line 60-75: `fetchConfigFlavors()` useEffect
- Line 263: Sends configFlavor in API request
- Line 462-463: UI selector for config flavor

**Impact:** HIGH - User-facing UI
**Action:** Remove state, remove UI component, remove API call

**Status:** ✅ Will be updated in Phase 3 (Task 3.1)

---

### 2. `frontend/src/app/quick-gen-page/page.tsx`

**References:** 22 lines

**Usage:**
- Similar to create page - config flavor state and UI
- Multiple references throughout component

**Impact:** MEDIUM - Quick generation workflow
**Action:** Remove config flavor UI (may be separate refactor)

**Status:** ⚠️ Out of scope - Quick-gen may be separate refactor

---

### 3. `frontend/src/lib/api/client.ts`

**References:** 1 line

**Functions:**
- `getConfigFlavors()` - Line 558
  - **Usage:** Fetches available config flavors from API
  - **Impact:** MEDIUM - API client
  - **Action:** Remove function

**Status:** ✅ Will be updated in Phase 3 (Task 3.2)

---

## Documentation Files

### 1. `backend/_docs/API_ENDPOINTS.md`

**References:** 10+ lines

**Usage:**
- Documents config_flavor query parameter
- Examples with config_flavor

**Impact:** LOW - Documentation only
**Action:** Update documentation

**Status:** ✅ Will be updated in Phase 7 (Task 7.3)

---

## Migration Impact Summary

### High Priority (Must Update)
1. ✅ `backend/mv/scene_generator.py` - Core functionality
2. ✅ `backend/routers/mv_projects.py` - Background task
3. ✅ `frontend/src/app/create/page.tsx` - User interface
4. ✅ `frontend/src/lib/api/client.ts` - API client

### Medium Priority (Should Update)
5. ✅ `backend/routers/mv.py` - API endpoints
6. ✅ `backend/workers/scene_worker.py` - Worker process
7. ✅ `backend/tests/mv/test_scene_generator.py` - Tests

### Low Priority (Documentation/Deprecation)
8. ✅ `backend/mv/config_manager.py` - Mark deprecated
9. ✅ `backend/main.py` - Add deprecation comment
10. ✅ `backend/_docs/API_ENDPOINTS.md` - Update docs

### Out of Scope (Separate Refactors)
- ⚠️ `backend/mv/video_generator.py` - Video generation (separate refactor)
- ⚠️ `backend/mv/image_generator.py` - Image generation (separate refactor)
- ⚠️ `frontend/src/app/quick-gen-page/page.tsx` - Quick-gen workflow (may be separate)

---

## Breaking Changes

### API Breaking Changes
1. **Removed:** `GET /api/mv/get_config_flavors` endpoint
2. **Removed:** `config_flavor` query parameter from:
   - `POST /api/mv/create_scenes`
   - `POST /api/mv/generate_video`
   - `POST /api/mv/generate_image`
3. **Changed:** `generate_scenes()` function signature (removed config_flavor parameter)

### Frontend Breaking Changes
1. **Removed:** Config flavor selector UI component
2. **Removed:** `configFlavor` state variable
3. **Removed:** `getConfigFlavors()` API client function

### Backend Breaking Changes
1. **Deprecated:** `get_default_parameters()` function
2. **Deprecated:** `get_prompt_template()` function
3. **Deprecated:** `config_manager.py` module (kept for legacy support)

---

## Migration Strategy

### Phase 0: ✅ Preparation (Current)
- Create template directory structure
- Extract templates from existing configs
- Document current usage (this file)

### Phase 1: Template System
- Create template_loader.py
- Implement mode-based template loading

### Phase 2: Scene Generator
- Refactor generate_scenes() to use templates
- Remove config_flavor parameter

### Phase 3: Frontend
- Remove config flavor UI
- Update API client

### Phase 4: API Routers
- Update endpoints
- Update background tasks

### Phase 5: Deprecation
- Mark old functions as deprecated
- Archive old configs

### Phase 6: Testing
- Update tests
- End-to-end validation

### Phase 7: Documentation
- Update all docs
- Create migration guide

---

## Notes

- **Legacy Support:** Old config_manager.py will be kept for legacy projects that don't have a `mode` field
- **Gradual Migration:** Background task will check for mode field and use appropriate generator
- **No Data Loss:** Existing projects will continue to work via legacy path

---

**Audit Complete:** 2025-11-21

