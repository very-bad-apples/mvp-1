## v1

In the backend api/mv/generate_character_reference to accept a request for 1-4 generated images on the same prompt and modify the replicate api service call to also do this, and modify the response from the python api to pass the frontend all the character_ref_xxx ids.
In the frontend for generate character reference enable the display of 4 simulataeous character reference images and allow the user to select one and only one of those references to proceed to the next step.

## v2

For the generate_character on the frontend let's add to new features: 
- loading state (per image): ideally this is some kind of animation demonstrate the image is being generated.
- regenerate capability (per image)