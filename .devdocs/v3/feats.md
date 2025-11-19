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

Add the first config: Config Flavor select box
    - we'll probably need create an endpoint: /api/mv/get_config_flavors to populate this