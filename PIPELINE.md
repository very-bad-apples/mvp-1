# Video Generation Pipeline

## Project Highlights & Key Features

### Core Capabilities

- **Project-Integrated Lip-Sync**: Automatic audio timing calculation based on scene sequence and cumulative duration, with configurable expressiveness, active speaker detection, and occlusion handling
- **Dynamic Prompt Expansion System**: AI-powered decomposition of simple concept prompts into multiple fully-fleshed scenes with detailed visual descriptions, camera angles, and narrative flow
- **Specialized Reference Image Prompting**: Character and product reference image integration with model-specific prompt engineering for consistent visual identity across scenes
- **Multi-Backend Video Generation**: Flexible architecture supporting both Gemini Video and Replicate (Veo) backends with seamless switching and fallback capabilities
- **Full Scene CRUD Operations**: Complete create, read, update, delete, reorder, trim, and regenerate capabilities at the individual scene level with non-destructive editing
- **Director Style Specialization**: Creative templates (e.g., "Wes Anderson", "Christopher Nolan") that apply distinctive visual styles and narrative techniques to generated scenes
- **Dual Mode Support**: Purpose-built workflows for both music video creation (narrative-driven, audio-synchronized) and advertisement creative generation (product-focused, platform-optimized)

---

## Overview

This project implements an AI-powered video generation pipeline that transforms text prompts into complete music videos or advertisement creatives. The system orchestrates multiple AI models and cloud services to generate scene-by-scene videos with optional lip-sync capabilities, ultimately composing them into a final polished output.

The pipeline supports two distinct modes: **music-video** mode for narrative-driven content synchronized to backing tracks, and **ad-creative** mode for product-focused promotional videos. Both modes leverage the same underlying architecture but apply different creative templates and generation parameters.

## Architecture & Technology Stack

The system employs a **microservices architecture** with distinct frontend and backend components. The frontend is built with **Next.js** and **React**, providing a real-time dashboard for project monitoring and editing. The backend uses **FastAPI** (Python) with **DynamoDB** for data persistence and **AWS S3** for media storage.

AI generation is powered by multiple specialized models: **Google Gemini** for scene description generation, **Replicate** for video synthesis (Veo model) and lip-sync processing (Lipsync-2-Pro), and various image generation models for character references. Background workers handle long-running generation tasks asynchronously, enabling the system to process multiple projects concurrently without blocking user interactions.

## End-to-End Pipeline Flow

### 1. Project Initialization

Users create a project by providing a concept prompt, character description, product details (for ads), and an optional audio backing track. The system generates a unique project ID and stores metadata in DynamoDB with a status of "pending." For music videos, the backing track duration determines the total video length; for ads, a target duration is specified.

### 2. Scene Generation

When generation starts, the system uses **Gemini** to decompose the concept into individual scenes. Each scene receives a detailed prompt describing the visual content, camera angles, and action. Scenes are stored as separate DynamoDB items with their own status tracking (pending, processing, completed, failed). This granular approach enables independent regeneration and editing of individual scenes without affecting others.

### 3. Video Synthesis

For each scene, the system calls **Replicate's Veo model** to generate a 5-10 second video clip based on the scene prompt. Character reference images can be provided to maintain consistency across scenes. Videos are generated in parallel using background workers, with each scene tracked independently. Generated videos are immediately uploaded to **S3** with automatic local file cleanup to prevent disk space accumulation.

The system calculates optimal video durations based on the backing track and number of scenes, ensuring the final composition matches the audio length. Each scene stores both an `originalVideoClipS3Key` (unmodified Veo output) and a `workingVideoClipS3Key` (current working version after trimming or lip-sync).

### 4. Video Editing & Trimming

After initial generation, users can trim individual scene videos through the frontend interface. The trim operation downloads the original video from S3, uses **ffmpeg** to extract the specified segment (in-point to out-point), uploads the trimmed version to S3, and updates the scene's `workingVideoClipS3Key`. The original remains preserved for rollback purposes.

Scene reordering is supported through a `displaySequence` field separate from the immutable `sequence` identifier, allowing users to rearrange scenes without changing their underlying database keys.

### 5. Lip-Sync Processing (Optional)

For scenes with dialogue or singing, the system offers project-integrated lip-sync capabilities. The newly implemented `/api/mv/projects/{project_id}/lipsync/{sequence}` endpoint automatically calculates audio timing by summing the durations of all previous scenes in the project. This ensures each scene syncs to the correct portion of the backing track.

The system uses **ffmpeg** to clip the relevant audio segment, then calls **Replicate's Lipsync-2-Pro model** with both the scene video and clipped audio. Users can configure temperature (lip movement expressiveness), active speaker detection (for multi-person scenes), and occlusion detection (for partially obscured faces). The lip-synced video replaces the working video while preserving the original for regeneration.

### 6. Final Composition

Once all scenes are completed, users trigger the composition phase. A background worker downloads all scene videos from S3 (using `workingVideoClipS3Key` to get the latest edited versions), concatenates them using **ffmpeg**, and optionally overlays the backing audio track. The final video is uploaded to S3 and linked in the project metadata as `finalOutputS3Key`.

The composition worker employs robust error handling with temp file cleanup in finally blocks, ensuring no orphaned files remain even if the process fails mid-operation.

## Storage & Resource Management

All media files are stored in **AWS S3** with a structured key hierarchy: `mv/projects/{project_id}/scenes/{sequence}/`. The system uses **presigned URLs** with configurable expiry times for secure temporary access, never exposing permanent URLs or credentials to the frontend.

A critical optimization is **automatic local file deletion**: after every successful S3 upload (scene videos, trimmed clips, lip-synced videos, final compositions), the local copy is immediately deleted using a `delete_local_file_after_upload()` utility. This prevents disk space accumulation on backend servers during high-volume operation.

DynamoDB employs a **single-table design** with composite sort keys: project metadata uses `SK="METADATA"` while scenes use `SK="SCENE#{sequence:03d}"`. This enables efficient querying of all scenes for a project in a single operation. A Global Secondary Index on project status supports fast filtering and dashboard views.

## Background Workers & Concurrency

Long-running operations (scene generation, video synthesis, lip-sync, composition) execute in background workers to prevent API timeout issues. The system uses **Python's asyncio** and **concurrent.futures** for parallelization, enabling multiple scenes to generate simultaneously within a project.

Workers implement **retry logic** with exponential backoff for transient failures (API rate limits, network issues) and maintain detailed **structured logging** (via structlog) for debugging and monitoring. Each operation logs start/completion events with processing times, enabling performance analysis and bottleneck identification.

## Real-Time Updates & User Experience

The frontend implements **polling-based real-time updates** via the `useProjectPolling` hook, checking project status every few seconds during active generation. This provides users with live progress tracking without requiring WebSocket infrastructure.

Projects and scenes track status transitions through a finite state machine: `pending → processing → completed/failed`. The UI renders different controls based on status, hiding regeneration options until generation completes and displaying detailed error messages when failures occur.

## Error Handling & Resilience

The system implements defense-in-depth error handling at multiple layers. API endpoints validate all inputs before processing, returning structured error responses with HTTP status codes (400 for validation, 404 for not found, 500 for internal errors). Background workers catch exceptions, log full stack traces, update item status to "failed" with error messages, and preserve partial results for debugging.

Critical operations use try-finally blocks to guarantee cleanup: temp directories are removed even if processing fails, database status is always updated to reflect reality, and S3 upload failures leave local files intact for manual retry. The `retryCount` field tracks regeneration attempts to prevent infinite loops.

## Mode-Specific Behavior

**Music Video Mode** emphasizes narrative coherence across scenes, with Gemini generating story-driven scene descriptions that flow together. The backing track is mandatory and determines total duration. Character consistency is enforced through reference images, and lip-sync is commonly applied to dialogue-heavy scenes.

**Ad Creative Mode** focuses on product presentation and brand messaging. Scenes highlight product features, benefits, and use cases. The product image serves as a reference, and durations are optimized for social media platforms (15-30 seconds typical). Backing tracks are optional, with many ads using voiceover or ambient sound instead.

## Future Scalability Considerations

The architecture is designed for horizontal scaling: additional background workers can be deployed to increase throughput, S3 handles unlimited storage growth, and DynamoDB auto-scales with demand. The single-table design minimizes cross-table joins, and the immutable `sequence` field prevents race conditions during concurrent edits.

Potential optimizations include: caching presigned URLs to reduce S3 API calls, implementing a job queue (SQS/Redis) for better worker distribution, adding CDN caching for frequently accessed videos, and introducing scene-level caching to avoid redundant regeneration of unchanged content.

## Full Diagram

![diagram](./pipeline-diagram.png)
