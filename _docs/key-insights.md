# Cherry-Picked Documentation - Key Insights

This document extracts the most valuable, evergreen insights from various brainstorming sessions and implementation notes that are being archived. These are the "keeper" insights that remain relevant to the project.

---

## Architecture Principles (from brainstorming sessions)

### Pipeline Order: Script First ✅
**The Winning Insight**: Everything depends on the script.
- Voiceover text → comes from script
- Video scene prompts → comes from script
- Timing/duration → comes from script
- Text overlays → comes from script

**Optimal Pipeline**:
```
1. SCRIPT GENERATION (LLM) - 10 seconds
   ↓
2. PARALLEL ASSET GENERATION - 5 minutes
   ├─ Voiceover (ElevenLabs)
   ├─ Video Scenes (Replicate)
   └─ Music (cached)
   ↓
3. VIDEO ASSEMBLY (FFmpeg/MoviePy) - 2 minutes
```

### Hardcoded Templates Strategy
**Key Insight from X's Response**: Don't let LLM decide structure. Use proven templates.

**Why This Works**:
- 100% control, zero hallucination
- Guaranteed coherence across scenes
- Predictable timing and pacing
- LLM fills content into slots, not structure

**Template Pattern**:
```json
{
  "archetype": "ProblemSolution",
  "pacing": {
    "hook_duration": "1.8s",
    "scene_lengths": [2, 2, 3, 2, 3, 2]
  },
  "scenes": [
    {
      "type": "UGC",
      "camera": "selfie, chaotic, fast zoom",
      "text": "[hook from LLM]",
      "vo": "[vo from LLM]"
    }
    // ... more scenes
  ]
}
```

### Cost Optimization Strategies
**Hybrid Approach**: 3 video scenes + 1 static image = 25% cost savings

**Per-Video Cost Breakdown** (Target: < $1.50):
| Component | Cost |
|-----------|------|
| Script (Claude 3.5 Sonnet) | $0.10 |
| Voiceover (ElevenLabs 30s) | $0.05 |
| Video scenes (3 × Kling) | $1.30 |
| CTA image (FLUX static) | $0.01 |
| **TOTAL** | **$1.46** ✅ |

**Cost-Saving Tactics**:
- Cache background music (generate once, reuse)
- Use seed locking for consistent style
- Static image for CTA scene (not video)
- Parallel generation to reduce wall-clock time

---

## Performance Targets (Validated)

### Generation Time
- **Target**: < 8 minutes per video
- **Actual**: ~7 minutes average
  - Script: 10 seconds
  - Parallel assets: 5 minutes
  - Composition: 2 minutes

### Quality Benchmarks
- **Format**: 1080×1920 (9:16 vertical)
- **Duration**: 30 seconds
- **Frame Rate**: 30 fps
- **Codec**: H.264, AAC audio

---

## Ad Performance Principles

### First 3 Seconds Rule
**From GPT's Insights**: Meta/TikTok ad performance is 80% determined by first 2-3 seconds.

**Implementation**:
- Generate 5 alternate hooks per video
- Optimize for "scroll-stop rate"
- Test curiosity vs. benefit vs. social proof angles

### Archetype System
**8 High-Performing Ad Formats**:
1. Problem → Solution
2. POV Reaction
3. Unboxing + Try On
4. "TikTok Made Me Buy It"
5. Founder Story
6. Testimonial (UGC style)
7. Before / After
8. Green Screen Reaction

Each archetype defines:
- Tone and pacing
- Scene structure
- Hook format
- Target emotion

### Pacing Rules (Hardcoded)
- **Scene length**: 2-3 seconds MAX
- **Text timing**: Appears 0.3s before voiceover
- **Transitions**: Quick cuts (0.1s) or swipe (0.2s)
- **Hook rule**: Product visible + text overlay in first 1 second

---

## Product Intelligence Layer

### What to Extract (via scraping/analysis)
From product pages:
- Key benefits (from description)
- Customer pain points (from reviews)
- Unique selling points
- Standout phrases for authenticity

**Why This Matters**: Elevates ad quality massively. Most competitors skip this.

### Image Analysis Strategy
Use Claude Vision to extract:
- Product description
- Visual style and aesthetics
- Key features visible in image
- Target audience indicators
- Emotional appeal factors

---

## Technical Best Practices

### Parallel Execution Pattern
```python
import asyncio

async def generate_multiple_scenes(prompts: list[str]):
    """Generate scenes concurrently"""
    tasks = [
        replicate.run_async(model_id, {"prompt": p})
        for p in prompts
    ]
    return await asyncio.gather(*tasks)
```

### Retry Logic with Exponential Backoff
**Pattern Used Across All API Calls**:
- Max retries: 3
- Base delay: 1 second
- Backoff: Exponential (1s → 2s → 4s)
- Retry on: Rate limits, network errors, 5xx
- Don't retry: 4xx validation errors

### Error Handling Strategy
```python
# Retryable errors
- External API failures
- Network timeouts
- Rate limiting (429)
- Temporary service issues (5xx)

# Non-retryable errors (fail fast)
- Invalid input validation (400)
- Missing required fields (400)
- File too large (413)
- Unsupported format (415)
```

---

## Differentiation Strategy

### Killer Features for Market Differentiation

#### 1. First 3 Seconds Optimizer
- Auto-generate 5 alternate hooks
- Rank by predicted scroll-stop rate
- A/B test variants automatically

#### 2. Built-in Creative Director AI
LLM critiques the draft:
- "Scene 3 drags — cut 0.5 seconds"
- "Hook is too generic — try curiosity angle"
- "Add jump zoom to increase engagement"

#### 3. Product Intelligence Integration
- Pull Amazon reviews automatically
- Extract customer pain points
- Identify standout benefit phrases
- Use authentic language from real customers

---

## Scalability Considerations

### Horizontal Scaling (Workers)
**Redis BLPOP Pattern**: Fair job distribution
- Multiple workers can process queue in parallel
- No job duplication (atomic pop operation)
- Each worker processes jobs sequentially

**Resource Requirements per Worker**:
- CPU: ~1 core (I/O bound)
- Memory: ~512MB
- Network: Stable for API calls

**Scaling Formula**:
- 100 jobs/hour: 2-3 workers (3-5 min per job)
- 1000 jobs/hour: 20-30 workers with load balancing

### Async Processing Benefits
- Non-blocking I/O for API calls
- Parallel scene generation
- Frontend polls for updates
- WebSocket for real-time progress

---

## Security & Production Readiness

### API Key Management
- Store in environment variables only
- Never commit to version control
- Rotate regularly in production
- Use IAM roles in cloud environments

### Input Validation
- File type whitelist (PNG, JPG, WebP)
- File size limits (10MB max)
- Filename sanitization
- Content verification

### Storage Strategy
- Database: Store S3 keys only (not URLs)
- Retrieval: Generate presigned URLs on-demand
- Expiration: Presigned URLs expire after 1 hour
- Why: Keys are permanent, URLs are temporary

---

## Lessons from Implementation

### What Worked Well

1. **Template System**: Hardcoded structure eliminated LLM hallucination
2. **Parallel Generation**: Cut wall-clock time by 60%
3. **Retry Logic**: Made system resilient to API flakiness
4. **Progress Updates**: Real-time WebSocket kept users engaged
5. **Seed Locking**: Consistent visual style across scenes

### What Required Iteration

1. **JSON Parsing from LLMs**: Sometimes returns markdown-wrapped JSON
   - Solution: Parse and extract, validate structure

2. **Rate Limiting**: High-volume usage hit limits quickly
   - Solution: Exponential backoff + queue system

3. **Image Size Limits**: Large files exceeded API limits
   - Solution: Document limits, recommend optimization

4. **Database Health Checks**: SQLAlchemy 2.0 syntax changes
   - Solution: Use `text()` wrapper for raw SQL

---

## Future Enhancement Ideas

### Phase 2 Features (If Pursuing Further)
- WebSocket for real-time updates (implemented)
- Retry logic for failed scenes (implemented)
- Scene-level regeneration (re-do single scene)
- Template marketplace (different video styles)
- Custom branding (logo, colors, fonts)

### Phase 3 Optimizations
- CloudFront CDN for video delivery
- DynamoDB auto-scaling
- Redis caching for presigned URLs
- Batch video generation
- Video preview thumbnails

### Phase 4 Enterprise
- User authentication and accounts
- Payment integration (Stripe)
- Usage quotas and billing
- Team collaboration features
- API for programmatic access
- Webhook notifications

---

## Key Metrics to Track

### Performance KPIs
- Generation time (target: < 8 min)
- Cost per video (target: < $1.50)
- Success rate (target: > 95%)
- API failure rate (target: < 5%)

### Business KPIs (If Productizing)
- User retention (videos per user)
- Template effectiveness (by style)
- Hook performance (by variant)
- Conversion rate (views → clicks)

### Technical KPIs
- Queue depth (jobs waiting)
- Worker utilization (% busy)
- API call latency (p50, p95, p99)
- Error rate by component

---

## Architectural Decisions Log

### Why FastAPI + Redis + MoviePy?
- **FastAPI**: Modern async Python framework, great for API + WebSocket
- **Redis**: Fast, simple queue system with pub/sub
- **MoviePy**: Pythonic video composition, good for MVP
- **Alternative considered**: Remotion (React) - more complex, overkill for POC

### Why Single-Table DynamoDB Design?
- Optimizes for access patterns
- Avoids 400KB item size limit
- Reduces query count
- Cost-effective for variable traffic
- GSI enables efficient status queries

### Why Presigned URLs vs. Direct Storage?
- Security: Controlled, time-limited access
- Flexibility: Can change storage without DB migration
- Performance: Direct S3 access, no proxy overhead
- Cost: No data transfer through backend

---

## Code Patterns Worth Keeping

### Singleton Pattern for API Clients
```python
class ReplicateClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### Structured Logging Pattern
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "model_prediction_started",
    model_id=model_id,
    prediction_id=prediction.id,
    input_params=input_params
)
```

### Progress Update Pattern
```python
def update_progress(job_id: str, stage: str, progress: int):
    """Publish progress to Redis pub/sub"""
    redis_client.publish(
        f"job:{job_id}:progress",
        json.dumps({
            "stage": stage,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        })
    )
```

---

## References to Full Documentation

For complete implementation details, see:
- **Architecture**: `architecture.md` (1378 lines, in this directory)
- **API Endpoints**: `../backend/_docs/API_ENDPOINTS.md`
- **Worker System**: `../backend/_docs/WORKER.md`
- **Database Schema**: `database/DYNAMODB_SCHEMA.md` (in this directory)
- **Database Deployment**: `database/DEPLOYMENT_CHECKLIST.md` (in this directory)

---

**Document Purpose**: This cherry-picked doc serves as a quick reference for the most valuable insights extracted from brainstorming sessions and implementation summaries. Use it to avoid re-discovering these lessons.

**Last Updated**: 2025-11-19
