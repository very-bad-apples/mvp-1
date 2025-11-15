# ScriptGenerator Integration Example

## FastAPI Endpoint Integration

Here's how to integrate the `ScriptGenerator` into your FastAPI application:

### 1. Add to Pipeline Worker

```python
# backend/pipeline/worker.py (or wherever your job processing happens)

from pipeline.script_generator import create_script_generator, ScriptGenerationError
from models import Job, Stage, StageNames, StageStatus
import json

def process_script_generation(job_id: str, db_session):
    """
    Process script generation stage using Claude API

    Args:
        job_id: Job ID to process
        db_session: Database session
    """
    # Get job from database
    job = db_session.query(Job).filter(Job.id == job_id).first()

    # Get or create script generation stage
    stage = db_session.query(Stage).filter(
        Stage.job_id == job_id,
        Stage.stage_name == StageNames.SCRIPT_GENERATION
    ).first()

    if not stage:
        stage = Stage(
            job_id=job_id,
            stage_name=StageNames.SCRIPT_GENERATION,
            status=StageStatus.PROCESSING
        )
        db_session.add(stage)
    else:
        stage.status = StageStatus.PROCESSING

    db_session.commit()

    try:
        # Create script generator
        generator = create_script_generator()

        # Update progress
        stage.progress = 25
        db_session.commit()

        # Generate script
        script = generator.generate_script(
            product_name=job.product_name,
            style=job.style,
            cta_text=job.cta_text,
            product_image_path=job.product_image_path
        )

        # Update progress
        stage.progress = 75
        db_session.commit()

        # Save script to stage data
        stage.stage_data = json.dumps(script)
        stage.progress = 100
        stage.status = StageStatus.COMPLETED
        db_session.commit()

        return script

    except ScriptGenerationError as e:
        stage.status = StageStatus.FAILED
        stage.error_message = f"Script generation failed: {str(e)}"
        db_session.commit()
        raise
    except Exception as e:
        stage.status = StageStatus.FAILED
        stage.error_message = f"Unexpected error: {str(e)}"
        db_session.commit()
        raise
```

### 2. Add FastAPI Endpoint

```python
# backend/main.py

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from pipeline.script_generator import create_script_generator, ScriptGenerationError

app = FastAPI()

class ScriptRequest(BaseModel):
    product_name: str
    style: str  # luxury, energetic, minimal, bold
    cta_text: str
    product_image_path: Optional[str] = None

class ScriptResponse(BaseModel):
    success: bool
    script: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.post("/api/generate-script", response_model=ScriptResponse)
async def generate_script_endpoint(request: ScriptRequest):
    """
    Generate video script using Claude API

    Example request:
    {
        "product_name": "Premium Headphones",
        "style": "luxury",
        "cta_text": "Shop Now",
        "product_image_path": "/path/to/image.jpg"
    }
    """
    try:
        generator = create_script_generator()

        script = generator.generate_script(
            product_name=request.product_name,
            style=request.style,
            cta_text=request.cta_text,
            product_image_path=request.product_image_path
        )

        return ScriptResponse(
            success=True,
            script=script
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ScriptGenerationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
```

### 3. Use in Video Generation Pipeline

```python
# backend/pipeline/video_pipeline.py

from pipeline.script_generator import create_script_generator

class VideoPipeline:
    def __init__(self):
        self.script_generator = create_script_generator()

    async def generate_video(self, job):
        """
        Complete video generation pipeline
        """
        # Stage 1: Generate script with Claude
        print("Stage 1: Generating script...")
        script = self.script_generator.generate_script(
            product_name=job.product_name,
            style=job.style,
            cta_text=job.cta_text,
            product_image_path=job.product_image_path
        )

        # Stage 2: Generate voiceovers
        print("Stage 2: Generating voiceovers...")
        audio_files = []
        for scene in script['scenes']:
            audio_file = await self.generate_voice(
                text=scene['voiceover_text'],
                scene_id=scene['id']
            )
            audio_files.append(audio_file)

        # Stage 3: Generate videos
        print("Stage 3: Generating videos...")
        video_files = []
        for scene in script['scenes']:
            if scene['type'] == 'video':
                video_file = await self.generate_video_clip(
                    prompt=scene['video_prompt_template'],
                    duration=scene['duration']
                )
                video_files.append(video_file)
            else:  # image
                image_file = await self.generate_image(
                    prompt=scene['image_prompt_template']
                )
                video_files.append(image_file)

        # Stage 4: Composite everything
        print("Stage 4: Compositing final video...")
        final_video = await self.composite_video(
            scenes=script['scenes'],
            video_files=video_files,
            audio_files=audio_files
        )

        return final_video
```

### 4. Queue-Based Processing

```python
# backend/worker.py (Redis queue worker)

import json
from redis import Redis
from pipeline.script_generator import create_script_generator, ScriptGenerationError
from database import SessionLocal
from models import Job, StageNames

redis_client = Redis(host='localhost', port=6379, db=0)

def process_job(job_id: str):
    """Process a video generation job"""
    db = SessionLocal()

    try:
        # Get job
        job = db.query(Job).filter(Job.id == job_id).first()

        # Update job status
        job.status = "processing"
        db.commit()

        # Stage 1: Script Generation
        redis_client.publish(
            'job_updates',
            json.dumps({'job_id': job_id, 'stage': 'script_gen', 'status': 'processing'})
        )

        try:
            generator = create_script_generator()
            script = generator.generate_script(
                product_name=job.product_name,
                style=job.style,
                cta_text=job.cta_text,
                product_image_path=job.product_image_path
            )

            # Store script in database
            stage = Stage(
                job_id=job_id,
                stage_name=StageNames.SCRIPT_GENERATION,
                status='completed',
                stage_data=json.dumps(script)
            )
            db.add(stage)
            db.commit()

            redis_client.publish(
                'job_updates',
                json.dumps({'job_id': job_id, 'stage': 'script_gen', 'status': 'completed'})
            )

        except ScriptGenerationError as e:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()

            redis_client.publish(
                'job_updates',
                json.dumps({'job_id': job_id, 'stage': 'script_gen', 'status': 'failed', 'error': str(e)})
            )
            return

        # Continue with other stages...
        # Stage 2: Voice generation
        # Stage 3: Video generation
        # Stage 4: Compositing

    finally:
        db.close()

# Start worker
if __name__ == "__main__":
    while True:
        # Pop job from queue
        job_data = redis_client.blpop('video_generation_queue', timeout=1)
        if job_data:
            job_id = job_data[1].decode('utf-8')
            process_job(job_id)
```

## Testing the Integration

### 1. Test Script Generation Endpoint

```bash
curl -X POST http://localhost:8000/api/generate-script \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Premium Coffee Maker",
    "style": "luxury",
    "cta_text": "Shop Now"
  }'
```

### 2. Test with Python Requests

```python
import requests

response = requests.post(
    "http://localhost:8000/api/generate-script",
    json={
        "product_name": "Smart Watch",
        "style": "energetic",
        "cta_text": "Get Yours Today"
    }
)

if response.status_code == 200:
    data = response.json()
    script = data['script']
    print(f"Hook: {script['hook']}")
    print(f"CTA: {script['cta']}")
else:
    print(f"Error: {response.json()['detail']}")
```

### 3. Test Full Pipeline

```python
from pipeline.video_pipeline import VideoPipeline
from models import Job

# Create test job
job = Job(
    product_name="Eco Water Bottle",
    style="minimal",
    cta_text="Join the Movement",
    product_image_path="./test_images/bottle.jpg"
)

# Run pipeline
pipeline = VideoPipeline()
video = await pipeline.generate_video(job)
print(f"Video generated: {video}")
```

## Environment Setup

Make sure your `.env` file has:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional (for full pipeline)
REPLICATE_API_KEY=your-replicate-key
ELEVENLABS_API_KEY=your-elevenlabs-key
```

## Error Monitoring

Add error tracking to monitor Claude API issues:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('script_generation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('script_generator')

# In your pipeline
try:
    script = generator.generate_script(...)
except ScriptGenerationError as e:
    logger.error(f"Script generation failed for job {job_id}: {e}")
    # Send alert, update database, etc.
```

## Performance Optimization

### 1. Caching

Cache generated scripts for identical inputs:

```python
from functools import lru_cache
import hashlib

def cache_key(product_name, style, cta_text, image_path):
    """Generate cache key"""
    data = f"{product_name}|{style}|{cta_text}|{image_path or ''}"
    return hashlib.md5(data.encode()).hexdigest()

# Simple in-memory cache
script_cache = {}

def generate_script_cached(product_name, style, cta_text, image_path=None):
    key = cache_key(product_name, style, cta_text, image_path)

    if key in script_cache:
        logger.info(f"Cache hit for {product_name}")
        return script_cache[key]

    generator = create_script_generator()
    script = generator.generate_script(
        product_name, style, cta_text, image_path
    )

    script_cache[key] = script
    return script
```

### 2. Async Processing

For high-volume scenarios, use async processing:

```python
from anthropic import AsyncAnthropic
import asyncio

class AsyncScriptGenerator:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate_script_async(self, product_name, style, cta_text, image_path=None):
        """Async version of generate_script"""
        # Implementation similar to sync version
        # but using await for API calls
        pass

# Process multiple scripts in parallel
async def process_batch(jobs):
    generator = AsyncScriptGenerator()
    tasks = [
        generator.generate_script_async(
            job.product_name, job.style, job.cta_text, job.product_image_path
        )
        for job in jobs
    ]
    return await asyncio.gather(*tasks)
```

## Next Steps

1. Update your pipeline to use `ScriptGenerator`
2. Add script generation endpoint to your API
3. Implement queue-based processing for scale
4. Add monitoring and error tracking
5. Test with real product images
6. Optimize caching strategy

## Support

For integration issues, refer to:
- `SCRIPT_GENERATOR_README.md` - Full API documentation
- `test_script_generator.py` - Test examples
- `script_generator_demo.py` - Usage examples
