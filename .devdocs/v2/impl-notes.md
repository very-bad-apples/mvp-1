# Implementation Notes - v2

## v1 - Multi-Image Character Reference Generation

### Implementation Summary

Successfully implemented batch generation of 1-4 character reference images with UUID-based storage.

### Key Changes

#### Backend

1. **UUID-based Storage**
   - Changed from timestamp-based filenames (`character_ref_YYYYMMDD_HHMMSS.ext`)
   - Now uses UUID filenames (`{uuid}.ext`)
   - Images stored in `backend/mv/outputs/character_reference/`

2. **Batch Generation via Replicate API**
   - Added `number_of_images` parameter to Replicate API call
   - API returns list of FileOutput objects for batch requests
   - Each image processed and saved with unique UUID

3. **Updated Request Model**
   ```python
   class GenerateCharacterReferenceRequest:
       character_description: str  # Required
       num_images: int = 4         # New: 1-4, default 4
       # ... other optional params
   ```

4. **New Response Structure**
   ```python
   class CharacterReferenceImage:
       id: str      # UUID
       path: str    # File path
       base64: str  # Encoded image data

   class GenerateCharacterReferenceResponse:
       images: list[CharacterReferenceImage]  # Changed from single image
       metadata: dict
   ```

5. **New Image Retrieval Endpoint**
   - `GET /api/mv/get_character_reference/{image_id}`
   - Returns image file directly
   - Supports png, jpg, jpeg, webp formats
   - Validates UUID format

6. **Debug Logging**
   - Added `log_batch_image_request()` and `log_batch_image_result()` functions
   - Enhanced logging with num_images_requested, num_images_generated, image_ids

### Deviations from Plan

1. **Parallel API Calls Instead of Batch Parameter**
   - Plan assumed Replicate supports `num_outputs` or `number_of_images` parameter
   - **Reality**: Google Imagen 4 does NOT support batch generation (1 image per call)
   - **Solution**: Implemented parallel API calls using `ThreadPoolExecutor`
   - Each of the N requested images triggers a separate Replicate API call
   - Calls run concurrently for better performance
   - Each call can have unique seed (base_seed + offset) for variation

2. **Frontend Implementation Deferred**
   - Backend-only implementation completed
   - Frontend tasks (grid display, single-select UI) not implemented
   - Frontend team can use the new API structure

3. **No Video Generation Integration Yet**
   - Endpoint returns image ID that can be used with video generation
   - Fetching image by ID available via `/api/mv/get_character_reference/{id}`
   - Frontend must convert to base64 for video generation request (or enhancement could be made to accept ID directly)

### Architecture Decisions

1. **Pydantic ge/le Validation**
   - Used `Field(4, ge=1, le=4)` for automatic range validation
   - Additional manual validation in function for clarity

2. **UUID via Python stdlib**
   - Using `uuid.uuid4()` for standard UUID generation
   - No external dependencies needed

3. **Single Replicate API Call**
   - Batch generation uses single API call with `number_of_images`
   - More cost-efficient than multiple separate calls
   - Single prompt/parameters applied to all images

4. **Backward Incompatibility**
   - Response structure changed (breaking change)
   - Old clients expecting single image will fail
   - Intentional for this version upgrade

### Testing

- 15 unit tests added/updated
- Tests cover:
  - Model validation (including num_images range)
  - Single and batch image generation
  - UUID filename format
  - Custom parameters
  - Error handling

### API Usage Examples

**Request (4 images, default):**
```json
POST /api/mv/generate_character_reference
{
  "character_description": "Silver metallic robot with blue eyes"
}
```

**Request (specific number):**
```json
POST /api/mv/generate_character_reference
{
  "character_description": "Silver metallic robot with blue eyes",
  "num_images": 2
}
```

**Response:**
```json
{
  "images": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "path": "/path/to/a1b2c3d4...png",
      "base64": "iVBORw0KGgoAAAANSUhEUgAA..."
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "path": "/path/to/b2c3d4e5...png",
      "base64": "iVBORw0KGgoAAAANSUhEUgBB..."
    }
  ],
  "metadata": {
    "character_description": "Silver metallic robot with blue eyes",
    "model_used": "google/imagen-4",
    "num_images_requested": 2,
    "num_images_generated": 2,
    "parameters_used": {
      "aspect_ratio": "1:1",
      "safety_filter_level": "block_medium_and_above",
      "person_generation": "allow_adult",
      "output_format": "png",
      "negative_prompt": null,
      "seed": null
    },
    "generation_timestamp": "2025-11-16T21:30:25Z"
  }
}
```

**Retrieve single image:**
```bash
GET /api/mv/get_character_reference/a1b2c3d4-e5f6-7890-abcd-ef1234567890
# Returns: Image file directly
```

### Future Improvements

1. **Frontend Selection UI**
   - 2x2 grid layout for 4 images
   - Single-select with visual feedback
   - Pass selected ID to video generation

2. **Video Generation Integration**
   - Option to accept image ID directly (not just base64)
   - Automatically fetch and convert to base64 server-side

3. **Image Metadata Endpoint**
   - Add `/api/mv/get_character_reference/{id}/info`
   - Return metadata without image data

4. **Partial Success Handling**
   - Handle cases where fewer images than requested are returned
   - Currently assumes all requested images are generated

### Files Modified

- `backend/mv/image_generator.py` - Core batch generation logic
- `backend/routers/mv.py` - Endpoint updates + new retrieval endpoint
- `backend/mv/debug.py` - New batch logging functions
- `backend/mv/test_image_generator.py` - 15 updated tests
- `frontend/src/app/create/page.tsx` - Multi-image handling, grid display, ID tracking
- `.devdocs/v2/tasklist.md` - Task tracking
- `.devdocs/v2/impl-notes.md` - This file


---

## Frontend Implementation

### Changes Made

1. **API Client Update**
   - Request now includes `num_images: 4` parameter
   - Response parsing handles `data.images` array instead of single `data.image_base64`
   - Each image's `id` and `base64` data extracted

2. **State Management**
   - Added `generatedImageIds` state to track UUIDs alongside blob URLs
   - Maintains parallel arrays: `generatedImages` (blob URLs) and `generatedImageIds` (UUIDs)

3. **Loading Skeleton**
   - Updated to show 4 skeleton placeholders in 2x2 grid
   - Message indicates "Generating 4 character images..."

4. **Image Selection**
   - Grid already supported multiple images (2x2 layout)
   - Single-select with blue border and checkmark indicator
   - Selected image ID available via `generatedImageIds[selectedImageIndex]`

5. **Form Submission**
   - Selected image ID appended to FormData as `characterReferenceImageId`
   - Ready for backend integration with video generation

### Frontend File Details

**Location**: `frontend/src/app/create/page.tsx`

**Key State Variables**:
```typescript
const [generatedImages, setGeneratedImages] = useState<string[]>([])        // Blob URLs for display
const [generatedImageIds, setGeneratedImageIds] = useState<string[]>([])    // UUIDs for backend
const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null)
```

**API Call** (lines 172-217):
```typescript
const response = await fetch(`${API_URL}/api/mv/generate_character_reference`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    character_description: characterDescription.trim(),
    num_images: 4,  // NEW: Request 4 images
  }),
})

const data = await response.json()
// Process data.images array (not single image)
for (const image of data.images) {
  // Convert base64 to blob URL
  blobUrls.push(blobUrl)
  imageIds.push(image.id)  // Store UUID
}
```

**Form Submission** (lines 124-127):
```typescript
if (useAICharacter && selectedImageIndex !== null && generatedImageIds[selectedImageIndex]) {
  formData.append('characterReferenceImageId', generatedImageIds[selectedImageIndex])
}
```

### UI Features

- 2x2 grid layout for 4 images
- Blue border + checkmark on selected image
- Ring effect for visual feedback
- "Option 1/2/3/4" labels on each image
- Confirmation message when image selected
- Skeleton loading placeholders during generation

### Not Implemented

1. **Actual Video Generation Integration**
   - Form submission is still mock (uses setTimeout)
   - Need to connect to real `/api/mv/generate_video` endpoint
   - Need to fetch image by ID and convert to base64 for video request

2. **Progressive Loading**
   - All images load at once (as returned by API)
   - Could add individual loading states if backend supports streaming

3. **Partial Failure Handling**
   - If backend returns fewer than 4 images, UI will display what's available
   - No specific error message for partial success
