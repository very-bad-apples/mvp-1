# AI Video Pipeline MVP

AI-powered video generation pipeline for creating short-form social media content (30-second vertical videos).

## Overview

This system generates marketing videos using AI-powered script generation, video scene creation, voiceover synthesis, and automated composition.

**Key Features:**
- Script-first pipeline architecture (LLM → parallel asset generation → video assembly)
- Template-based video archetypes (Problem/Solution, POV Reaction, Testimonial, etc.)
- **Configuration Flavors** - Multiple preset configurations for different video styles
- Parallel scene generation for optimal performance (~7 min per video)
- Cost-optimized generation (~$1.46 per video)
- **Direct Backend Integration** - Frontend communicates directly with FastAPI (no Next.js API routes)
- Real-time progress tracking via WebSocket
- Async job processing with Redis queue
- **Project Management UI** - Dedicated project pages with scene-level control

## Tech Stack

### Backend
- **FastAPI** - API server with WebSocket support
- **DynamoDB** - Project and scene metadata storage
- **S3** - Asset storage (videos, images, audio)
- **Redis** - Job queue and pub/sub
- **MoviePy** - Video composition
- **Replicate** - AI video generation (Kling)
- **ElevenLabs** - Voice synthesis

### Frontend
- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Styling
- **Shadcn/ui** - Component library
- **Direct API Client** - Type-safe backend communication without Next.js API routes

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- pnpm
- Docker (for local DynamoDB and Redis)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start local services
docker-compose up -d dynamodb-local redis

# Initialize DynamoDB
python init_dynamodb.py

# Run server
uvicorn main:app --reload
```

Backend runs at http://localhost:8000

### Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with backend URL

# Run development server
pnpm dev
```

Frontend runs at http://localhost:3000

### Worker Setup

```bash
cd backend

# In a separate terminal (with venv activated)
python worker_mv.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Frontend (Next.js 15)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Direct API Client (lib/api/client.ts)              │   │
│  │  • Type-safe TypeScript interfaces                   │   │
│  │  • No Next.js API routes (direct backend calls)     │   │
│  └────────────────────┬─────────────────────────────────┘   │
└───────────────────────┼─────────────────────────────────────┘
                        │ HTTP/WebSocket
                        ▼
              ┌──────────────────┐
              │  FastAPI Backend │
              │  • REST API      │
              │  • Config Mgr    │
              └────────┬─────────┘
                       │
      ┌────────────────┼────────────────┐
      ▼                ▼                ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│ DynamoDB │    │    S3    │    │  Redis   │
│ Projects │    │  Assets  │    │  Queue   │
└──────────┘    └──────────┘    └────┬─────┘
                                      │
                                      ▼
                               ┌────────────┐
                               │   Worker   │
                               │  Process   │
                               └──────┬─────┘
                                      │
                       ┌──────────────┼──────────────┐
                       ▼              ▼              ▼
                ┌──────────┐   ┌──────────┐   ┌──────────┐
                │ Claude   │   │Replicate │   │ElevenLabs│
                │  (LLM)   │   │  (Video) │   │  (Voice) │
                └──────────┘   └──────────┘   └──────────┘
```

**Key Architecture Points:**
- **Direct Backend Communication**: Frontend bypasses Next.js API routes, calls FastAPI directly
- **Type Safety**: TypeScript interfaces ensure contract between frontend/backend
- **Configuration System**: Backend config manager supports multiple video style flavors
- **Async Processing**: Redis queue + worker process for long-running video generation
- **Cloud Storage**: S3 for all assets, DynamoDB for metadata

## Pipeline Flow

1. **Script Generation** (~10s)
   - LLM generates scene-by-scene script from concept prompt
   - Template-based structure ensures consistency

2. **Parallel Asset Generation** (~5 min)
   - Video scenes (Replicate/Kling)
   - Voiceover (ElevenLabs)
   - Background music (cached/reused)

3. **Video Assembly** (~2 min)
   - MoviePy composes scenes, audio, and overlays
   - Final output: 1080x1920, 30fps, H.264

## Documentation

- **[System Architecture](_docs/architecture.md)** - Complete system design and deployment
- **[Key Insights](_docs/key-insights.md)** - Important patterns and lessons learned
- **[Best Practices](_docs/best-practices.md)** - MVP development guidelines
- **[API Reference](backend/_docs/API_ENDPOINTS.md)** - Complete API documentation
- **[Worker System](backend/_docs/WORKER.md)** - Async processing architecture
- **[Database Schema](_docs/database/DYNAMODB_SCHEMA.md)** - DynamoDB table design

## Project Structure

```
.
├── backend/               # FastAPI backend
│   ├── routers/          # API endpoints
│   ├── services/         # External API clients
│   ├── mv/               # Music video pipeline
│   │   ├── configs/     # Configuration flavors
│   │   ├── scene_generator.py
│   │   ├── video_generator.py
│   │   └── config_manager.py
│   ├── worker_mv.py      # Background worker
│   └── _docs/            # Backend documentation
├── frontend/             # Next.js frontend
│   ├── app/              # App Router pages
│   │   ├── create/      # Project creation
│   │   └── project/[id] # Project detail pages
│   ├── components/       # React components
│   ├── lib/              # Utilities
│   │   ├── api/         # Direct backend API client
│   │   └── orchestration.ts  # Generation orchestration
│   ├── hooks/            # Custom React hooks
│   └── types/            # TypeScript definitions
├── _docs/                # Project documentation
│   ├── backend/          # Backend component docs
│   └── database/         # Database documentation
└── docker-compose.yml    # Local development services
```

## Environment Variables

### Backend (.env)
```bash
# AI Services
ANTHROPIC_API_KEY=your_key
REPLICATE_API_TOKEN=your_key
ELEVENLABS_API_KEY=your_key

# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
STORAGE_BUCKET=your_bucket_name

# Database
DYNAMODB_TABLE_NAME=MVProjects
USE_LOCAL_DYNAMODB=true  # false for production
DYNAMODB_ENDPOINT=http://localhost:8001

# Redis
REDIS_URL=redis://localhost:6379/0
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Configuration Flavors

The system supports multiple configuration "flavors" for different video styles and use cases. Each flavor contains preset configurations for:

- **Scene Prompts** - Template prompts for video generation
- **Image Prompts** - Character/product image generation settings
- **Image Parameters** - Model parameters for image generation
- **Pipeline Parameters** - Video composition settings

### Available Flavors

```bash
backend/mv/configs/
├── default/          # Standard configuration
└── example/          # Example alternative configuration
```

### Using Config Flavors

**Backend API:**
```python
# Pass config_flavor parameter to endpoints
POST /api/mv/scenes?config_flavor=example
```

**Frontend UI:**
- Config flavor selector available on `/create` page
- Changes apply to all generation operations

### Adding New Flavors

1. Create new directory in `backend/mv/configs/`
2. Add required YAML files (see `default/` for template)
3. Restart backend to discover new flavor

## Performance Targets

- **Generation Time**: < 8 minutes per video
- **Cost**: < $1.50 per video
- **Format**: 1080x1920 (9:16 vertical), 30fps
- **Success Rate**: > 95%

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests (when implemented)
cd frontend
pnpm test
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# DynamoDB connection
python backend/check_database.py dynamodb --list

# Redis connection
redis-cli ping
```

## Deployment

See [Deployment Checklist](_docs/database/DEPLOYMENT_CHECKLIST.md) for production deployment steps.

## Contributing

This is an internal MVP project. For development guidelines, see [Best Practices](_docs/best-practices.md).

## License

Private/Internal Project
