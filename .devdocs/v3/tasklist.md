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

---

# v4: Music Video Config Flavor (`mv1`)

## Overview
Create a new config flavor `mv1` optimized for generating music videos featuring a band and lead singer performing at an outdoor stadium venue. This config will modify scene generation prompts and parameters to produce concert/performance-style videos with appropriate camera work, staging, and audience elements.

## Task List

### 1. Create mv1 Config Directory
**Location**: `backend/mv/configs/`

- [ ] 1.1: Copy the entire `default/` directory to create `mv1/` directory
- [ ] 1.2: Verify all YAML files copied successfully:
  - `scene_prompts.yaml`
  - `parameters.yaml`
  - `image_params.yaml` (copied but not modified)
  - `image_prompts.yaml` (if exists - copied but not modified)

**Commands**:
```bash
cd backend/mv/configs/
cp -r default/ mv1/
```

### 2. Update scene_prompts.yaml for Music Video
**File**: `backend/mv/configs/mv1/scene_prompts.yaml`

- [ ] 2.1: Read current `default/scene_prompts.yaml` to understand structure
- [ ] 2.2: Update `scene_generation_prompt` (or equivalent prompt field):
  - Add outdoor stadium performance context
  - Specify live concert/music video aesthetic
  - Include band and lead singer performance elements
  - Add staging and lighting descriptions
  - Specify camera work variety (wide shots, close-ups)
  - Include selective audience presence
  - Maintain character consistency references

- [ ] 2.3: Update prompt to ensure scene variety:
  - At least one scene with close-up of lead singer's face
  - Mix of wide stadium shots showing full band
  - Medium shots of band performing
  - Some scenes with audience visible
  - Some scenes focused only on performers
  - Dynamic stage lighting and outdoor atmosphere

- [ ] 2.4: Update negative prompts (if present):
  - Add negative terms to avoid (e.g., indoor venues, studio settings, static/boring performances)
  - Maintain quality-related negative prompts from default

**Key Elements to Include**:
- Outdoor stadium setting
- Stage with professional lighting
- Full band (drums, guitar, bass, keyboards/instruments)
- Prominent lead singer
- Dynamic performance energy
- Concert atmosphere
- Selective audience presence (excited crowd in background for some scenes)
- Professional camera work (mix of wide and close-up shots)

### 3. Update parameters.yaml for Music Video
**File**: `backend/mv/configs/mv1/parameters.yaml`

- [ ] 3.1: Read current `default/parameters.yaml` to understand structure
- [ ] 3.2: Review and adjust generation parameters as needed:
  - Camera movement parameters (if applicable) - more dynamic for concert feel
  - Scene duration/timing parameters (if applicable)
  - Any scene-count or pacing parameters
  - Aspect ratio considerations (if configurable)

- [ ] 3.3: Update any prompt-related parameters:
  - Strength/weight of certain prompt elements
  - Negative prompt weights
  - Scene variety parameters

- [ ] 3.4: Add comments documenting mv1-specific parameter choices
- [ ] 3.5: Ensure parameters align with music video aesthetic (energetic, dynamic)

**Notes**:
- Review what parameters actually exist in the default config first
- Only modify parameters that enhance music video generation
- Document reasoning for parameter changes in comments

### 4. Testing and Validation

#### Task 4.1: Config Discovery Test
- [ ] 4.1.1: Restart backend server (or trigger config reload)
- [ ] 4.1.2: Verify `mv1` appears in `/api/mv/get_config_flavors` response
- [ ] 4.1.3: Check startup logs for successful `mv1` flavor loading (if MV_DEBUG_MODE=true)

#### Task 4.2: Scene Generation Test
- [ ] 4.2.1: Create test request to `/api/mv/create_scenes` with `config_flavor: "mv1"`
- [ ] 4.2.2: Verify generated scenes match music video theme:
  - Outdoor stadium setting present
  - Band and lead singer mentioned
  - Mix of shot types (wide, close-up)
  - Audience mentioned in some scenes but not all
  - Performance/concert context clear
- [ ] 4.2.3: Generate multiple batches to verify scene variety

#### Task 4.3: Video Generation Test
- [ ] 4.3.1: Generate actual videos using mv1 config flavor
- [ ] 4.3.2: Verify video outputs align with music video aesthetic:
  - Outdoor stadium visuals
  - Band performance visible
  - Lead singer prominence in appropriate scenes
  - Audience visible in select scenes
  - Concert lighting and atmosphere

#### Task 4.4: Frontend Integration Test
- [ ] 4.4.1: Verify `mv1` appears in config flavor dropdown on create page
- [ ] 4.4.2: Select `mv1` flavor and create a quick job
- [ ] 4.4.3: Verify scenes and videos generated match music video theme
- [ ] 4.4.4: Test full workflow: create → quick-gen → scene generation → video generation

### 5. Prompt Engineering Refinement

#### Task 5.1: Iterate on Scene Prompts
- [ ] 5.1.1: Review initial test results from Task 4.2
- [ ] 5.1.2: Identify areas for improvement:
  - Scene descriptions too generic?
  - Missing key music video elements?
  - Insufficient variety in camera angles?
  - Lead singer not prominent enough in close-ups?
  - Audience presence unclear or inconsistent?

- [ ] 5.1.3: Refine `scene_prompts.yaml` based on test results:
  - Strengthen outdoor stadium descriptors
  - Emphasize lead singer face close-ups
  - Clarify audience placement instructions
  - Enhance performance energy descriptors
  - Improve camera work variety instructions

- [ ] 5.1.4: Re-test after refinements (repeat Task 4.2)
- [ ] 5.1.5: Iterate until scene descriptions consistently match requirements

#### Task 5.2: Validate Scene Variety
- [ ] 5.2.1: Generate 10+ scene batches with mv1 config
- [ ] 5.2.2: Analyze scene variety across batches:
  - Count scenes with lead singer close-ups
  - Count scenes with audience visible
  - Count wide vs medium vs close shots
  - Verify mix is appropriate and varied

- [ ] 5.2.3: Adjust prompts if variety is insufficient

### 6. Documentation

#### Task 6.1: Update Feature Documentation
- [ ] 6.1.1: Update `.devdocs/v3/feats.md` - add completion note to v4 section
- [ ] 6.1.2: Document final implementation details
- [ ] 6.1.3: Include example scenes generated with mv1 config (optional)

#### Task 6.2: Create mv1 Config Documentation
- [ ] 6.2.1: Add comments to `mv1/scene_prompts.yaml` explaining:
  - Purpose of mv1 flavor (music video for outdoor stadium performance)
  - Key elements included in prompts
  - Differences from default config

- [ ] 6.2.2: Add comments to `mv1/parameters.yaml` explaining:
  - Parameter choices specific to mv1
  - Why parameters differ from default (if they do)

#### Task 6.3: Create Usage Guide (Optional)
- [ ] 6.3.1: Create `.devdocs/v3/mv1-config-guide.md` (optional)
- [ ] 6.3.2: Document when to use mv1 vs default flavor
- [ ] 6.3.3: Provide example inputs and expected outputs
- [ ] 6.3.4: Include tips for best results with mv1 config

### 7. Quality Assurance

#### Task 7.1: Cross-Config Comparison
- [ ] 7.1.1: Generate same video idea with both `default` and `mv1` configs
- [ ] 7.1.2: Compare scene descriptions:
  - Verify mv1 has stadium/concert elements
  - Verify mv1 has band/performance focus
  - Verify default doesn't have these elements (confirms configs are distinct)

- [ ] 7.1.3: Compare generated videos
- [ ] 7.1.4: Document observable differences

#### Task 7.2: Edge Cases
- [ ] 7.2.1: Test mv1 with non-music video prompts (e.g., "cooking tutorial")
  - Verify config still applies music video aesthetic
  - Determine if this is acceptable behavior

- [ ] 7.2.2: Test mv1 with explicit band/music mentions in user prompt
  - Check for redundancy or conflicts
  - Verify prompts work harmoniously

- [ ] 7.2.3: Test with different character descriptions
  - Solo artist vs full band
  - Different music genres
  - Various performer descriptions

### 8. Performance Validation

- [ ] 8.1: Verify mv1 config loads at similar speed to default
- [ ] 8.2: Verify no performance degradation in scene/video generation
- [ ] 8.3: Check for any memory or resource issues with mv1
- [ ] 8.4: Validate concurrent usage of multiple config flavors works correctly

---

## Implementation Notes

### Scene Prompt Structure Considerations

The `scene_prompts.yaml` likely contains a prompt template that gets filled with user inputs. The mv1 version should:

1. **Establish Setting Context**:
   ```
   "Generate a scene for a music video set in an outdoor stadium concert..."
   ```

2. **Camera Work Variety**:
   - Specify shot types: "Mix wide stadium shots showing the full band on stage, medium shots of the band performing, and intimate close-ups of the lead singer's face"
   - Emphasize at least one scene must feature lead singer face close-up

3. **Performance Elements**:
   - "The band is performing live with full instrumentation (drums, guitars, bass, keyboards)"
   - "Lead singer is engaging and prominent, especially in close-up shots"
   - "Dynamic stage lighting with outdoor concert atmosphere"

4. **Selective Audience**:
   - "Some scenes should include an excited audience visible in the background"
   - "Other scenes focus solely on the performers on stage"

5. **Character Consistency**:
   - Maintain references to character descriptions provided by user
   - Ensure lead singer matches character reference image

### Parameters to Consider

In `parameters.yaml`, common adjustable parameters might include:

- **Number of scenes**: Keep same or adjust for music video pacing
- **Scene descriptions length**: May want more detailed descriptions for mv1
- **Negative prompt strength**: Adjust to avoid unwanted elements
- **Randomness/temperature**: Control variety vs consistency
- **Any motion/camera parameters**: Increase for dynamic concert feel

### Example Scene Descriptions (Expected Output)

With mv1 config, generated scenes might look like:

1. "Wide shot of outdoor stadium stage at sunset, full band performing with dramatic lighting, excited crowd visible in background"
2. "Extreme close-up of lead singer's face under stage lights, passionate expression, singing into microphone"
3. "Medium shot of guitarist and bassist performing together on stage, outdoor stadium setting, energetic performance"
4. "Wide angle from audience perspective, entire band visible on massive outdoor stage, stadium lights illuminating the night"
5. "Close-up of drummer performing, outdoor concert stage, intense focus"
6. "Lead singer center stage with arms raised, crowd visible in foreground and background, outdoor stadium concert atmosphere"

---

## Definition of Done

- [ ] `mv1` config directory created with all necessary YAML files
- [ ] `scene_prompts.yaml` updated with music video outdoor stadium performance theme
- [ ] `parameters.yaml` reviewed and adjusted appropriately
- [ ] Config flavor discoverable via `/api/mv/get_config_flavors` API
- [ ] Scenes generated with mv1 consistently match music video theme:
  - Outdoor stadium setting
  - Band with lead singer
  - Mix of wide shots and close-ups (including lead singer face)
  - Selective audience presence
  - Concert/performance atmosphere
- [ ] Videos generated with mv1 match expected aesthetic
- [ ] Frontend can select and use mv1 config flavor
- [ ] Documentation complete with implementation notes
- [ ] Quality assurance tests pass
- [ ] No performance degradation introduced

---

## Success Criteria

1. **Functional**: mv1 config flavor generates scenes and videos distinct from default config
2. **Thematic Accuracy**: Generated content clearly reflects outdoor stadium music video aesthetic
3. **Scene Variety**: Mix of shot types (wide, medium, close-up) with prominent lead singer moments
4. **Audience Integration**: Audience appears in some scenes but not all, as specified
5. **Quality**: Generated videos maintain same quality standards as default config
6. **Usability**: Config can be selected and used through frontend UI workflow
7. **Consistency**: Character references properly maintained across music video scenes
8. **Documentation**: Clear documentation of mv1 purpose and usage

---

# v5: Audio Start Trimming Feature

## Overview
Add audio start trimming functionality to the create page, allowing users to specify a start position (in seconds) for the audio track. When the user clicks a trim button, the audio will be clipped from the start position onward, creating a new UUID and trimmed audio file that replaces the current one and gets passed to the quick-gen page.

---

## Task List

### Backend Tasks

#### Task 1: Create Audio Trim Endpoint
**File**: `backend/routers/audio.py`

- [ ] 1.1: Add new POST endpoint `/api/audio/trim`
- [ ] 1.2: Create `AudioTrimRequest` schema in `backend/schemas.py`:
  - `audio_id: str` - UUID of the source audio file
  - `start_at: int` - Start position in seconds (default: 0)
- [ ] 1.3: Create `AudioTrimResponse` schema in `backend/schemas.py`:
  - `audio_id: str` - UUID of the new trimmed audio file
  - `audio_path: str` - Filesystem path to trimmed audio
  - `audio_url: str` - URL path to retrieve trimmed audio
  - `original_audio_id: str` - Reference to original audio UUID
  - `start_at: int` - The start position used for trimming
  - `duration: Optional[float]` - Duration of trimmed audio (if available)
  - `file_size_bytes: int` - Size of trimmed audio file
  - `metadata: dict` - Additional metadata

**Notes**:
- This endpoint will handle the business logic of trimming audio and storing it
- Should follow similar patterns as `/api/audio/download` endpoint

#### Task 2: Implement Audio Trimming Logic
**File**: `backend/routers/audio.py` (in `/api/audio/trim` endpoint)

- [ ] 2.1: Validate `audio_id` exists (look for source audio file)
  - Search in `AUDIO_BASE_PATH` (backend/mv/outputs/audio)
  - Check for .mp3 extension first, then fallback to other formats
  - Raise 404 if not found
- [ ] 2.2: Validate `start_at` parameter
  - Must be >= 0
  - No upper limit validation needed (as per requirements)
- [ ] 2.3: Find source audio file path (same logic as `get_audio` endpoint)
- [ ] 2.4: Generate new UUID for trimmed audio
- [ ] 2.5: Call audio trimming utility function (see Task 3)
- [ ] 2.6: Save trimmed audio to `AUDIO_BASE_PATH` with new UUID as filename
- [ ] 2.7: Upload trimmed audio to S3 if cloud storage configured
  - Use same S3 path pattern as original audio: `backend/mv/outputs/audio/{uuid}.mp3`
  - Follow patterns from `lipsync.py` for S3 upload
  - Handle S3 upload failures gracefully (log warning, continue with local file)
- [ ] 2.8: Build response with new audio_id, paths, and metadata
- [ ] 2.9: Add error handling for:
  - Source audio file not found
  - Invalid start_at value
  - FFmpeg trimming failures
  - File I/O errors
  - S3 upload failures (non-fatal)

**Notes**:
- Use `clip_audio` function from `backend/mv/lipsync.py` as reference pattern
- The trimming should cut from `start_at` seconds to the end of the audio file
- Original audio file should remain unchanged

#### Task 3: Create Audio Trimming Utility Function
**File**: `backend/routers/audio.py` or `backend/services/audio_trimmer.py` (choose based on code organization)

- [ ] 3.1: Create `trim_audio_from_start(source_path: str, output_path: str, start_at: int) -> dict` function
- [ ] 3.2: Use ffmpeg to trim audio from start position to end:
  ```bash
  ffmpeg -i {source_path} -ss {start_at} -acodec copy -y {output_path}
  ```
- [ ] 3.3: Implement subprocess call to ffmpeg with timeout (60 seconds)
- [ ] 3.4: Capture stdout/stderr for debugging
- [ ] 3.5: Return metadata dict with:
  - `trimmed_duration`: Duration of trimmed audio (if extractable from ffmpeg output)
  - `file_size_bytes`: Size of output file
  - `ffmpeg_command`: Command used for debugging
- [ ] 3.6: Raise RuntimeError if ffmpeg fails with stderr details
- [ ] 3.7: Add logging for trim operation start, success, and failure

**Notes**:
- Follow pattern from `clip_audio` in `backend/mv/lipsync.py:170-246`
- Use `-ss {start_at}` without `-t` duration to trim from start to end
- Use `-acodec copy` for fast processing without re-encoding

#### Task 4: S3 Upload Integration
**File**: `backend/routers/audio.py` (in `/api/audio/trim` endpoint, after trimming)

- [ ] 4.1: Check if `settings.STORAGE_BUCKET` is configured
- [ ] 4.2: If configured, upload trimmed audio to S3:
  - Import `get_storage_backend` from `services.storage_backend`
  - Upload to same directory structure as original audio files
  - Generate presigned URL for trimmed audio
- [ ] 4.3: Store S3 URL in response metadata if upload succeeds
- [ ] 4.4: Handle upload failures gracefully (log warning, don't fail request)
- [ ] 4.5: Add cloud_url field to response metadata if available

**Notes**:
- Audio files are stored in same directory as downloaded audio
- Follow same pattern as audio download endpoint
- S3 failures should not block the trim operation

### Frontend Tasks

#### Task 5: Add Audio Trim UI to Create Page
**File**: `frontend/src/app/create/page.tsx`

- [ ] 5.1: Locate the Configuration section (added in v2)
- [ ] 5.2: Add `start_at` state variable: `const [startAt, setStartAt] = useState<number>(0)`
- [ ] 5.3: Add numeric input field for `start_at` inside Configuration section:
  - Label: "Audio Start Position (seconds)"
  - Type: number
  - Default value: 0
  - Min value: 0 (HTML validation)
  - Integer only (step="1")
  - Placeholder: "0"
- [ ] 5.4: Add "Trim Audio" button next to the input field
  - Label: "Trim Audio from Start"
  - Only enabled if an audio file is loaded
  - Disabled state if no audio_id exists
- [ ] 5.5: Add loading state for trim operation: `const [isTrimming, setIsTrimming] = useState(false)`
- [ ] 5.6: Show spinner/loading indicator on button when trimming
- [ ] 5.7: Style the input + button to be visually grouped together

**Notes**:
- This UI should be in the Configuration section (collapsed by default)
- The trim button should only be clickable if user has uploaded/selected audio
- Simple numeric input, no fancy waveform or preview needed

#### Task 6: Implement Trim Button Handler
**File**: `frontend/src/app/create/page.tsx`

- [ ] 6.1: Create `handleTrimAudio` async function
- [ ] 6.2: Validate that audio_id exists before making request
- [ ] 6.3: Validate that `start_at` is a valid number >= 0
- [ ] 6.4: Set `isTrimming` to true
- [ ] 6.5: Make POST request to `/api/audio/trim`:
  ```typescript
  const response = await fetch(`${API_URL}/api/audio/trim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      audio_id: currentAudioId,
      start_at: startAt
    })
  })
  ```
- [ ] 6.6: Parse response to get new `audio_id`, `audio_url`, and metadata
- [ ] 6.7: Replace existing audio state with trimmed audio:
  - Update audio_id state variable
  - Update audio_url state variable
  - Update any displayed audio metadata
  - Update audio player source (if audio player present)
- [ ] 6.8: Show success notification/toast (optional but recommended)
- [ ] 6.9: Handle errors gracefully:
  - Network failures
  - 404 if audio not found
  - 400 if validation fails
  - 500 if trimming fails
  - Show error message to user
- [ ] 6.10: Set `isTrimming` to false in finally block
- [ ] 6.11: Add console logging for debugging (trim started, success, error)

**Notes**:
- The trimmed audio replaces the current audio
- New UUID is generated server-side
- User cannot undo the trim (unless they re-upload original audio)

#### Task 7: Update Quick-Gen Data Passing
**File**: `frontend/src/app/create/page.tsx` (in `handleQuickGenerate` function)

- [ ] 7.1: Verify that `audioId` in `quickJobData` reflects the latest audio_id
  - If user trimmed audio, this should be the trimmed audio's UUID
  - If user didn't trim, this should be the original uploaded audio's UUID
- [ ] 7.2: Ensure `audioUrl` also reflects the latest audio URL
- [ ] 7.3: Add `trimmedFrom` metadata to sessionStorage data (optional):
  ```typescript
  const quickJobData = {
    // ... existing fields
    audioId: currentAudioId, // This will be trimmed UUID if user trimmed
    audioUrl: currentAudioUrl,
    audioStartAt: startAt, // Optional: track what start_at was used
  }
  ```
- [ ] 7.4: Test that trimmed audio UUID gets passed correctly to quick-gen page

**Notes**:
- No special handling needed if using state variables correctly
- The latest audio_id should naturally propagate to quick-gen page
- Optional: Add metadata about trimming for debugging/display purposes

#### Task 8: Update Quick-Gen Page Display (Optional Enhancement)
**File**: `frontend/src/app/quick-gen-page/page.tsx`

- [ ] 8.1: Add optional display of trim metadata in "Input Data" section
  - If `audioStartAt` exists in jobData, show "Audio trimmed from: {N} seconds"
- [ ] 8.2: Update audio player to use trimmed audio URL
- [ ] 8.3: Verify trimmed audio plays correctly in quick-gen page

**Notes**:
- This is optional enhancement for better UX
- Main requirement is that trimmed audio UUID gets passed to API calls

### Testing Tasks

#### Task 9: Backend Testing

- [ ] 9.1: Test `/api/audio/trim` endpoint with valid audio_id and start_at=10
  - Verify new UUID generated
  - Verify trimmed audio file created in AUDIO_BASE_PATH
  - Verify trimmed audio starts at 10 seconds (compare with original)
  - Verify response contains correct metadata
- [ ] 9.2: Test with start_at=0 (should return full audio as new UUID)
- [ ] 9.3: Test with large start_at value (beyond audio duration)
  - Should create very short or empty audio file (no validation error)
- [ ] 9.4: Test with invalid audio_id (non-existent UUID)
  - Should return 404 error
- [ ] 9.5: Test with missing start_at parameter
  - Should use default value 0 or return validation error
- [ ] 9.6: Test with negative start_at value
  - Should return 400 validation error
- [ ] 9.7: Test S3 upload when STORAGE_BUCKET configured
  - Verify trimmed audio uploaded to S3
  - Verify presigned URL returned in metadata
- [ ] 9.8: Test S3 upload failure handling
  - Verify operation continues with local file
  - Verify warning logged
- [ ] 9.9: Test that original audio file remains unchanged after trim
- [ ] 9.10: Test concurrent trim operations on same audio_id
  - Verify multiple trimmed versions created with different UUIDs

#### Task 10: Frontend Testing

- [ ] 10.1: Test audio trim UI on create page
  - Verify input field accepts numeric values
  - Verify button is disabled when no audio loaded
  - Verify button is enabled when audio loaded
  - Verify loading state shows during trim operation
- [ ] 10.2: Test successful trim operation
  - Click trim button with start_at=5
  - Verify API call made with correct parameters
  - Verify audio player updates with trimmed audio
  - Verify new UUID reflected in state
  - Verify success feedback shown to user
- [ ] 10.3: Test trim with start_at=0 (edge case)
  - Should create a copy of full audio with new UUID
- [ ] 10.4: Test error handling
  - Test with invalid audio_id (manually set bad state)
  - Test network failure (disconnect network)
  - Verify error messages displayed
- [ ] 10.5: Test integration with quick-gen page
  - Trim audio on create page
  - Navigate to quick-gen page
  - Verify trimmed audio UUID in "Input Data" section
  - Verify audio player uses trimmed audio
- [ ] 10.6: Test scene generation with trimmed audio
  - Verify trimmed audio_id passed to create_scenes API
  - Verify generated scenes use trimmed audio
- [ ] 10.7: Test video stitching with trimmed audio
  - Verify stitched video uses trimmed audio track

#### Task 11: End-to-End Testing

- [ ] 11.1: Full workflow test:
  1. Upload YouTube audio on create page
  2. Set start_at to 30 seconds
  3. Click "Trim Audio"
  4. Verify trimmed audio plays (starts from 30s mark of original)
  5. Navigate to quick-gen page
  6. Generate scenes
  7. Generate videos
  8. Verify final stitched video uses trimmed audio (starts from 30s)
- [ ] 11.2: Test multiple trim operations in sequence:
  1. Upload audio
  2. Trim from 10s
  3. Trim again from 5s (should trim from 5s of already-trimmed audio)
  4. Verify cumulative effect (audio starts from 15s of original)
- [ ] 11.3: Test without trimming (baseline):
  1. Upload audio
  2. Don't use trim feature
  3. Navigate to quick-gen
  4. Verify full original audio used

**Notes**:
- Test with different audio formats (mp3, m4a, etc.)
- Test with short audio files (< 10 seconds)
- Test with very long audio files (> 10 minutes)

### Documentation Tasks

#### Task 12: API Documentation

- [ ] 12.1: Document `/api/audio/trim` endpoint in OpenAPI/Swagger
  - Request schema
  - Response schema
  - Error responses (400, 404, 500)
  - Example request/response
- [ ] 12.2: Add endpoint description and usage examples
- [ ] 12.3: Document that original audio remains unchanged
- [ ] 12.4: Document S3 upload behavior (optional, based on configuration)

#### Task 13: Feature Documentation

- [ ] 13.1: Update `.devdocs/v3/feats.md`
  - Add completion note to v5 section
  - Document final implementation approach
  - Add example use case
- [ ] 13.2: Create inline code comments:
  - Comment the trim endpoint logic
  - Comment the frontend trim handler
  - Explain UUID replacement strategy
- [ ] 13.3: Update user-facing documentation (if exists):
  - How to use audio trimming feature
  - When to use it (e.g., skip intro, start at chorus)
  - Behavior and limitations

#### Task 14: Code Comments and Cleanup

- [ ] 14.1: Add clear comments to trim endpoint explaining:
  - Why new UUID is generated
  - S3 upload behavior
  - Error handling strategy
- [ ] 14.2: Add JSDoc comments to frontend trim handler
- [ ] 14.3: Clean up any debug console.logs
- [ ] 14.4: Ensure consistent code style with existing codebase
- [ ] 14.5: Remove any unused imports or variables

---

## Implementation Notes

### Audio Trimming Logic (FFmpeg Command)

```bash
# Trim from start_at seconds to end of file
ffmpeg -i input.mp3 -ss {start_at} -acodec copy -y output.mp3

# Example: Trim from 30 seconds onward
ffmpeg -i original.mp3 -ss 30 -acodec copy -y trimmed.mp3
```

**Parameters**:
- `-i input.mp3`: Input file
- `-ss 30`: Start at 30 seconds
- `-acodec copy`: Copy audio codec (fast, no re-encoding)
- `-y`: Overwrite output file if exists
- `output.mp3`: Output file path

### Backend Endpoint Structure

```python
# backend/routers/audio.py

@router.post("/trim", response_model=AudioTrimResponse)
async def trim_audio(request: AudioTrimRequest):
    """
    Trim audio from specified start position to end.

    Creates a new audio file with a new UUID, leaving the original unchanged.
    """
    # 1. Validate audio_id exists
    source_audio_path = find_audio_file(request.audio_id)
    if not source_audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")

    # 2. Generate new UUID for trimmed audio
    new_audio_id = str(uuid.uuid4())
    output_path = Path(AUDIO_BASE_PATH) / f"{new_audio_id}.mp3"

    # 3. Trim audio using ffmpeg
    metadata = trim_audio_from_start(
        source_path=str(source_audio_path),
        output_path=str(output_path),
        start_at=request.start_at
    )

    # 4. Upload to S3 if configured (optional)
    cloud_url = None
    if settings.STORAGE_BUCKET:
        try:
            cloud_url = upload_to_s3(output_path, new_audio_id)
        except Exception as e:
            logger.warning(f"S3 upload failed: {e}")

    # 5. Build response
    return AudioTrimResponse(
        audio_id=new_audio_id,
        audio_path=str(output_path),
        audio_url=f"/api/audio/get/{new_audio_id}",
        original_audio_id=request.audio_id,
        start_at=request.start_at,
        duration=metadata.get("duration"),
        file_size_bytes=output_path.stat().st_size,
        metadata={"cloud_url": cloud_url, **metadata}
    )
```

### Frontend Trim Handler

```typescript
// frontend/src/app/create/page.tsx

const handleTrimAudio = async () => {
  if (!audioId) {
    toast.error("No audio file loaded");
    return;
  }

  if (startAt < 0) {
    toast.error("Start position must be 0 or greater");
    return;
  }

  setIsTrimming(true);

  try {
    const response = await fetch(`${API_URL}/api/audio/trim`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        audio_id: audioId,
        start_at: startAt
      })
    });

    if (!response.ok) {
      throw new Error(`Trim failed: ${response.statusText}`);
    }

    const data = await response.json();

    // Replace audio with trimmed version
    setAudioId(data.audio_id);
    setAudioUrl(data.audio_url);

    toast.success(`Audio trimmed from ${startAt}s`);

  } catch (error) {
    console.error("Audio trim error:", error);
    toast.error("Failed to trim audio");
  } finally {
    setIsTrimming(false);
  }
};
```

### Create Page UI Structure

```
┌─────────────────────────────────────────┐
│ ▶ Configuration              [collapsed]│
│   ├─ Config Flavor: [default ▼]        │
│   └─ Audio Start Position (seconds)    │
│      ├─ [   10   ] (numeric input)     │
│      └─ [Trim Audio from Start] (btn)  │
├─────────────────────────────────────────┤
│ Video Description *                     │
└─────────────────────────────────────────┘
```

### Data Flow

1. **User uploads audio** → Original UUID: `abc-123`, stored at `backend/mv/outputs/audio/abc-123.mp3`
2. **User sets start_at=30** → Input field value: 30
3. **User clicks "Trim Audio"** → Frontend calls `/api/audio/trim` with `audio_id=abc-123, start_at=30`
4. **Backend trims audio** → New UUID: `def-456`, stored at `backend/mv/outputs/audio/def-456.mp3`
5. **Backend uploads to S3** (if configured) → Uploaded to same S3 path structure
6. **Frontend updates state** → `audioId = def-456`, `audioUrl = /api/audio/get/def-456`
7. **User navigates to quick-gen** → sessionStorage contains `audioId: def-456`
8. **Quick-gen uses trimmed audio** → All API calls use `audio_id=def-456`
9. **Final video has trimmed audio** → Stitched video uses audio starting from 30s mark

### Storage Locations

- **Local Storage**: `backend/mv/outputs/audio/{uuid}.mp3`
- **S3 Storage** (if configured): Same directory structure as local
- **Both original and trimmed audio persist** (no deletion of original)

### Error Handling Strategy

**Non-fatal errors** (log warning, continue):
- S3 upload failures
- Metadata extraction failures

**Fatal errors** (return error to user):
- Audio file not found (404)
- Invalid start_at value (400)
- FFmpeg trimming failure (500)
- File I/O errors (500)

---

## Dependencies

- **Task 2 depends on Task 1**: Endpoint must exist before implementing logic
- **Task 3 can be done in parallel with Task 1-2**: Utility function is independent
- **Task 4 depends on Task 2**: S3 upload happens after trimming
- **Task 5-6 depend on Task 1-2**: Frontend needs backend endpoint to exist
- **Task 7 depends on Task 6**: Data passing happens after trim handler works
- **Task 9 depends on Tasks 1-4**: All backend features must be implemented
- **Task 10 depends on Tasks 5-7**: All frontend features must be implemented
- **Task 11 depends on Tasks 9-10**: E2E tests require all features working
- **Tasks 12-14 can be done in parallel after implementation complete**

---

## Definition of Done

- [ ] `/api/audio/trim` endpoint accepts audio_id and start_at parameters
- [ ] Endpoint trims audio using ffmpeg from start_at to end of file
- [ ] New UUID generated for trimmed audio file
- [ ] Trimmed audio stored in same directory as original audio
- [ ] Original audio file remains unchanged after trim operation
- [ ] Trimmed audio uploaded to S3 if cloud storage configured
- [ ] S3 upload failures handled gracefully (non-fatal)
- [ ] Create page has numeric input field for start_at (default: 0)
- [ ] Create page has "Trim Audio" button that calls trim endpoint
- [ ] Button shows loading state during trim operation
- [ ] After successful trim, audio player updates with trimmed audio
- [ ] Trimmed audio UUID replaces original UUID in component state
- [ ] Trimmed audio UUID passed to quick-gen page via sessionStorage
- [ ] Quick-gen page uses trimmed audio for scene/video generation
- [ ] Error handling for invalid audio_id, network failures, ffmpeg errors
- [ ] All backend tests pass (valid trim, edge cases, errors)
- [ ] All frontend tests pass (UI, trim handler, quick-gen integration)
- [ ] E2E test passes (upload → trim → generate → verify trimmed audio used)
- [ ] API documentation complete with examples
- [ ] Code comments added explaining trim logic and UUID replacement
- [ ] Feature documentation updated in `.devdocs/v3/feats.md`

---

## Success Criteria

1. **Functional**: Users can trim audio from a specified start position
2. **UUID Generation**: Each trim creates a new unique UUID
3. **Non-destructive**: Original audio remains unchanged after trim
4. **S3 Integration**: Trimmed audio uploads to S3 when configured
5. **UI/UX**: Clear, simple numeric input + button interface
6. **Integration**: Trimmed audio seamlessly passes through create → quick-gen → generation pipeline
7. **Error Handling**: Graceful handling of edge cases and failures
8. **Performance**: Trim operation completes in reasonable time (< 60s for typical audio)
9. **Testing**: All test cases pass including edge cases
10. **Documentation**: Clear API docs and usage examples