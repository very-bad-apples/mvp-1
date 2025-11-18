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
  - Handle batch image response (array instead of single image)
  - Store all image IDs for user selection

- [x] **Create multi-image display component**
  - Display 4 images in grid layout (2x2 or 1x4)
  - Support selecting one image
  - Add selection indicator (border, checkmark, etc.)

- [x] **Update character reference selection logic**
  - Allow only one image to be selected at a time
  - Store selected image ID for next step
  - Update "Generate Videos" button to use selected ID

- [x] **Update UI/UX**
  - Loading state for all 4 images
  - Individual loading indicators per image
  - Error state if generation fails
  - Placeholder UI before images load

- [x] **Update form validation**
  - Require at least one image selected to proceed
  - Disable "Generate Videos" if no selection
  - Show error message if user tries to proceed without selection

---

## v2 - Quick Job Button and Page

### Summary
Add "Quick Job" button to /create page that routes to /quick-gen-page and displays input data without validation.

### Frontend Tasks

- [x] **Add Quick Job button to /create page**
  - Position below "Generate Videos" button
  - No validation logic required (button always enabled)
  - Route to `/quick-gen-page`

- [x] **Create /quick-gen-page route and component**
  - Create `src/app/quick-gen-page/page.tsx`
  - Use similar layout/styling as `/result/job_[id]` page

- [x] **Pass data from /create to /quick-gen-page**
  - Use Next.js router state or sessionStorage
  - Pass: video description, character & style, character reference image ID

- [x] **Display input data on /quick-gen-page**
  - Create card component to display data
  - Show "video description" field
  - Show "character and style" field
  - Show "character reference image ID" field

- [x] **Basic styling**
  - Match overall theme of existing pages
  - Card layout for input data display
  - Placeholder for future sections

---

## v3 - Scene Generation on Quick Gen Page

### Summary
Kick off `/api/mv/create_scenes` call on page load and display scenes in cards with progress bar.

### Frontend Tasks

- [x] **Implement scene generation trigger**
  - Auto-trigger on page load when data is available
  - Call `/api/mv/create_scenes` with idea and character_description
  - Handle loading state

- [x] **Add progress/loading UI**
  - Progress bar similar to `/result/job_[id]` page
  - Expected time: 10-30 seconds
  - Loading message

- [x] **Display scene cards when response arrives**
  - Parse scenes array from response
  - Create card component for each scene
  - Display scene data (description, negative_description, etc.)

- [x] **Error handling**
  - Handle API errors
  - Display error message if scene generation fails
  - Retry option

---

## v4 - Video Generation from Scenes

### Summary
Generate videos for each scene and display in individual cards with loading states.

### Frontend Tasks

- [x] **Trigger video generation when scenes arrive**
  - One `/api/mv/generate_video` call per scene
  - Map scene fields: `description → prompt`, `negative_description → negative_prompt`
  - Generate videos in parallel

- [x] **Create video card placeholders immediately**
  - Show loading state for each video
  - Display alongside or within scene cards

- [x] **Fetch and display videos as they complete**
  - Call `/api/mv/get_video` with UUID/video_url
  - Update card from loading to video player
  - Handle individual video failures

- [x] **Loading states per video**
  - Spinner/progress indicator
  - Expected time display (can be 2-7 minutes)
  - Video title or scene number

- [x] **Error handling**
  - Individual error states per video
  - Don't block other videos if one fails
  - Retry option per video

---

## v5 - Dual Storage Backend Support

### Summary
Fix `/quick-gen-page` to work with both local filesystem and S3 cloud storage backends.

### Backend Tasks

- [x] **Verify SERVE_FROM_CLOUD environment variable**
  - Check behavior when `SERVE_FROM_CLOUD=true`
  - Check behavior when `SERVE_FROM_CLOUD=false`
  - Document the difference in video_url format

- [x] **Document get_video redirect parameter**
  - `redirect=false` returns JSON with presigned URL (cloud) or file URL (local)
  - `redirect=true` returns actual video file
  - Update API docs

### Frontend Tasks

- [x] **Update video URL resolution logic**
  - Check if video_url is absolute URL (S3 presigned) or relative path (local API)
  - Handle both formats seamlessly
  - Add helper function to resolve video URLs

- [x] **Use redirect=false for video fetching** (if needed)
  - Fetch video metadata before displaying
  - Extract presigned URL from JSON response
  - Use URL in video element src

- [x] **Test both storage modes**
  - Test with local filesystem storage
  - Test with S3 cloud storage
  - Verify video playback in both modes

---

## v6 - Video Stitching Endpoint

### Summary
Implement `/api/mv/stitch-videos` endpoint to merge multiple video clips into one.

### Backend Tasks

- [x] **Create /api/mv/stitch-videos endpoint**
  - Accept list of video IDs in request body
  - Implement merge functionality (reference: `.ref-pipeline/src/main.py:merge_videos`)

- [x] **Implement video merging logic**
  - Fetch videos by IDs
  - Concatenate videos in order
  - Return stitched video with new UUID

- [x] **Handle storage backend logic**
  - Save to local filesystem if `SERVE_FROM_CLOUD=false`
  - Upload to S3 if `SERVE_FROM_CLOUD=true`
  - Return appropriate video_url based on storage mode

- [x] **Add debug logging**
  - Log when MV_DEBUG_MODE is enabled
  - Log stitch operation details (num videos, IDs, output size)

- [x] **Error handling**
  - Handle missing video IDs
  - Handle merge failures
  - Return meaningful error messages

---

## v7 - Frontend Video Stitching Integration

### Summary
Call `/api/mv/stitch-videos` when all scene clips finish and display result.

### Frontend Tasks

- [x] **Detect when all videos are complete**
  - Track status of all video generation tasks
  - Trigger stitch when all succeeded (or some failed)

- [x] **Call /api/mv/stitch-videos endpoint**
  - Pass array of successful video IDs in order
  - Handle loading state during stitching
  - Expected time: ~5 seconds per video

- [x] **Display stitched video**
  - Create "Full Video" section below individual clips
  - Show video player when stitching completes
  - Display metadata (duration, num clips, etc.)

- [x] **Loading state**
  - Progress indicator during stitching
  - Estimated time display
  - Message: "Stitching X videos together..."

- [x] **Error handling**
  - Handle stitch failures
  - Retry option
  - Fallback: still show individual clips

---

## v8 - Create Page Form Improvements

### Summary
Update /create page to default to "Music Video" mode with appropriate field visibility.

### Frontend Tasks

- [x] **Update generation mode toggle default**
  - Set default to "music video" instead of product video
  - Update initial state

- [x] **Update field visibility for music video mode**
  - Hide product image upload field
  - Show character & style input by default
  - Default "use AI generation" to toggled ON

- [x] **Update validation logic**
  - Don't require product image for music video mode
  - Enable "Generate Videos" button without product image in music video mode

- [x] **Test mode switching**
  - Verify switching between modes works correctly
  - Verify field visibility changes
  - Verify validation changes

---

## v9 - Quick Gen Page UI Refactor

### Summary
Major refactor of /quick-gen-page to combine scene and video cards, improve loading animations, and add editing/regeneration controls.

### Frontend Tasks

#### Layout Refactor

- [x] **Combine scene and video cards**
  - Single card per scene with two sections: scene prompt (left/top) and video clip (right/bottom)
  - Responsive layout: side-by-side on desktop (50/50 split), stacked on mobile (scene top, video bottom)
  - Use Tailwind: `flex-col md:flex-row`

- [x] **Refactor scene prompt display**
  - Emphasize description text
  - Make negative_description collapsible (default collapsed)
  - Improve typography and spacing

#### Loading Animations

- [x] **Improve scene prompt loading**
  - Remove separate scene generation loading page
  - Move progress bar to individual scene cards
  - Show contextual snippets based on input data
  - Display video description and character description excerpts
  - Estimated time: 20-30 seconds

- [x] **Improve video clip loading**
  - Show contextual loading message using scene prompt
  - Brief snippets that rotate every 10-15 seconds
  - Estimated time: 2-7 minutes
  - Visual spinner or animated placeholder

#### Interactive Controls

- [x] **Scene prompt editing**
  - Add "Edit" button on completed scene cards
  - Inline text editing within card (not modal)
  - Save/Cancel buttons when editing

- [x] **Scene prompt regeneration**
  - Add "Regenerate" button
  - Call `/api/mv/create_scenes` again
  - Update only that specific card's scene prompt (using scene index from response)

- [x] **Video clip regeneration**
  - Add "Regenerate" button on video section
  - Call `/api/mv/generate_video` with current scene prompt (edited or original)
  - Replace video in that card

#### Special Effects

- [x] **Teletype animation for scene prompts**
  - When scenes return from API, animate text appearing character-by-character
  - Total duration: 10 seconds for all scenes combined
  - Parallel animation: all scenes type simultaneously
  - Configurable duration constant in code
  - Click to skip animation

- [x] **Auto-collapse input data**
  - Collapse input data section when scene generation completes
  - Add expand/collapse toggle button
  - Smooth animation

- [x] **Auto-scroll to stitched video**
  - When video stitching completes, auto-scroll to "Full Video" section
  - Smooth scroll animation
  - Small delay before scrolling (300ms)

#### Implementation Notes

- Use React hooks for edit state management
- Store edited prompts in component state
- Scene regeneration uses same API, just updates one card
- Video regeneration uses current (possibly edited) prompt
- Teletype calculates character delay: `totalDuration / totalCharacters`
- Loading snippets rotate on timer (useEffect with setInterval)
- Input collapse state persists during session
- Auto-scroll uses `scrollIntoView({ behavior: 'smooth' })`

---

## v10 - Remove Base64 Image Transfer

### Summary
Optimize character reference image handling by removing base64 encoding from API responses and using separate image fetch endpoint.

### Backend Tasks

- [x] **Update CharacterReferenceImage model**
  - Remove `base64` field from model definition
  - Keep `id`, `path`, and `cloud_url` fields
  - Update docstring to note base64 removal

- [x] **Update generate_character_reference_image()**
  - Remove base64 encoding logic
  - Don't read image into memory for encoding
  - Just save file and return metadata (id, path, cloud_url)

- [x] **Update response building**
  - Remove base64 encoding from image objects
  - Reduce response payload size dramatically (4-16MB → ~1KB)

- [x] **Verify /get_character_reference endpoint**
  - Ensure `redirect=false` returns JSON with presigned URL (cloud) or serves file (local)
  - Test both storage modes
  - Verify CORS headers allow frontend access

### Frontend Tasks

- [x] **Remove base64 handling from create page**
  - Don't expect `base64` field in API response
  - Store only image IDs

- [x] **Implement image fetching logic**
  - Create `fetchCharacterImage(imageId)` function
  - Use `/api/mv/get_character_reference/{id}?redirect=false`
  - Handle JSON response (cloud) vs blob response (local)
  - Create blob URLs for local mode

- [x] **Fetch all images in parallel**
  - Use `Promise.allSettled()` for parallel fetching
  - Don't block on individual failures
  - Update UI as each image loads

- [x] **Add loading states for images**
  - Show spinner on placeholder cards while fetching
  - Fixed aspect ratio placeholders (prevent layout shift)
  - Individual loading state per image

- [x] **Add error states for images**
  - Show error icon/message if image fetch fails
  - Individual error state per image
  - No individual retry (use existing "Regenerate All" button)

- [x] **Update image display logic**
  - Use fetched blob URLs or presigned URLs
  - `<img src={imageUrl} />` for both modes
  - Clean up blob URLs on unmount

### Testing Tasks

- [x] **Test with local storage**
  - Generate images with `SERVE_FROM_CLOUD=false`
  - Verify images fetch correctly
  - Verify blob URL creation

- [x] **Test with cloud storage**
  - Generate images with `SERVE_FROM_CLOUD=true`
  - Verify presigned URLs work
  - Verify images display correctly

- [x] **Test parallel loading**
  - Verify all 4 images load in parallel
  - Test with network throttling
  - Verify loading spinners appear

- [x] **Test error cases**
  - Simulate image fetch failure
  - Verify error state displays
  - Verify other images still load

### Documentation Tasks

- [x] **Update impl-notes.md**
  - Document v10 implementation
  - Explain redirect=false usage
  - Document payload size reduction
  - Note performance benefits

- [x] **Update API documentation**
  - Update `GenerateCharacterReferenceResponse` schema
  - Remove `base64` field from example responses
  - Add note about fetching images via `/get_character_reference` endpoint
  - Document recommended frontend flow

- [x] **Add code comments**
  - Comment on why base64 was removed (performance, payload size)
  - Document image fetching pattern in frontend code
  - Note that `path` field will be removed in future iteration

---

## v11 - Character Reference UUID for Video Generation

### Summary
Refactor `/api/mv/generate_video` endpoint to accept character reference image UUID instead of base64-encoded image data. The backend will fetch the image from storage and provide it to the Replicate API as a file handle.

### Backend Tasks

#### 1. Update Request Model (`mv/video_generator.py`)

- [ ] **Add new parameter to GenerateVideoRequest**
  - Add `character_reference_id: Optional[str]` field
  - Keep `reference_image_base64: Optional[str]` field for backward compatibility (deprecated)
  - Add field description noting UUID format
  - Mark `reference_image_base64` as deprecated in docstring

- [ ] **Add validation logic**
  - Validate UUID format if `character_reference_id` is provided
  - Log warning if both `character_reference_id` and `reference_image_base64` are provided
  - Prioritize `character_reference_id` over `reference_image_base64` if both present

#### 2. Create Character Reference Fetcher Helper (`mv/video_generator.py` or new `mv/utils.py`)

- [ ] **Implement get_character_reference_image() function**
  - Accept `character_reference_id: str` parameter
  - Build file path: `mv/outputs/character_reference/{character_reference_id}.{ext}`
  - Check for common extensions: `.png`, `.jpg`, `.jpeg`, `.webp`
  - Return tuple of `(file_path: Path | None, exists: bool)`
  - Handle file not found case gracefully

- [ ] **Add error logging**
  - Log to stdout when UUID doesn't exist
  - Log warning with UUID and attempted file paths
  - Return None if file doesn't exist

#### 3. Update generate_video() Function (`mv/video_generator.py`)

- [ ] **Add character reference fetching logic**
  - Call `get_character_reference_image()` if `character_reference_id` provided
  - Handle file not found case
  - Add warning to metadata if UUID not found: `{"character_reference_warning": "Image {uuid} not found"}`
  - Pass file path to backend instead of base64 data

- [ ] **Update backend calls**
  - Pass `character_reference_path` parameter to backend functions
  - Remove base64 passing when UUID is used
  - Keep base64 path for backward compatibility

- [ ] **Update debug logging**
  - Log `character_reference_id` instead of `has_reference_image` boolean
  - Add new debug function: `log_character_reference_fetch()`
  - Include UUID and resolved file path in logs

- [ ] **Update metadata building**
  - Replace `has_reference_image` with `character_reference_id` in metadata
  - Add `character_reference_warning` field if UUID not found
  - Remove reference_image saving logic (already saved from generation)
  - Update metadata.json structure to include UUID instead of base64 indicator

#### 4. Update Replicate Backend (`mv/video_backends/replicate_backend.py`)

- [ ] **Add new parameter: character_reference_path**
  - Add `character_reference_path: Optional[str]` parameter
  - Keep `reference_image_base64: Optional[str]` for backward compatibility
  - Update function signature and docstring

- [ ] **Refactor reference image handling**
  - Check if `character_reference_path` is provided first
  - If provided, open file directly (skip base64 decode and temp file creation)
  - Pass open file handle to `input_params["reference_images"]`
  - Fallback to base64 logic if `character_reference_path` not provided

- [ ] **Simplify temp file logic**
  - Only create temp file if using base64 path (backward compatibility)
  - Use direct file handle if using character_reference_path
  - Ensure file handle is properly closed in finally block

- [ ] **Update error handling**
  - Handle FileNotFoundError if character_reference_path doesn't exist
  - Raise clear error message with UUID and file path
  - Log error before raising

#### 5. Update Gemini Backend (`mv/video_backends/gemini_backend.py`) (if applicable)

- [ ] **Check if Gemini backend uses reference images**
  - Review `generate_video_gemini()` function
  - Determine if similar changes needed

- [ ] **Apply same pattern if needed**
  - Add `character_reference_path` parameter
  - Update file handling logic
  - Update error handling

#### 6. Update Router Endpoint (`routers/mv.py`)

- [ ] **Update endpoint handler for /api/mv/generate_video**
  - Accept `character_reference_id` from request body
  - Pass to `generate_video()` function
  - Update OpenAPI documentation
  - Add example request with UUID

- [ ] **Update response model if needed**
  - Add `character_reference_warning` field to response if UUID not found
  - Document the warning field in response model
  - Make warning field optional

#### 7. Testing Tasks

- [ ] **Unit tests for get_character_reference_image()**
  - Test with valid UUID that exists
  - Test with valid UUID that doesn't exist
  - Test with invalid UUID format (should still check file)
  - Test with multiple file extensions (.png, .jpg, .webp)

- [ ] **Integration tests for generate_video**
  - Test with valid `character_reference_id`
  - Test with invalid/non-existent UUID (should warn but not fail)
  - Test with both `character_reference_id` and `reference_image_base64` (UUID should take priority)
  - Test with neither parameter (should work without reference image)

- [ ] **Backend API tests**
  - Test `/api/mv/generate_video` with `character_reference_id` in request
  - Verify warning in response when UUID not found
  - Verify successful generation with valid UUID
  - Test backward compatibility with `reference_image_base64`

- [ ] **Manual testing with actual Replicate API**
  - Generate a character reference image (get UUID)
  - Use that UUID in `generate_video` call
  - Verify video generation works with character reference
  - Verify character consistency in output video

#### 8. Documentation Tasks

- [ ] **Update API documentation**
  - Document new `character_reference_id` parameter
  - Mark `reference_image_base64` as deprecated
  - Add migration guide for clients
  - Document warning field in response

- [ ] **Update impl-notes.md**
  - Add v11 implementation section
  - Document UUID-based character reference flow
  - Explain file path resolution logic
  - Note performance benefits (no base64 encoding/decoding)

- [ ] **Update swagger/OpenAPI docs**
  - Add `character_reference_id` to request schema
  - Add examples with UUIDs
  - Mark `reference_image_base64` as deprecated in schema

### Frontend Tasks (Future - not part of v11)

- [ ] **Update /quick-gen-page to send character reference UUID** (deferred to future version)
  - Currently frontend doesn't send character reference to generate_video
  - When implemented, send `character_reference_id` from sessionStorage
  - Remove any base64 encoding logic if present

### Implementation Notes

- **Backward Compatibility**: Keep `reference_image_base64` parameter functional during transition period
- **Priority**: If both UUID and base64 provided, UUID takes precedence with a warning log
- **Error Handling**: UUID not found should log warning and add to metadata, but NOT fail video generation
- **File Extensions**: Check for .png, .jpg, .jpeg, .webp extensions when resolving UUID to file path
- **Performance**: Eliminates base64 encoding/decoding overhead, reduces request payload size
- **Debugging**: Enhanced logging for character reference resolution path

### Technical Details

**File Path Resolution**:
```
UUID: "abc123-def456-..."
Possible paths:
- backend/mv/outputs/character_reference/abc123-def456-....png
- backend/mv/outputs/character_reference/abc123-def456-....jpg
- backend/mv/outputs/character_reference/abc123-def456-....jpeg
- backend/mv/outputs/character_reference/abc123-def456-....webp
```

**Replicate API Integration**:
- Accepts `reference_images` as list of open file handles
- Example: `input_params["reference_images"] = [open("/path/to/image.png", "rb")]`
- File handles must be closed after API call completes

**Request Flow**:
1. Frontend sends `character_reference_id` in request
2. Backend resolves UUID to file path
3. If found: Opens file, passes handle to Replicate
4. If not found: Logs warning, adds to metadata, continues without reference
5. Replicate generates video (with or without reference)
6. Response includes warning field if UUID not found

---
