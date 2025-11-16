# Task List: `/api/mv/create_scenes` Endpoint (v1)

## Overview
Port the `generate_scenes` functionality from `.ref-pipeline/src/main.py` into the backend server as a new endpoint for music video scene generation.

---

## Tasks

### 1. Setup Configuration Infrastructure
- [ ] Create `backend/mv/` directory structure
- [ ] Create `backend/mv/configs/` directory
- [ ] Create `backend/mv/configs/parameters.yaml` with default scene generation parameters
- [ ] Create `backend/mv/configs/scene_prompts.yaml` with prompt templates
- [ ] Add YAML loading utility to load configs at backend startup

### 2. Environment Configuration
- [ ] Add `GEMINI_API_KEY` to `backend/.env`
- [ ] Add `GEMINI_API_KEY` to `backend/config.py` Settings class
- [ ] Add `MV_DEBUG_MODE` environment variable to `backend/.env`
- [ ] Add `MV_DEBUG_MODE` to `backend/config.py` Settings class

### 3. Core Scene Generation Module
- [ ] Create `backend/mv/__init__.py`
- [ ] Create `backend/mv/scene_generator.py` with:
  - [ ] Pydantic models: `Scene`, `SceneResponse`, `CreateScenesRequest`
  - [ ] `generate_scenes()` function ported from reference pipeline
  - [ ] Integration with `google-genai` client
  - [ ] Default parameter handling (load from YAML configs)
  - [ ] Debug mode logging support

### 4. Debug Mode Implementation
- [ ] Create debug logging utilities in `backend/mv/debug.py`
- [ ] Log request arguments received
- [ ] Log default arguments applied
- [ ] Log config parameters loaded
- [ ] Log full prompts sent to Gemini
- [ ] Conditional logging based on `MV_DEBUG_MODE`

### 5. API Endpoint Router
- [ ] Create `backend/routers/mv.py` router file
- [ ] Implement `POST /api/mv/create_scenes` endpoint
- [ ] Define request schema (JSON body with required and optional fields):
  - Required: `idea`, `character_description`
  - Optional with defaults: `character_characteristics`, `number_of_scenes`, `video_type`, `video_characteristics`, `camera_angle`, `output_dir`
- [ ] Return JSON response with generated scenes
- [ ] Add error handling for:
  - Missing Gemini API key
  - Gemini API errors
  - Invalid request parameters

### 6. Backend Integration
- [ ] Import and include `mv` router in `backend/main.py`
- [ ] Update `lifespan` function to load MV configs at startup
- [ ] Store loaded configs in app state or module-level variables

### 7. Package Dependencies
- [ ] Add `google-genai` to backend dependencies (check pyproject.toml/requirements.txt)
- [ ] Add `pyyaml` if not already present
- [ ] Run `pnpm install` or equivalent for Python packages

### 8. File-Based Storage
- [ ] Create output directory for scene data (e.g., `backend/mv/outputs/`)
- [ ] Save `scenes.json` and `scenes.md` to output directory
- [ ] Include file paths in response

### 9. Documentation
- [ ] Create `backend/.devdocs/impl-notes.md` with:
  - [ ] Current limitations (sync processing, file-based storage)
  - [ ] Future improvement plans (async job queue, database persistence)
- [ ] Add endpoint documentation in router docstrings
- [ ] Update root endpoint info in `backend/main.py`

### 10. Testing
- [ ] Create basic test file `backend/mv/test_scene_generator.py`
- [ ] Test endpoint with sample requests
- [ ] Verify debug mode output
- [ ] Validate JSON response structure

---

## Request Schema (Suggested)

```json
{
  "idea": "string (required) - The core concept or topic of the video",
  "character_description": "string (required) - Visual description of main character",
  "character_characteristics": "string (optional) - Personality traits, default: from config",
  "number_of_scenes": "int (optional) - Number of scenes to generate, default: from config",
  "video_type": "string (optional) - Type of video, default: from config",
  "video_characteristics": "string (optional) - Visual style, default: from config",
  "camera_angle": "string (optional) - Camera perspective, default: from config",
  "output_dir": "string (optional) - Directory to save scenes, default: auto-generated"
}
```

## Response Schema (Suggested)

```json
{
  "scenes": [
    {
      "description": "string - Scene description for video generation",
      "negative_description": "string - Elements to exclude"
    }
  ],
  "output_files": {
    "json": "path to scenes.json",
    "markdown": "path to scenes.md"
  },
  "metadata": {
    "idea": "string",
    "number_of_scenes": "int",
    "parameters_used": {}
  }
}
```

---

## Dependencies to Add

- `google-genai` - Google's Generative AI Python SDK
- `pyyaml` - YAML parsing (likely already present)
- `pydantic` - Data validation (likely already present)

## Environment Variables to Add

```bash
# Google AI / Gemini
GEMINI_API_KEY=your_key_here

# Music Video Module Debug Mode
MV_DEBUG_MODE=false
```

# v2 Feature: Generate Character Reference Image Endpoint

## Overview
Port `generate_character_reference_image` from `.ref-pipeline/src/image_generator.py` to `/api/mv/generate_character_reference` endpoint.

---

## Task List

### 1. Environment & Configuration Setup
- [ ] **1.1** Add `REPLICATE_API_TOKEN` to `backend/.env`
- [ ] **1.2** Add `REPLICATE_API_TOKEN` to `backend/config.py` settings
- [ ] **1.3** Create/update `backend/mv/configs/image_params.yaml` with default parameters:
  - `aspect_ratio: "1:1"`
  - `safety_filter_level: "block_medium_and_above"`
  - `person_generation: "allow_adult"`
  - `output_format: "png"`
  - `model: "google/imagen-4"`
- [ ] **1.4** Create/update `backend/mv/configs/image_prompts.yaml` with character reference prompt template:
  - `character_reference_prompt: "A full-body character reference image of {character_description}. Clear, well-lit, neutral background, professional quality, detailed features, front-facing view."`

### 2. Dependencies
- [ ] **2.1** Use Context7 MCP to get latest Replicate Python SDK documentation
- [ ] **2.2** Add `replicate` package to `backend/requirements.txt`
- [ ] **2.3** Install package with `uv pip install replicate`

### 3. Core Module Implementation
- [ ] **3.1** Create `backend/mv/image_generator.py` with:
  - Pydantic models:
    - `GenerateCharacterReferenceRequest` (character_description required, optional: aspect_ratio, safety_filter_level, person_generation, output_format, negative_prompt, seed)
    - `GenerateCharacterReferenceResponse` (image_base64, output_file, metadata)
  - Config loading functions (load from image_params.yaml and image_prompts.yaml)
  - `generate_character_reference_image()` function:
    - Validate `REPLICATE_API_TOKEN` is set
    - Apply defaults from YAML config
    - Format prompt from template
    - Call Replicate API with `google/imagen-4`
    - Save image to `backend/mv/outputs/character_reference/` with timestamp filename (e.g., `character_ref_20251115_143025.png`)
    - Return base64-encoded image data along with file path
- [ ] **3.2** Update `backend/mv/debug.py` to add image generation specific debug logging:
  - `log_image_request_args()`
  - `log_image_defaults_applied()`
  - `log_image_prompt()`
  - `log_replicate_response()`

### 4. Router Integration
- [ ] **4.1** Add endpoint to `backend/routers/mv.py`:
  - `POST /api/mv/generate_character_reference`
  - Request validation (character_description required)
  - Response with base64 image, file path, and metadata
  - Error handling (400 for validation, 500 for API/config errors)
  - OpenAPI documentation with examples

### 5. Startup Integration
- [ ] **5.1** Update `backend/main.py` lifespan to load image configs at startup (if not already handled by existing `load_configs()`)
- [ ] **5.2** Update root endpoint to include new endpoint in available endpoints list

### 6. Testing
- [ ] **6.1** Create `backend/mv/test_image_generator.py` with unit tests:
  - Model validation tests
  - Config loading tests
  - Missing API key error test
  - Successful generation mock test
  - Timestamp filename format test
- [ ] **6.2** Run tests with `uv run pytest backend/mv/test_image_generator.py -v`
- [ ] **6.3** Create `/.devdocs/scripts/test_generate_character_reference.sh` curl script

### 7. Documentation
- [ ] **7.1** Create `.devdocs/v2/impl-notes.md` documenting:
  - Synchronous processing limitation (future: async with job queue)
  - File storage pattern (timestamp-based)
  - Base64 response size considerations
  - Replicate API rate limits and costs

### 8. Git & Cleanup
- [ ] **8.1** Ensure `backend/mv/outputs/character_reference/` is covered by existing gitignore
- [ ] **8.2** Verify no sensitive data in committed configs

---

## API Contract

### Request
```json
POST /api/mv/generate_character_reference
{
  "character_description": "Silver metallic humanoid robot with a red shield",
  "aspect_ratio": "1:1",           // optional, default from config
  "safety_filter_level": "block_medium_and_above",  // optional
  "person_generation": "allow_adult",  // optional
  "output_format": "png",          // optional
  "negative_prompt": "blurry, low quality",  // optional
  "seed": 12345                    // optional, for reproducibility
}
```

### Response
```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "output_file": "/path/to/character_ref_20251115_143025.png",
  "metadata": {
    "character_description": "Silver metallic humanoid robot...",
    "model_used": "google/imagen-4",
    "parameters_used": {
      "aspect_ratio": "1:1",
      "safety_filter_level": "block_medium_and_above",
      ...
    },
    "generation_timestamp": "2025-11-15T14:30:25Z"
  }
}
```
