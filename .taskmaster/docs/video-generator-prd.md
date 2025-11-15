# AI Ad Creative Video Generator - Product Requirements Document

## Overview
Build an AI-powered video generation pipeline that transforms a product image and prompt into a professional 30-second ad in ~7 minutes, using the script-first approach with parallel asset generation.

## Core Features

### 1. Frontend Application (Next.js 14)

#### 1.1 Landing Page Setup
Initialize Next.js 14 application with App Router, TypeScript, and Tailwind CSS. Configure for standalone builds and environment variable support.

#### 1.2 Product Upload Form
Create a form component using v0 and Kibo UI MCP that accepts:
- Product image upload (drag & drop, max 10MB)
- Product name input field
- Style selector dropdown (luxury, energetic, minimal, bold)
- CTA text input with price
- Submit button with loading states
Form should validate inputs and show real-time feedback.

#### 1.3 Job Status Page
Build a dynamic page at /jobs/[id] that displays:
- Real-time progress tracker with 3 stages (Script, Assets, Assembly)
- Progress bars for each stage
- WebSocket connection for live updates
- Video player when complete
- Download button for final video
- Error display with retry option

#### 1.4 Video Player Component
Create a custom video player component with:
- Play/pause controls
- Timeline scrubbing
- Volume control
- Fullscreen toggle
- Mobile-optimized controls
- Share functionality

#### 1.5 shadcn/ui Component Setup
Install and configure shadcn/ui with the following components:
- Button, Input, Label, Form
- Progress, Card, Badge
- Dialog, Toast, Dropdown
- Tabs, Separator
Use Kibo UI MCP for customization guidance.

### 2. Backend API (FastAPI)

#### 2.1 FastAPI Application Setup
Initialize FastAPI application with:
- CORS middleware configuration
- Environment variable management (python-dotenv)
- Logging configuration (structlog)
- Error handling middleware
- Health check endpoint

#### 2.2 Video Generation Endpoint
Create POST /api/generate endpoint that:
- Accepts multipart form data (image + JSON params)
- Validates input parameters (file size, format, text length)
- Generates unique job ID (UUID)
- Enqueues job to Redis queue
- Returns job ID and estimated completion time

#### 2.3 Job Status Endpoint
Create GET /api/jobs/{job_id} endpoint that:
- Fetches job status from Redis cache and database
- Returns current progress, stage, and any errors
- Includes video URL when completed
- Returns 404 for invalid job IDs

#### 2.4 WebSocket Progress Updates
Implement WebSocket endpoint at /ws/jobs/{job_id} that:
- Establishes persistent connection
- Subscribes to Redis pub/sub for job updates
- Streams progress events to client
- Handles connection cleanup on job completion
- Manages reconnection logic

#### 2.5 File Upload Handling
Create file upload service that:
- Saves uploaded images to temporary storage
- Generates thumbnails for preview
- Validates image formats (PNG, JPG, WebP)
- Implements size limits (max 10MB)
- Returns file path for pipeline processing

### 3. Video Generation Pipeline

#### 3.1 Scene Template System
Create hardcoded scene templates in templates.py:
- Define 4-scene structure (8s, 8s, 10s, 4s)
- Template for luxury style
- Template for energetic style
- Template for minimal style
- Template for bold style
Each template includes video prompts, voiceover templates, and text overlays.

#### 3.2 Script Generator (Claude Integration)
Build script_generator.py that:
- Analyzes uploaded product image using Claude vision
- Generates structured scene JSON based on template
- Fills in voiceover text for each scene
- Creates compelling hooks and CTAs
- Returns complete script with timing
Uses Claude 3.5 Sonnet API with specific prompt engineering.

#### 3.3 Voiceover Generator (ElevenLabs)
Build voiceover_generator.py that:
- Combines voiceover text from all scenes
- Calls ElevenLabs API with optimal voice settings
- Downloads generated MP3 file
- Validates audio duration matches expected length
- Saves to temporary storage
- Returns audio file path

#### 3.4 Video Scene Generator (Replicate/Kling)
Build video_generator.py that:
- Generates Scene 1: Product close-up (8s) using Kling
- Generates Scene 2: Product in use (8s) using Kling
- Generates Scene 3: Benefit visualization (10s) using Kling
- Uses consistent seed for style coherence
- Includes product image compositing where specified
- Downloads generated video clips
- Returns list of video file paths
Uses Replicate API with Kling model.

#### 3.5 CTA Image Generator (Replicate/FLUX)
Build cta_generator.py that:
- Generates static CTA image with text overlay
- Uses FLUX.1-schnell for speed
- Includes product name, price, and CTA text
- Matches style from video scenes
- Returns image file path

#### 3.6 Video Composer (FFmpeg/MoviePy)
Build video_composer.py that:
- Loads all generated assets (3 videos + 1 image)
- Creates video clips with proper durations
- Adds 0.5s crossfade transitions
- Syncs voiceover audio to timeline
- Adds background music (ducked to 30%)
- Adds text overlays with timing
- Exports 1080x1920 MP4 at 30fps
- Generates thumbnail from first frame
- Returns final video path

#### 3.7 Asset Manager
Build asset_manager.py that:
- Creates temporary directories for each job
- Manages file downloads from Replicate
- Handles file cleanup after job completion
- Implements retry logic for failed downloads
- Validates file integrity

#### 3.8 Pipeline Orchestrator
Build orchestrator.py that:
- Coordinates all pipeline steps
- Runs asset generation in parallel using asyncio
- Publishes progress updates to Redis pub/sub
- Handles errors at each stage
- Implements retry logic with exponential backoff
- Updates job status in database and cache
- Cleans up temporary files

### 4. Job Queue System

#### 4.1 Redis Setup
Configure Redis for:
- Job queue storage (pending jobs)
- Job status cache (current progress)
- Pub/sub channels for real-time updates
- Connection pooling
- Automatic reconnection

#### 4.2 Queue Worker
Build worker.py that:
- Listens to Redis job queue
- Processes jobs sequentially
- Handles worker failures gracefully
- Implements health checks
- Logs all operations
- Can be scaled horizontally

#### 4.3 Job Database Schema
Design and implement database models:
- Job table (id, status, created_at, updated_at, video_url, error)
- Stage table (job_id, stage_name, progress, started_at, completed_at)
- Use SQLite for MVP (easy to upgrade to PostgreSQL)

### 5. Development Infrastructure

#### 5.1 Environment Configuration
Create comprehensive .env.example with:
- API keys (Claude, Replicate, ElevenLabs)
- Redis connection string
- Database URL
- CORS origins
- Debug settings
- Storage paths

#### 5.2 Docker Setup
Create docker-compose.yml for:
- Redis container
- Backend container (optional for dev)
- Volume mounts for development
- Network configuration
- Environment variable passing

#### 5.3 Development Scripts
Create npm/python scripts for:
- Starting frontend dev server
- Starting backend dev server
- Running both in parallel
- Database migrations
- Clearing cache/temp files
- Running tests

#### 5.4 API Documentation
Set up FastAPI automatic documentation:
- Swagger UI at /docs
- ReDoc at /redoc
- Add detailed endpoint descriptions
- Include request/response examples
- Document error codes

### 6. Error Handling & Monitoring

#### 6.1 Error Handling System
Implement comprehensive error handling:
- API-level error responses with codes
- Pipeline error catching and logging
- User-friendly error messages
- Retry mechanisms for transient failures
- Fallback strategies for API failures

#### 6.2 Logging Infrastructure
Set up structured logging:
- JSON log format for parsing
- Different log levels (DEBUG, INFO, ERROR)
- Request/response logging
- Performance metrics logging
- Separate logs per service

#### 6.3 Progress Tracking System
Build detailed progress tracking:
- Stage-level progress (0-100%)
- Sub-stage granularity (script, voice, video 1, video 2, etc.)
- Time estimates based on historical data
- Real-time updates via WebSocket
- Persistent progress in Redis

### 7. Testing & Quality

#### 7.1 Backend Unit Tests
Write pytest tests for:
- Script generation logic
- Template rendering
- File upload validation
- Job queue operations
- Error handling scenarios

#### 7.2 Frontend Component Tests
Write Vitest tests for:
- Upload form validation
- Progress tracker updates
- Video player controls
- Error display states
- API integration mocks

#### 7.3 Integration Tests
Create end-to-end tests:
- Full video generation flow
- WebSocket connection handling
- File upload and processing
- Error recovery scenarios
- Concurrent job processing

#### 7.4 Manual Test Cases
Document test cases for:
- Different product types (bottles, electronics, clothing)
- All style variations
- Various image formats and sizes
- Edge cases (very long product names, special characters)
- Network failures and recovery

### 8. Deployment & Operations

#### 8.1 Frontend Deployment
Deploy Next.js to:
- Vercel (recommended) or
- Docker container on cloud provider
- Configure environment variables
- Set up custom domain
- Enable CDN for static assets

#### 8.2 Backend Deployment
Deploy FastAPI to:
- Cloud Run / Railway / Fly.io or
- Docker container on EC2/DigitalOcean
- Configure Redis connection
- Set up file storage (local or S3)
- Enable HTTPS

#### 8.3 Monitoring Setup
Implement basic monitoring:
- API health check endpoint
- Queue depth monitoring
- Job success/failure rates
- Average generation time
- Error rate tracking

#### 8.4 Cost Monitoring
Track API costs:
- Log all external API calls
- Calculate cost per video
- Set up usage alerts
- Monthly cost reporting

### 9. Documentation

#### 9.1 README Setup
Create comprehensive README with:
- Project overview and architecture diagram
- Quick start guide
- Environment setup instructions
- Development workflow
- Deployment guide
- Troubleshooting section

#### 9.2 API Documentation
Document all API endpoints:
- Request/response formats
- Authentication (future)
- Rate limits
- Error codes
- Example curl commands

#### 9.3 Pipeline Documentation
Document video generation pipeline:
- Architecture diagram
- Data flow between stages
- Asset specifications (sizes, formats, durations)
- Customization guide
- Performance optimization tips

## Success Criteria

### MVP Success Metrics
- Generate 30-second ad video in under 8 minutes
- Cost per video under $1.50
- Video quality: 1080x1920, 30fps, proper audio sync
- Success rate: >90% for valid inputs
- Frontend responsive on mobile and desktop

### Performance Targets
- API response time: <500ms
- WebSocket latency: <200ms
- File upload: <5 seconds for 10MB
- Parallel asset generation working correctly
- Graceful degradation on failures

### Quality Targets
- Videos have coherent visual style across scenes
- Audio perfectly synced to video
- Text overlays readable on mobile
- Smooth transitions between scenes
- No artifacts or quality loss in final export

## Technical Constraints

- Must use provided API keys (Claude, Replicate, ElevenLabs)
- Must support 1 product image per video (no multi-product)
- Must generate vertical video (9:16 aspect ratio)
- Must complete within 8-minute target
- Must cost less than $1.50 per video
- Must work on modern browsers (Chrome, Safari, Firefox)
- Must handle concurrent users (at least 5 simultaneous jobs)

## Out of Scope (Phase 2)

- User authentication and accounts
- Payment processing
- Multiple video templates
- Video editing after generation
- Custom branding (logos, colors)
- Analytics dashboard
- A/B testing variants
- Batch video generation
- API for developers
- Mobile native apps
