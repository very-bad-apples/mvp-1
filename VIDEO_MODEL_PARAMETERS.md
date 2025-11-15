# Video Model Parameters Reference

**Comprehensive parameter specification for all video generation models in the pipeline.**

This document describes the parameters supported by each video model and how they're unified through the `VideoParameterAdapter` system.

## Architecture Overview

```
Template System (templates.py)
    ↓
Unified Parameters (VideoModelParameters)
    ↓
Parameter Adapter (VideoParameterAdapter)
    ↓
Model-Specific Parameters
    ↓
Replicate API
```

## Quick Model Comparison

| Model | Max Duration | Resolution | Cost/sec | First Frame | Prompt Optimizer | Best For |
|-------|-------------|------------|----------|-------------|------------------|----------|
| **Minimax Video-01** | 6s | 1280x720 | $0.02 | ✅ | ✅ | General purpose, high quality |
| **LTX Video** | 10s | 1216x704 | $0.016 | ✅ | ❌ | Longer videos, fast generation |
| **Stable Video Diffusion** | 4s | 576x1024 | $0.0125 | ✅ (required) | ❌ | Product shots, image-to-video |
| **Seedance-1 Pro** | 6s | 720-1280 | $0.067 | ✅ | ❌ | Cinematic quality |
| **Hailuo 2.3** | 10s | 720-1080p | $0.03 | ❌ | ✅ | High fidelity, longer videos |
| **Google Veo 3.1** | 10s | 720-1080p | $0.04 | ❌ | ❌ | Context-aware generation |
| **OpenAI Sora 2** | 20s | 480-1080p | $0.10 | ❌ | ❌ | Premium quality, long form |

---

## 1. Minimax Video-01 (Kling)

**Model ID:** `minimax/video-01`
**Replicate URL:** https://replicate.com/minimax/video-01

### Capabilities
- **Resolution:** Fixed at 1280×720 (720p)
- **FPS:** Fixed at 25 fps
- **Duration:** 1-6 seconds
- **Aspect Ratios:** 16:9 (landscape), 9:16 (portrait), 1:1 (square)
- **Features:** Text-to-video, image-to-video, first/last frame support, prompt optimizer, camera control

### Parameters

```python
{
    "prompt": str,                    # Required - text description of video
    "prompt_optimizer": bool,         # Default: True - enhances prompt quality
    "first_frame_image": str | None,  # Optional - URL or path to starting image
    "last_image_url": str | None,     # Optional - URL or path to ending image
}
```

### Example

```python
params = {
    "prompt": "Close-up of luxury watch, slow camera tilt, soft lighting",
    "prompt_optimizer": True,
    "first_frame_image": "./product.jpg"
}
```

### Cost
- **Price:** $0.12 per 6-second video
- **Cost per second:** ~$0.02
- **Generation time:** ~3 minutes

### Best For
- General-purpose video generation
- Product showcases with image input
- Camera movement control
- High-quality 720p output

---

## 2. LTX Video (Lightricks)

**Model ID:** `lightricks/ltx-video`
**Replicate URL:** https://replicate.com/lightricks/ltx-video

### Capabilities
- **Resolution:** Up to 1216×704, divisible by 32
- **FPS:** 24, 25, or 30 fps
- **Duration:** 1-10 seconds
- **Aspect Ratios:** 9:16, 16:9, 1:1, custom (as long as divisible by 32)
- **Features:** Text-to-video, image-to-video, guidance scale, negative prompts

### Parameters

```python
{
    "prompt": str,                    # Required - text description
    "negative_prompt": str | None,    # Optional - what to avoid
    "width": int,                     # Default: 768, must be divisible by 32
    "height": int,                    # Default: 512, must be divisible by 32
    "num_frames": int,                # Must be 8n+1 (e.g., 9, 17, 25, 121, 257)
    "num_inference_steps": int,       # Default: 50 (quality vs speed trade-off)
    "guidance_scale": float,          # Default: 3.0 (1-20, how closely to follow prompt)
    "seed": int | None,               # Optional - for reproducibility
    "frame_rate": int,                # Default: 25 (24, 25, or 30)
    "image": str | None,              # Optional - first frame for image-to-video
}
```

### Frame Calculation Formula

```python
# LTX Video requires num_frames = 8n + 1
# Examples:
# 1s @ 24fps: 8*3 + 1 = 25 frames
# 2s @ 24fps: 8*6 + 1 = 49 frames
# 5s @ 24fps: 8*15 + 1 = 121 frames
# 10s @ 24fps: 8*32 + 1 = 257 frames (maximum)

def calculate_ltx_frames(duration_seconds: float, fps: int) -> int:
    target_frames = int(duration_seconds * fps)
    n = (target_frames - 1) // 8
    return 8 * n + 1
```

### Example

```python
params = {
    "prompt": "Cinematic product showcase, smooth rotation",
    "negative_prompt": "blurry, low quality, distorted",
    "width": 768,
    "height": 512,
    "num_frames": 121,  # ~5 seconds @ 25fps
    "num_inference_steps": 50,
    "guidance_scale": 7.5,
    "frame_rate": 25,
    "image": "./product.jpg"  # Optional starting frame
}
```

### Cost
- **Price:** $0.08 per 5-second video
- **Cost per second:** ~$0.016
- **Generation time:** ~90 seconds

### Best For
- Longer videos (up to 10s)
- Fine-grained control over generation
- Negative prompts to avoid unwanted elements
- Fast generation times

---

## 3. Stable Video Diffusion (SVD)

**Model ID:** `stability-ai/stable-video-diffusion`
**Replicate URL:** https://replicate.com/stability-ai/stable-video-diffusion

### Capabilities
- **Resolution:** Fixed at 576×1024 (portrait only)
- **FPS:** 6, 12, or 24 fps
- **Duration:** 1-4 seconds maximum
- **Aspect Ratios:** 9:16 (portrait only)
- **Features:** **Image-to-video only** (no text-to-video), motion control

### Parameters

```python
{
    "image": str,                     # Required - input image (path or URL)
    "num_frames": int,                # Default: 25, max: 25
    "fps": int,                       # Default: 6 (options: 6, 12, 24)
    "motion_bucket_id": int,          # Default: 127 (1-255, controls motion amount)
    "cond_aug": float,                # Default: 0.02 (conditioning augmentation)
    "decoding_t": int,                # Default: 14 (frames decoded at a time)
    "seed": int | None,               # Optional - for reproducibility
}
```

### Motion Control

```python
# Motion bucket ID controls how much the image moves:
# 1-50: Minimal motion (subtle camera movement)
# 50-127: Moderate motion (product rotation, gentle movements)
# 128-200: High motion (dynamic movement, scene changes)
# 201-255: Very high motion (aggressive movement, may lose coherence)

motion_map = {
    "low": 50,      # Subtle, elegant movements
    "medium": 127,  # Balanced motion
    "high": 200     # Dynamic, energetic motion
}
```

### Example

```python
params = {
    "image": "./product.jpg",
    "num_frames": 25,
    "fps": 6,
    "motion_bucket_id": 127,  # Moderate motion
    "cond_aug": 0.02,
    "decoding_t": 14,
}
```

### Cost
- **Price:** $0.05 per 4-second video
- **Cost per second:** ~$0.0125
- **Generation time:** ~60 seconds

### Best For
- Product animations from static images
- Image-to-video conversion
- Precise motion control
- Cost-effective video generation
- When you already have the perfect image

### Limitations
- **No text-to-video** - requires input image
- Maximum 4 seconds duration
- Fixed portrait resolution
- Limited to 25 frames maximum

---

## 4. Seedance-1 Pro (ByteDance)

**Model ID:** `bytedance/seedance-1-pro`
**Replicate URL:** https://replicate.com/bytedance/seedance-1-pro

### Capabilities
- **Resolution:** 720×1280 or 1280×720
- **FPS:** 24 fps (fixed)
- **Duration:** 4 or 6 seconds only
- **Aspect Ratios:** 9:16, 16:9, 1:1
- **Features:** Text-to-video, image-to-video, first/last frame, cinematic quality

### Parameters

```python
{
    "prompt": str,                    # Required - text description
    "width": int,                     # Default: 720
    "height": int,                    # Default: 1280
    "duration": "4s" | "6s",          # Must be exactly "4s" or "6s"
    "aspect_ratio": str,              # "9:16", "16:9", or "1:1"
    "first_frame": str | None,        # Optional - starting image
    "last_frame": str | None,         # Optional - ending image
    "seed": int | None,               # Optional - for reproducibility
}
```

### Example

```python
params = {
    "prompt": "Cinematic reveal of luxury product with dramatic lighting",
    "duration": "6s",
    "aspect_ratio": "9:16",
    "width": 720,
    "height": 1280,
    "first_frame": "./product.jpg",
    "seed": 42
}
```

### Cost
- **Price:** $0.40 per 6-second video
- **Cost per second:** ~$0.067
- **Generation time:** ~5 minutes

### Best For
- Cinematic quality videos
- Professional-grade output
- First and last frame control
- When budget allows for premium quality

---

## 5. Hailuo 2.3 (Minimax)

**Model ID:** `minimax/hailuo-2.3`
**Replicate URL:** https://replicate.com/minimax/hailuo-2.3

### Capabilities
- **Resolution:** 720P or 1080P
- **FPS:** 25 or 30 fps
- **Duration:** 5 or 10 seconds only
- **Aspect Ratios:** 16:9, 9:16
- **Features:** Text-to-video, prompt optimizer, high fidelity

### Parameters

```python
{
    "prompt": str,                    # Required - text description
    "resolution": "720P" | "1080P",   # Default: "720P"
    "duration": "5s" | "10s",         # Must be exactly "5s" or "10s"
    "prompt_optimizer": bool,         # Default: True - enhances prompt
    "seed": int | None,               # Optional - for reproducibility
}
```

### Example

```python
params = {
    "prompt": "High-quality product showcase with smooth camera movement",
    "resolution": "1080P",
    "duration": "10s",
    "prompt_optimizer": True,
}
```

### Cost
- **Price:** $0.15 per 5-second video
- **Cost per second:** ~$0.03
- **Generation time:** ~4 minutes

### Best For
- Longer videos (up to 10s)
- High-fidelity output
- 1080p resolution support
- Automated prompt optimization

---

## 6. Google Veo 3.1

**Model ID:** `google/veo-3.1`
**Replicate URL:** https://replicate.com/google/veo-3.1

### Capabilities
- **Resolution:** 720-1080p
- **FPS:** 24 or 30 fps
- **Duration:** 2-10 seconds
- **Aspect Ratios:** 9:16, 16:9, 1:1
- **Features:** Text-to-video, context-aware generation

### Parameters

```python
{
    "prompt": str,                    # Required - text description
    "aspect_ratio": str,              # "9:16", "16:9", or "1:1"
    "duration": int,                  # 2-10 seconds
    "seed": int | None,               # Optional - for reproducibility
}
```

### Example

```python
params = {
    "prompt": "Professional product video with dynamic lighting",
    "aspect_ratio": "9:16",
    "duration": 8,
}
```

### Cost
- **Price:** $0.20 per 5-second video
- **Cost per second:** ~$0.04
- **Generation time:** ~3 minutes

### Best For
- Context-aware video generation
- Consistent quality across durations
- Google's latest video technology

---

## 7. OpenAI Sora 2

**Model ID:** `openai/sora-2`
**Replicate URL:** https://replicate.com/openai/sora-2

### Capabilities
- **Resolution:** 480p, 720p, or 1080p
- **FPS:** 24 or 30 fps
- **Duration:** 1-20 seconds (longest duration)
- **Aspect Ratios:** 9:16, 16:9, 1:1
- **Features:** Text-to-video, synced audio, flagship quality

### Parameters

```python
{
    "prompt": str,                    # Required - text description
    "aspect_ratio": str,              # "9:16", "16:9", or "1:1"
    "duration": int,                  # 1-20 seconds (maximum in class)
    "resolution": str,                # "480p", "720p", or "1080p"
    "seed": int | None,               # Optional - for reproducibility
}
```

### Example

```python
params = {
    "prompt": "Cinematic product reveal with dramatic music sync",
    "aspect_ratio": "9:16",
    "duration": 15,  # Can go up to 20s
    "resolution": "1080p",
}
```

### Cost
- **Price:** $0.50 per 5-second video
- **Cost per second:** ~$0.10
- **Generation time:** ~5 minutes

### Best For
- Long-form content (up to 20s)
- Premium quality requirements
- Synced audio generation
- When budget allows for flagship model

---

## Unified Parameter Interface

All models are accessed through a unified `VideoModelParameters` interface:

```python
from services.video_model_params import (
    VideoModelParameters,
    VideoParameterAdapter,
    AspectRatio
)

# Create unified parameters
params = VideoModelParameters(
    prompt="Luxury product showcase with elegant lighting",
    aspect_ratio=AspectRatio.PORTRAIT,
    duration=6.0,
    fps=25,
    first_frame_image="./product.jpg",
    motion_intensity="low",
    guidance_scale=7.5,
    prompt_optimizer=True,
)

# Adapt to any model
minimax_params = VideoParameterAdapter.adapt_for_model("minimax", params)
ltx_params = VideoParameterAdapter.adapt_for_model("ltxv", params)
svd_params = VideoParameterAdapter.adapt_for_model("svd", params)
```

## Parameter Validation

The adapter automatically validates parameters against model capabilities:

```python
# This will raise ValueError - SVD max duration is 4s
params = VideoModelParameters(
    prompt="...",
    duration=10.0,  # Too long for SVD
    first_frame_image="./product.jpg"
)

# This raises an error:
VideoParameterAdapter.adapt_for_model("svd", params)
# ValueError: Duration 10.0s exceeds maximum 4.0s
```

## Model Selection Guide

### For Product Showcases (with image)
1. **Minimax Video-01** - Best overall quality with image input
2. **Stable Video Diffusion** - Most cost-effective for short animations
3. **LTX Video** - Best for longer showcases (up to 10s)

### For Text-Only Generation
1. **Hailuo 2.3** - Best quality at 1080p
2. **LTX Video** - Best balance of speed and quality
3. **Sora 2** - Best for long-form content (budget permitting)

### For Fast Iteration
1. **LTX Video** - Fastest generation (~90s)
2. **Stable Video Diffusion** - Fast for image-to-video (~60s)
3. **Minimax Video-01** - Good quality/speed balance

### For Budget Optimization
1. **Stable Video Diffusion** - $0.0125/second (image-to-video only)
2. **LTX Video** - $0.016/second
3. **Minimax Video-01** - $0.02/second

### For Premium Quality
1. **Sora 2** - Flagship quality, long duration
2. **Seedance-1 Pro** - Cinematic quality
3. **Hailuo 2.3** - High fidelity at 1080p

## Integration Example

```python
# In your video_generator.py
from services.video_model_params import (
    VideoModelParameters,
    VideoParameterAdapter,
    AspectRatio,
    get_model_spec
)

class VideoGenerator:
    def __init__(self, model_preference: str = "minimax"):
        self.model_spec = get_model_spec(model_preference)

    def _get_model_input_params(self, prompt, style, scene_config, product_image):
        # Create unified parameters
        params = VideoModelParameters(
            prompt=prompt,
            aspect_ratio=AspectRatio.PORTRAIT,
            duration=scene_config.get("duration", 5),
            fps=24,
            first_frame_image=product_image,
            prompt_optimizer=True,
        )

        # Adapt to model-specific parameters
        return VideoParameterAdapter.adapt_for_model(
            self.model_spec.model_id,
            params
        )
```

## Adding New Models

To add a new video model:

1. Add capabilities specification
2. Add parameter class
3. Add to VIDEO_MODEL_REGISTRY
4. Add adapter method in VideoParameterAdapter

See `services/video_model_params.py` for details.
