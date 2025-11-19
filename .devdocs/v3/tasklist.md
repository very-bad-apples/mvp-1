# v1: Config Flavors System ✅ COMPLETED

## Overview
Refactor the MV config system to support multiple "config flavors" that can be selected at runtime via API parameters. Each flavor represents a different set of prompts and parameters for video/image generation.

**Status**: ✅ Implementation Complete

---

# v2: Frontend Config Flavor UI Integration

## Overview
Add config flavor selection UI to the frontend create page and quick-gen page. Users can select which config flavor to use for video generation, with the selection persisted through the workflow and attached to API requests.

---

## Task List

### 1. Directory Structure Refactor
- [ ] Create new directory structure under `backend/mv/configs/`
  - [ ] Create `default/` subdirectory
  - [ ] Move existing YAML files into `default/`
    - `image_params.yaml`
    - `image_prompts.yaml`
    - `scene_prompts.yaml`
    - `parameters.yaml` (if exists)
- [ ] Create example `flavor1/` subdirectory with sample configs
- [ ] Update `.gitignore` if needed to handle custom flavors

### 2. Multi-Flavor Config Loader
- [ ] Create new module `backend/mv/config_manager.py`
  - [ ] Implement `discover_flavors()` - auto-discover all subdirectories in `configs/`
  - [ ] Implement `load_all_flavors()` - load all YAMLs from all flavors at startup
  - [ ] Create data structure to store configs by flavor:
    ```python
    # Structure: flavors[flavor_name][config_type] = config_dict
    _flavors: dict[str, dict[str, dict]] = {}
    ```
  - [ ] Implement `get_config(flavor: str, config_type: str) -> dict`
    - Returns config for specified flavor
    - Falls back to "default" if flavor not found (with warning log)
    - Falls back to "default" if specific config file missing (with warning log)
  - [ ] Add startup initialization function `initialize_config_flavors()`

### 3. Update Existing Config Loaders
- [ ] Refactor `backend/mv/scene_generator.py`
  - [ ] Replace `load_configs()` with call to config_manager
  - [ ] Remove module-level `_parameters_config` and `_prompts_config`
  - [ ] Update `get_default_parameters()` to accept `config_flavor` param
  - [ ] Update `get_prompt_template()` to accept `config_flavor` param
  - [ ] Update `generate_scenes()` to accept `config_flavor` param and pass through

- [ ] Refactor `backend/mv/video_generator.py`
  - [ ] Replace `load_video_configs()` with call to config_manager
  - [ ] Remove module-level `_video_params_config`
  - [ ] Update `get_default_video_parameters()` to accept `config_flavor` param
  - [ ] Update `generate_video()` to accept `config_flavor` param and pass through

- [ ] Refactor `backend/mv/image_generator.py`
  - [ ] Replace `load_image_configs()` with call to config_manager
  - [ ] Remove module-level `_image_params_config` and `_image_prompts_config`
  - [ ] Update `get_default_image_parameters()` to accept `config_flavor` param
  - [ ] Update `get_character_reference_prompt_template()` to accept `config_flavor` param
  - [ ] Update `generate_character_reference_image()` to accept `config_flavor` param

### 4. API Schema Updates
- [ ] Update `backend/mv/scene_generator.py` - `CreateScenesRequest`
  - [ ] Add optional `config_flavor: Optional[str] = Field(None, description="Config flavor to use (defaults to 'default')")`

- [ ] Update `backend/mv/video_generator.py` - `GenerateVideoRequest`
  - [ ] Add optional `config_flavor: Optional[str] = Field(None, description="Config flavor to use (defaults to 'default')")`

- [ ] Update `backend/mv/image_generator.py` - `GenerateCharacterReferenceRequest`
  - [ ] Add optional `config_flavor: Optional[str] = Field(None, description="Config flavor to use (defaults to 'default')")`

### 5. Router/Endpoint Updates
- [ ] Update `backend/routers/mv.py` (or wherever endpoints are defined)
  - [ ] Update `/api/mv/create_scenes` endpoint to pass `config_flavor` to `generate_scenes()`
  - [ ] Update `/api/mv/generate_video` endpoint to pass `config_flavor` to `generate_video()`
  - [ ] Update `/api/mv/generate_character_reference` endpoint to pass `config_flavor` to `generate_character_reference_image()`

### 6. Startup Integration
- [ ] Update `backend/main.py` or app startup
  - [ ] Remove old individual config loader calls
  - [ ] Add single call to `initialize_config_flavors()`
  - [ ] Verify all flavors loaded successfully on startup

- [ ] Update `backend/worker_mv.py` (if exists)
  - [ ] Ensure worker also calls `initialize_config_flavors()` on startup

### 7. Debug Logging Enhancement
- [ ] Update `backend/mv/debug.py`
  - [ ] Add `log_flavors_discovered(flavors: list[str])` - log at startup
  - [ ] Add `log_flavor_selected(flavor: str, config_type: str)` - log at prompt time
  - [ ] Add `log_flavor_config_loaded(flavor: str, config_type: str, config: dict)` - log config values at prompt time
  - [ ] Add `log_flavor_fallback_warning(requested_flavor: str, config_type: str, fallback: str)` - log when falling back to default

- [ ] Update config_manager to use debug logging:
  - [ ] Log all discovered flavors at startup (when MV_DEBUG_MODE=true)
  - [ ] Log flavor name at prompt time (when MV_DEBUG_MODE=true)
  - [ ] Log full config values at prompt time (when MV_DEBUG_MODE=true)
  - [ ] Log fallback warnings when flavor/config not found

- [ ] Update scene_generator, video_generator, image_generator
  - [ ] Add debug logs when loading config flavor at prompt time
  - [ ] Include flavor name in existing debug logs

### 8. Testing
- [ ] Create test configs under `configs/test_flavor/`
  - [ ] Create modified versions of all YAML files with distinct values

- [ ] Write unit tests for `config_manager.py`
  - [ ] Test flavor discovery
  - [ ] Test config loading
  - [ ] Test fallback to default when flavor not found
  - [ ] Test fallback to default when specific config file missing

- [ ] Write integration tests
  - [ ] Test scene generation with custom flavor
  - [ ] Test video generation with custom flavor
  - [ ] Test image generation with custom flavor
  - [ ] Test default flavor when no config_flavor specified
  - [ ] Test invalid flavor falls back to default

- [ ] Manual testing with MV_DEBUG_MODE=true
  - [ ] Verify startup logs show all discovered flavors
  - [ ] Verify prompt-time logs show selected flavor and config values
  - [ ] Verify fallback warnings appear when appropriate

### 9. Documentation
- [ ] Update `.devdocs/v3/feats.md`
  - [ ] Add completion note to v1 section
  - [ ] Document final implementation approach

- [ ] Create `.devdocs/v3/config-flavors.md`
  - [ ] Document config flavor system architecture
  - [ ] Provide examples of creating custom flavors
  - [ ] Document API usage with `config_flavor` parameter
  - [ ] Document debug logging output

- [ ] Update API documentation (if exists)
  - [ ] Document new `config_flavor` parameter for all three endpoints

### 10. Migration & Cleanup
- [ ] Verify backward compatibility
  - [ ] Ensure existing API calls without `config_flavor` work (use default)
  - [ ] Verify all existing tests still pass

- [ ] Remove deprecated code
  - [ ] Remove old module-level config storage if fully replaced
  - [ ] Clean up any unused import statements

- [ ] Add example flavor
  - [ ] Create `configs/example/` with sample alternative configs
  - [ ] Add comments explaining customization options

---

## Implementation Notes

### Config Manager Data Structure
```python
# backend/mv/config_manager.py
_flavors: dict[str, dict[str, dict]] = {
    "default": {
        "image_params": {...},
        "image_prompts": {...},
        "scene_prompts": {...},
        "parameters": {...}
    },
    "flavor1": {
        "image_params": {...},
        "image_prompts": {...},
        ...
    }
}
```

### API Usage Example
```python
# Request with custom flavor
POST /api/mv/create_scenes
{
    "idea": "sunset beach scene",
    "character_description": "surfer",
    "config_flavor": "cinematic"  # <-- new parameter
}

# Request with default flavor (backward compatible)
POST /api/mv/create_scenes
{
    "idea": "sunset beach scene",
    "character_description": "surfer"
    # config_flavor omitted = uses "default"
}
```

### Debug Log Examples
```
# At startup (MV_DEBUG_MODE=true)
INFO: config_flavors_discovered flavors=['default', 'cinematic', 'vlog_style']

# At prompt time (MV_DEBUG_MODE=true)
INFO: config_flavor_selected flavor='cinematic' config_type='scene_prompts'
DEBUG: scene_prompts_config={'scene_generation_prompt': '...full prompt...'}
```

---

## Definition of Done
- [ ] All config YAMLs moved to `configs/default/`
- [ ] Config manager successfully loads all flavors at startup
- [ ] All three endpoints accept optional `config_flavor` parameter
- [ ] Flavor selection works correctly with fallback to default
- [ ] Debug logging shows flavor discovery and selection
- [ ] All tests pass (unit + integration)
- [ ] Documentation complete
- [ ] Backward compatibility maintained

---

# v2: Frontend Config Flavor UI Integration

## Task List

### 1. Backend API Endpoint
- [ ] Create `/api/mv/get_config_flavors` endpoint in `backend/routers/mv.py`
  - [ ] Import `get_discovered_flavors` from `config_manager`
  - [ ] Return JSON array of available flavor names
  - [ ] Add API documentation/docstring
  - [ ] Response schema: `{"flavors": ["default", "example", ...]}`

### 2. Create Page - Configuration Section UI
- [ ] Create collapsible Configuration section in `frontend/src/app/create/page.tsx`
  - [ ] Position between "Generation Mode" and "Video Description" sections
  - [ ] Use Collapsible component (or Accordion) - collapsed by default
  - [ ] Header: "Configuration" with chevron icon for expand/collapse
  - [ ] Add state: `const [isConfigExpanded, setIsConfigExpanded] = useState(false)`

- [ ] Add Config Flavor select box inside Configuration section
  - [ ] Add state: `const [configFlavor, setConfigFlavor] = useState<string>('default')`
  - [ ] Label: "Config Flavor"
  - [ ] Use Select component from shadcn/ui
  - [ ] Default value: "default"
  - [ ] Fetch available flavors from `/api/mv/get_config_flavors` on mount
  - [ ] Add state: `const [availableFlavors, setAvailableFlavors] = useState<string[]>(['default'])`
  - [ ] Add loading state while fetching flavors
  - [ ] Handle fetch errors gracefully (fallback to ['default'])

### 3. Create Page - Data Passing
- [ ] Update `quickJobData` object in `handleQuickGenerate` function
  - [ ] Add `configFlavor` field to sessionStorage data
  ```typescript
  const quickJobData = {
    videoDescription: prompt,
    characterDescription: characterDescription,
    characterReferenceImageId: ...,
    audioId: ...,
    audioUrl: ...,
    audioTitle: ...,
    configFlavor: configFlavor, // NEW
  }
  ```

### 4. Quick-Gen Page - Data Types
- [ ] Update `QuickJobData` interface in `frontend/src/app/quick-gen-page/page.tsx`
  ```typescript
  interface QuickJobData {
    videoDescription: string
    characterDescription: string
    characterReferenceImageId: string
    audioId?: string
    audioUrl?: string
    audioTitle?: string
    configFlavor?: string // NEW
  }
  ```

### 5. Quick-Gen Page - Configuration Section UI
- [ ] Add Configuration section above "Input Data" card
  - [ ] Use same collapsible Card style as "Input Data"
  - [ ] Header: "Configuration" with chevron icon
  - [ ] Collapsed by default
  - [ ] Add state: `const [isConfigExpanded, setIsConfigExpanded] = useState(false)`

- [ ] Add Config Flavor select box inside Configuration section
  - [ ] Add state for current selection
  - [ ] Fetch available flavors from `/api/mv/get_config_flavors` on mount
  - [ ] Initialize with value from sessionStorage (from create page)
  - [ ] Allow user to change selection
  - [ ] Use Select component from shadcn/ui

### 6. Quick-Gen Page - Input Data Display
- [ ] Update "Input Data" card to display config flavor
  - [ ] Find the CardContent section showing video description, character, etc.
  - [ ] Add new row showing selected config flavor
  ```tsx
  <div className="space-y-2">
    <p className="text-sm text-gray-400">Config Flavor:</p>
    <p className="text-white">{jobData.configFlavor || 'default'}</p>
  </div>
  ```

### 7. Quick-Gen Page - API Integration
- [ ] Update `generateScenes` function
  - [ ] Add `config_flavor` parameter to `/api/mv/create_scenes` request body
  - [ ] Use current selected flavor value from state
  ```typescript
  const response = await fetch(`${API_URL}/api/mv/create_scenes`, {
    method: 'POST',
    body: JSON.stringify({
      idea: jobData.videoDescription,
      character_description: jobData.characterDescription,
      config_flavor: selectedConfigFlavor, // NEW
      // ... other params
    })
  })
  ```

- [ ] Update `generateVideoForScene` function
  - [ ] Add `config_flavor` parameter to `/api/mv/generate_video` request body
  - [ ] Use current selected flavor value from state
  ```typescript
  const response = await fetch(`${API_URL}/api/mv/generate_video`, {
    method: 'POST',
    body: JSON.stringify({
      prompt: scene.description,
      negative_prompt: scene.negative_description,
      character_reference_id: jobData.characterReferenceImageId,
      config_flavor: selectedConfigFlavor, // NEW
      // ... other params
    })
  })
  ```

### 8. UI/UX Polish
- [ ] Create page Configuration section styling
  - [ ] Match existing section styles
  - [ ] Ensure proper spacing with adjacent sections
  - [ ] Add subtle border/background to distinguish section
  - [ ] Smooth collapse/expand animation

- [ ] Quick-gen page Configuration section styling
  - [ ] Match "Input Data" card styling
  - [ ] Consistent collapse/expand behavior
  - [ ] Proper spacing above "Input Data" card

- [ ] Select component styling
  - [ ] Dark mode compatible (match existing UI)
  - [ ] Clear label and help text
  - [ ] Accessible dropdown behavior
  - [ ] Show loading state while fetching flavors

### 9. Error Handling
- [ ] Create page error handling
  - [ ] Handle API fetch failures for `/get_config_flavors`
  - [ ] Show fallback UI if flavors can't be loaded
  - [ ] Toast notification for errors (optional)
  - [ ] Default to 'default' flavor on error

- [ ] Quick-gen page error handling
  - [ ] Handle missing configFlavor in sessionStorage
  - [ ] Default to 'default' if not provided from create page
  - [ ] Handle flavor fetch errors
  - [ ] Validate flavor exists before using in API calls

### 10. Testing & Validation
- [ ] Manual testing - Create page
  - [ ] Configuration section collapses/expands correctly
  - [ ] Config Flavor select populates with flavors from API
  - [ ] Selection persists when navigating to quick-gen
  - [ ] Default flavor selected initially

- [ ] Manual testing - Quick-gen page  
  - [ ] Receives config flavor from create page
  - [ ] Displays config flavor in Input Data
  - [ ] Configuration section allows changing flavor
  - [ ] Changed flavor applies to scene generation
  - [ ] Changed flavor applies to video generation
  - [ ] API requests include correct config_flavor parameter

- [ ] Edge cases
  - [ ] Direct navigation to quick-gen (no sessionStorage data)
  - [ ] Invalid flavor name in sessionStorage
  - [ ] API endpoint unavailable
  - [ ] Empty flavors array from API

### 11. Documentation
- [ ] Update `.devdocs/v3/feats.md`
  - [ ] Add completion note to v2 section
  - [ ] Document final implementation approach
  - [ ] Add screenshots/examples (optional)

- [ ] Code comments
  - [ ] Document sessionStorage data structure
  - [ ] Explain config flavor data flow
  - [ ] Document API integration points

---

## Implementation Notes

### API Endpoint Example
```python
# backend/routers/mv.py
@router.get("/get_config_flavors")
async def get_config_flavors():
    """Get list of available config flavors."""
    from mv.config_manager import get_discovered_flavors
    flavors = get_discovered_flavors()
    return {"flavors": flavors}
```

### SessionStorage Data Structure
```typescript
// Stored in sessionStorage under key 'quickJobData'
{
  "videoDescription": "...",
  "characterDescription": "...",
  "characterReferenceImageId": "uuid-here",
  "audioId": "audio-uuid",
  "audioUrl": "/api/audio/...",
  "audioTitle": "Song Name",
  "configFlavor": "example"  // NEW field
}
```

### Create Page UI Structure
```
┌─────────────────────────────────────┐
│ Generation Mode                     │  ← Existing section
├─────────────────────────────────────┤
│ ▶ Configuration          [collapsed]│  ← NEW section (collapsed by default)
│   └─ Config Flavor: [default ▼]    │
├─────────────────────────────────────┤
│ Video Description *                 │  ← Existing section
└─────────────────────────────────────┘
```

### Quick-Gen Page UI Structure
```
┌─────────────────────────────────────┐
│ ▶ Configuration          [collapsed]│  ← NEW section
│   └─ Config Flavor: [example ▼]    │
├─────────────────────────────────────┤
│ ▼ Input Data            [expanded]  │  ← Existing section
│   ├─ Video Description: ...        │
│   ├─ Character: ...                │
│   └─ Config Flavor: example        │  ← NEW display row
└─────────────────────────────────────┘
```

---

## Definition of Done
- [ ] `/api/mv/get_config_flavors` endpoint returns available flavors
- [ ] Create page has collapsible Configuration section with flavor select
- [ ] Config flavor persists from create page to quick-gen page
- [ ] Quick-gen page displays received config flavor
- [ ] Quick-gen page allows changing config flavor
- [ ] `create_scenes` API calls include `config_flavor` parameter
- [ ] `generate_video` API calls include `config_flavor` parameter
- [ ] Error handling for missing/invalid flavors
- [ ] UI matches existing dark theme styling
- [ ] All manual tests pass
