# AI Ad Creative Generator - PoC Architecture

## Pipeline Order Decision: **SCRIPT FIRST** ✅

Based on analysis of all three approaches (Claude, GPT, X), the optimal order is:

```
1. SCRIPT GENERATION (Claude LLM) - 10 seconds
   ↓
2. PARALLEL ASSET GENERATION - 5 minutes
   ├─ Voiceover (ElevenLabs)
   ├─ Video Scenes (Replicate/Kling)
   └─ Music (cached, pre-generated)
   ↓
3. VIDEO ASSEMBLY (FFmpeg/MoviePy) - 2 minutes
   ↓
TOTAL: ~7 minutes per video
```

### Why Script First?

**Everything depends on the script:**
- Voiceover text → comes from script
- Video scene prompts → comes from script
- Timing/duration → comes from script
- Text overlays → comes from script

**X's Key Insight:** Use **hardcoded templates** so script generation is fast and predictable.

---

## Tech Stack (Simplified for PoC)

### Frontend
- **Next.js 14** (App Router)
- **shadcn/ui** (via Kibo UI MCP)
- **v0** for layouts
- **Tailwind CSS** (latest config approach)

### Backend
- **FastAPI** (Python 3.11+)
- **Redis** for job queue
- **asyncio** for parallel execution

### Video Pipeline
- **Script**: Claude 3.5 Sonnet API
- **Voice**: ElevenLabs API
- **Video**: Replicate (Kling AI for 5s clips)
- **Images**: Replicate (FLUX.1-schnell for CTA scene)
- **Assembly**: FFmpeg + MoviePy

### Storage
- Local filesystem for MVP (can upgrade to S3 later)

---

## Data Flow

```
USER UPLOADS:
- 1 product image
- Prompt (what the ad should say)
- Style selection (luxury, energetic, etc.)

↓

STEP 1: SCRIPT GENERATION (Claude)
├─ Input: product image analysis + prompt + style
├─ Output: Structured JSON with 4 scenes
│   Scene 1 (8s): Close-up product shot + voiceover text
│   Scene 2 (8s): Product in use + voiceover text
│   Scene 3 (10s): Product benefit/feature + voiceover text
│   Scene 4 (4s): CTA with price + voiceover text
└─ Time: ~10 seconds

↓

STEP 2: PARALLEL GENERATION (ALL AT ONCE)
├─ Voiceover Generation (ElevenLabs)
│   └─ Input: Combined voiceover text from all scenes
│   └─ Output: 30-second .mp3 file
│   └─ Time: ~30 seconds
│
├─ Video Scene Generation (Replicate/Kling)
│   └─ Scene 1: 8s video (product close-up + uploaded image)
│   └─ Scene 2: 8s video (product in use scenario)
│   └─ Scene 3: 10s video (benefit visualization)
│   └─ Time: ~5 minutes (parallel)
│
└─ CTA Image (Replicate/FLUX)
    └─ Scene 4: Static image with text overlay
    └─ Time: ~10 seconds

↓

STEP 3: VIDEO ASSEMBLY (MoviePy + FFmpeg)
├─ Load all assets
├─ Stitch scenes with 0.5s crossfade
├─ Sync voiceover to timeline
├─ Mix background music (ducked to 30%)
├─ Export 1080x1920 MP4
└─ Time: ~2 minutes

↓

OUTPUT: 30-second ad video ready to download
```

---

## Scene Template (Hardcoded)

**X's genius insight:** Don't let LLM decide structure. Use proven templates.

```python
def generate_ad_scenes(product_name: str, product_image_url: str, style: str):
    """Hardcoded 4-scene template for product ads"""

    return {
        "scenes": [
            {
                "id": 1,
                "duration": 8,
                "type": "video",
                "video_prompt": f"Close-up of {product_name}, slow camera tilt, {style} lighting, soft background, luxury feel, product photography, 9:16 vertical",
                "use_product_image": True,  # Composite uploaded image
                "voiceover_template": "Discover [product_name].",
                "text_overlay": product_name,
            },
            {
                "id": 2,
                "duration": 8,
                "type": "video",
                "video_prompt": f"Hand holding {product_name}, using product, satisfied expression, {style} aesthetic, natural light, lifestyle shot, 9:16",
                "use_product_image": False,
                "voiceover_template": "[benefit statement from Claude]",
                "text_overlay": "Transform Your [Category]",
            },
            {
                "id": 3,
                "duration": 10,
                "type": "video",
                "video_prompt": f"{product_name} in beautiful setting, {style} mood, premium feel, slow motion, elegant composition, 9:16",
                "use_product_image": True,  # Show product again
                "voiceover_template": "[social proof from Claude]",
                "text_overlay": "Loved by Thousands",
            },
            {
                "id": 4,
                "duration": 4,
                "type": "image",  # Static CTA (cheap!)
                "image_prompt": f"Clean white background, {product_name} in corner, bold text: '[CTA] - $[price]', modern typography, {style} branding",
                "voiceover_template": "Get yours today.",
                "text_overlay": "Shop Now - $XX",
            }
        ],
        "total_duration": 30
    }
```

---

## API Endpoints (FastAPI)

```python
# POST /api/generate
# Input: { product_name, product_image, style, cta_text }
# Output: { job_id }

# GET /api/jobs/{job_id}
# Output: { status, progress, video_url }

# WebSocket /ws/jobs/{job_id}
# Real-time progress updates
```

---

## File Structure

```
video-ad-generator/
├── frontend/                  # Next.js
│   ├── app/
│   │   ├── page.tsx          # Upload form
│   │   └── jobs/[id]/
│   │       └── page.tsx      # Progress + video player
│   ├── components/
│   │   ├── upload-form.tsx   # Product upload (v0 + Kibo)
│   │   └── progress-tracker.tsx
│   └── package.json
│
├── backend/                   # FastAPI
│   ├── main.py               # API routes
│   ├── pipeline/
│   │   ├── script_generator.py    # Claude integration
│   │   ├── asset_generator.py     # Replicate + ElevenLabs
│   │   ├── video_composer.py      # FFmpeg/MoviePy
│   │   └── templates.py           # Hardcoded scene templates
│   └── requirements.txt
│
├── .env                       # API keys
└── ARCHITECTURE.md           # This file
```

---

## Key Decisions from Each Approach

### From Claude's Response:
✅ **Script first** - Everything flows from the script
✅ **ElevenLabs voice** - Best quality, non-negotiable
✅ **Pexels for B-roll** - Free, good enough for MVP
✅ **Batch processing** - Don't optimize for speed yet
✅ **3 variants per product** - Built-in A/B testing

### From GPT's Response:
✅ **Archetype system** - Proven templates (Problem-Solution, Testimonial, etc.)
✅ **Product intelligence** - Scrape reviews for authentic messaging
✅ **Hook optimizer** - Generate 5 alternate first 3 seconds
✅ **2-4 second clips** - Modular building blocks, not full videos

### From X's Response:
✅ **Hardcoded scenes** - 100% control, zero hallucination
✅ **Parallel generation** - asyncio for speed
✅ **Hybrid approach** - 3 videos + 1 static image (saves 25% cost)
✅ **Seed locking** - Consistent visual style across scenes
✅ **Music caching** - Generate once, reuse forever

---

## Cost Breakdown (Per Video)

| Component | Service | Cost |
|-----------|---------|------|
| Script generation | Claude 3.5 Sonnet | $0.10 |
| Voiceover (30s) | ElevenLabs | $0.05 |
| Video scene 1 (8s) | Replicate Kling | $0.40 |
| Video scene 2 (8s) | Replicate Kling | $0.40 |
| Video scene 3 (10s) | Replicate Kling | $0.50 |
| CTA image (static) | Replicate FLUX | $0.01 |
| Music | Cached | $0.00 |
| **TOTAL** | | **$1.46** |

**Target: Under $1.50 ✅**

---

## MVP Timeline (7 Days)

### Day 1-2: Foundation
- Initialize Next.js + FastAPI
- Basic upload form (v0 + Kibo UI)
- Redis job queue setup
- Scene template system

### Day 3-4: AI Integration
- Claude script generation
- Replicate video generation
- ElevenLabs voiceover
- Parallel asset execution

### Day 5-6: Video Assembly
- FFmpeg/MoviePy composition
- Audio sync
- Text overlays
- Export pipeline

### Day 7: Polish & Deploy
- Progress tracking (WebSocket)
- Error handling
- Sample video generation
- Deploy to production

---

## What We're NOT Building (Yet)

❌ User authentication - Anyone can generate
❌ Payment system - Free for MVP
❌ Template marketplace - One hardcoded template
❌ Video editing - No post-generation changes
❌ Custom branding - Use defaults
❌ Analytics - Just generate videos

---

## Next Steps

1. ✅ MCP mandates added to CLAUDE.md
2. ✅ Architecture documented
3. ⬜ Initialize Next.js frontend
4. ⬜ Initialize FastAPI backend
5. ⬜ Implement hardcoded scene templates
6. ⬜ Integrate Claude for script generation
7. ⬜ Integrate Replicate + ElevenLabs
8. ⬜ Build video composer
9. ⬜ Create upload form (v0 + Kibo)
10. ⬜ Deploy and test

---

**The Answer to Your Question:**

**Script First → Parallel Assets → Assembly**

This is the winning order because the script is the single source of truth that enables everything else to run in parallel for maximum speed.
