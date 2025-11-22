# DynamoDB Schema Documentation

## Overview

The Music Video (MV) pipeline uses a **single-table design** in DynamoDB to store both project metadata and individual scene items. This design optimizes access patterns, avoids the 400KB item size limit, and enables efficient queries via Global Secondary Indexes (GSI).

## Table Structure

**Table Name:** `MVProjects` (configurable via `DYNAMODB_TABLE_NAME`)

### Primary Keys

- **Partition Key (PK):** `PROJECT#{project_id}`
  - Format: `PROJECT#` prefix + UUID
  - Example: `PROJECT#550e8400-e29b-41d4-a716-446655440000`

- **Sort Key (SK):** Composite key indicating item type
  - Project metadata: `METADATA`
  - Scene items: `SCENE#{sequence}` (e.g., `SCENE#001`, `SCENE#002`)

### Global Secondary Index (GSI)

**Index Name:** `status-created-index`

- **GSI Partition Key (GSI1PK):** `status` (pending, processing, completed, failed, composing, generating_scenes)
- **GSI Sort Key (GSI1SK):** `createdAt` (ISO 8601 timestamp string)

**Purpose:** Query projects by status and creation time for monitoring and reporting.

## Item Types

### 1. Project Metadata Item

**SK:** `METADATA`

**Attributes:**
- `entityType`: `"project"`
- `projectId`: UUID string
- `status`: Current project status (pending, processing, completed, failed, composing, generating_scenes)
- `conceptPrompt`: Video concept description
- `characterDescription`: Character/style description
- `characterImageS3Key`: S3 object key for character reference image (optional, validated - not a URL)
- `productDescription`: Product description for ad-creative mode (optional)
- `productImageS3Key`: S3 object key for product image (optional, validated - not a URL)
- `audioBackingTrackS3Key`: S3 object key for audio backing track (optional, validated - not a URL)
- `finalOutputS3Key`: S3 object key for final composed video (optional, validated - not a URL)
- `sceneCount`: Number of scenes (integer, default: 0)
- `completedScenes`: Number of completed scenes (integer, default: 0)
- `failedScenes`: Number of failed scenes (integer, default: 0)
- `createdAt`: UTC datetime
- `updatedAt`: UTC datetime
- `GSI1PK`: Status value (for GSI queries)
- `GSI1SK`: Created timestamp as ISO string (for GSI queries)

**Example:**
```
PK: PROJECT#550e8400-e29b-41d4-a716-446655440000
SK: METADATA
entityType: project
projectId: 550e8400-e29b-41d4-a716-446655440000
status: processing
conceptPrompt: "Robot exploring Austin, Texas"
characterDescription: "Silver metallic humanoid robot"
sceneCount: 4
completedScenes: 2
failedScenes: 0
createdAt: 2025-11-17T10:00:00Z
updatedAt: 2025-11-17T10:15:00Z
GSI1PK: processing
GSI1SK: 2025-11-17T10:00:00Z
```

### 2. Scene Item

**SK:** `SCENE#{sequence}` (e.g., `SCENE#001`, `SCENE#002`)

**Attributes:**
- `entityType`: `"scene"`
- `projectId`: UUID string (same as parent project)
- `sequence`: Scene sequence number (integer, 1-based)
- `status`: Scene status (pending, processing, completed, failed)
- `prompt`: Scene description for video generation
- `negativePrompt`: Elements to exclude from scene (optional)
- `duration`: Scene duration in seconds (float)
- `referenceImageS3Keys`: List of S3 object keys for reference images (optional, validated - not URLs)
- `audioClipS3Key`: S3 object key for scene audio clip (optional, validated - not a URL)
- `videoClipS3Key`: S3 object key for generated video clip (optional, validated - not a URL)
- `needsLipSync`: Boolean indicating if lip sync is required
- `lipSyncedVideoClipS3Key`: S3 object key for lip-synced video clip (optional, validated - not a URL)
- `retryCount`: Number of retry attempts (integer, default: 0)
- `errorMessage`: Error message if scene generation failed (optional)
- `createdAt`: UTC datetime
- `updatedAt`: UTC datetime

**Example:**
```
PK: PROJECT#550e8400-e29b-41d4-a716-446655440000
SK: SCENE#001
entityType: scene
projectId: 550e8400-e29b-41d4-a716-446655440000
sequence: 1
status: completed
prompt: "Robot walking through downtown Austin"
negativePrompt: "No other people"
duration: 8.0
referenceImageS3Keys: ["mv/projects/550e8400/character.png"]
videoClipS3Key: "mv/projects/550e8400/scenes/scene_001.mp4"
needsLipSync: true
lipSyncedVideoClipS3Key: "mv/projects/550e8400/scenes/scene_001_lipsync.mp4"
retryCount: 0
createdAt: 2025-11-17T10:05:00Z
updatedAt: 2025-11-17T10:10:00Z
```

## Access Patterns

### 1. Get Project Metadata

**Query:** Get item with `PK = PROJECT#{project_id}` and `SK = METADATA`

**Example:**
```python
project = MVProjectItem.get(f"PROJECT#{project_id}", "METADATA")
```

### 2. Get All Scenes for a Project

**Query:** Query items with `PK = PROJECT#{project_id}` and `SK begins_with("SCENE#")`

**Example:**
```python
scenes = MVProjectItem.query(
    f"PROJECT#{project_id}",
    MVProjectItem.SK.begins_with("SCENE#")
)
```

### 3. Query Projects by Status

**Query:** Use GSI `status-created-index` with `GSI1PK = status`

**Example:**
```python
pending_projects = MVProjectItem.status_index.query("pending")
```

### 4. Query Recent Projects by Status

**Query:** Use GSI with `GSI1PK = status` and sort by `GSI1SK` (createdAt)

**Example:**
```python
recent_pending = MVProjectItem.status_index.query(
    "pending",
    scan_index_forward=False  # Descending order
)
```

## S3 Integration

### S3 Key Storage Strategy

**Principle:** Store only S3 object keys in DynamoDB, generate presigned URLs on-demand.

**Important:** All `*S3Key` fields in the database store **S3 object keys only** (e.g., `mv/projects/{id}/file.ext`), **NOT** presigned URLs or full S3 URLs. The system validates this automatically to prevent accidentally saving URLs.

**Benefits:**
- Presigned URLs expire (default: 1 hour), improving security
- S3 keys are immutable and don't change
- Reduces database size
- Enables URL regeneration without database updates
- Validation ensures data integrity (keys vs URLs)

**Validation:**
- All S3 key assignments are validated using `validate_s3_key()` from `services.s3_storage`
- Rejects URLs starting with `http://`, `https://`, or `s3://`
- Rejects presigned URLs (detects AWS signature query parameters)
- Raises `ValueError` with clear error message if URL is detected

### S3 Key Patterns

**Project Assets:**
- Character image: `mv/projects/{project_id}/character.png`
- Product image: `mv/projects/{project_id}/product.jpg`
- Audio backing track: `mv/projects/{project_id}/audio.mp3`
- Final video: `mv/projects/{project_id}/final.mp4`

**Scene Assets:**
- Scene video: `mv/projects/{project_id}/scenes/scene_{sequence:03d}.mp4`
- Scene audio: `mv/projects/{project_id}/scenes/audio_{sequence:03d}.mp3`
- Lip-synced video: `mv/projects/{project_id}/scenes/scene_{sequence:03d}_lipsync.mp4`

**Character Reference:**
- Character reference images: `mv/outputs/character_reference/{character_id}.png`

### Presigned URL Generation

Presigned URLs are generated **on-demand** when serving API responses, never stored in the database. Use `S3StorageService.generate_presigned_url()`:

```python
from services.s3_storage import get_s3_storage_service

s3_service = get_s3_storage_service()
# s3_key comes from database (e.g., "mv/projects/{id}/file.ext")
url = s3_service.generate_presigned_url(s3_key, expiry=3600)  # 1 hour default
```

**Example Flow:**
1. Database stores: `characterImageS3Key = "mv/projects/123/character.png"`
2. API endpoint reads S3 key from database
3. API generates presigned URL: `https://bucket.s3.amazonaws.com/mv/projects/123/character.png?X-Amz-Signature=...`
4. API returns presigned URL in response (URL expires after 1 hour)
5. Client uses presigned URL to access file directly from S3

### S3 Key Validation

All S3 keys are validated before being saved to ensure they are keys, not URLs:

```python
from services.s3_storage import validate_s3_key

# Valid S3 key (accepted)
key = validate_s3_key("mv/projects/123/file.png")  # Returns: "mv/projects/123/file.png"

# Invalid - URL (rejected)
try:
    validate_s3_key("https://bucket.s3.amazonaws.com/file.png")
except ValueError as e:
    # Error: "S3 key must be an S3 key, not a URL"
    pass

# Invalid - Presigned URL (rejected)
try:
    validate_s3_key("mv/projects/123/file.png?X-Amz-Signature=abc123")
except ValueError as e:
    # Error: "S3 key must be an S3 key, not a presigned URL"
    pass
```

**Where Validation Occurs:**
- `create_project_metadata()` - Validates all project S3 keys
- `create_scene_item()` - Validates reference image S3 keys
- Direct assignments in routers/workers - Validates before saving
- Update endpoints - Validates user-provided S3 keys

## Status Values

### Project Status State Machine

**Valid Status Values:**
- `pending`: Project created, awaiting scene generation
- `generating_scenes`: Scene prompts being generated (worker processing)
- `processing`: Scenes are being generated/composed
- `composing`: Final video composition in progress
- `queued`: Job queued for processing (internal worker state)
- `completed`: All scenes complete, final video ready
- `failed`: Project failed (check error messages)

**Status Transitions:**
```
pending → generating_scenes → processing → composing → completed
  ↓           ↓                  ↓            ↓
failed      failed            failed       failed
```

**Notes:**
- `queued` is an internal status used when jobs are enqueued to Redis
- `generating_scenes` is set by scene worker when processing scene generation
- `composing` is set when composition job is queued
- All statuses can transition to `failed` on error

### Scene Status State Machine

**Valid Status Values:**
- `pending`: Scene created, awaiting video generation
- `processing`: Video generation or lipsync in progress
- `completed`: Video generated successfully
- `failed`: Video generation failed (check errorMessage)

**Status Transitions:**
```
pending → processing → completed
  ↓           ↓
failed      failed
```

**Notes:**
- Scene status is set to `processing` before video generation and before lipsync
- Scene status updates are non-blocking (errors don't break request flow)

## Design Rationale

### Why Single-Table Design?

1. **Avoids 400KB Item Limit:** Scenes stored separately prevent project items from exceeding DynamoDB's 400KB limit
2. **Efficient Queries:** Single query retrieves all scenes for a project using `begins_with()` on sort key
3. **Cost Optimization:** Fewer tables = lower costs
4. **Simplified Access Patterns:** All project data accessible via single partition key

### Why Composite Sort Key?

- Enables querying all scenes for a project in one operation
- Maintains scene ordering via sequence number in sort key
- Allows future expansion (e.g., `SCENE#001#VERSION#1` for versioning)

### Why GSI for Status Queries?

- Enables monitoring dashboards (query by status)
- Supports reporting and analytics
- Allows efficient queries without full table scans

## Migration Notes

This DynamoDB schema is **independent** from the existing SQLAlchemy/SQLite database. The legacy database continues to operate for existing endpoints, while new MV endpoints use DynamoDB exclusively.

## References

- Model Definition: `backend/mv_models.py`
- S3 Storage Service: `backend/services/s3_storage.py` (includes `validate_s3_key()`)
- Database Initialization: `backend/init_dynamodb.py`
- API Endpoints: `backend/routers/mv_projects.py`
- Validation Function: `backend/services/s3_storage.py::validate_s3_key()`

