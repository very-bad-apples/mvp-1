# Video Generator

## Overview

The `VideoGenerator` class generates video scenes using Replicate's AI video generation models. It provides a unified interface for multiple video generation models with style-specific configurations and async batch processing.

## Features

- **Multiple Model Support**: Minimax Video-01, LTX Video, Stable Video Diffusion, Zeroscope, Hotshot-XL
- **Style Coherence**: Luxury, energetic, minimal, bold visual styles
- **Async Batch Generation**: Generate multiple scenes in parallel for performance
- **Product Image Integration**: Support for image-to-video models
- **Retry Logic**: Built-in retry mechanism via ReplicateClient
- **Asset Management**: Automatic file download and validation

## Architecture

```
┌─────────────────┐
│ ScriptGenerator │ → Generates scene templates
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ VideoGenerator  │ → Enhances prompts, calls models
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ ReplicateClient │ → API wrapper with retry logic
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ AssetManager    │ → Downloads and validates videos
└─────────────────┘
```

## Supported Video Models

### 1. Minimax Video-01 (Recommended)
- **Model ID**: `minimax/video-01`
- **Type**: Text-to-video
- **Quality**: High
- **Speed**: Medium
- **Best for**: Professional product videos, luxury style

### 2. LTX Video
- **Model ID**: `fofr/ltxv`
- **Type**: Text-to-video
- **Quality**: Medium-High
- **Speed**: Fast
- **Best for**: Quick generation, energetic style

### 3. Stable Video Diffusion
- **Model ID**: `stability-ai/stable-video-diffusion`
- **Type**: Image-to-video
- **Quality**: High
- **Speed**: Medium
- **Best for**: Product shots with specific image input

### 4. Zeroscope V2 XL
- **Model ID**: `anotherjesse/zeroscope-v2-xl`
- **Type**: Text-to-video
- **Quality**: Medium
- **Speed**: Fast
- **Best for**: Open-source alternative, minimal style

### 5. Hotshot-XL
- **Model ID**: `lucataco/hotshot-xl`
- **Type**: Image-to-video
- **Quality**: Medium
- **Speed**: Very Fast
- **Best for**: Quick image animation, bold style

## Style Configurations

Each style has specific visual parameters to ensure coherence:

### Luxury Style
```python
{
    "prompt_suffix": "soft lighting, elegant camera movement, premium aesthetics",
    "duration": 5,
    "fps": 24,
    "aspect_ratio": "9:16",
    "motion_intensity": "low"
}
```

### Energetic Style
```python
{
    "prompt_suffix": "dynamic transitions, vibrant colors, fast-paced",
    "duration": 5,
    "fps": 30,  # Higher fps for smoother fast motion
    "aspect_ratio": "9:16",
    "motion_intensity": "high"
}
```

### Minimal Style
```python
{
    "prompt_suffix": "clean composition, simple movements, muted palette",
    "duration": 5,
    "fps": 24,
    "aspect_ratio": "9:16",
    "motion_intensity": "low"
}
```

### Bold Style
```python
{
    "prompt_suffix": "strong contrasts, dramatic angles, impactful visuals",
    "duration": 5,
    "fps": 24,
    "aspect_ratio": "9:16",
    "motion_intensity": "medium"
}
```

## Usage

### Basic Usage

```python
from services.replicate_client import get_replicate_client
from pipeline.video_generator import create_video_generator
from pipeline.asset_manager import AssetManager

# Initialize components
client = get_replicate_client()
video_gen = create_video_generator(client, model_preference="minimax")
asset_manager = AssetManager("job-123")
await asset_manager.create_job_directory()

# Generate single scene
scene_config = {
    "id": 1,
    "video_prompt_template": "Close-up of {product_name}, luxury lighting",
    "use_product_image": True
}

video_path = await video_gen.generate_scene(
    scene_config,
    style="luxury",
    product_image_path="./product.jpg",
    asset_manager=asset_manager,
    scene_id=1
)

print(f"Generated video: {video_path}")
```

### Full Pipeline Integration

```python
from pipeline.script_generator import create_script_generator
from services.replicate_client import get_replicate_client
from pipeline.video_generator import create_video_generator
from pipeline.asset_manager import AssetManager

# Generate script
script_gen = create_script_generator()
script = script_gen.generate_script(
    product_name="Premium Headphones",
    style="luxury",
    cta_text="Shop Now",
    product_image_path="./headphones.jpg"
)

# Generate all video scenes
client = get_replicate_client()
video_gen = create_video_generator(client, model_preference="minimax")
asset_manager = AssetManager("job-456")
await asset_manager.create_job_directory()

video_paths = await video_gen.generate_all_scenes(
    script=script,
    style="luxury",
    product_image_path="./headphones.jpg",
    asset_manager=asset_manager
)

print(f"Generated {len(video_paths)} video scenes")
for path in video_paths:
    print(f"  - {path}")
```

### Async Batch Generation

```python
import asyncio

async def generate_videos_for_products(products):
    """Generate videos for multiple products in parallel"""

    client = get_replicate_client()
    video_gen = create_video_generator(client)

    tasks = []
    for product in products:
        script_gen = create_script_generator()
        script = script_gen.generate_script(
            product_name=product["name"],
            style=product["style"],
            cta_text="Shop Now"
        )

        task = video_gen.generate_all_scenes(
            script=script,
            style=product["style"]
        )
        tasks.append(task)

    # Generate all products in parallel
    results = await asyncio.gather(*tasks)
    return results

# Usage
products = [
    {"name": "Watch", "style": "luxury"},
    {"name": "Shoes", "style": "energetic"},
    {"name": "Lamp", "style": "minimal"}
]

video_results = asyncio.run(generate_videos_for_products(products))
```

## Model Selection Guide

Choose the best model for your use case:

| Use Case | Recommended Model | Why |
|----------|------------------|-----|
| High-quality product ads | Minimax Video-01 | Best quality, professional output |
| Fast iteration/testing | LTX Video | Quick generation, good quality |
| Product with specific image | Stable Video Diffusion | Image-to-video preserves product details |
| Budget-conscious | Zeroscope V2 XL | Open source, lower cost |
| Quick animations | Hotshot-XL | Very fast, good for simple animations |

## Performance Metrics

### Generation Times (Approximate)

- **Minimax Video-01**: 60-90 seconds per scene
- **LTX Video**: 30-45 seconds per scene
- **Stable Video Diffusion**: 45-60 seconds per scene
- **Zeroscope V2 XL**: 40-60 seconds per scene
- **Hotshot-XL**: 20-30 seconds per scene

### Parallel Generation

Using `generate_all_scenes()` with 3 video scenes:
- **Sequential**: 180-270 seconds (3-4.5 minutes)
- **Parallel**: 60-90 seconds (1-1.5 minutes)

**Performance improvement**: ~3x faster with async batch generation

## Error Handling

The VideoGenerator includes comprehensive error handling:

```python
from pipeline.video_generator import VideoGenerationError

try:
    video_path = await video_gen.generate_scene(
        scene_config,
        style="luxury",
        asset_manager=am
    )
except VideoGenerationError as e:
    print(f"Video generation failed: {e}")
    # Log error, retry, or fallback to alternative model
```

### Common Errors

1. **Missing video_prompt_template**: Scene config must include prompt template
2. **Invalid model preference**: Model must be one of: minimax, ltxv, svd, zeroscope, hotshot
3. **Image-to-video without image**: SVD and Hotshot require product_image_path
4. **API timeout**: Replicate API timeout (handled by retry logic)
5. **Invalid file**: Downloaded video failed validation (size check)

## Testing

Run the test suite:

```bash
# Run all tests
pytest backend/pipeline/test_video_generator.py -v

# Run specific test class
pytest backend/pipeline/test_video_generator.py::TestGenerateScene -v

# Run with coverage
pytest backend/pipeline/test_video_generator.py --cov=pipeline.video_generator
```

## Integration with Other Components

### ScriptGenerator Integration

```python
# ScriptGenerator provides scene configs with prompts
script = script_gen.generate_script(...)

# VideoGenerator uses these configs
for scene in script['scenes']:
    if scene['type'] == 'video':
        video_path = await video_gen.generate_scene(
            scene,
            style=script['style'],
            asset_manager=am
        )
```

### AssetManager Integration

```python
# AssetManager handles file operations
asset_manager = AssetManager("job-123")
await asset_manager.create_job_directory()

# VideoGenerator downloads videos via AssetManager
video_path = await video_gen.generate_scene(
    scene_config,
    style="luxury",
    asset_manager=asset_manager  # Handles download & validation
)

# Files are organized in job directory
# /tmp/video_jobs/job-123/scenes/scene_1.mp4
```

### ReplicateClient Integration

```python
# ReplicateClient provides retry logic and error handling
client = get_replicate_client()  # Singleton pattern

# VideoGenerator uses client for all API calls
video_gen = VideoGenerator(client)

# Client handles:
# - Retry logic with exponential backoff
# - Error handling (ModelError, network errors)
# - Logging and monitoring
```

## Future Enhancements

### Product Image Compositing
Currently a placeholder. Future implementation could:
- Use FFmpeg overlays to composite product images
- Apply style-specific compositing parameters
- Support multiple image placements

### Additional Features
- **Custom duration per scene**: Override default 5-second duration
- **Motion control**: Fine-tune camera movement intensity
- **Transition effects**: Smooth transitions between scenes
- **Audio sync**: Generate videos timed to voiceover length
- **Quality presets**: Low/medium/high quality settings
- **Cost optimization**: Automatic model selection based on budget

## Contributing

When adding new video models:

1. Add model to `VIDEO_MODELS` dictionary
2. Implement model-specific parameters in `_get_model_input_params()`
3. Add tests for new model
4. Update this README with model details

Example:
```python
# In video_generator.py
VIDEO_MODELS = {
    # ... existing models ...
    "new_model": "owner/new-video-model",
}

# Add to _get_model_input_params()
elif self.model_preference == "new_model":
    return {
        "prompt": prompt,
        # model-specific params
    }
```

## License

Part of the Bad Apple Video Generator project.

## Support

For issues or questions:
- Check test suite for usage examples
- Review ReplicateClient documentation
- Consult Replicate model documentation
