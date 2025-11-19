# AI Video Pipeline Architecture

## Document Metadata
- Created: 2025-11-17
- Project: AI Video Generator MVP-1
- Version: 1.0

## Table of Contents
1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Database Architecture](#database-architecture)
4. [Storage Architecture](#storage-architecture)
5. [API Architecture](#api-architecture)
6. [Worker Architecture](#worker-architecture)
7. [Data Flow](#data-flow)
8. [Deployment Architecture](#deployment-architecture)

---

## System Overview

The AI Video Pipeline is a full-stack application that generates AI-powered videos for two primary use cases:
1. **Music Videos (MV)**: User-uploaded music with AI-generated visual scenes
2. **Ad Creatives**: Product videos with generated scenes and voiceover

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Vercel)                        │
│                      Next.js 14 (localhost:3000)                │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Create     │  │   Project    │  │   Result     │         │
│  │   Page       │  │   Page       │  │   Page       │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          │   FormData       │  Poll Status     │  Get Video
          │   (images,       │  (project UUID)  │  (presigned URL)
          │    audio,        │                  │
          │    metadata)     │                  │
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend API (AWS/Local)                       │
│                   FastAPI (localhost:8000)                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      API Routers                          │  │
│  │                                                            │  │
│  │  /api/mv/projects          POST, GET, PATCH              │  │
│  │  /api/mv/projects/{id}/compose                           │  │
│  │  /api/mv/projects/{id}/final-video                       │  │
│  │  /api/mv/create_scenes                                   │  │
│  │  /api/mv/generate_character_reference                    │  │
│  │  /api/mv/generate_video                                  │  │
│  │  /api/mv/lipsync                                         │  │
│  └──────────────┬───────────────────────────────────────────┘  │
│                 │                                               │
└─────────────────┼───────────────────────────────────────────────┘
                  │
                  │
        ┌─────────┼─────────┬──────────────┬──────────────┐
        │         │         │              │              │
        ▼         ▼         ▼              ▼              ▼
   ┌────────┐ ┌────────┐ ┌────────┐  ┌────────┐    ┌────────┐
   │DynamoDB│ │   S3   │ │ Redis  │  │External│    │Worker  │
   │ (NoSQL)│ │Storage │ │ Queue  │  │  APIs  │    │Process │
   └────────┘ └────────┘ └────────┘  └────────┘    └────────┘
   Projects/   Videos/    Job Queue   Replicate    Scene Gen/
   Scenes      Images/                Gemini       Video Gen/
   Metadata    Audio                  ElevenLabs   Composition
```

### Core Components

1. **Frontend (Next.js 15)**
   - User interface for project creation and viewing
   - Direct backend API communication (no Next.js API routes)
   - Type-safe API client (`lib/api/client.ts`)
   - File uploads (images, audio)
   - Real-time project status polling with smart intervals
   - Video playback and project management UI
   - Configuration flavor selection

2. **Backend API (FastAPI)**
   - RESTful API endpoints
   - File upload handling
   - Database operations (DynamoDB)
   - S3 integration
   - Job queue management (Redis)
   - Configuration flavor system (`mv/configs/`)
   - Multi-config support for different video styles

3. **Database (DynamoDB)**
   - Project metadata storage
   - Scene tracking
   - Status management

4. **Storage (S3)**
   - Image storage
   - Audio storage
   - Video clip storage
   - Final output storage

5. **Queue (Redis)**
   - Async job processing
   - Scene generation jobs
   - Video generation jobs
   - Composition jobs

6. **Worker Process**
   - Background job processor
   - Scene prompt generation
   - Video clip stitching
   - Asset management

7. **External APIs**
   - Replicate (video generation, image generation)
   - Google Gemini (scene prompt generation)
   - ElevenLabs (voiceover - future)

---

## Technology Stack

### Frontend
```yaml
Framework: Next.js 15 (App Router)
Language: TypeScript
UI Components: shadcn/ui
Styling: Tailwind CSS
API Client: Direct FastAPI communication (no Next.js API routes)
State Management: React hooks (useState, useEffect, custom hooks)
Real-time Updates: Polling with smart intervals
Type Safety: TypeScript interfaces for API contracts
Deployment: Vercel
Dev Server: localhost:3000
```

**Key Architecture Decisions**:
- **Direct Backend Communication**: Removed Next.js API route layer for simpler, more maintainable architecture
- **Type-Safe API Client**: Centralized `lib/api/client.ts` with TypeScript interfaces
- **Smart Polling**: `useProjectPolling` hook with dynamic intervals based on project status
- **Component Organization**: Dedicated project detail page (`/project/[id]`) with modular components

### Backend
```yaml
Framework: FastAPI
Language: Python 3.12
Database ORM: PynamoDB (for DynamoDB)
Async Runtime: asyncio, aiofiles
Storage SDK: boto3 (AWS S3)
Queue: Redis
Configuration: YAML-based flavor system
Dev Server: localhost:8000
Deployment: AWS (EC2/ECS/Lambda)
```

**Configuration Flavor System**:
- **Location**: `backend/mv/configs/{flavor_name}/`
- **Manager**: `mv/config_manager.py` loads all flavors at startup
- **Flavors**: Multiple preset configurations (default, example, custom)
- **Files per Flavor**:
  - `image_params.yaml` - Image generation model parameters
  - `image_prompts.yaml` - Character/product image prompts
  - `scene_prompts.yaml` - Video scene generation prompts
  - `parameters.yaml` - Pipeline parameters
- **Usage**: Pass `?config_flavor=example` query parameter to endpoints
- **Discovery**: Auto-detects subdirectories in `configs/` at startup

### Database
```yaml
Primary DB: AWS DynamoDB
  - Table Design: Single-table with composite sort key
  - Partition Key: PROJECT#{uuid}
  - Sort Key: METADATA | SCENE#{sequence}
  - GSI: status-created-index

Legacy DB: SQLite (SQLAlchemy)
  - Used for existing Job/Stage models
  - Independent from MV pipeline
```

### Storage
```yaml
Cloud Storage: AWS S3
  - Bucket: Configured via Terraform
  - Structure: mv/projects/{projectId}/...
  - Access: Presigned URLs (on-demand generation)
  - Encryption: AES256 (server-side)
```

### Queue
```yaml
Queue System: Redis
  - Queues:
    - scene_generation_queue
    - video_composition_queue
  - Patterns: FIFO with blocking pop (brpop)
```

### External Services
```yaml
Video Generation: Replicate API
  - Models: Google Veo 3.1, Minimax, Seedance

Image Generation: Replicate API
  - Model: Google Imagen 4

Scene Generation: Google Gemini 2.5 Pro
  - Structured output for scene prompts

Lipsync: Replicate API
  - Model: Sync Labs Lipsync-2-Pro

Voiceover (Future): ElevenLabs
  - Voice synthesis for ad creatives
```

### Video Processing
```yaml
Composition: moviepy + FFmpeg
  - Scene stitching
  - Audio sync
  - Format: MP4, 1080p, H.264
```

### Infrastructure
```yaml
IaC: Terraform (Tofu fork)
  - S3 bucket configuration
  - IAM policies
  - Lifecycle rules

Local Development:
  - DynamoDB Local (Docker)
  - Redis (Docker)
  - Backend (Python venv)
  - Frontend (pnpm)
```

---

## Database Architecture

### DynamoDB Single-Table Design

**Table Name**: `MVProjects`

**Rationale**: Single-table design optimizes for access patterns and cost while avoiding the 400KB item size limit by storing scenes as separate items.

#### Primary Key Structure

```
Partition Key (PK): PROJECT#{uuid}
Sort Key (SK):      METADATA | SCENE#{sequence}
```

#### Global Secondary Index

```yaml
Index Name: status-created-index
Purpose: Query projects by status
Partition Key (GSI1PK): status
Sort Key (GSI1SK): createdAt (ISO timestamp)
Projection: All attributes
```

#### Item Types

##### 1. Project Metadata Item

```python
{
    "PK": "PROJECT#550e8400-e29b-41d4-a716-446655440000",
    "SK": "METADATA",
    "entityType": "project",
    "projectId": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",  # pending, processing, completed, failed

    # User Input
    "conceptPrompt": "Robot exploring Austin, Texas",
    "characterDescription": "Silver metallic humanoid robot",
    "productDescription": "EcoWater sustainable bottle",  # Optional

    # S3 References (object keys, not URLs - validated before saving)
    # All *S3Key fields store keys like "mv/projects/{id}/file.ext"
    # Presigned URLs are generated on-demand when serving API responses
    "characterImageS3Key": "mv/projects/550e8400/character.png",
    "productImageS3Key": "mv/projects/550e8400/product.jpg",
    "audioBackingTrackS3Key": "mv/projects/550e8400/audio.mp3",
    "finalOutputS3Key": "mv/projects/550e8400/final.mp4",

    # Progress Tracking
    "sceneCount": 4,
    "completedScenes": 2,
    "failedScenes": 0,

    # Timestamps
    "createdAt": "2025-11-17T10:00:00Z",
    "updatedAt": "2025-11-17T10:15:00Z",

    # GSI Attributes
    "GSI1PK": "processing",
    "GSI1SK": "2025-11-17T10:00:00Z"
}
```

##### 2. Scene Item

```python
{
    "PK": "PROJECT#550e8400-e29b-41d4-a716-446655440000",
    "SK": "SCENE#001",  # Zero-padded sequence
    "entityType": "scene",
    "projectId": "550e8400-e29b-41d4-a716-446655440000",
    "sequence": 1,
    "status": "completed",  # pending, processing, completed, failed

    # Scene Definition
    "prompt": "Silver robot walks through downtown Austin at sunset",
    "negativePrompt": "No other people, no music",
    "duration": 8.0,  # seconds

    # Assets (S3 object keys, validated - not URLs)
    # Presigned URLs generated on-demand in API responses
    "referenceImageS3Keys": [
        "mv/projects/550e8400/character.png"
    ],
    "audioClipS3Key": "mv/projects/550e8400/scenes/001/audio.mp3",
    "videoClipS3Key": "mv/projects/550e8400/scenes/001/video.mp4",
    "lipSyncedVideoClipS3Key": "mv/projects/550e8400/scenes/001/lipsynced.mp4",

    # Metadata
    "needsLipSync": true,
    "videoGenerationJobId": "replicate_abc123",
    "lipsyncJobId": "replicate_def456",
    "retryCount": 0,
    "errorMessage": null,

    # Timestamps
    "createdAt": "2025-11-17T10:01:00Z",
    "updatedAt": "2025-11-17T10:15:00Z"
}
```

#### Access Patterns

```python
# 1. Get project metadata
project = MVProjectItem.get("PROJECT#{uuid}", "METADATA")

# 2. Get all scenes for project (ordered by sequence)
scenes = MVProjectItem.query(
    "PROJECT#{uuid}",
    MVProjectItem.SK.begins_with("SCENE#")
)

# 3. Get specific scene
scene = MVProjectItem.get("PROJECT#{uuid}", "SCENE#001")

# 4. Query projects by status
projects = MVProjectItem.status_index.query(
    "processing",  # status
    MVProjectItem.GSI1SK > "2025-11-17T00:00:00Z"
)

# 5. Update project status
project.status = "completed"
project.GSI1PK = "completed"
project.updatedAt = datetime.now(timezone.utc)
project.save()
```

### Legacy Database (SQLAlchemy + SQLite)

The existing SQLAlchemy database remains **independent** for backward compatibility:

```python
# Tables: jobs, stages
# Used by: /api/generate, /api/jobs endpoints
# Location: backend/video_generator.db

# NOT used by MV endpoints
# No migration needed
```

---

## Storage Architecture

### S3 Bucket Structure

```
s3://{bucket-name}/
└── mv/
    ├── outputs/                        # Shared outputs from existing endpoints
    │   ├── character_reference/        # Character images from /api/mv/generate_character_reference
    │   │   └── {image_id}.png
    │   ├── videos/                     # Videos from /api/mv/generate_video
    │   │   └── {video_id}.mp4
    │   └── mock/                       # Mock videos for testing
    │       └── sample.mp4
    │
    └── projects/                       # Project-specific storage
        └── {projectId}/
            ├── character.png           # Character reference image
            ├── product.jpg             # Product image (ad-creative mode)
            ├── audio.mp3               # Full backing track
            ├── final.mp4               # Final composed video
            └── scenes/
                ├── 001/
                │   ├── audio.mp3       # Scene audio segment
                │   ├── video.mp4       # Generated video clip
                │   └── lipsynced.mp4   # Lipsynced version (if needed)
                ├── 002/
                │   └── ...
                └── ...
```

### S3 Access Patterns

#### Storage Strategy
- **Database**: Store S3 object keys only (not full URLs)
- **Retrieval**: Generate presigned URLs on-demand
- **Expiration**: Presigned URLs expire after configured time (default 1 hour)

#### Key Generation

```python
# Project assets
character_key = f"mv/projects/{project_id}/character.png"
product_key = f"mv/projects/{project_id}/product.jpg"
audio_key = f"mv/projects/{project_id}/audio.mp3"
final_key = f"mv/projects/{project_id}/final.mp4"

# Scene assets
scene_audio_key = f"mv/projects/{project_id}/scenes/{sequence:03d}/audio.mp3"
scene_video_key = f"mv/projects/{project_id}/scenes/{sequence:03d}/video.mp4"
scene_lipsync_key = f"mv/projects/{project_id}/scenes/{sequence:03d}/lipsynced.mp4"
```

#### Presigned URL Generation

Presigned URLs are generated **on-demand** when serving API responses, never stored in the database:

```python
from services.s3_storage import get_s3_storage_service

s3_service = get_s3_storage_service()

# Read S3 key from database (e.g., "mv/projects/{project_id}/final.mp4")
s3_key = project_item.finalOutputS3Key

# Generate presigned URL (expires in 1 hour)
video_url = s3_service.generate_presigned_url(
    s3_key=s3_key,
    expiry=3600
)
# Returns: "https://bucket.s3.amazonaws.com/mv/projects/{id}/final.mp4?X-Amz-Signature=..."
```

#### S3 Key Validation

All S3 keys are validated before being saved to ensure they are keys, not URLs:

```python
from services.s3_storage import validate_s3_key

# ✅ Valid - S3 key (accepted)
key = validate_s3_key("mv/projects/123/file.png")

# ❌ Invalid - HTTP URL (rejected with ValueError)
validate_s3_key("https://bucket.s3.amazonaws.com/file.png")

# ❌ Invalid - Presigned URL (rejected with ValueError)
validate_s3_key("mv/projects/123/file.png?X-Amz-Signature=abc123")
```

**Validation occurs automatically in:**
- `create_project_metadata()` - All project S3 keys
- `create_scene_item()` - Reference image S3 keys
- Direct assignments in routers/workers
- Update endpoints when users provide S3 keys

**Why validate?**
- Prevents accidentally saving presigned URLs (which expire)
- Ensures data integrity (keys are permanent, URLs are temporary)
- Makes debugging easier (clear error messages)

### Terraform S3 Configuration

```hcl
# Location: terraform/main.tf

resource "aws_s3_bucket" "video_storage" {
  bucket = var.bucket_name

  # Features:
  # - Versioning enabled
  # - Server-side encryption (AES256)
  # - Public access blocked
  # - CORS configured for web access
  # - Lifecycle policies for cleanup
}

resource "aws_iam_user" "video_generator_app" {
  name = var.iam_user_name

  # Permissions:
  # - s3:PutObject, s3:GetObject, s3:DeleteObject
  # - s3:ListBucket
  # - s3:GeneratePresignedUrl (via access keys)
}
```

---

## API Architecture

### Endpoint Structure

All MV endpoints are prefixed with `/api/mv/`:

```
/api/mv/
├── projects                                 # CRUD operations
│   ├── POST                                # Create project
│   ├── GET /{projectId}                    # Get project + scenes
│   ├── PATCH /{projectId}                  # Update project
│   ├── POST /{projectId}/compose           # Queue composition
│   └── GET /{projectId}/final-video        # Get final video URL
│
├── create_scenes                           # Scene generation (existing)
│   └── POST
│
├── generate_character_reference            # Character image gen (existing)
│   ├── POST
│   └── GET /{image_id}
│
├── generate_video                          # Video clip generation (existing)
│   ├── POST
│   └── GET /{video_id}
│
└── lipsync                                 # Lipsync processing (existing)
    └── POST
```

### Request/Response Flow

#### 1. Create Project

```http
POST /api/mv/projects
Content-Type: multipart/form-data

Form Fields:
  mode: "music-video" | "ad-creative"
  prompt: "User's video concept"
  characterDescription: "Character details"
  characterReferenceImageId: "uuid" (optional)
  productDescription: "Product details" (optional)

Files:
  images[]: File[] (ad-creative mode)
  audio: File (music-video mode)

Response (201 Created):
{
  "projectId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Project created successfully"
}
```

**Backend Processing**:
1. Validate form data and files
2. Upload files to S3
3. Create project metadata in DynamoDB (status=pending)
4. Return project ID
5. (Optional) Queue scene generation job

#### 2. Get Project

```http
GET /api/mv/projects/{projectId}

Response (200 OK):
{
  "projectId": "550e8400-...",
  "status": "processing",
  "conceptPrompt": "Robot exploring Austin",
  "characterDescription": "Silver robot",
  "characterImageUrl": "https://s3.amazonaws.com/...",  // Presigned URL
  "productImageUrl": null,
  "audioBackingTrackUrl": "https://s3.amazonaws.com/...",  // Presigned URL
  "finalOutputUrl": null,
  "sceneCount": 4,
  "completedScenes": 2,
  "failedScenes": 0,
  "scenes": [
    {
      "sequence": 1,
      "status": "completed",
      "prompt": "Robot walking through downtown Austin",
      "negativePrompt": "No other people",
      "duration": 8.0,
      "referenceImageUrls": ["https://s3.amazonaws.com/..."],
      "audioClipUrl": "https://s3.amazonaws.com/...",
      "videoClipUrl": "https://s3.amazonaws.com/...",
      "needsLipSync": true,
      "lipSyncedVideoClipUrl": "https://s3.amazonaws.com/...",
      "retryCount": 0,
      "errorMessage": null,
      "createdAt": "2025-11-17T10:01:00Z",
      "updatedAt": "2025-11-17T10:15:00Z"
    },
    // ... more scenes
  ],
  "createdAt": "2025-11-17T10:00:00Z",
  "updatedAt": "2025-11-17T10:15:00Z"
}
```

**Backend Processing**:
1. Query project metadata from DynamoDB
2. Query all scenes for project
3. Generate presigned URLs for all S3 assets
4. Return combined response

#### 3. Compose Final Video

```http
POST /api/mv/projects/{projectId}/compose

Response (200 OK):
{
  "jobId": "compose_550e8400-...",
  "projectId": "550e8400-...",
  "status": "queued",
  "message": "Video composition job queued"
}
```

**Backend Processing**:
1. Validate all scenes are completed
2. Create composition job
3. Queue job to Redis
4. Update project status to "composing"
5. Return job ID

**Worker Processing** (async):
1. Download all scene videos from S3
2. Download audio backing track
3. Stitch videos with moviepy
4. Add audio track
5. Upload final video to S3
6. Update project with final output S3 key
7. Update project status to "completed"

#### 4. Get Final Video

```http
GET /api/mv/projects/{projectId}/final-video

Response (200 OK):
{
  "projectId": "550e8400-...",
  "videoUrl": "https://s3.amazonaws.com/...",  // Presigned URL
  "expiresInSeconds": 3600
}

Response (404 Not Found):
{
  "error": "NotFound",
  "message": "Final video not yet available",
  "details": "Project status: processing"
}
```

### API Error Handling

All endpoints use consistent error response format:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message",
  "details": "Additional context"
}
```

**Common Error Codes**:
- `400 Bad Request`: Validation errors
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Database/S3/API failures

---

## Worker Architecture

### Worker Process Overview

```
Worker Process (worker_mv.py)
│
├── Main Loop
│   ├── Poll scene_generation_queue (Redis)
│   ├── Poll video_composition_queue (Redis)
│   └── Process jobs asynchronously
│
├── Scene Generation Worker
│   ├── Retrieve project metadata from DynamoDB
│   ├── Call scene generation API (Gemini)
│   ├── Create scene items in DynamoDB
│   └── Update project scene count
│
└── Composition Worker
    ├── Retrieve project + scenes from DynamoDB
    ├── Download scene videos from S3
    ├── Download audio from S3
    ├── Stitch with moviepy
    ├── Upload final video to S3
    └── Update project status
```

### Job Queue Structure

#### Scene Generation Queue

```python
# Queue: scene_generation_queue
# Format: JSON

{
  "job_id": "scene_550e8400-...",
  "project_id": "550e8400-...",
  "type": "scene_generation",
  "created_at": "2025-11-17T10:00:00Z"
}
```

**Triggered By**: Project creation or manual trigger

**Processing**:
1. Get project metadata
2. Generate 4 scene prompts using Gemini
3. Create scene items in DynamoDB
4. Update project scene count

#### Composition Queue

```python
# Queue: video_composition_queue
# Format: JSON

{
  "job_id": "compose_550e8400-...",
  "project_id": "550e8400-...",
  "type": "compose",
  "created_at": "2025-11-17T10:30:00Z"
}
```

**Triggered By**: POST /api/mv/projects/{projectId}/compose

**Processing**:
1. Validate all scenes completed
2. Download scene videos (use lipsynced if available)
3. Download audio backing track
4. Stitch scenes with moviepy + FFmpeg
5. Upload final.mp4 to S3
6. Update project status to "completed"

### Worker Error Handling

```python
# Scene generation failure
try:
    # ... generate scenes
except Exception as e:
    project.status = "failed"
    project.save()
    logger.error("scene_generation_failed", error=str(e))

# Composition failure
try:
    # ... compose video
except Exception as e:
    project.status = "failed"
    project.save()
    logger.error("composition_failed", error=str(e))

# Cleanup temp files always
finally:
    cleanup_temp_files(temp_dir)
```

### Video Composition with moviepy

```python
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip

# Load scene clips
clips = [VideoFileClip(path) for path in scene_paths]

# Concatenate
final_clip = concatenate_videoclips(clips, method="compose")

# Add audio (loop if needed)
audio = AudioFileClip(audio_path)
if audio.duration < final_clip.duration:
    # Loop audio to match video duration
    loops = int(final_clip.duration / audio.duration) + 1
    audio = concatenate_videoclips([audio] * loops)
    audio = audio.subclip(0, final_clip.duration)

final_clip = final_clip.set_audio(audio)

# Write output
final_clip.write_videofile(
    output_path,
    codec='libx264',
    audio_codec='aac',
    fps=24,
    preset='medium'
)
```

---

## Data Flow

### End-to-End User Journey: Music Video

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER CREATES PROJECT                                          │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Frontend: User fills form
    │ - Mode: "music-video"
    │ - Prompt: "Robot exploring Austin"
    │ - Character: "Silver robot"
    │ - Uploads: audio.mp3
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ POST /api/mv/projects                                            │
│                                                                  │
│ Backend:                                                         │
│ 1. Upload audio.mp3 → S3: mv/projects/{uuid}/audio.mp3         │
│ 2. Create project in DynamoDB (status=pending)                  │
│ 3. Return projectId to frontend                                 │
└─────────────────────────────────────────────────────────────────┘
    │
    │ projectId: 550e8400-...
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. FRONTEND ROUTES TO PROJECT PAGE                              │
│    /project/{projectId}                                          │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Project page loads, pings backend for scene generation
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ POST /api/mv/projects/{projectId}/scenes (hypothetical)         │
│                                                                  │
│ Backend:                                                         │
│ 1. Queue scene generation job → Redis                           │
│ 2. Worker picks up job                                          │
│ 3. Worker calls Gemini API with project metadata                │
│ 4. Gemini generates 4 scene prompts                             │
│ 5. Worker creates 4 scene items in DynamoDB                     │
│ 6. Worker updates project.sceneCount = 4                        │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Scenes created in DynamoDB (status=pending)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. FRONTEND POLLS PROJECT STATUS                                │
│    GET /api/mv/projects/{projectId}                              │
│                                                                  │
│ Response:                                                        │
│ {                                                                │
│   "status": "pending",                                           │
│   "sceneCount": 4,                                               │
│   "completedScenes": 0,                                          │
│   "scenes": [                                                    │
│     { "sequence": 1, "status": "pending", ... },                │
│     ...                                                          │
│   ]                                                              │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘
    │
    │ User sees scenes, triggers video generation
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. GENERATE VIDEOS FOR EACH SCENE                               │
│    (Manual trigger or auto-queue)                               │
│                                                                  │
│ For each scene:                                                  │
│   POST /api/mv/generate_video                                    │
│   {                                                              │
│     "prompt": scene.prompt,                                      │
│     "reference_image_base64": character_image,                   │
│     "duration": 8                                                │
│   }                                                              │
│                                                                  │
│ Backend:                                                         │
│ 1. Call Replicate API (Veo 3.1)                                 │
│ 2. Wait for video generation (20-400s)                          │
│ 3. Upload video → S3: mv/projects/{uuid}/scenes/001/video.mp4  │
│ 4. Update scene.videoClipS3Key                                  │
│ 5. Update scene.status = "completed"                            │
│ 6. Increment project.completedScenes                            │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Repeat for all 4 scenes (can be parallelized)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. ALL SCENES COMPLETED                                         │
│                                                                  │
│ Project state:                                                   │
│ {                                                                │
│   "status": "pending",                                           │
│   "sceneCount": 4,                                               │
│   "completedScenes": 4,                                          │
│   "failedScenes": 0                                              │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘
    │
    │ User clicks "Compose Final Video"
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ POST /api/mv/projects/{projectId}/compose                        │
│                                                                  │
│ Backend:                                                         │
│ 1. Validate completedScenes == sceneCount                       │
│ 2. Queue composition job → Redis                                │
│ 3. Update project.status = "composing"                          │
│ 4. Return jobId                                                  │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Worker picks up composition job
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. WORKER COMPOSES FINAL VIDEO                                  │
│                                                                  │
│ Worker:                                                          │
│ 1. Download scene videos from S3                                │
│    - scenes/001/video.mp4                                        │
│    - scenes/002/video.mp4                                        │
│    - scenes/003/video.mp4                                        │
│    - scenes/004/video.mp4                                        │
│                                                                  │
│ 2. Download audio backing track from S3                         │
│    - audio.mp3                                                   │
│                                                                  │
│ 3. Stitch with moviepy:                                          │
│    - Concatenate scenes in order                                │
│    - Add audio track                                             │
│    - Export as MP4                                               │
│                                                                  │
│ 4. Upload final video → S3: mv/projects/{uuid}/final.mp4       │
│                                                                  │
│ 5. Update project:                                               │
│    - project.finalOutputS3Key = "mv/projects/{uuid}/final.mp4" │
│    - project.status = "completed"                                │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Composition complete
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. FRONTEND DETECTS COMPLETION                                  │
│    GET /api/mv/projects/{projectId}                              │
│                                                                  │
│ Response:                                                        │
│ {                                                                │
│   "status": "completed",                                         │
│   "finalOutputUrl": "https://s3.amazonaws.com/..." (presigned)  │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘
    │
    │ User downloads or views final video
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. USER DOWNLOADS FINAL VIDEO                                   │
│    GET /api/mv/projects/{projectId}/final-video                 │
│                                                                  │
│ Backend:                                                         │
│ 1. Retrieve project from DynamoDB                               │
│ 2. Generate presigned URL for final.mp4 (expires in 1 hour)    │
│ 3. Return URL to frontend                                        │
│                                                                  │
│ Frontend:                                                        │
│ 1. Receives presigned URL                                        │
│ 2. Displays video player or download link                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Local Development

```yaml
Services:
  - Frontend: localhost:3000 (pnpm dev)
  - Backend: localhost:8000 (uvicorn main:app --reload)
  - DynamoDB Local: localhost:8001 (Docker)
  - Redis: localhost:6379 (Docker)

Environment:
  USE_LOCAL_DYNAMODB: true
  DYNAMODB_ENDPOINT: http://localhost:8001
  STORAGE_BACKEND: s3
  AWS_ACCESS_KEY_ID: fakeAccessKey (for local DynamoDB)
  AWS_SECRET_ACCESS_KEY: fakeSecretKey (for local DynamoDB)

Startup:
  1. docker-compose up -d dynamodb-local redis
  2. cd backend && python init_dynamodb.py
  3. cd backend && uvicorn main:app --reload
  4. cd frontend && pnpm dev
  5. cd backend && python worker_mv.py (optional)
```

### Production Deployment

#### Frontend (Vercel)

```yaml
Platform: Vercel
Build Command: pnpm build
Output Directory: .next
Environment Variables:
  NEXT_PUBLIC_API_URL: https://api.yourdomain.com
```

#### Backend (AWS)

```yaml
Options:
  - EC2: Long-running server
  - ECS Fargate: Containerized, auto-scaling
  - Lambda + API Gateway: Serverless (for low traffic)

Recommended: ECS Fargate

Environment Variables:
  USE_LOCAL_DYNAMODB: false
  DYNAMODB_TABLE_NAME: MVProjects
  DYNAMODB_REGION: us-east-1
  STORAGE_BUCKET: your-s3-bucket-name
  AWS_REGION: us-east-1
  PRESIGNED_URL_EXPIRY: 3600
  REDIS_URL: redis://your-redis-host:6379
```

#### Worker Process

```yaml
Deployment:
  - Same EC2/ECS instance as backend
  - Separate ECS service (recommended)
  - Background process in same container

Command: python worker_mv.py
Restart Policy: Always
```

#### DynamoDB

```yaml
Service: AWS DynamoDB
Table: MVProjects
Capacity Mode: On-Demand (recommended for variable traffic)
Billing Mode: Pay per request
Point-in-Time Recovery: Enabled
Encryption: AWS managed keys

Manual Creation Steps:
  1. AWS Console → DynamoDB → Create table
  2. Table name: MVProjects
  3. Partition key: PK (String)
  4. Sort key: SK (String)
  5. Create GSI: status-created-index
     - Partition key: GSI1PK (String)
     - Sort key: GSI1SK (String)
     - Projection: All attributes
```

#### S3

```yaml
Service: AWS S3
Bucket: Created via Terraform
Region: us-east-1

Features:
  - Versioning: Enabled
  - Encryption: AES256
  - Public Access: Blocked
  - CORS: Configured for web access
  - Lifecycle: Old versions deleted after 30 days

Access:
  - IAM User: video-generator-app
  - Permissions: S3 read/write for specific bucket
  - Access via: Access key ID + Secret access key
```

#### Redis

```yaml
Options:
  - AWS ElastiCache (Redis)
  - Self-hosted on EC2
  - Redis Labs Cloud

Recommended: AWS ElastiCache

Configuration:
  - Node type: cache.t3.micro (start small)
  - Engine version: 7.x
  - Cluster mode: Disabled
  - Encryption: In-transit and at-rest
```

### Infrastructure as Code (Terraform)

```yaml
Managed Resources:
  - S3 bucket (terraform/main.tf)
  - IAM user and policies
  - Lifecycle rules
  - CORS configuration

Not Managed (Manual):
  - DynamoDB table (create manually in AWS Console)
  - ElastiCache Redis
  - ECS cluster and services
```

### Monitoring and Logging

```yaml
Application Logs:
  - Backend: structlog → CloudWatch Logs
  - Worker: structlog → CloudWatch Logs

Metrics:
  - DynamoDB: Read/Write capacity units
  - S3: Bucket size, request count
  - Redis: Memory usage, queue depth

Alerts:
  - DynamoDB throttling
  - S3 bucket size threshold
  - Worker queue backlog
  - API error rate spike
```

---

## Security Considerations

### Authentication and Authorization
```yaml
Current State: No authentication (MVP)

Future:
  - JWT-based authentication
  - User accounts with project ownership
  - API key authentication for programmatic access
```

### File Upload Security
```yaml
Validation:
  - File type whitelist (images: jpg, png, webp; audio: mp3, wav)
  - File size limits (10MB for images, 50MB for audio)
  - Filename sanitization (prevent directory traversal)
  - Content verification (PIL for images, metadata check for audio)

Storage:
  - Files uploaded to S3 with private ACL
  - Presigned URLs for controlled access
  - URL expiration (default 1 hour)
```

### Database Security
```yaml
DynamoDB:
  - Encryption at rest (AWS managed keys)
  - IAM policies for least privilege access
  - No public access

Access Control:
  - Backend uses IAM role (in production)
  - Access keys rotated regularly
  - No hardcoded credentials
```

### API Security
```yaml
Current:
  - CORS configured for specific origins
  - Input validation on all endpoints
  - SQL injection prevention (DynamoDB + PynamoDB ORM)

Future:
  - Rate limiting per IP/user
  - API key authentication
  - Request signing for sensitive operations
```

---

## Performance Optimization

### Caching Strategy
```yaml
Presigned URLs:
  - Cache URLs with TTL matching expiration
  - Redis key: presigned:{s3_key}
  - TTL: expiration - 60 seconds (safety margin)

Project Metadata:
  - Cache frequently accessed projects in Redis
  - Key: project:{projectId}
  - TTL: 5 minutes
  - Invalidate on update
```

### Async Processing
```yaml
Video Generation:
  - All video generation is async via workers
  - Frontend polls for status updates
  - WebSocket support (future) for real-time updates

Scene Generation:
  - Queued to Redis
  - Processed by worker
  - Multiple workers can process in parallel
```

### Database Optimization
```yaml
DynamoDB:
  - Single-table design reduces query count
  - GSI for status queries (avoid scan)
  - Batch get for multiple scenes
  - Consistent reads only when necessary

Query Patterns:
  - Efficient: query by PK + SK prefix
  - Inefficient (avoid): table scan
```

### S3 Optimization
```yaml
Upload:
  - Stream large files (no memory buffering)
  - Multipart upload for files > 100MB
  - Parallel uploads for multiple files

Download:
  - Presigned URLs served directly from S3
  - No backend proxy (reduces latency)
  - CDN (CloudFront) for frequently accessed files (future)
```

---

## Cost Estimation (Monthly)

```yaml
Assumptions:
  - 100 projects/month
  - 4 scenes per project = 400 scenes
  - Average scene: 8 seconds
  - Final video: 32 seconds

DynamoDB:
  - Reads: ~10,000/month (on-demand)
  - Writes: ~500/month
  - Storage: ~1 GB
  - Cost: ~$2/month

S3:
  - Storage: ~50 GB (100 projects × 500 MB)
  - Requests: ~5,000 PUT, ~20,000 GET
  - Data transfer: ~50 GB out
  - Cost: ~$3/month (storage) + $5/month (transfer) = $8/month

Redis (ElastiCache):
  - Instance: cache.t3.micro
  - Cost: ~$15/month

EC2/ECS (Backend + Worker):
  - Instance: t3.small (2 vCPU, 2 GB RAM)
  - Cost: ~$15/month

External APIs:
  - Replicate (video gen): $0.50/scene × 400 = $200/month
  - Gemini (scene gen): $0.10/project × 100 = $10/month
  - Total API: ~$210/month

Total: ~$250/month for 100 projects
Cost per project: ~$2.50
```

---

## Future Enhancements

### Phase 2: Advanced Features
```yaml
- WebSocket for real-time progress updates
- Retry logic for failed scenes
- Scene-level regeneration (re-do single scene)
- Template marketplace (different video styles)
- Custom branding (logo, colors, fonts)
```

### Phase 3: Optimization
```yaml
- CloudFront CDN for video delivery
- DynamoDB auto-scaling
- Redis caching for presigned URLs
- Batch video generation (process multiple scenes in parallel)
- Video preview thumbnails
```

### Phase 4: Enterprise
```yaml
- User authentication and accounts
- Payment integration (Stripe)
- Usage quotas and billing
- Team collaboration
- API for programmatic access
- Webhook notifications
```

---

## Appendix: Key File Locations

```yaml
Backend:
  Main App: backend/main.py
  Config: backend/config.py
  DynamoDB Models: backend/mv_models.py
  DynamoDB Config: backend/dynamodb_config.py
  S3 Service: backend/services/s3_storage.py
  Schemas: backend/mv_schemas.py
  Routers: backend/routers/mv_projects.py
  Workers:
    - backend/workers/scene_worker.py
    - backend/workers/compose_worker.py
    - backend/worker_mv.py
  Init Script: backend/init_dynamodb.py
  Documentation: backend/_docs/

Frontend:
  Main Page: frontend/src/app/page.tsx
  Create Page: frontend/src/app/create/page.tsx
  Project Page: frontend/src/app/project/[id]/page.tsx (future)
  Result Page: frontend/src/app/result/[id]/page.tsx

Infrastructure:
  Terraform: terraform/main.tf
  Docker: docker-compose.yml

Documentation:
  Architecture: _docs/architecture.md (this file)
  API Docs: backend/_docs/API_ENDPOINTS.md
  Worker Docs: backend/_docs/WORKER.md
  DynamoDB Schema: _docs/database/DYNAMODB_SCHEMA.md
  Database Deployment: _docs/database/DEPLOYMENT_CHECKLIST.md
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-17 | Initial architecture documentation |

---

**End of Architecture Document**