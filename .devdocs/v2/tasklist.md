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
