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


## v2

on the frontend create page create a toggelable config section between Generation Mode and Video Description. It is collpase on page creation.

Add the first config: Config Flavor select box, default is "default"
    - we'll probably need create an endpoint: /api/mv/get_config_flavors to populate this

Pass this information to the quick-gen-page and display in the input data. Allow this to be adjustable by a select box just like on th ecreate page

Have the quickgen page attach the config flavor specified (either passed from create page or specified from quickgen-page select box) to the outgoing requests to the api e.g. create_scenes, generate_videos

## v3

Let's integrate the lipsync capability with the quick-gen-page:

1. add a checkbox (default off) next to every regenerate button on the video section of the card.
    - when this box is checked, the regenerate button changes to say "Regenearate with lipsync" and it's behavior will be to make a request to the /api/mv/lipsync endpoint instead of generate_video. 

2. update the api/mv/lipsync to:
    - make video_url and audio_url optional params
    - add video_id and audio_id params as optional.
        - when video_id or audio_id is supplied, they should use methods to lookup the url for those resources and pass those urls to the replicate api call.
    - add optional paramaters of start_time and end_time (floats)
    - it should clip 

3. configure the client to utilize these parameters by sending a request with the video_id of the current clip on that card, the audio_id of the assoicated audio track (as displayed in the quick-gen-page input data section) and the start_time and end_time as calculated by assuming each clip is 8 seconds long and starts at start_time 0 seconds. So determine based on the scenes position where the start and end position should be.

4. when the lipsync api returns to the client it should use the newly returned id to replace the id for that scene in the card, display the newly created video and update any react state properties holding current video ids.

5. When the lipsync endpoint returns it should kickoff a new call to the stitch-video endpoint with the updated id to the newly returned stitched video and return that new video.
    - also add a "re-stitch with current clips" button to the final video section which will call the stitch-video endpoint with the current id's of the videos and the audio paramaters unchanged from the original call.

---

### v3 Implementation Notes

**Status**: Planning Complete - Ready for Implementation

**Task List**: See `.devdocs/v3/tasklist.md` (v3 section)

#### Key Decisions Made:

1. **Lipsync Replacement Behavior**: Lipsynced videos will replace the original video in the UI and state
2. **Audio Source**: Audio comes from the clipped version of the YouTube video attached to the generation (jobData.audioId)
3. **Audio Clipping**: Added start_time and end_time parameters to lipsync endpoint
   - Each clip assumed to be 8 seconds long
   - Start time calculated based on scene position (scene_index * 8 seconds)
   - End time = start_time + 8 seconds
4. **ID Lookup Pattern**: video_id and audio_id will be looked up using existing patterns from `/api/mv/get_video/{id}` and `/api/audio/get/{id}`
5. **Auto-restitch**: When lipsync returns, automatically trigger stitch-video with updated IDs
6. **Manual Re-stitch**: Add "re-stitch with current clips" button using current video IDs and unchanged audio parameters
7. **Processing Status**: Yes, will show processing status during lipsync operations similar to video generation
8. **Video ID Tracking**: video_id references are the same as the video_ids array currently tracked in scenes
9. **UI Placement**: Lipsync checkbox only appears next to video regenerate buttons, NOT scene regenerate buttons

#### Implementation Scope:

**Backend Changes**:
- Update `/api/mv/lipsync` endpoint to accept optional video_id/audio_id parameters
- Add optional start_time and end_time parameters to lipsync endpoint
- Add ID-to-URL lookup logic for both video and audio
- Implement audio clipping before passing to Replicate API
- Maintain backwards compatibility with direct URLs

**Frontend Changes**:
- Add lipsync checkbox next to video regenerate buttons (one per video card)
- Implement lipsync request flow with video_id, audio_id, start_time, and end_time
- Calculate start_time and end_time based on scene position (scene_index * 8 seconds)
- Add processing status for lipsync operations
- Replace video in UI when lipsync completes
- Update video_ids array to track lipsynced versions
- Auto-trigger stitch-video when lipsync returns
- Add "Re-stitch with current clips" button to final video section
- Implement manual re-stitch functionality using latest video IDs

**Data Flow**:
1. User enables lipsync checkbox → button text changes to "Regenerate with lipsync"
2. Click triggers lipsync API call with:
   - video_id: current video ID from scene
   - audio_id: from jobData.audioId
   - start_time: scene_index * 8
   - end_time: (scene_index * 8) + 8
3. Backend looks up URLs, clips audio, and processes lipsync
4. Frontend receives new lipsynced video ID
5. UI updates to show lipsynced video, video_ids array updated
6. Auto-trigger stitch-video with all current video IDs
7. Update final stitched video in UI
8. Manual "Re-stitch" button available for re-stitching without regenerating

#### Edge Cases Addressed:
- Missing audio_id (no YouTube audio): Hide or disable lipsync checkbox
- Invalid video_id or audio_id: Show error, don't crash
- Multiple lipsync operations: Track history in video_ids array
- Incomplete scenes: Only use scenes with at least one video
- Long-running operations: Show meaningful progress indicators
- Audio clipping failures: Handle gracefully with error messages



