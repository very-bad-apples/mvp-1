## v1

In the backend api/mv/generate_character_reference to accept a request for 1-4 generated images on the same prompt and modify the replicate api service call to also do this, and modify the response from the python api to pass the frontend all the character_ref_xxx ids.
In the frontend for generate character reference enable the display of 4 simulataeous character reference images and allow the user to select one and only one of those references to proceed to the next step.

## v2

Let's add another button to the front end on the create page below the "Generate videos" button. this new button is called "Quick Job" and it will operate simliar to "generate videos" by routing to a new page of route /quick-gen-page instead of result/job_<id>. But this button will have no validation logic for being enabled.

This page should utilize the layout and styling of the result/job_<id> page but this should send the data from the create page onto the second page and display:
- the "video description"
- the "character and style"
- the id of the character reference image.
These fields should de displayed in a card on that page above the other sections. Don't worry about styling these, in future these fields will be used as payloads in requests to the backend from that /quick-gen-page.

## v3

on /quick-gen-page let's kickoff a call to /api/mv/create_scenes and display the response json in cards on the page when it's created.
- Create a progress bar like on the /result/job_id page waiting for the scenes json to be returned (expected 10-30 seconds).
- Utilize only the following field for the request:
    - "idea": <video description data>,
    - "character_description": <character and style data>

## v4

on the /quick-gen-page we'll await the scenes.json to arrive and when they do quick off a call to /api/mv/generate_video, one request per scene, we'll pass each scenes's field to respective endpoint 
    - description -> prompt
    - negative_description -> negative_prompt
omit all other endpoint params.

return the generated videos by calling the /api/mv/get_video with uuid / video_url and display each video clip in it's own card.
    - create the cards for the videos immediately and show loading status for them until the video is generated and loaded.

## v5

Overall goal: get the quick-gen-page to work in local dev both when the video assets are stored to local filesystem or when they are stored in the s3 buckets. Currently the page only works when they are stored in local filesystem, but the s3 system is working when we do the proper flow with curls, so we need the frontend to be able to switch between modes seemlessly based on the data passed back from generate_video

after adding a new backend feature of enabling .backend/.env: SERVE_FROM_CLOUD=true which puts the video assets into an s3 bucket (even when running from local dev) where getting an issue calling get_video/ from quick-gen-page. This seems to be because when:
- SERVE_FROM_CLOUD=true the "video_url" of generate_video comes back as: "/api/mv/get_video/fb25d756-a58a-4b1a-bc5a-acd9ed3b2373" but
- SERVE_FROM_CLOUD=false the "video_url" of generate_video comes back as: "https://video-generator-storage.s3.amazonaws.com/mv/jobs/de0279c3-4948-42dd-821d-761daf783959/video.mp4?AWSAccessKeyId=REDACTED&Signature=REDACTED&Expires=1763407044"
this seems to cause problems in contructing the url for get_video request and recieve the data.

However there is also new logic on the get_video route which you can query with the /<uuid>?redirect=<boolean> and you can get back either a json of the s3 presigned url or the actual file download (you can check the swagger doc for elaboration)
- redirect=false:
{
  "video_id": "38940f21-e2a8-4bf8-9442-6742ca101a92",
  "video_url": "https://video-generator-storage.s3.amazonaws.com/mv/jobs/38940f21-e2a8-4bf8-9442-6742ca101a92/video.mp4?AWSAccessKeyId=REDACTED&Signature=REDACTED&Expires=1763405772",
  "storage_backend": "s3",
  "expires_in_seconds": 3600,
  "cloud_path": "mv/jobs/38940f21-e2a8-4bf8-9442-6742ca101a92/video.mp4"
}
- redirect=true: downloads the actual video data from the video_url

## v6

implement the endpoint /api/mv/stitch-videos which implements the functionality of .ref-pipeline/src/main.py:merge_videos 

the client will pass a list of video-ids in the request which this method should then merge into one video clip.

implement the file storage logic in generate_video of utilizing storage buckets when the setting is enabled, and saving to local file system if not.

also utilize the MV_DEBUG_MODE logic to print out debugging data when that setting is enabled.

## v7

Integrate the /api/stitch-videos endpoint with quick-gen-page frontend page: when the all the individual scene clips finish generating call the stitch-video endpoint with each clips, then when that's finished processing, return the fully stitched-video and display below all the individual clips.

## v8

on the fronend /create page make the following modifications:
- on generation mode toggle button default to "music video"
- for music video selection:
    - don't display the product image upload, and don't require for validation for "generate video" button
    - display character & style input box by default with "use ai generation" toggled on by default

## v9

on the frontend /quick-gen-page make a large refactor of the page display:
- combine the scene cards with the clip cards:
    - scene prompt on the left of the card, corresponding clip on the right
        - refactor how scene prompt displays to be more visually appealing, and emphasize description with negative description as toggeable, default collpased
        - for both scene prompts and video clips improve the loading animation to be more visually compelling for the long wait times. Use input data about what the video description and character description in the loading state so use understand what's going to be generated there. Note: scene prompts take an estimated 20-30s, and video clips take 2-7minutes to generate
        - enable new buttons and associate routes with them for these combined cards:
            - scene prompt:
                - enable edit of the prompt
                - regenerate the prompt
            - video prompt:
                - regenerate video
        - remove the scene generation loading page, and move the progress bar loading to the individual scene prompt cards
        - collapse the input data section into a toggeable expand/collapse when scene prompt generation returns.
        - when scene generation returns, teletype the scene prompts into the display over 10 second duration.

### Implementation Details (Clarified):
- **Layout**: Side-by-side on desktop (50/50 split), vertical stack on mobile (scene top, video bottom)
- **Edit Prompt**: Inline editing within card with Save/Cancel buttons
- **Regenerate Prompt**: Calls `/api/mv/create_scenes` and updates only that specific card's scene prompt (using scene index)
- **Regenerate Video**: Calls `/api/mv/generate_video` with current scene prompt (edited or original)
- **Loading Snippets**: Brief contextual text that rotates every 3-5s (scene) or 10-15s (video) based on input data
- **Teletype**: Parallel animation - all scenes type simultaneously within 10 second total duration (configurable constant)
- **Input Data Collapse**: Auto-collapses when scene generation completes, manually toggleable
- **Auto-scroll**: Automatically scrolls to Full Video section when stitching completes
- **Responsive**: Uses Tailwind `flex-col md:flex-row` for responsive behavior

## v10

- update the generate_character_reference endpoint and the frontend elements that utilize it to no longer send back base64 encoded image, but instead get the frontend to download the image /get_character_reference endpoint.

### Implementation Details (Clarified):
- **Backend Model Changes**: Remove `base64` field from `CharacterReferenceImage`, keep `id`, `path`, and `cloud_url`
- **Image Fetching**: Frontend uses `/api/mv/get_character_reference/{id}?redirect=false` to fetch images
  - `redirect=false` returns JSON with presigned URL (cloud) or serves file directly (local)
  - Mark in `v2/impl-notes.md` that we use `redirect=false` for img element population
- **Frontend Flow**:
  1. Call `/generate_character_reference` → receive image IDs only (no base64)
  2. Fetch all 4 images in parallel via `/get_character_reference/{id}`
  3. Show loading spinners on placeholder cards during fetch
  4. Display images when loaded, show error state on individual failures
- **UI/UX**: Fixed aspect ratio placeholders prevent layout shift, parallel loading with individual loading states
- **Error Handling**: Show error icon/message on failed images, use existing "Regenerate All" button (no individual retry)
- **Performance**: Reduces response payload from 4-16MB to ~1KB, enables HTTP caching, parallel image loading

## v11

for the generate_video endpoint refactor the character_reference handling: replace the request paramater of expecting base64 and instead expect a uuid of the character_reference which can be converted into to url via /get_character_reference that can be used by replicate service call supply the reference_image to the video generation call to replicate's api.

### Implementation Details (Clarified):
- **New Parameter**: Add `character_reference_id: Optional[str]` to request model
- **Backward Compatibility**: Keep `reference_image_base64` parameter (deprecated) for transition period
- **Priority**: If both UUID and base64 provided, UUID takes precedence with warning log
- **File Resolution**: Backend resolves UUID to file path: `mv/outputs/character_reference/{uuid}.{ext}`
- **File Extensions**: Check for `.png`, `.jpg`, `.jpeg`, `.webp` extensions
- **Replicate Integration**: Pass open file handle to `input_params["reference_images"]`
- **Error Handling**:
  - UUID not found: Log warning to stdout, add warning to response metadata, continue without reference (don't fail)
  - Invalid file path: Raise clear error with UUID and attempted paths
- **Response Warning**: Add optional `character_reference_warning` field if UUID not found
- **Performance**: Eliminates base64 encoding/decoding overhead, reduces request payload
- **Frontend**: Not implemented yet - frontend doesn't currently send character reference to generate_video

## v12

implement a trim_audio method that will operate on youtube video audio download and accept start/end duration.

for the frontend quick-gen-page add the id of audio file and the audio component that will allow the user to play the clip. do this only if a youtube video's audio has been selected.

on the stitch-videos endpoint add an optional paramater for audio stiching that accepts optional params:
    - audio_overlay_id: which is an id to audio track downloaded from youtube which will be overlaid to the sitched video output
    - suppress_video_audio: which will strip the audio from the video clips leaving only the audio_overlay audio in the final video.

thes desired behavior here is to make the target output duration equal to the sum of the video clip duration so clip the audio to make this work.

have the frontend attach those new params to the stitch-video request if a youtube song is selected on the create page.

### Implementation Details (Clarified):
- **Audio Trimmer Module**: New utility in `services/audio_trimmer.py` with `trim_audio(audio_id, start_time, end_time)` function
- **Trimming Strategy**: Create new UUID for trimmed audio, preserve original file
- **Audio Storage**: All audio files in `mv/outputs/audio/{uuid}.mp3` format
- **Duration Matching**: If audio > video duration, trim audio from start (0 to video_duration)
- **Video Audio Suppression**: Use `clip.without_audio()` on video clips when `suppress_video_audio=True`
- **Audio Overlay**: Use `final_clip.set_audio(audio_clip)` from moviepy's `AudioFileClip`
- **Error Handling**: Audio errors never fail stitching - log warning and continue without audio overlay
- **Frontend Audio Display**: Reuse AudioPlayer component from create page in quick-gen-page Input Data section
- **Data Flow**: audioId passed from create page → quick-gen-page via router state/sessionStorage
- **Conditional Parameters**: Only send `audio_overlay_id` and `suppress_video_audio` to stitch endpoint if audioId exists
- **Response Fields**: Add `audio_overlay_applied` (bool) and `audio_overlay_warning` (optional string) to StitchVideosResponse
- **Debug Logging**: Log audio operations when `MV_DEBUG_MODE=true`
- **Metadata Tracking**: Store trimmed audio metadata in `{uuid}_metadata.json` with source_audio_id, start_time, end_time