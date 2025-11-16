# Task List: `/api/mv/create_scenes` Endpoint

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
