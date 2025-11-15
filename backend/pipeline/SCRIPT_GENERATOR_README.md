# Script Generator with Claude Integration

## Overview

The `script_generator.py` module integrates Claude 3.5 Sonnet API to analyze product images and generate structured video scripts with compelling voiceovers, hooks, and CTAs.

## Features

- **Product Image Analysis**: Uses Claude's vision capabilities to analyze product images and extract key features, benefits, and selling points
- **AI-Generated Voiceovers**: Creates natural, engaging voiceover scripts tailored to each scene and style
- **Template Integration**: Works seamlessly with the existing template system
- **Retry Logic**: Implements exponential backoff for handling rate limits and transient errors
- **Error Handling**: Comprehensive error handling with detailed logging
- **Multiple Styles**: Supports luxury, energetic, minimal, and bold styles

## Installation

### 1. Install Dependencies

The Anthropic SDK has already been installed and added to `requirements.txt`:

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Key

Add your Anthropic API key to `backend/.env`:

```env
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

## Usage

### Basic Usage (No Image)

```python
from pipeline.script_generator import create_script_generator

# Create generator
generator = create_script_generator()

# Generate script
script = generator.generate_script(
    product_name="Premium Headphones",
    style="luxury",
    cta_text="Shop Now"
)

# Access generated content
print(f"Hook: {script['hook']}")
print(f"CTA: {script['cta']}")

# Access scene voiceovers
for scene in script['scenes']:
    print(f"Scene {scene['id']}: {scene['voiceover_text']}")
```

### With Product Image Analysis

```python
# Generate script with image analysis
script = generator.generate_script(
    product_name="Smart Watch",
    style="bold",
    cta_text="Get Yours Today",
    product_image_path="./path/to/product.jpg"
)

# Access product analysis
if 'product_analysis' in script:
    analysis = script['product_analysis']
    print(f"Description: {analysis['product_description']}")
    print(f"Benefits: {analysis['key_benefits']}")
    print(f"USPs: {analysis['unique_selling_points']}")
```

### Error Handling

```python
from pipeline.script_generator import ScriptGenerationError

try:
    script = generator.generate_script(
        product_name="Product",
        style="luxury",
        cta_text="Buy Now",
        product_image_path="./product.jpg"
    )
except ScriptGenerationError as e:
    print(f"Script generation failed: {e}")
except ValueError as e:
    print(f"Invalid parameters: {e}")
```

## API Reference

### `ScriptGenerator`

Main class for generating video scripts with Claude integration.

#### `__init__(api_key: Optional[str] = None)`

Initialize the script generator.

**Parameters:**
- `api_key` (Optional[str]): Anthropic API key. Defaults to `settings.ANTHROPIC_API_KEY`

**Raises:**
- `ValueError`: If API key is not configured

#### `generate_script(product_name, style, cta_text, product_image_path=None)`

Generate complete video script with Claude integration.

**Parameters:**
- `product_name` (str): Name of the product
- `style` (str): Visual style - one of: 'luxury', 'energetic', 'minimal', 'bold'
- `cta_text` (str): Call-to-action text (e.g., "Shop Now")
- `product_image_path` (Optional[str]): Path to product image for analysis

**Returns:**
- `Dict[str, Any]`: Complete scene specification with:
  - `total_duration`: Total video length (30 seconds)
  - `style`: Selected style
  - `product_name`: Product name
  - `scenes`: List of 4 scene specifications
  - `hook`: Generated hook text
  - `cta`: Call-to-action text
  - `product_analysis`: Product analysis (if image provided)

**Raises:**
- `ScriptGenerationError`: If script generation fails
- `ValueError`: If style is invalid

#### `analyze_product_image(image_path, product_name, style)`

Analyze product image using Claude's vision API.

**Parameters:**
- `image_path` (str): Path to product image
- `product_name` (str): Name of the product
- `style` (str): Visual style

**Returns:**
- `Dict[str, Any]`: Product analysis with:
  - `product_description`: Detailed description
  - `key_benefits`: List of benefits
  - `target_audience`: Target audience description
  - `unique_selling_points`: List of USPs
  - `emotional_appeal`: Emotional appeal description

**Raises:**
- `ScriptGenerationError`: If analysis fails
- `FileNotFoundError`: If image doesn't exist

### `create_script_generator()`

Factory function to create a ScriptGenerator instance.

**Returns:**
- `ScriptGenerator`: Configured instance

**Raises:**
- `ValueError`: If ANTHROPIC_API_KEY is not configured

## Output Format

### Generated Script Structure

```json
{
  "total_duration": 30,
  "style": "luxury",
  "product_name": "Premium Headphones",
  "style_keywords": "soft lighting, elegant, premium, refined",
  "hook": "Discover the perfect sound experience...",
  "cta": "Shop Now and Elevate Your Audio",
  "scenes": [
    {
      "id": 1,
      "duration": 8,
      "type": "video",
      "video_prompt_template": "Close-up of Premium Headphones...",
      "use_product_image": true,
      "voiceover_text": "Discover Premium Headphones. Experience audio like never before.",
      "text_overlay": "Premium Headphones",
      "text_timing": "0.3s before voice",
      "text_style": "elegant serif, gold accent"
    },
    {
      "id": 2,
      "duration": 8,
      "type": "video",
      "voiceover_text": "Immerse yourself in crystal-clear sound...",
      ...
    },
    {
      "id": 3,
      "duration": 10,
      "type": "video",
      "voiceover_text": "Join thousands of music lovers...",
      ...
    },
    {
      "id": 4,
      "duration": 4,
      "type": "image",
      "voiceover_text": "Get yours today.",
      ...
    }
  ],
  "product_analysis": {
    "product_description": "Premium over-ear headphones with...",
    "key_benefits": [
      "Superior sound quality",
      "All-day comfort",
      "Premium materials"
    ],
    "target_audience": "Audiophiles and music enthusiasts",
    "unique_selling_points": [
      "Studio-grade audio",
      "Active noise cancellation"
    ],
    "emotional_appeal": "Luxury and immersion"
  }
}
```

## Testing

### Run Test Suite

```bash
cd backend/pipeline
python test_script_generator.py
```

Tests include:
- Script generation without image
- Script generation with image (if sample image available)
- All style variations
- API key validation

### Run Demos

```bash
cd backend/pipeline
python script_generator_demo.py
```

Demonstrates:
- Basic usage
- Image analysis
- All styles
- Error handling
- Saving to file

## Integration with Pipeline

The ScriptGenerator integrates with the video generation pipeline:

```python
# In your pipeline
from pipeline.script_generator import create_script_generator
from pipeline.templates import get_scene_template

# 1. Generate script
generator = create_script_generator()
script = generator.generate_script(
    product_name=job.product_name,
    style=job.style,
    cta_text=job.cta_text,
    product_image_path=job.product_image_path
)

# 2. Use script for downstream tasks
# - Voice generation: Use scene['voiceover_text']
# - Video generation: Use scene['video_prompt_template']
# - Compositing: Use scene['text_overlay'] and timing
```

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY`: Required. Your Anthropic API key

### Model Configuration

The module uses Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`). To change:

```python
generator = ScriptGenerator()
generator.model = "claude-3-5-sonnet-20250514"  # Use newer version
```

### Retry Configuration

```python
generator = ScriptGenerator()
generator.max_retries = 5  # Increase retries
generator.base_retry_delay = 2.0  # Longer initial delay
```

## Error Handling

### Common Errors

1. **Missing API Key**
   ```
   ValueError: ANTHROPIC_API_KEY not configured
   ```
   Solution: Set `ANTHROPIC_API_KEY` in `.env` file

2. **Rate Limiting**
   ```
   ScriptGenerationError: Failed after 3 retries: RateLimitError
   ```
   Solution: Module automatically retries with exponential backoff

3. **Invalid Image**
   ```
   FileNotFoundError: Image not found: ./product.jpg
   ```
   Solution: Verify image path exists

4. **Invalid Style**
   ```
   ValueError: Invalid style 'custom'. Available: luxury, energetic, minimal, bold
   ```
   Solution: Use one of the available styles

## Best Practices

1. **API Key Security**: Never commit API keys to version control
2. **Image Optimization**: Use compressed images to reduce API payload size
3. **Error Handling**: Always wrap calls in try-except blocks
4. **Logging**: Enable debug logging for troubleshooting:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```
5. **Cost Management**: Each script generation makes 2 API calls (1 for analysis, 1 for voiceovers). Monitor usage.

## Supported Image Formats

- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- GIF (`.gif`)
- WebP (`.webp`)

## Performance

- **Without Image**: ~3-5 seconds (1 API call)
- **With Image**: ~6-10 seconds (2 API calls)
- **Rate Limits**: Automatic retry with exponential backoff

## Cost Estimation

Approximate costs per script generation (Claude 3.5 Sonnet pricing):

- **Without Image**: ~$0.01-0.02
- **With Image**: ~$0.02-0.04

(Based on ~2K input tokens + ~1K output tokens)

## Changelog

### v1.0.0 (2024-11-14)
- Initial implementation
- Claude 3.5 Sonnet integration
- Vision API for product image analysis
- Template-based voiceover generation
- Exponential backoff retry logic
- Comprehensive error handling
- Test suite and demos

## License

Part of the Bad Apple Video Generator project.

## Support

For issues or questions:
1. Check the test suite: `python test_script_generator.py`
2. Review error logs
3. Verify API key configuration
4. Check Anthropic API status
