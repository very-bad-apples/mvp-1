# Client Implementation Notes - Music Video Endpoints

This document provides guidance for frontend developers integrating with the Music Video (MV) API endpoints.

---

## Overview

The MV API provides three main endpoints for generating music videos:
1. **Scene Generation** (`/api/mv/create_scenes`) - Generate scene descriptions
2. **Character Reference** (`/api/mv/generate_character_reference`) - Generate character images
3. **Video Generation** (`/api/mv/generate_video`) - Generate individual video clips

---

## Complete Workflow Example

To generate a 4-scene music video:

### Step 1: Generate Scene Descriptions
```javascript
const scenesResponse = await fetch('http://localhost:8000/api/mv/create_scenes', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    idea: "Tourist exploring Austin, Texas",
    character_description: "Silver metallic humanoid robot with a red shield",
    number_of_scenes: 4
  })
});

const scenes = await scenesResponse.json();
// scenes.scenes contains array of { description, negative_description }
```

### Step 2: Generate Character Reference (Optional but Recommended)
```javascript
const charRefResponse = await fetch('http://localhost:8000/api/mv/generate_character_reference', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    character_description: "Silver metallic humanoid robot with a red shield"
  })
});

const charRef = await charRefResponse.json();
const referenceImageBase64 = charRef.image_base64;
```

### Step 3: Generate Videos for Each Scene (Concurrent)
```javascript
// Generate all scenes concurrently
const videoPromises = scenes.scenes.map(scene =>
  fetch('http://localhost:8000/api/mv/generate_video', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt: scene.description,
      negative_prompt: scene.negative_description,
      reference_image_base64: referenceImageBase64, // from step 2
      duration: 8,
      generate_audio: true
    })
  }).then(res => res.json())
);

const videos = await Promise.all(videoPromises);
// Each video has: video_id, video_url, metadata
```

### Step 4: Download/Display Videos
```javascript
// Download videos
const videoFiles = await Promise.all(
  videos.map(async (video) => {
    const response = await fetch(`http://localhost:8000${video.video_url}`);
    return response.blob();
  })
);

// Or get video info first
const videoInfos = await Promise.all(
  videos.map(video =>
    fetch(`http://localhost:8000/api/mv/get_video/${video.video_id}/info`)
      .then(res => res.json())
  )
);
```

---

## `/api/mv/generate_video` - Video Generation

### Request

```http
POST /api/mv/generate_video
Content-Type: application/json
```

```json
{
  "prompt": "A silver robot walks through a futuristic city at sunset",
  "negative_prompt": "blurry, low quality, distorted",
  "aspect_ratio": "16:9",
  "duration": 8,
  "generate_audio": true,
  "seed": 12345,
  "reference_image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "video_rules_template": "Keep it cinematic, no text overlays",
  "backend": "replicate"
}
```

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| prompt | Yes | string | - | Text description of the video content |
| negative_prompt | No | string | null | Elements to exclude from video |
| aspect_ratio | No | string | "16:9" | Video aspect ratio |
| duration | No | int | 8 | Duration in seconds |
| generate_audio | No | bool | true | Generate audio track |
| seed | No | int | null | Random seed for reproducibility |
| reference_image_base64 | No | string | null | Base64 encoded reference image |
| video_rules_template | No | string | default | Custom rules for generation |
| backend | No | string | "replicate" | Backend: "replicate" or "gemini" |

### Response (Success - 200)

```json
{
  "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "video_path": "/home/user/.../backend/mv/outputs/videos/a1b2c3d4...mp4",
  "video_url": "/api/mv/get_video/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "metadata": {
    "prompt": "A silver robot walks through a futuristic city at sunset",
    "backend_used": "replicate",
    "model_used": "google/veo-3.1",
    "parameters_used": {
      "aspect_ratio": "16:9",
      "duration": 8,
      "generate_audio": true,
      "seed": 12345
    },
    "generation_timestamp": "2025-11-16T10:30:25Z",
    "processing_time_seconds": 45.7
  }
}
```

### Response (Error - 500)

```json
{
  "error": "VideoGenerationError",
  "error_code": "CONTENT_POLICY_VIOLATION",
  "message": "An unexpected error occurred during video generation",
  "backend_used": "replicate",
  "timestamp": "2025-11-16T10:30:25Z",
  "details": "The prompt violated content safety policies"
}
```

---

## `/api/mv/get_video/{video_id}` - Video Retrieval

### Request

```http
GET /api/mv/get_video/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Response (Success - 200)

Returns the video file directly with:
- `Content-Type: video/mp4`
- Binary video data

### Response (Not Found - 404)

```json
{
  "error": "NotFound",
  "message": "Video with ID a1b2c3d4... not found",
  "details": "The video may have been deleted or the ID is incorrect"
}
```

---

## `/api/mv/get_video/{video_id}/info` - Video Metadata

### Request

```http
GET /api/mv/get_video/a1b2c3d4-e5f6-7890-abcd-ef1234567890/info
```

### Response (Exists)

```json
{
  "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "exists": true,
  "file_size_bytes": 15234567,
  "created_at": "2025-11-16T10:30:25Z"
}
```

### Response (Not Exists)

```json
{
  "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "exists": false,
  "file_size_bytes": null,
  "created_at": null
}
```

---

## Critical Implementation Considerations

### 1. Long Request Timeouts (20-400+ seconds)

Video generation takes **significantly longer** than typical API requests:

```javascript
// BAD - Will timeout
fetch('/api/mv/generate_video', {
  method: 'POST',
  body: JSON.stringify({ prompt: '...' })
});

// GOOD - Extended timeout
fetch('/api/mv/generate_video', {
  method: 'POST',
  body: JSON.stringify({ prompt: '...' }),
  signal: AbortSignal.timeout(420000) // 7 minutes
});

// BETTER - With user feedback
const controller = new AbortController();
const timeout = setTimeout(() => {
  showWarning('Generation taking longer than expected...');
}, 60000);

try {
  const response = await fetch('/api/mv/generate_video', {
    method: 'POST',
    body: JSON.stringify({ prompt: '...' }),
    signal: controller.signal
  });
  clearTimeout(timeout);
} catch (error) {
  if (error.name === 'AbortError') {
    showError('Request was cancelled');
  }
}
```

### 2. User Experience During Long Waits

Since there's no progress tracking, implement client-side feedback:

```javascript
function generateVideo(prompt) {
  const startTime = Date.now();

  // Show loading state
  showLoadingSpinner();
  updateStatus('Starting video generation...');

  // Update status periodically
  const statusInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    updateStatus(`Generating video... (${elapsed}s elapsed)`);

    if (elapsed > 60) {
      updateStatus(`Still generating... This can take up to 6 minutes.`);
    }
    if (elapsed > 180) {
      updateStatus(`Almost there... Video generation is computationally intensive.`);
    }
  }, 5000);

  return fetch('/api/mv/generate_video', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
    signal: AbortSignal.timeout(420000)
  })
    .then(res => res.json())
    .finally(() => {
      clearInterval(statusInterval);
      hideLoadingSpinner();
    });
}
```

### 3. Concurrent Scene Generation

Generate multiple scene videos in parallel for faster total completion:

```javascript
async function generateMusicVideo(scenes, referenceImage) {
  const MAX_CONCURRENT = 4; // Adjust based on server capacity

  const results = [];
  const queue = [...scenes];

  // Process in batches
  while (queue.length > 0) {
    const batch = queue.splice(0, MAX_CONCURRENT);
    const batchPromises = batch.map(scene =>
      generateVideo({
        prompt: scene.description,
        negative_prompt: scene.negative_description,
        reference_image_base64: referenceImage
      })
    );

    const batchResults = await Promise.allSettled(batchPromises);
    results.push(...batchResults);
  }

  // Handle successes and failures
  const successes = results.filter(r => r.status === 'fulfilled');
  const failures = results.filter(r => r.status === 'rejected');

  return { successes, failures };
}
```

### 4. Error Handling

Handle different error types appropriately:

```javascript
async function generateVideoWithRetry(request, maxRetries = 2) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch('/api/mv/generate_video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: AbortSignal.timeout(420000)
      });

      if (!response.ok) {
        const error = await response.json();

        switch (error.error_code) {
          case 'CONTENT_POLICY_VIOLATION':
            throw new Error('Prompt violates content policies. Please modify.');
          case 'RATE_LIMIT_EXCEEDED':
            if (attempt < maxRetries) {
              await sleep(30000); // Wait 30s before retry
              continue;
            }
            throw new Error('Rate limit exceeded. Please try again later.');
          case 'AUTHENTICATION_ERROR':
            throw new Error('Server configuration error. Contact support.');
          default:
            throw new Error(error.message || 'Video generation failed');
        }
      }

      return await response.json();

    } catch (error) {
      if (attempt === maxRetries) {
        throw error;
      }
      // Retry on network errors
      if (error.name === 'TypeError' || error.name === 'AbortError') {
        await sleep(5000);
        continue;
      }
      throw error;
    }
  }
}
```

### 5. Video Storage and Access

**Important**: Videos are stored server-side with UUIDs. There's currently **no authentication**, so:

- Videos are accessible to anyone with the UUID
- UUIDs are cryptographically random (hard to guess)
- Don't expose video IDs in URLs unnecessarily
- Consider implementing client-side video ID storage for user's own videos

```javascript
// Store generated video IDs locally
function saveVideoToLocalStorage(videoResponse) {
  const videos = JSON.parse(localStorage.getItem('mv_videos') || '[]');
  videos.push({
    id: videoResponse.video_id,
    url: videoResponse.video_url,
    createdAt: videoResponse.metadata.generation_timestamp,
    prompt: videoResponse.metadata.prompt
  });
  localStorage.setItem('mv_videos', JSON.stringify(videos));
}

// Retrieve user's videos
function getUserVideos() {
  return JSON.parse(localStorage.getItem('mv_videos') || '[]');
}
```

### 6. Base64 Reference Images

When using character reference images:

```javascript
// Convert file to base64
async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      // Remove data URL prefix
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// From character reference endpoint
async function generateWithCharacterReference(prompt, characterDescription) {
  // First generate character reference
  const charRef = await fetch('/api/mv/generate_character_reference', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_description: characterDescription })
  }).then(r => r.json());

  // Then generate video with reference
  return fetch('/api/mv/generate_video', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt: prompt,
      reference_image_base64: charRef.image_base64
    }),
    signal: AbortSignal.timeout(420000)
  }).then(r => r.json());
}
```

### 7. Video Merging (Client-Side)

The server generates individual clips. You'll need to merge them client-side or wait for a future server-side merge endpoint:

```javascript
// Using a library like ffmpeg.wasm or similar
async function mergeVideos(videoBlobs) {
  // This is a conceptual example
  // Actual implementation depends on your video processing library
  const { createFFmpeg } = await import('@ffmpeg/ffmpeg');
  const ffmpeg = createFFmpeg({ log: true });
  await ffmpeg.load();

  // Write input files
  for (let i = 0; i < videoBlobs.length; i++) {
    const arrayBuffer = await videoBlobs[i].arrayBuffer();
    ffmpeg.FS('writeFile', `input${i}.mp4`, new Uint8Array(arrayBuffer));
  }

  // Create concat file
  const concatList = videoBlobs.map((_, i) => `file input${i}.mp4`).join('\n');
  ffmpeg.FS('writeFile', 'concat.txt', concatList);

  // Merge
  await ffmpeg.run('-f', 'concat', '-i', 'concat.txt', '-c', 'copy', 'output.mp4');

  // Get result
  const data = ffmpeg.FS('readFile', 'output.mp4');
  return new Blob([data.buffer], { type: 'video/mp4' });
}
```

---

## Known Limitations (Important!)

1. **No progress tracking** - Client cannot see generation progress
2. **No authentication** - Videos accessible by anyone with UUID
3. **No rate limiting** - Be careful about cost (each generation uses API credits)
4. **No cleanup** - Videos stored indefinitely (may fill disk)
5. **Large request payloads** - Base64 images can be 1-4MB+
6. **Backend differences** - Gemini backend doesn't support all features (duration, audio, reference images)
7. **Client-side merging required** - Server doesn't merge multiple scene videos

---

## Best Practices

1. **Show loading states** - Users need feedback during long waits
2. **Implement cancellation** - Allow users to abort long-running requests
3. **Batch wisely** - Don't generate too many videos concurrently
4. **Cache reference images** - Reuse character references across scenes
5. **Store video IDs** - Save UUIDs for later retrieval
6. **Handle errors gracefully** - Different error types require different handling
7. **Set appropriate timeouts** - At least 420 seconds (7 minutes)
8. **Validate prompts** - Check prompts before sending to avoid content policy violations
9. **Monitor costs** - Track how many generations users are making
