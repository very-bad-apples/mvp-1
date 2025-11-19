# API Endpoints Documentation

This document describes the three core API endpoints implemented for the Bad Apple Video Generator.

## Overview

The backend provides three main endpoints for video generation:

1. **POST /api/generate** - Create a new video generation job
2. **GET /api/jobs/{job_id}** - Get job status and progress
3. **WebSocket /ws/jobs/{job_id}** - Real-time progress updates

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌───────────┐      ┌──────────┐
│   Client    │─────▶│  FastAPI     │─────▶│   Redis   │─────▶│  Worker  │
│             │◀─────│  Endpoints   │◀─────│   Queue   │◀─────│  Process │
└─────────────┘      └──────────────┘      └───────────┘      └──────────┘
      │                     │                     │
      │                     │                     │
      │              ┌──────▼──────┐              │
      │              │  PostgreSQL │              │
      │              │  Database   │              │
      │              └─────────────┘              │
      │                                           │
      └──────────── WebSocket ◀───────────────────┘
                     (Real-time)
```

## 1. Video Generation Endpoint

### POST /api/generate

Creates a new video generation job and returns a job ID.

**Request Format:** `multipart/form-data`

**Parameters:**
- `product_name` (string, required) - Name of the product (1-100 characters)
- `style` (string, required) - Video style (e.g., "modern", "minimalist", "energetic")
- `cta_text` (string, required) - Call-to-action text (1-50 characters)
- `product_image` (file, optional) - Product image (JPEG, PNG, WebP, max 10MB)

**Example Request (cURL):**
```bash
curl -X POST "http://localhost:8000/api/generate" \
  -F "product_name=EcoWater Bottle" \
  -F "style=modern" \
  -F "cta_text=Buy Now!" \
  -F "product_image=@product.jpg"
```

**Example Request (Python):**
```python
import requests

data = {
    "product_name": "EcoWater Bottle",
    "style": "modern",
    "cta_text": "Buy Now!"
}

files = {
    "product_image": open("product.jpg", "rb")
}

response = requests.post(
    "http://localhost:8000/api/generate",
    data=data,
    files=files
)

job_id = response.json()["job_id"]
```

**Success Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "estimated_completion_time": 300,
  "message": "Video generation job created successfully"
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "ValidationError",
  "message": "Product name is required",
  "details": "Product name cannot be empty"
}
```

### Implementation Details

**Task 8 Subtasks:**

1. **Multipart Form Data Handling (8.1)** ✓
   - Uses FastAPI's `Form()` and `File()` dependencies
   - Automatically parses multipart/form-data requests
   - Handles file uploads with streaming

2. **Input Validation Logic (8.2)** ✓
   - Validates required fields are not empty
   - Checks file types (JPEG, PNG, WebP only)
   - Enforces file size limit (10MB max)
   - Returns detailed error messages

3. **Generate Unique Job ID (8.3)** ✓
   - Uses Python's `uuid.uuid4()` for unique IDs
   - UUID format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
   - Guaranteed uniqueness across all jobs

4. **Enqueue Job to Redis (8.4)** ✓
   - Creates database record with job metadata
   - Enqueues job to Redis queue for processing
   - Stores job data in Redis with TTL (24 hours)
   - Transactional: rolls back database if Redis fails

## 2. Job Status Endpoint

### GET /api/jobs/{job_id}

Retrieves the current status and progress of a video generation job.

**Path Parameters:**
- `job_id` (UUID, required) - The unique job identifier

**Example Request:**
```bash
curl "http://localhost:8000/api/jobs/550e8400-e29b-41d4-a716-446655440000"
```

**Success Response (200 OK):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 45,
  "created_at": "2025-01-14T10:00:00",
  "updated_at": "2025-01-14T10:05:00",
  "product_name": "EcoWater Bottle",
  "style": "modern",
  "cta_text": "Buy Now!",
  "video_url": null,
  "error_message": null,
  "cost_usd": 0.0,
  "stages": [
    {
      "id": 1,
      "stage_name": "script_gen",
      "status": "completed",
      "progress": 100,
      "started_at": "2025-01-14T10:00:00",
      "completed_at": "2025-01-14T10:02:00",
      "error_message": null
    },
    {
      "id": 2,
      "stage_name": "voice_gen",
      "status": "processing",
      "progress": 60,
      "started_at": "2025-01-14T10:02:00",
      "completed_at": null,
      "error_message": null
    }
  ]
}
```

**Error Response (404 Not Found):**
```json
{
  "error": "JobNotFound",
  "message": "Job with ID '...' not found",
  "details": "The specified job ID does not exist in the system"
}
```

### Status Values

- `pending` - Job is queued and waiting to be processed
- `processing` - Job is currently being processed
- `completed` - Video generation completed successfully (includes `video_url`)
- `failed` - Job failed due to an error (includes `error_message`)

### Stage Names

1. `script_gen` - Script generation stage
2. `voice_gen` - Voice generation stage
3. `video_gen` - Video generation stage
4. `compositing` - Final video compositing stage

### Implementation Details

**Task 9 Subtasks:**

1. **Integrate Redis for Job Status Retrieval (9.1)** ✓
   - Fetches job from PostgreSQL database
   - Optionally checks Redis for additional status
   - Handles Redis connection failures gracefully

2. **Implement Error Handling for Invalid Job IDs (9.2)** ✓
   - Returns 404 for non-existent job IDs
   - Provides clear error messages
   - Logs invalid job ID attempts

3. **Format API Response with Job Details (9.3)** ✓
   - Calculates overall progress from stages
   - Includes all job metadata
   - Returns stage-by-stage progress
   - Includes video URL when completed

## 3. WebSocket Progress Updates

### WebSocket /ws/jobs/{job_id}

Establishes a persistent WebSocket connection for real-time job progress updates.

**Connection URL:**
```
ws://localhost:8000/ws/jobs/{job_id}
```

**Message Format:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "stage": "video_gen",
  "progress": 75,
  "status": "processing",
  "message": "Generating video scenes...",
  "timestamp": "2025-01-14T10:05:00"
}
```

**Example Client (JavaScript):**
```javascript
const jobId = "550e8400-e29b-41d4-a716-446655440000";
const ws = new WebSocket(`ws://localhost:8000/ws/jobs/${jobId}`);

ws.onopen = () => {
  console.log("Connected to job updates");
};

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(`Progress: ${update.progress}%`);
  console.log(`Stage: ${update.stage}`);
  console.log(`Message: ${update.message}`);

  // Update UI with progress
  updateProgressBar(update.progress);
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};

ws.onclose = () => {
  console.log("Connection closed");
};

// Send keepalive ping
setInterval(() => {
  ws.send(JSON.stringify({ type: "ping" }));
}, 30000);
```

**Example Client (Python):**
```python
import asyncio
import websockets
import json

async def monitor_job(job_id):
    uri = f"ws://localhost:8000/ws/jobs/{job_id}"

    async with websockets.connect(uri) as websocket:
        print("Connected to job updates")

        async for message in websocket:
            update = json.loads(message)
            print(f"Progress: {update['progress']}%")
            print(f"Stage: {update['stage']}")
            print(f"Message: {update.get('message', 'N/A')}")

# Run the client
asyncio.run(monitor_job("550e8400-e29b-41d4-a716-446655440000"))
```

### Connection Flow

1. Client connects to `/ws/jobs/{job_id}`
2. Server validates job exists (closes with 1008 if not found)
3. Server accepts connection and sends initial status
4. Server subscribes to Redis pub/sub for job updates
5. Server streams progress events to client in real-time
6. Connection remains open until client disconnects or job completes

### Implementation Details

**Task 10 Subtasks:**

1. **Establish WebSocket Connection (10.1)** ✓
   - Uses FastAPI's WebSocket support
   - Validates job exists before accepting connection
   - Sends initial connection confirmation
   - Implements connection manager for multiple clients

2. **Implement Redis Pub/Sub Subscription (10.2)** ✓
   - Subscribes to job status and progress channels
   - Filters messages by job ID
   - One subscription per active job
   - Automatically unsubscribes when all clients disconnect

3. **Stream Progress Events to Clients (10.3)** ✓
   - Broadcasts Redis messages to all connected clients
   - Sends JSON-formatted progress updates
   - Handles client disconnections gracefully
   - Supports multiple concurrent clients per job

4. **Manage Connection Cleanup and Reconnection (10.4)** ✓
   - Tracks active connections per job
   - Cleans up on client disconnect
   - Cancels Redis subscription when last client disconnects
   - Implements keepalive ping/pong mechanism

## Additional Endpoints

### GET /api/jobs

Lists all video generation jobs with pagination.

**Query Parameters:**
- `limit` (int, optional) - Maximum jobs to return (default: 100)
- `offset` (int, optional) - Number of jobs to skip (default: 0)
- `status` (string, optional) - Filter by status

**Example:**
```bash
curl "http://localhost:8000/api/jobs?limit=10&status=completed"
```

### GET /ws/health

WebSocket server health check.

**Response:**
```json
{
  "status": "healthy",
  "websocket_server": "running",
  "active_jobs": 5,
  "total_connections": 12
}
```

## Testing

Run the test suite:

```bash
# Make sure server is running
cd backend
python main.py

# In another terminal
python test_endpoints.py
```

Expected output:
```
============================================================
Starting API Endpoint Tests
============================================================

=== Testing Health Check ===
Status: 200
✓ Health check passed

=== Testing Video Generation Endpoint ===
Status: 202
✓ Video generation endpoint passed

=== Testing Job Status Endpoint ===
Status: 200
✓ Job status endpoint passed

============================================================
✓ ALL TESTS PASSED!
============================================================
```

## Database Schema

### Jobs Table

```sql
CREATE TABLE jobs (
    id VARCHAR PRIMARY KEY,
    status VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    product_name VARCHAR NOT NULL,
    style VARCHAR NOT NULL,
    cta_text VARCHAR NOT NULL,
    product_image_path VARCHAR,
    video_url VARCHAR,
    error_message TEXT,
    cost_usd FLOAT
);
```

### Stages Table

```sql
CREATE TABLE stages (
    id INTEGER PRIMARY KEY,
    job_id VARCHAR NOT NULL REFERENCES jobs(id),
    stage_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    progress INTEGER NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    stage_data TEXT,
    error_message TEXT
);
```

## Redis Data Structures

### Job Queue
- **Key:** `video_generation_queue`
- **Type:** List (FIFO)
- **Data:** JSON-serialized job data

### Job Metadata
- **Key:** `job:{job_id}`
- **Type:** Hash
- **Fields:** id, status, data
- **TTL:** 24 hours

### Pub/Sub Channels
- **Channel:** `job_status_updates` - Job status changes
- **Channel:** `job_progress_updates` - Progress updates
- **Message Format:** JSON with job_id, status, stage, progress

## Error Handling

All endpoints implement comprehensive error handling:

1. **Validation Errors (400)** - Invalid input data
2. **Not Found (404)** - Job ID doesn't exist
3. **Internal Errors (500)** - Database, Redis, or processing errors

Error responses follow a consistent format:
```json
{
  "error": "ErrorType",
  "message": "Human-readable message",
  "details": "Additional context"
}
```

## Security Considerations

1. **File Upload Validation**
   - File type whitelist (images only)
   - File size limits (10MB max)
   - Filename sanitization

2. **Input Validation**
   - All inputs validated and sanitized
   - Length limits enforced
   - SQL injection prevention (SQLAlchemy ORM)

3. **Rate Limiting** (TODO)
   - Implement rate limiting middleware
   - Prevent abuse of generation endpoint

## Performance

- **Connection Pooling:** Redis and PostgreSQL use connection pools
- **Async Operations:** All I/O operations are async
- **Efficient WebSocket:** One Redis subscription per job (not per client)
- **Resource Cleanup:** Automatic cleanup of temporary files and connections

---

## Music Video (MV) Pipeline Endpoints

The MV pipeline provides a separate set of endpoints for the music video generation system with configuration flavor support.

### Configuration Flavors

All MV endpoints support the `config_flavor` query parameter to select different preset configurations:

```bash
# Use default configuration
POST /api/mv/scenes

# Use example configuration
POST /api/mv/scenes?config_flavor=example
```

### Available Endpoints

#### GET /api/mv/config-flavors

List all available configuration flavors.

**Response:**
```json
{
  "flavors": ["default", "example"],
  "default_flavor": "default"
}
```

#### POST /api/mv/scenes

Generate scene prompts using the scene generator.

**Query Parameters:**
- `config_flavor` (string, optional) - Configuration flavor to use (default: "default")

**Request Body:**
```json
{
  "concept_prompt": "Robot exploring Austin, Texas",
  "num_scenes": 4
}
```

**Response:**
```json
{
  "scenes": [
    {
      "sequence": 1,
      "prompt": "Silver metallic robot walking through downtown Austin...",
      "duration": 8.0
    }
  ]
}
```

#### POST /api/mv/character-reference

Generate a character reference image.

**Query Parameters:**
- `config_flavor` (string, optional) - Configuration flavor to use

**Request Body:**
```json
{
  "character_description": "Silver metallic humanoid robot"
}
```

**Response:**
```json
{
  "image_url": "https://...",
  "s3_key": "mv/outputs/character_reference/abc123.png"
}
```

#### POST /api/mv/video

Generate a video clip for a scene.

**Query Parameters:**
- `config_flavor` (string, optional) - Configuration flavor to use

**Request Body:**
```json
{
  "prompt": "Robot walking through downtown",
  "duration": 8.0,
  "reference_image_s3_keys": ["mv/outputs/character_reference/abc123.png"]
}
```

**Response:**
```json
{
  "video_url": "https://...",
  "s3_key": "mv/projects/proj123/scenes/scene_001.mp4"
}
```

### Configuration Flavor Structure

Each flavor is a directory in `backend/mv/configs/{flavor_name}/` containing:

- **image_params.yaml** - Image generation model parameters
- **image_prompts.yaml** - Character/product image prompts
- **scene_prompts.yaml** - Video scene generation prompts
- **parameters.yaml** - Pipeline parameters

**Example flavor usage:**
1. Create new directory: `backend/mv/configs/my_custom_flavor/`
2. Add required YAML files (copy from `default/` as template)
3. Restart backend to discover new flavor
4. Use via `?config_flavor=my_custom_flavor` query parameter

---

## Future Enhancements

1. Add authentication/authorization
2. Implement rate limiting
3. Add job cancellation endpoint
4. Support batch job creation
5. Add job priority queuing
6. Implement job result caching
7. Add metrics and monitoring endpoints
