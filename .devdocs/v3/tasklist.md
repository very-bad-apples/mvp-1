# v1: Config Flavors System

## Overview
Refactor the MV config system to support multiple "config flavors" that can be selected at runtime via API parameters. Each flavor represents a different set of prompts and parameters for video/image generation.

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
