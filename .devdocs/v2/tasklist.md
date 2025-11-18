# v2 Task List

## v1 - Multi-Image Character Reference Generation

### Summary
Enable batch generation of 1-4 character reference images from a single prompt, with UUID-based storage and frontend selection UI.

### Backend Tasks

- [x] **Update image storage pattern to UUID**
  - Change from `character_ref_YYYYMMDD_HHMMSS.ext` to `{uuid}.ext`
  - Update `generate_character_reference_image()` to use UUID for filenames
  - Ensure backward compatibility or migration path for existing files

- [x] **Modify Replicate API call for batch generation**
  - Update Replicate service call to support `number_of_images` parameter (1-4)
  - Handle batch response from Replicate API (list of image URLs)
  - Process and save each image with unique UUID

- [x] **Update request model**
  - Add `num_images` parameter to `GenerateCharacterReferenceRequest` (default: 4, range: 1-4)
  - Validate input range

- [x] **Update response model**
  - Change from single image response to list of image objects
  - Each object contains: `id` (UUID), `path`, `base64`, `metadata`
  - Return all generated images in single response

- [x] **Update endpoint logic**
  - Modify `/api/mv/generate_character_reference` to handle batch generation
  - Process all images from Replicate response
  - Build and return list of image data

- [x] **Add image retrieval endpoint** (if not exists)
  - `GET /api/mv/get_character_reference/{image_id}` to fetch image by UUID
  - Support fetching previously generated images

- [x] **Update debug logging**
  - Log batch generation details (num_images requested, num generated)
  - Log individual image UUIDs

- [x] **Update unit tests**
  - Test batch generation (1, 2, 3, 4 images)
  - Test UUID filename format
  - Test response structure with multiple images
  - Test validation (num_images out of range)

### Frontend Tasks

- [x] **Update API client**
  - Modify character reference generation request to include `num_images` parameter
  - Update response type to handle list of images

- [x] **Create image selection UI**
  - Display 4 images in a grid layout (2x2 or horizontal)
  - Each image should be clearly visible and comparable
  - Add selection indicator (border, checkmark, etc.)

- [x] **Implement single-select logic**
  - Allow only one image to be selected at a time
  - Clear previous selection when new image is clicked
  - Highlight selected image

- [x] **Add proceed button/action**
  - Enable "Continue" or "Select" button only when an image is selected
  - Pass selected image ID to next step (video generation)

- [x] **Handle loading state**
  - Show loading indicator while generating 4 images
  - Consider progressive loading if images return at different times

- [x] **Error handling**
  - Handle partial failures (e.g., 3 of 4 images generated)
  - Display error message if all generations fail

- [x] **Update video generation flow**
  - Accept selected image ID from previous step
  - Fetch image data by ID for reference_image_base64 parameter
  - Or pass image ID directly if video endpoint supports it

### Documentation Tasks

- [ ] **Update API documentation**
  - Document new `num_images` parameter
  - Document new response structure
  - Add examples for batch generation

- [ ] **Update client implementation notes**
  - Document selection flow for frontend developers
  - Explain how to pass selected image to video generation

- [ ] **Update impl-notes.md**
  - Document UUID storage change
  - Document batch generation architecture decisions
  - Note any limitations (Replicate API constraints, etc.)

---

## v2 - Quick Job Button & Data Display Page

### Summary
Add a "Quick Job" button to the create page that navigates to a new `/quick-gen-page` route, passing form data via URL state and displaying it in a card.

### Frontend Tasks

- [ ] **Add "Quick Job" button to create page**
  - Add button below "Generate videos" button
  - Match styling of "Generate videos" button
  - No validation logic required (always enabled)
  - On click: navigate to `/quick-gen-page` with form data

- [ ] **Implement data passing via URL state**
  - Use Next.js `router.push` with state object
  - Pass: `videoDescription`, `characterDescription`, `selectedImageId`
  - Handle case where state is empty/undefined

- [ ] **Create /quick-gen-page route**
  - Create `frontend/src/app/quick-gen-page/page.tsx`
  - Match layout/styling of `/result/[id]/page.tsx`:
    - Dark gradient background
    - Nav bar with logo and "Back to Create" button
    - Centered content with max-w-4xl

- [ ] **Create input data display card**
  - Display card at top of page with form data:
    - "Video Description" field
    - "Character and Style" field (characterDescription)
    - "Character Reference Image ID" field
  - Show empty/placeholder if data not provided
  - Use Card component with gray-800/50 background styling

- [ ] **Handle missing state gracefully**
  - If no state passed (direct URL access), show empty values
  - Consider redirect to `/create` if state is missing (optional)

### Testing Tasks

- [ ] **Manual testing**
  - Test navigation from create page to quick-gen-page
  - Verify data displays correctly in card
  - Test with missing/empty fields
  - Test direct URL access (no state)
  - Test "Back to Create" navigation

---

## v3 - Scene Generation API Integration

### Summary
Integrate `/api/mv/create_scenes` API call on `/quick-gen-page`, showing simulated progress bar during request and displaying generated scenes in cards.

### Frontend Tasks

- [ ] **Add API call on page load**
  - Call `/api/mv/create_scenes` immediately when page mounts
  - Request body: `{ "idea": videoDescription, "character_description": characterDescription }`
  - Only call if both fields are non-empty
  - Handle case where data is missing (skip API call)

- [ ] **Implement simulated progress bar**
  - Show progress bar during API call (10-30 second expected duration)
  - Simulate progress from 0% to ~90% over time
  - Jump to 100% when response arrives
  - Use same Progress component as `/result/[id]/page.tsx`
  - Show "Generating scenes..." status message

- [ ] **Display scenes in cards**
  - Parse response: `response.scenes` array
  - Each scene contains: `description` and `negative_description`
  - Create card for each scene with:
    - Scene number/title
    - Description text
    - Negative description text (clearly labeled)
  - Use same Card styling as existing cards (gray-800/50, border-gray-700)

- [ ] **Handle loading states**
  - Show progress bar card while loading
  - Replace with scene cards when complete
  - Show status indicators (pending → processing → completed)

- [ ] **Error handling**
  - Display error message in card area if API fails
  - Show error details (network error, server error, etc.)
  - Use Alert component with destructive variant
  - Allow retry or navigation back to create page

- [ ] **Update state management**
  - Track: isLoading, progress, scenes array, error state
  - Clear progress simulation interval on response/error

### Testing Tasks

- [ ] **Manual testing**
  - Test API call triggers on page load
  - Verify progress bar animates during wait
  - Check scene cards display correctly with both fields
  - Test error scenarios (backend down, invalid data)
  - Test with missing input data (no API call)

---

## v4 - Video Generation from Scenes

### Summary
After scenes are generated, automatically trigger parallel video generation for each scene via `/api/mv/generate_video`. Display videos in individual cards with loading states and an overall status summary bar.

### Frontend Tasks

- [ ] **Trigger video generation after scenes complete**
  - After scenes array is populated, automatically start video generation
  - One API call per scene, all in parallel
  - Request body per scene:
    - `prompt`: scene.description
    - `negative_prompt`: scene.negative_description
  - Omit all other parameters (reference_image_base64, etc.)
  - NOTE: Character reference image integration deferred (document as limitation)

- [ ] **Create video cards immediately**
  - Create placeholder cards for each video before generation starts
  - Show loading state per card (spinner, "Generating video...")
  - Display scene number in card header
  - Use configurable expected load time (default: 7 seconds)

- [ ] **Handle individual video responses**
  - Track state per video: loading | completed | error
  - On success: store video_id and video_url from response
  - On error: store error message for that specific card
  - Update card state as each response arrives

- [ ] **Display videos in cards**
  - Replace loading state with video player when ready
  - Video controls: enabled, sound enabled, no autoplay
  - Show video metadata (video_id, etc.)
  - Use video URL from response (or fetch via `/api/mv/get_video/{id}`)

- [ ] **Implement overall status summary bar**
  - Show at top of videos section
  - Display counts: "X loading / Y succeeded / Z failed"
  - Update in real-time as videos complete
  - Use Badge components for status colors:
    - Blue: loading
    - Green: succeeded
    - Red: failed

- [ ] **Error handling per card**
  - Display error message within the specific video card
  - Show which scene number failed
  - Keep other videos unaffected
  - Use Alert component within card

- [ ] **State management**
  - Track array of video states (one per scene)
  - Each entry: { sceneIndex, status, videoId?, videoUrl?, error? }
  - Calculate summary stats from this array

### Documentation Tasks

- [ ] **Update impl-notes.md**
  - Document character reference image limitation
  - Note that reference_image_base64 is not passed to generate_video
  - Document parallel generation approach
  - Document expected load time configuration

### Testing Tasks

- [ ] **Manual testing**
  - Verify video generation triggers after scenes complete
  - Check all videos generate in parallel
  - Test loading states display correctly
  - Verify videos play with controls and sound
  - Test error scenarios (some videos fail, all fail)
  - Check status summary bar updates correctly
  - Test with mock mode enabled (MOCK_VID_GENS=true)

---

## v5 - Dual Storage Backend Support (Local/S3)

### Summary
Enable the quick-gen-page frontend to seamlessly handle video URLs from both local filesystem (relative paths) and S3 cloud storage (presigned URLs) without backend changes. The frontend should automatically detect the URL type and handle appropriately.

### Frontend Tasks

- [ ] **Update video URL handling logic**
  - Detect if `video_url` from `generate_video` response is absolute (starts with `http`)
  - If absolute URL (S3 presigned): use directly as video src
  - If relative URL (local): prepend `API_URL` as before
  - Update `generateSingleVideo()` function in `/quick-gen-page/page.tsx`

- [ ] **Add helper function for URL resolution**
  - Create `resolveVideoUrl(videoUrl: string)` function
  - Returns absolute URL ready for use in video player
  - Handles both S3 presigned URLs and local backend paths

- [ ] **Update video player src assignment**
  - Use resolved URL in video card component
  - Ensure video element can load from both sources

### Testing Tasks

- [ ] **Test with SERVE_FROM_CLOUD=true (S3 mode)**
  - Verify video URLs are S3 presigned URLs (start with https://)
  - Confirm videos load and play correctly from S3
  - Check that no API_URL is incorrectly prepended

- [ ] **Test with SERVE_FROM_CLOUD=false (local mode)**
  - Verify video URLs are relative paths (/api/mv/get_video/{uuid})
  - Confirm API_URL is prepended correctly
  - Check videos load from local backend

- [ ] **Edge case testing**
  - Test switching between modes (requires backend restart)
  - Verify mixed responses don't cause issues
  - Check error handling for both storage backends

### Documentation Tasks

- [ ] **Update impl-notes.md**
  - Document dual storage backend detection logic
  - Note that frontend auto-detects based on URL format
  - Document the URL resolution approach

---

## v6 - Video Stitching Endpoint

### Summary
Implement `/api/mv/stitch-videos` endpoint that merges multiple video clips into a single video using MoviePy. Support both local filesystem and S3 storage backends based on SERVE_FROM_CLOUD setting. Include debug logging when MV_DEBUG_MODE is enabled.

### Backend Tasks

- [ ] **Add MoviePy dependency**
  - Add `moviepy` to requirements.txt
  - Verify installation with `uv pip install moviepy`

- [ ] **Create video stitching module**
  - Create `backend/mv/video_stitcher.py`
  - Implement `stitch_videos(video_ids: list[str]) -> tuple[str, str, str, dict]`
  - Return format: (video_id, video_path, video_url, metadata)
  - Handle both local and S3 storage modes

- [ ] **Implement video file retrieval**
  - For SERVE_FROM_CLOUD=false: read from local filesystem
  - For SERVE_FROM_CLOUD=true: download from S3 to temp directory
  - Validate all video IDs exist before processing
  - Fail entire operation if any video is missing

- [ ] **Implement video merging logic**
  - Use MoviePy's `VideoFileClip` and `concatenate_videoclips`
  - Configure codec (libx264) and audio codec (aac)
  - Generate new UUID for merged video
  - Save to appropriate location based on SERVE_FROM_CLOUD

- [ ] **Implement storage backend logic**
  - SERVE_FROM_CLOUD=false: save to local filesystem
  - SERVE_FROM_CLOUD=true: upload merged video to S3
  - Return appropriate video_url (relative path vs S3 presigned URL)

- [ ] **Create request/response models**
  - Request: `StitchVideosRequest` with `video_ids: list[str]`
  - Response: `StitchVideosResponse` similar to `GenerateVideoResponse`
  - Include metadata: input video IDs, processing time, storage backend

- [ ] **Add endpoint to router**
  - POST `/api/mv/stitch-videos`
  - Validate video IDs format (UUID)
  - Call stitch_videos function
  - Return response with video_id, video_url, metadata

- [ ] **Add debug logging**
  - Log when MV_DEBUG_MODE is enabled
  - Log: video IDs received, storage mode, temp file locations
  - Log: merging start/end, upload progress, final URL
  - Add debug functions to `backend/mv/debug.py`

- [ ] **Error handling**
  - Return 400 if empty video_ids list
  - Return 404 if any video ID not found
  - Return 500 for MoviePy processing errors
  - Clean up temp files on error

- [ ] **Cleanup temporary files**
  - Remove downloaded S3 files after merging
  - Remove intermediate files from MoviePy processing

### Testing Tasks

- [ ] **Manual testing with SERVE_FROM_CLOUD=false**
  - Test with 2-3 local video files
  - Verify merged video plays correctly
  - Check metadata contains input video IDs

- [ ] **Manual testing with SERVE_FROM_CLOUD=true**
  - Test with videos stored in S3
  - Verify S3 download and re-upload works
  - Check presigned URL returned for merged video

- [ ] **Error case testing**
  - Test with non-existent video ID
  - Test with empty video_ids list
  - Test with single video (edge case)

### Documentation Tasks

- [ ] **Update impl-notes.md**
  - Document video stitching implementation
  - Note MoviePy usage and codecs
  - Document storage backend handling
  - Note temporary file management

---

## v7 - Automatic Video Stitching Integration

### Summary
Automatically trigger video stitching when all individual scene clips finish generating. Display a loading indicator with estimated completion time (5 seconds per video), then show the final stitched video in a special "Full Video" card below the individual clips. Include error handling with retry capability and user-friendly error messages.

### Frontend Tasks

- [ ] **Detect when all scene videos complete**
  - Monitor video generation state array
  - Trigger stitching when all videos have status: 'completed'
  - Only trigger if at least one video succeeded (skip if all failed)
  - Ensure stitching only triggers once (use flag or status check)

- [ ] **Prepare video IDs for stitching**
  - Collect all successfully generated video IDs in sequential order
  - Filter out any failed videos from the stitching list
  - Maintain original scene order for stitching

- [ ] **Call /api/mv/stitch-videos endpoint**
  - POST request with body: `{ "video_ids": [...] }`
  - Pass array of video IDs in sequential order
  - Handle response with video_id, video_url, metadata

- [ ] **Create "Full Video" card section**
  - Display below individual scene video cards
  - Card title: "Full Video"
  - Section header to visually separate from individual clips
  - Use same card styling as other cards (gray-800/50, border-gray-700)

- [ ] **Implement stitching loading state**
  - Show loading indicator in Full Video card while stitching
  - Display progress message: "Stitching videos..."
  - Show estimated time: "Estimated time: X seconds" (5 seconds × number of videos)
  - Use Progress component or loading spinner
  - Update timer/progress as time elapses

- [ ] **Display stitched video on success**
  - Replace loading state with video player
  - Use resolved video URL (handle both local and S3 URLs like individual videos)
  - Video controls: enabled, sound enabled, no autoplay
  - Display metadata below video:
    - Number of clips stitched
    - Total duration (if available in metadata)
    - Stitched video ID

- [ ] **Error handling for stitching failures**
  - Catch API errors from stitch-videos endpoint
  - Display user-friendly error message in Full Video card:
    - "Failed to stitch videos. Please try again."
    - Show specific error if available (e.g., "Video not found")
  - Add "Retry Stitching" button
  - Allow user to retry without regenerating individual videos
  - Use Alert component with destructive variant for errors

- [ ] **Implement retry functionality**
  - "Retry Stitching" button clears error state
  - Re-triggers stitch-videos API call with same video IDs
  - Returns to loading state
  - Limit retries or allow unlimited attempts (TBD based on preference)

- [ ] **State management for stitching**
  - Add state variables:
    - `stitchingStatus`: 'idle' | 'loading' | 'completed' | 'error'
    - `stitchedVideo`: { videoId, videoUrl, metadata }
    - `stitchingError`: error message string
    - `estimatedStitchTime`: calculated based on video count
  - Track whether stitching has been triggered to prevent duplicates

- [ ] **Handle edge cases**
  - No videos generated successfully (don't show Full Video card)
  - Only 1 video generated (still stitch for consistency, or skip?)
  - Partial video failures (stitch only successful ones)

### Testing Tasks

- [ ] **Manual testing - Happy path**
  - Generate multiple scene videos (2-4 clips)
  - Verify stitching triggers automatically when all complete
  - Check loading indicator shows correct estimated time
  - Confirm stitched video plays correctly
  - Verify individual clips remain visible above stitched video

- [ ] **Manual testing - Error scenarios**
  - Simulate backend stitching failure (backend down, invalid IDs)
  - Verify user-friendly error message displays
  - Test retry button functionality
  - Confirm retry works after fixing backend issue

- [ ] **Manual testing - Edge cases**
  - Test with single generated video
  - Test when some individual videos fail (partial success)
  - Test with both storage modes (SERVE_FROM_CLOUD=true/false)
  - Verify stitched video URL resolution works for both modes

- [ ] **Manual testing - State management**
  - Verify stitching only triggers once
  - Check that page refresh doesn't re-trigger stitching
  - Test loading state displays correctly during processing
  - Verify state transitions (idle → loading → completed/error)

### Documentation Tasks

- [ ] **Update impl-notes.md**
  - Document automatic stitching trigger logic
  - Note estimated time calculation (5 seconds per video)
  - Document error handling and retry mechanism
  - Note edge case handling (partial failures, single video, etc.)
  - Document Full Video card placement and styling
