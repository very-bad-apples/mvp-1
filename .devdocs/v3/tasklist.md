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

---

# v3: Lipsync Integration with Quick-Gen Page

## Overview
Integrate lipsync capability with the quick-gen-page, allowing users to regenerate individual video clips with lipsync applied using the audio from the original YouTube video.

## Task List

### Backend Tasks

#### Task 1: Update Lipsync API Endpoint
**File**: `backend/routers/mv.py`

- [ ] 1.1: Make `video_url` and `audio_url` optional parameters in lipsync endpoint
- [ ] 1.2: Add optional `video_id` parameter to lipsync request schema
- [ ] 1.3: Add optional `audio_id` parameter to lipsync request schema
- [ ] 1.4: Add optional `start_time` parameter (float) to lipsync request schema
- [ ] 1.5: Add optional `end_time` parameter (float) to lipsync request schema
- [ ] 1.6: Implement URL lookup logic for `video_id` (similar to `/api/mv/get_video/{id}`)
- [ ] 1.7: Implement URL lookup logic for `audio_id` (similar to `/api/audio/get/{id}`)
- [ ] 1.8: Implement audio clipping logic using start_time and end_time before Replicate API call
- [ ] 1.9: Update lipsync endpoint to use looked-up URLs when IDs are provided
- [ ] 1.10: Ensure backwards compatibility (direct URLs still work)
- [ ] 1.11: Add error handling for invalid IDs
- [ ] 1.12: Add error handling for audio clipping failures

**Notes**:
- The endpoint should prioritize IDs over URLs if both are provided
- Use existing patterns from `get_video` and `get_audio` endpoints for URL lookup
- Audio comes from the clipped version of YouTube audio attached to this generation

#### Task 2: Verify Video/Audio Retrieval Endpoints
**Files**: `backend/routers/mv.py`, `backend/routers/audio.py`

- [ ] 2.1: Verify `/api/mv/get_video/{id}` returns correct URL format
- [ ] 2.2: Verify `/api/audio/get/{id}` returns correct URL format
- [ ] 2.3: Document the ID-to-URL lookup pattern for consistency

### Frontend Tasks

#### Task 3: Add Lipsync UI to Video Cards
**File**: `frontend/src/app/quick-gen-page/page.tsx`

- [ ] 3.1: Add `lipsyncEnabled` state array (one boolean per video index)
- [ ] 3.2: Add checkbox component next to each video's "Regenerate" button (NOT scene regenerate)
- [ ] 3.3: Update button text to "Regenerate with lipsync" when checkbox is checked
- [ ] 3.4: Keep regular "Regenerate" text when checkbox is unchecked
- [ ] 3.5: Style checkbox to be visually aligned with regenerate button
- [ ] 3.6: Ensure checkbox only appears for video regenerate, NOT scene regenerate

**Notes**:
- This applies ONLY to the video regenerate buttons in the video section of each card
- Each video card needs its own checkbox state
- The checkbox should be clearly associated with the regenerate button

#### Task 4: Implement Lipsync Request Flow
**File**: `frontend/src/app/quick-gen-page/page.tsx`

- [ ] 4.1: Create `handleLipsyncRegenerate` function
- [ ] 4.2: Determine which video_id to use (from current scene's video_ids array)
- [ ] 4.3: Determine which audio_id to use (from jobData.audioId)
- [ ] 4.4: Calculate start_time based on scene position (scene_index * 8 seconds)
- [ ] 4.5: Calculate end_time based on scene position (start_time + 8 seconds)
- [ ] 4.6: Call `/api/mv/lipsync` endpoint with video_id, audio_id, start_time, and end_time
- [ ] 4.7: Handle lipsync API response (get new video ID)
- [ ] 4.8: Replace the current video clip with lipsynced version in UI
- [ ] 4.9: Update the scene's video_ids array with new lipsynced video ID
- [ ] 4.10: Update video URL/source in UI to display lipsynced video
- [ ] 4.11: Auto-trigger stitch-video with all current video IDs after lipsync completes
- [ ] 4.12: Update final stitched video in UI
- [ ] 4.13: Add error handling and user feedback for failed lipsync
- [ ] 4.14: Add error handling for failed auto-restitch

**Notes**:
- Audio comes from jobData.audioId (the clipped YouTube audio)
- The lipsynced video replaces the existing video in both UI and state
- video_ids array must be updated to track the latest version
- Each clip is assumed to be 8 seconds long starting at time 0
- start_time = scene_index * 8, end_time = start_time + 8
- After lipsync completes, automatically trigger re-stitch with all current video IDs

#### Task 5: Add Lipsync Processing Status
**File**: `frontend/src/app/quick-gen-page/page.tsx`

- [ ] 5.1: Add `lipsyncProcessing` state array (one boolean per video index)
- [ ] 5.2: Show processing spinner/status while lipsync is in progress
- [ ] 5.3: Disable regenerate button and checkbox while lipsync is processing
- [ ] 5.4: Show completion message when lipsync finishes successfully
- [ ] 5.5: Show error message if lipsync fails
- [ ] 5.6: Clear processing status after completion/error
- [ ] 5.7: Update status text to indicate "Lipsyncing..." or similar

**Notes**:
- Similar pattern to existing video generation processing status
- Should provide clear feedback during the async lipsync operation
- Prevent multiple concurrent lipsync operations on same video

#### Task 6: Add Re-stitch Button to Final Video Section
**File**: `frontend/src/app/quick-gen-page/page.tsx`

- [ ] 6.1: Add "Re-stitch with current clips" button to final video card
- [ ] 6.2: Position button appropriately in the final video section
- [ ] 6.3: Create `handleRestitch` function
- [ ] 6.4: Collect current/latest video IDs from all scenes (use latest from video_ids arrays)
- [ ] 6.5: Call `/api/mv/stitch_video` endpoint with collected video IDs
- [ ] 6.6: Add processing status for re-stitch operation
- [ ] 6.7: Update final video display with newly stitched video
- [ ] 6.8: Update final video ID in state
- [ ] 6.9: Add error handling for failed re-stitch

**Notes**:
- Use the latest version of each scene's video (including lipsynced versions)
- This triggers a fresh stitch of all current clips
- Should use the most recent video ID from each scene's video_ids array

### Testing Tasks

#### Task 7: Integration Testing

- [ ] 7.1: Test lipsync endpoint with valid video_id and audio_id
- [ ] 7.2: Test lipsync endpoint with invalid IDs (error handling)
- [ ] 7.3: Test backwards compatibility with direct URLs (video_url/audio_url)
- [ ] 7.4: Test video replacement in UI after successful lipsync
- [ ] 7.5: Test video_ids array updates correctly with new lipsynced video ID
- [ ] 7.6: Test re-stitch with mix of original and lipsynced videos
- [ ] 7.7: Test processing status displays correctly during lipsync
- [ ] 7.8: Test checkbox toggle behavior (enabled/disabled states)
- [ ] 7.9: Test button text changes with checkbox state
- [ ] 7.10: Test that checkbox only appears on video regenerate (not scene regenerate)

#### Task 8: End-to-End Testing

- [ ] 8.1: Create full video generation with YouTube audio
- [ ] 8.2: Apply lipsync to one video clip
- [ ] 8.3: Verify lipsynced video replaces original in UI
- [ ] 8.4: Apply lipsync to multiple clips
- [ ] 8.5: Use re-stitch button to create new final video
- [ ] 8.6: Verify final video uses lipsynced versions where applied
- [ ] 8.7: Test error scenarios (network failures, invalid data, missing audio)
- [ ] 8.8: Test workflow without YouTube audio (ensure graceful handling)

## Dependencies

- Task 3 depends on Task 1 (backend API must support video_id/audio_id)
- Task 4 depends on Task 3 (UI elements must exist)
- Task 5 can be done in parallel with Task 4
- Task 6 depends on Tasks 1-5 (re-stitch uses updated video IDs from lipsync operations)
- Task 7 depends on Tasks 1-6 (all features implemented)
- Task 8 depends on Task 7 (integration tests pass)

## Technical Notes

### API Endpoints Used
- `POST /api/mv/lipsync` - Updated with video_id/audio_id/timing support
  - Accepts either (video_url + audio_url) OR (video_id + audio_id)
  - Accepts optional start_time and end_time for audio clipping
  - Clips audio segment before passing to Replicate API
  - Returns new lipsynced video ID
- `GET /api/mv/get_video/{id}` - For video ID to URL lookup
- `GET /api/audio/get/{id}` - For audio ID to URL lookup
- `POST /api/mv/stitch_video` - For re-stitching with current clips
  - Accepts array of video IDs
  - Returns new stitched video ID
  - Triggered automatically after lipsync OR manually via "Re-stitch" button

### State Management
- Track lipsync checkbox state per video: `lipsyncEnabled[sceneIndex]`
- Track lipsync processing state per video: `lipsyncProcessing[sceneIndex]`
- Update video_ids array when lipsync completes: `scenes[i].video_ids.push(newVideoId)`
- Maintain latest video IDs for re-stitch operation (use last element of video_ids arrays)

### Data Flow
1. User checks lipsync checkbox for a video
2. User clicks "Regenerate with lipsync" button
3. Frontend extracts:
   - `video_id`: Current video ID from scene.video_ids[scene.video_ids.length - 1]
   - `audio_id`: From jobData.audioId (YouTube audio clip)
   - `start_time`: scene_index * 8 (assuming 8 seconds per clip)
   - `end_time`: (scene_index * 8) + 8
4. Frontend calls `/api/mv/lipsync` with video_id, audio_id, start_time, end_time
5. Backend looks up URLs, clips audio segment, and calls Replicate lipsync API
6. Backend returns new lipsynced video ID
7. Frontend updates scene.video_ids array and displays new video
8. Frontend auto-triggers `/api/mv/stitch_video` with all current video IDs
9. Frontend updates final stitched video display
10. User can also manually click "Re-stitch with current clips" to re-stitch without regenerating

### UI/UX Considerations
- Clear visual indication of lipsync option (checkbox next to regenerate)
- Processing feedback during async lipsync operations
- Error messages for failed operations (network, API errors)
- Button state management (disabled during processing)
- Smooth replacement of video clips in UI
- Re-stitch button clearly indicates it uses "current clips"
- Only show lipsync checkbox on video regenerate buttons, NOT scene regenerate buttons

### Edge Cases to Handle
- Missing audio_id (no YouTube audio attached to generation)
  - Hide lipsync checkbox or disable it with tooltip
- Invalid video_id or audio_id
  - Show error message, don't crash
- Multiple lipsync operations on same video
  - Keep history in video_ids array (array of all versions)
- Re-stitch with incomplete scenes
  - Only use scenes that have at least one video
- Lipsync operation takes very long
  - Show meaningful progress indicator
  - Consider timeout handling

## Success Criteria

- [ ] Users can check a box next to video regenerate button to enable lipsync
- [ ] Button text changes to "Regenerate with lipsync" when checked
- [ ] Lipsync operation uses video_id and audio_id from current generation
- [ ] Processing status shows clearly during lipsync operation
- [ ] Video clip is replaced with lipsynced version on success
- [ ] video_ids array tracks all versions (original + lipsynced)
- [ ] Re-stitch button creates new final video using latest clips
- [ ] Re-stitch correctly uses lipsynced videos where applied
- [ ] All error cases handled gracefully with user feedback
- [ ] Feature works end-to-end in production environment
- [ ] Lipsync checkbox only appears on video regenerate, not scene regenerate
- [ ] UI clearly distinguishes between original and lipsynced videos (optional enhancement)

---

# v3.1: S3 Upload for Lipsynced Videos

## Overview
Add S3 cloud storage upload for lipsynced videos to match the pattern used in video_generator.py, ensuring videos are accessible via presigned URLs with graceful fallback to local storage.

## Task List

### Backend Implementation

#### Task 1: Add Required Imports
**File**: `backend/mv/lipsync.py`

- [ ] 1.1: Add `import asyncio` at top of file
- [ ] 1.2: Add `import concurrent.futures` at top of file
- [ ] 1.3: Verify `get_storage_backend` import already exists (should be present)

**Notes**:
- These imports are needed for async S3 upload from sync context
- `get_storage_backend` was already added in v3 implementation

#### Task 2: Implement S3 Upload Logic
**File**: `backend/mv/lipsync.py` (in `generate_lipsync()` function, after video is saved locally)

- [ ] 2.1: Initialize `cloud_urls = {}` before upload attempt
- [ ] 2.2: Add conditional check: `if settings.STORAGE_BUCKET:`
- [ ] 2.3: Define nested async function `upload_job_to_cloud()`:
  - Initialize storage backend
  - Upload video to `f"mv/jobs/{output_video_id}/video.mp4"`
  - Return dict with "video" key containing presigned URL
- [ ] 2.4: Implement ThreadPoolExecutor pattern:
  - Define `run_upload()` function that calls `asyncio.run(upload_job_to_cloud())`
  - Create ThreadPoolExecutor context
  - Submit upload job with 300-second timeout
  - Capture result in `cloud_urls`
- [ ] 2.5: Add try-except wrapper around upload block
- [ ] 2.6: Log success with `logger.info()`
- [ ] 2.7: Catch exceptions and log with `logger.warning()` (non-fatal)
- [ ] 2.8: Add comment: `# Continue without cloud upload - local files are still available`

**Notes**:
- Follow exact pattern from video_generator.py lines 394-453
- Upload failures should not crash lipsync operation
- Local files remain available as fallback

#### Task 3: Enhance Metadata and Return Values
**File**: `backend/mv/lipsync.py` (in `generate_lipsync()` function, before return statement)

- [ ] 3.1: Add `metadata["cloud_urls"] = cloud_urls` if upload succeeded
- [ ] 3.2: Add `metadata["cloud_url"] = cloud_urls.get("video")` for backward compatibility
- [ ] 3.3: Add `metadata["local_video_url"] = f"/api/mv/get_video/{output_video_id}"` always
- [ ] 3.4: Update `video_url_path` conditional:
  - Use `cloud_urls.get("video")` if cloud upload succeeded
  - Otherwise use `f"/api/mv/get_video/{output_video_id}"`

**Notes**:
- Maintains backward compatibility with existing API consumers
- Cloud URL is preferred but local URL is always available

### Testing Tasks

#### Task 4: Integration Testing

- [ ] 4.1: Test lipsync with cloud storage configured (STORAGE_BUCKET set)
- [ ] 4.2: Verify video uploads to S3 at correct path `mv/jobs/{id}/video.mp4`
- [ ] 4.3: Verify presigned URL is returned in response
- [ ] 4.4: Verify metadata includes all URL fields (cloud_urls, cloud_url, local_video_url)
- [ ] 4.5: Test lipsync without cloud storage configured (STORAGE_BUCKET empty)
- [ ] 4.6: Verify local file path is returned as fallback
- [ ] 4.7: Test S3 upload failure scenario (invalid credentials)
- [ ] 4.8: Verify operation continues successfully with local fallback
- [ ] 4.9: Verify warning is logged on upload failure (not error)
- [ ] 4.10: Verify `/api/mv/get_video/{id}` serves S3 URL for lipsynced videos

## Dependencies

- Task 2 depends on Task 1 (imports must be added first)
- Task 3 depends on Task 2 (upload logic must exist)
- Task 4 depends on Tasks 1-3 (all implementation complete)

## Technical Notes

### S3 Path Pattern
```
mv/jobs/{video_id}/video.mp4
```
Example: `mv/jobs/177adfe0-88fa-41d5-b18f-ba9a4455862f/video.mp4`

### Upload Pattern (from video_generator.py)
```python
cloud_urls = {}
try:
    if settings.STORAGE_BUCKET:
        from services.storage_backend import get_storage_backend

        async def upload_job_to_cloud():
            storage = get_storage_backend()
            urls = {}
            urls["video"] = await storage.upload_file(
                str(video_path),
                f"mv/jobs/{video_id}/video.mp4"
            )
            return urls

        def run_upload():
            return asyncio.run(upload_job_to_cloud())

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_upload)
            cloud_urls = future.result(timeout=300)

        logger.info(f"Uploaded lipsync job {video_id} to cloud storage")
except Exception as e:
    logger.warning(f"Failed to upload lipsync job {video_id} to cloud storage: {e}")
    # Continue without cloud upload - local files are still available
```

### Metadata Enhancement
```python
# If upload succeeded:
metadata["cloud_urls"] = {"video": "https://presigned-url..."}
metadata["cloud_url"] = "https://presigned-url..."  # Backward compat
metadata["local_video_url"] = "/api/mv/get_video/123..."  # Always present

# Set return URL:
video_url_path = cloud_urls.get("video") if cloud_urls else f"/api/mv/get_video/{output_video_id}"
```

### Error Handling Strategy
- **Non-fatal failures**: Upload errors are logged as warnings
- **Graceful degradation**: Operation continues with local files
- **No retries**: Single upload attempt (as specified)
- **No cleanup**: Local files kept even after successful upload

## Success Criteria

- [ ] Lipsynced videos upload to S3 path: `mv/jobs/{video_id}/video.mp4`
- [ ] Metadata includes `cloud_urls`, `cloud_url`, and `local_video_url` fields
- [ ] Upload failures gracefully handled with local fallback
- [ ] Logging matches video_generator pattern (info on success, warning on failure)
- [ ] No breaking changes to API response structure
- [ ] `/api/mv/get_video/{id}` endpoint serves S3 URLs for lipsynced videos
- [ ] Feature works in both cloud-enabled and local-only configurations