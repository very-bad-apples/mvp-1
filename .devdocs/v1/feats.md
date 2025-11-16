## v1

in .ref-pipeline/ there is an existing python app that works as video generation pipeline. we are porting this functionality into the backend server and applying it to different routes

generate a new endpoint: /api/mv/create_scenes which implements the functionality in .ref-pipeline/src/main.py:generate_scenes
    - suggest the the required inputs which arrive via JSON
    - keep the structure of the original function of minimal required arguments and supplying defaults for most arguments
        - create the yaml files into the backend repo which provide parameters and prompts and load them when the backend launches
    - add the nec packages and api keys to the env files
    - enable a module wide debug-mode setting which will print the request arguments recieved, default args applied, config params loaded and the full prompts and 

## v2

in .ref-pipeline/ there is an existing python app that works as video generation pipeline. we are porting this functionality into the backend server and applying it to different routes

generate a new endpoint: /api/mv/generate_character_reference which implements the functionality in .ref-pipeline/src/image_generator.py:generate_character_reference_image
    - suggest the the required inputs which arrive via JSON
    - keep the structure of the original function of minimal required arguments and supplying defaults for most arguments
        - create or modify existing yaml files into the backend repo which provide parameters and prompts and load them when the backend launches
    - add the nec packages and api keys to the env files
    - enable a module wide debug-mode setting which will print the request arguments recieved, default args applied, config params loaded and the full prompts and 
    - output the png to backend/mv/outputs/ but also return the image data back to the frontend making the request with the base64 encoded error.
    - use the MV_DEBUG_MODE in here to output to console the full meta prompt with templating filled in.

## v3

in .ref-pipeline/ there is an existing python app that works as video generation pipeline. we are porting this functionality into the backend server and applying it to different routes

generate a new endpoint: /api/mv/generate_video which implements the functionality in .ref-pipeline/src/main.py::generate_video and the src/video_backends/ with the individual video generation modules
    - default: to replicate backend
    - suggest the the required inputs which arrive via JSON
    - keep the structure of the original function of minimal required arguments and supplying defaults for most arguments
        - create or modify existing yaml files into the backend repo which provide parameters and prompts and load them when the backend launches
    - add the nec packages and api keys to the env files
    - enable a module wide debug-mode setting which will print the request arguments recieved, default args applied, config params loaded and the full prompts and 
    - use the MV_DEBUG_MODE in here to output to console the full meta prompt with templating filled in.
   
We'll need some new logic here to address this local python script which we're porting to server-side code to handle returning the success indicator and resulting video of the video creation job to the client:
    - expect this backend process to take 20 - 400 seconds to complete
    - this process has a plausibility of failure, in which case we want to return the failure status to the user along with any error codes we recieve from the video generation service.
    - we'll need a quick way for now to demonstrate proof-of-concept of this, the likely pattern is to:
        - download the video file to backend/outputs with a uuid for the video filename
        - create another endpoint which will serve this video file, e.g. /api/mv/get_video
        - feel free to suggest another pattern if you see problems here, but remeber we're trying to hit prooof-of-concept not a fully production app right now.
        - note the limitations of this approach into .devdocs/v1/impl-notes.md for future improvment
            - we currently don't auth implemented on the backend or client but will add down the road.
        - add notes about this approach and its limitations to .devdocs/v1/client-impl-notes.md which will be given to the frontend team to integrate these endpoints to the frontend.
