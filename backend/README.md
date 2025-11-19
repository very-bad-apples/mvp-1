# Backend Foundation - AI Video Generator

## Overview
FastAPI backend foundation for the AI ad creative video generator. This implementation covers the core infrastructure needed for video generation pipeline.

## Completed Tasks

### Task 7: Initialize FastAPI Application
Status: DONE

**What was implemented:**
- FastAPI application with CORS middleware configured for localhost:3000
- Structured logging with structlog
- Global error handling middleware
- Request logging middleware
- Health check endpoint at `/health`
- Root endpoint at `/` with API information
- Environment variable management with python-dotenv

**Files created:**
- `main.py` - FastAPI application entry point
- `config.py` - Configuration management
- `requirements.txt` - Python dependencies

### Task 20: Configure Redis for Job Queue System
Status: DONE

**What was implemented:**
- Redis client with connection pooling
- Auto-reconnection logic with health checks
- Job queue operations (enqueue, dequeue, status updates)
- Pub/sub channels for job status and progress updates
- Helper methods for job management

**Files created:**
- `redis_client.py` - Redis client with queue and pub/sub functionality

**Key features:**
- Connection pooling with configurable parameters
- Job queue: `video_generation_queue`
- Status channel: `job_status_updates`
- Progress channel: `job_progress_updates`
- TTL support for job data (24 hours default)

### Task 22: Design Job Database Schema
Status: DONE

**What was implemented:**
- SQLAlchemy models for Job and Stage tracking
- Database initialization and session management
- Relationship between Jobs and Stages (one-to-many)
- Helper methods for data serialization

**Files created:**
- `models.py` - SQLAlchemy models (Job, Stage)
- `database.py` - Database configuration and session management

**Database schema:**

**Job Model:**
- id (UUID primary key)
- status (pending, processing, completed, failed)
- created_at, updated_at (timestamps)
- product_name, style, cta_text (input parameters)
- product_image_path (optional)
- video_url (output)
- error_message (error handling)
- cost_usd (cost tracking)

**Stage Model:**
- id (integer primary key)
- job_id (foreign key to Job)
- stage_name (script_gen, voice_gen, video_gen, compositing)
- status (pending, processing, completed, failed)
- progress (0-100)
- started_at, completed_at (timestamps)
- stage_data (JSON/text for stage-specific data)
- error_message (error handling)

### Task 24: Create Docker Setup
Status: DONE

**What was implemented:**
- Docker Compose configuration for Redis
- Health checks for Redis container
- Volume persistence for Redis data
- Network configuration for future backend container

**Files created:**
- `docker-compose.yml` (in project root)

**Note:** Redis is currently running locally on port 6379 and is working correctly. The Docker Compose file is ready for future containerization.

### Task 12: Scene Template System
Status: DONE

**What was implemented:**
- Hardcoded scene templates for 4 video styles (luxury, energetic, minimal, bold)
- Template structure with 4 scenes per video (30 seconds total)
- Scene 4 optimized as static image for cost efficiency
- Template validation and helper functions

**Files created:**
- `pipeline/templates.py` - Scene template system

**Available styles:**
- `luxury` - Soft lighting, elegant, premium aesthetic
- `energetic` - Vibrant, dynamic, bold visuals
- `minimal` - Clean, simple, modern design
- `bold` - Strong, impactful, dramatic presentation

### Task 13: Build Script Generator with Claude Integration
Status: DONE

**What was implemented:**
- Claude 3.5 Sonnet API integration for script generation
- Product image analysis using Claude's vision capabilities
- AI-generated voiceovers tailored to each scene and style
- Automatic hook and CTA generation
- Exponential backoff retry logic for API resilience
- Comprehensive error handling and logging

**Files created:**
- `pipeline/script_generator.py` - Main ScriptGenerator class with Claude integration
- `pipeline/test_script_generator.py` - Comprehensive test suite
- `pipeline/script_generator_demo.py` - Usage examples and demos
- `pipeline/SCRIPT_GENERATOR_README.md` - Full API documentation
- `pipeline/INTEGRATION_EXAMPLE.md` - FastAPI integration guide
- Updated `config.py` to include ANTHROPIC_API_KEY
- Updated `requirements.txt` with anthropic SDK

**Key features:**
- **Vision Analysis**: Analyzes product images to extract features, benefits, USPs
- **Voiceover Generation**: Creates compelling, style-matched voiceovers for all 4 scenes
- **Template Integration**: Works seamlessly with existing template system
- **Retry Logic**: Handles rate limits and transient errors automatically
- **Multiple Styles**: Supports all 4 template styles
- **Structured Output**: Returns validated JSON matching template schema

**API Usage:**
```python
from pipeline.script_generator import create_script_generator

generator = create_script_generator()
script = generator.generate_script(
    product_name="Premium Headphones",
    style="luxury",
    cta_text="Shop Now",
    product_image_path="./product.jpg"  # Optional
)

# Access generated content
print(script['hook'])  # AI-generated hook
print(script['cta'])   # AI-generated CTA
for scene in script['scenes']:
    print(scene['voiceover_text'])  # AI-generated voiceovers
```

**Configuration:**
- Requires `ANTHROPIC_API_KEY` in `.env` file
- Uses Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`)
- Configurable retry logic (default: 3 retries with exponential backoff)
- Supports JPEG, PNG, GIF, WebP images

**Performance:**
- Without image: ~3-5 seconds (1 API call)
- With image: ~6-10 seconds (2 API calls)
- Cost: ~$0.01-0.04 per script generation

## Project Structure

```
backend/
├── main.py                 # FastAPI application
├── config.py              # Configuration management
├── database.py            # Database session management
├── models.py              # SQLAlchemy models
├── redis_client.py        # Redis client with queue ops
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── venv/                  # Virtual environment
├── video_generator.db     # SQLite database
├── _docs/                 # Documentation
│   ├── API_ENDPOINTS.md  # API reference
│   └── WORKER.md         # Worker system docs
└── README.md             # This file
```

## Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./video_generator.db

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=http://localhost:3000

# Application
DEBUG=true

# API Keys
OPENAI_API_KEY=<your-key>
REPLICATE_API_KEY=<your-key>
```

## Installation & Setup

### 1. Install Dependencies

```bash
cd /Users/zeno/Projects/bad-apple/video/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start Redis

Redis is already running on port 6379. To verify:

```bash
redis-cli ping
# Should return: PONG
```

### 3. Run the Server

```bash
cd /Users/zeno/Projects/bad-apple/video/backend
source venv/bin/activate
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify Setup

Test health endpoint:
```bash
curl http://localhost:8000/health
# {"status":"healthy","service":"ai-video-generator","version":"1.0.0"}
```

Access API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

### Test Redis Connection

```python
from redis_client import redis_client

# Test ping
print(redis_client.ping())  # Should print: True

# Test job enqueue
redis_client.enqueue_job("test-123", {"product": "Test Product"})
status = redis_client.get_job_status("test-123")
print(status)
```

### Test Database

```python
from database import SessionLocal, init_db
from models import Job, Stage
import uuid

# Initialize database
init_db()

# Create a job
db = SessionLocal()
job = Job(
    id=str(uuid.uuid4()),
    product_name="Test Product",
    style="modern",
    cta_text="Buy Now",
    status="pending"
)
db.add(job)
db.commit()
print(f"Created job: {job.id}")
db.close()
```

## API Endpoints

### Health Check
```
GET /health
Response: {"status": "healthy", "service": "ai-video-generator", "version": "1.0.0"}
```

### Root
```
GET /
Response: {"message": "AI Video Generator API", "version": "1.0.0", "docs": "/docs", "health": "/health"}
```

## Dependencies

- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **python-dotenv**: Environment variable management
- **structlog**: Structured logging
- **redis**: Redis client
- **sqlalchemy**: ORM for database
- **aiofiles**: Async file operations

## Additional Documentation

For detailed information about specific components:
- **API Endpoints**: See [_docs/API_ENDPOINTS.md](_docs/API_ENDPOINTS.md)
- **Worker System**: See [_docs/WORKER.md](_docs/WORKER.md)
- **System Architecture**: See [../_docs/architecture.md](../_docs/architecture.md)
- **Database Schema**: See [../_docs/database/DYNAMODB_SCHEMA.md](../_docs/database/DYNAMODB_SCHEMA.md)
- **Key Insights**: See [../_docs/key-insights.md](../_docs/key-insights.md)
- **Best Practices**: See [../_docs/best-practices.md](../_docs/best-practices.md)

## Success Criteria

All success criteria have been met:

- [x] FastAPI runs at http://localhost:8000
- [x] GET http://localhost:8000/health returns {"status": "healthy"}
- [x] Redis running on port 6379
- [x] Can connect to Redis from Python
- [x] Database models defined (Job and Stage)
- [x] SQLite database file created on first run
- [x] All 4 Task Master tasks marked as "done"

## Troubleshooting

### Server won't start
- Check if port 8000 is already in use: `lsof -i :8000`
- Verify virtual environment is activated: `which python`

### Redis connection errors
- Check if Redis is running: `redis-cli ping`
- Verify REDIS_URL in .env file

### Database errors
- Delete `video_generator.db` and restart server to recreate
- Check DATABASE_URL in .env file

## Development Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Install new dependency
pip install <package-name>
pip freeze > requirements.txt

# Run server with auto-reload
uvicorn main:app --reload

# Run in production mode
uvicorn main:app --host 0.0.0.0 --port 8000

# Check logs
# Logs are printed to stdout with structured format
```
