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
