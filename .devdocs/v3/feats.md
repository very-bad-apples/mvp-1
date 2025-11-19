## v1

For backend/mv/configs/*.yaml we currently load these to supply needed prompts and paramaters to various services. We want to do two main things to refactor this logic:
- allow multiple config directories for "config-flavors" with a default if the flavor isnt specified.
- allow config flavor to be loaded at prompt time for the service calls and endpoints


Multiple config directories: backend/mv/configs/ currently has all the yaml's in it but we'll refactor to backend/mv/configs/ to:
configs/
    default/
        - image_params.yaml
        - scene_prompts.yaml
        ...
    flavor1/
        - image_params.yaml
        - scene_prompts.yaml
        ...
    ...

Config load at run time: since there's multiple possible syncronous requests with different flavors specified we'll probably need a secondary data structure the configs get loaded to at startup time and then loaded to the service when the endpoint requests specifies a flavor (flavor specification will be an optional param)

When MV_DEBUG_MODE=true, the flavor of config chosen at prompt time should log out that it has been loaded succesfully (or not found) and log out the config text/value loaded and the associated variable/module where it has been loaded to.
    - log which flavors are being loaded at run time, but not all the prompts at this time.

---

### Implementation Plan (v1)

**Status**: Planning Complete - See `.devdocs/v3/tasklist.md` for detailed task breakdown

**Key Design Decisions**:
1. **Auto-discovery**: System automatically discovers all flavor directories under `backend/mv/configs/`
2. **Parameter naming**: API parameter will be called `config_flavor` (optional)
3. **Fallback behavior**: If flavor or specific config file not found → fall back to `default/` with warning log
4. **Loading strategy**: All flavors loaded into memory at startup into queryable data structure
5. **Endpoint integration**: All three MV endpoints (`create_scenes`, `generate_video`, `generate_character_reference`) will accept `config_flavor` parameter
6. **Storage**: Configs live in memory only (not stored in DynamoDB) - static between startup/runtime
7. **Debug logging**:
   - At startup: Log discovered flavor names
   - At prompt time: Log selected flavor name + full config values/prompts

**Architecture**:
- New `backend/mv/config_manager.py` module handles all config loading/querying
- Data structure: `_flavors[flavor_name][config_type] = config_dict`
- Existing modules (scene_generator, video_generator, image_generator) refactored to query config_manager
- Backward compatible: requests without `config_flavor` default to "default" flavor

**See**: `.devdocs/v3/tasklist.md` for complete 10-section task breakdown with 40+ subtasks


## v2

on the frontend create page create a toggelable config section between Generation Mode and Video Description. It is collpase on page creation.

Add the first config: Config Flavor select box, default is "default"
    - we'll probably need create an endpoint: /api/mv/get_config_flavors to populate this

Pass this information to the quick-gen-page and display in the input data. Allow this to be adjustable by a select box just like on th ecreate page

Have the quickgen page attach the config flavor specified (either passed from create page or specified from quickgen-page select box) to the outgoing requests to the api e.g. create_scenes, generate_videos

---

### Implementation Plan (v2)

**Status**: Planning Complete - See `.devdocs/v3/tasklist.md` (v2 section) for detailed task breakdown

**Key Design Decisions**:
1. **API Endpoint**: New `GET /api/mv/get_config_flavors` endpoint returns list of available flavors
2. **Data Flow**: Config flavor passed via sessionStorage (same as other create → quick-gen data)
3. **UI Component**: Collapsible "Configuration" section using Card/Collapsible component
4. **Positioning**: Section placed between "Generation Mode" and "Video Description" on create page
5. **Default State**: Configuration section collapsed by default on both pages
6. **Quick-Gen Integration**:
   - Configuration section above "Input Data" card
   - Selected flavor displayed in "Input Data" section
   - Flavor changeable via select box in Configuration section
7. **API Integration**: `config_flavor` parameter added to both `create_scenes` and `generate_video` calls

**Frontend Changes**:
- **Create page** (`frontend/src/app/create/page.tsx`):
  - New collapsible Configuration section with config flavor select
  - Fetch flavors from `/api/mv/get_config_flavors` on mount
  - Add `configFlavor` to sessionStorage when navigating to quick-gen

- **Quick-gen page** (`frontend/src/app/quick-gen-page/page.tsx`):
  - New Configuration section for changing flavor
  - Display received flavor in Input Data card
  - Attach flavor to `create_scenes` API call
  - Attach flavor to `generate_video` API calls

**Backend Changes**:
- New endpoint: `GET /api/mv/get_config_flavors`
- Returns: `{"flavors": ["default", "example", ...]}`
- Uses existing `get_discovered_flavors()` from config_manager

**See**: `.devdocs/v3/tasklist.md` (v2 section) for complete 11-section task breakdown with 40+ subtasks