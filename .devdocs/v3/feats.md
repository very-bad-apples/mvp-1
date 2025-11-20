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

## v4

create a new config_flavor by copying the default directory in backend/mv/configs/ and renaming it mv1. then update the files scene_prompts.yaml and parameters.yaml to be suited to producing a music video that will feature a band and a lead singer performing a song to an audience.

