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