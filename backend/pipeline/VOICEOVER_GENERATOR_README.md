# Voiceover Generator

Professional text-to-speech generation using ElevenLabs API for Bad Apple Video Generator.

## Overview

The `VoiceoverGenerator` class provides high-quality text-to-speech capabilities for generating voiceovers for video scenes. It integrates seamlessly with the `ScriptGenerator` and `AssetManager` to create professional audio narration.

## Features

- **High-Quality TTS**: Uses ElevenLabs API for natural-sounding voices
- **Multiple Voices**: Different voice options for various styles
- **Duration Validation**: Ensures audio matches expected scene timing
- **Retry Logic**: Automatic retry with exponential backoff for API failures
- **Async Support**: Parallel generation for faster batch processing
- **Asset Management**: Integrates with AssetManager for organized file storage

## Installation

```bash
pip install elevenlabs pydub
```

Dependencies are automatically included in `requirements.txt`.

## Configuration

### Environment Variables

Add to `backend/.env`:

```bash
# ElevenLabs API Configuration
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL  # Optional, defaults to Sarah
```

### Voice Options

The generator includes pre-configured voice recommendations for different video styles:

| Style      | Voice ID                    | Voice Name | Characteristics           |
|------------|----------------------------|------------|---------------------------|
| `luxury`   | `EXAVITQu4vr4xnSDxMaL`     | Sarah      | Sophisticated, calm       |
| `energetic`| `ErXwobaYiN019PkySvjV`     | Antoni     | Upbeat, enthusiastic      |
| `minimal`  | `21m00Tcm4TlvDq8ikWAM`     | Rachel     | Clear, direct, neutral    |
| `bold`     | `pNInz6obpgDQGcFmaJgB`     | Adam       | Confident, powerful       |

## Usage

### Basic Usage

```python
from pipeline.voiceover_generator import create_voiceover_generator
from pipeline.asset_manager import AssetManager

# Create generator
generator = create_voiceover_generator()

# Create asset manager for file storage
am = AssetManager(job_id="job-123")
await am.create_job_directory()

# Generate single voiceover
audio_path = await generator.generate_voiceover(
    text="Introducing the future of innovation",
    asset_manager=am,
    target_duration=8.0,
    scene_number=1
)

print(f"Generated voiceover: {audio_path}")
# Output: /tmp/video_jobs/job-123/audio/scene_1_voiceover_1699123456.mp3
```

### Integration with Script Generator

```python
from pipeline.script_generator import create_script_generator
from pipeline.voiceover_generator import create_voiceover_generator
from pipeline.asset_manager import AssetManager

# Generate script
script_gen = create_script_generator()
script = script_gen.generate_script(
    product_name="Premium Headphones",
    style="luxury",
    cta_text="Shop Now",
    product_image_path="./product.jpg"
)

# Generate all voiceovers
am = AssetManager(job_id="job-123")
await am.create_job_directory()

voiceover_gen = create_voiceover_generator()
audio_paths = await voiceover_gen.generate_all_voiceovers(
    script=script,
    asset_manager=am,
    style="luxury"
)

print(f"Generated {len(audio_paths)} voiceovers")
# Output: Generated 4 voiceovers

for i, path in enumerate(audio_paths, 1):
    print(f"Scene {i}: {path}")
# Output:
# Scene 1: /tmp/video_jobs/job-123/audio/scene_1_voiceover_1699123456.mp3
# Scene 2: /tmp/video_jobs/job-123/audio/scene_2_voiceover_1699123457.mp3
# Scene 3: /tmp/video_jobs/job-123/audio/scene_3_voiceover_1699123458.mp3
# Scene 4: /tmp/video_jobs/job-123/audio/scene_4_voiceover_1699123459.mp3
```

### Custom Voice Selection

```python
# Use a specific voice
audio_path = await generator.generate_voiceover(
    text="Bold and powerful message",
    asset_manager=am,
    voice_id="pNInz6obpgDQGcFmaJgB",  # Adam voice
    scene_number=1
)

# Or let the generator select based on style
voice_id = generator.get_voice_for_style("energetic")
audio_path = await generator.generate_voiceover(
    text="Exciting announcement!",
    asset_manager=am,
    voice_id=voice_id,
    scene_number=2
)
```

### Duration Validation

```python
# Generate with duration validation
audio_path = await generator.generate_voiceover(
    text="This should be about 5 seconds long",
    asset_manager=am,
    target_duration=5.0,
    tolerance=0.5,  # Allow ±0.5 seconds
    scene_number=1
)

# Get actual audio duration
duration = await generator.get_audio_duration(audio_path)
print(f"Actual duration: {duration:.2f}s")
```

### Error Handling

```python
from pipeline.voiceover_generator import VoiceoverGenerationError

try:
    audio_path = await generator.generate_voiceover(
        text="Generate this audio",
        asset_manager=am,
        scene_number=1
    )
except VoiceoverGenerationError as e:
    print(f"Failed to generate voiceover: {e}")
    # Handle error (retry, use fallback, etc.)
```

## API Reference

### VoiceoverGenerator

#### Constructor

```python
VoiceoverGenerator(api_key: Optional[str] = None, voice_id: Optional[str] = None)
```

**Parameters:**
- `api_key`: ElevenLabs API key (defaults to `settings.ELEVENLABS_API_KEY`)
- `voice_id`: Voice ID to use (defaults to `settings.ELEVENLABS_VOICE_ID`)

**Raises:**
- `ValueError`: If API key is not provided

#### Methods

##### `generate_voiceover()`

Generate TTS audio from text.

```python
async def generate_voiceover(
    text: str,
    asset_manager: AssetManager,
    target_duration: Optional[float] = None,
    voice_id: Optional[str] = None,
    scene_number: Optional[int] = None,
    tolerance: float = 0.5
) -> str
```

**Parameters:**
- `text`: Text to convert to speech
- `asset_manager`: AssetManager instance for saving files
- `target_duration`: Expected duration in seconds (optional)
- `voice_id`: Voice ID to use (defaults to instance default)
- `scene_number`: Scene number for filename (optional)
- `tolerance`: Duration tolerance in seconds (default: 0.5)

**Returns:** Absolute path to generated MP3 file

**Raises:** `VoiceoverGenerationError` if generation fails

##### `generate_all_voiceovers()`

Generate voiceovers for all scenes in a script.

```python
async def generate_all_voiceovers(
    script: Dict[str, Any],
    asset_manager: AssetManager,
    style: Optional[str] = None
) -> List[str]
```

**Parameters:**
- `script`: Script dictionary from ScriptGenerator
- `asset_manager`: AssetManager instance for saving files
- `style`: Optional style to select appropriate voice

**Returns:** List of audio file paths in scene order

**Raises:** `VoiceoverGenerationError` if generation fails

##### `get_voice_for_style()`

Get recommended voice ID for a given style.

```python
def get_voice_for_style(style: str) -> str
```

**Parameters:**
- `style`: Visual style (luxury, energetic, minimal, bold)

**Returns:** Voice ID string

##### `get_audio_duration()`

Get duration of audio file in seconds.

```python
async def get_audio_duration(audio_path: str) -> float
```

**Parameters:**
- `audio_path`: Path to audio file

**Returns:** Duration in seconds

### Factory Function

```python
def create_voiceover_generator(
    api_key: Optional[str] = None,
    voice_id: Optional[str] = None
) -> VoiceoverGenerator
```

Creates a configured VoiceoverGenerator instance.

## Architecture

### Retry Logic

The generator includes exponential backoff retry logic for API failures:

- **Attempt 1**: Immediate
- **Attempt 2**: 1 second delay
- **Attempt 3**: 2 second delay

Rate limit errors (429) are automatically retried. Client errors (4xx) except rate limits are not retried.

### Duration Validation

Duration validation uses `pydub` to:
1. Load the generated MP3 file
2. Get actual duration in seconds
3. Compare to target duration
4. Check if within tolerance range

### File Storage

Generated audio files are stored through AssetManager:
- Directory: `/tmp/video_jobs/{job_id}/audio/`
- Filename format: `scene_{N}_voiceover_{timestamp}.mp3`
- Format: MP3 at 44.1kHz, 128kbps

## Testing

### Run Unit Tests

```bash
cd backend
pytest pipeline/test_voiceover_generator.py -v
```

### Run Integration Tests

Integration tests require a real ElevenLabs API key:

```bash
# Set API key in .env first
pytest pipeline/test_voiceover_generator.py --elevenlabs -v
```

**Note**: Integration tests use minimal text to reduce API costs.

### Test Coverage

Tests cover:
- ✅ Initialization with/without API key
- ✅ Voice selection for all styles
- ✅ Single voiceover generation
- ✅ Batch voiceover generation
- ✅ Duration validation
- ✅ Error handling
- ✅ Retry logic
- ✅ Factory function

## Performance

### Timing

| Operation | Approximate Time |
|-----------|-----------------|
| Single voiceover (8s audio) | 2-4 seconds |
| Batch generation (4 scenes) | 5-10 seconds (parallel) |

### Parallel Processing

`generate_all_voiceovers()` uses `asyncio.gather()` to generate all scene voiceovers in parallel, significantly reducing total generation time.

## Error Handling

### Common Errors

1. **Missing API Key**
   ```python
   ValueError: ELEVENLABS_API_KEY not configured
   ```
   **Solution**: Set `ELEVENLABS_API_KEY` in `.env`

2. **Rate Limit**
   ```
   Rate limit hit (attempt 1/3). Retrying in 1s...
   ```
   **Solution**: Automatic retry with backoff

3. **Invalid Voice ID**
   ```
   VoiceoverGenerationError: ElevenLabs API error: Voice not found
   ```
   **Solution**: Use a valid voice ID from ElevenLabs

4. **Duration Mismatch**
   ```
   Duration validation failed: 10.5s (target: 8.0s, diff: 2.5s)
   ```
   **Solution**: This is a warning, not an error. Adjust text length or tolerance.

## Best Practices

### 1. Voice Selection

Choose voices that match your video style:
- **Luxury products**: Use Sarah (default) for sophisticated tone
- **Fitness/energy drinks**: Use Antoni for upbeat delivery
- **Tech/minimal**: Use Rachel for clear, direct communication
- **Bold statements**: Use Adam for confident messaging

### 2. Text Length

For target durations:
- **8 seconds**: ~20-25 words
- **10 seconds**: ~25-30 words
- **4 seconds**: ~10-12 words

### 3. Duration Tolerance

Set appropriate tolerance based on use case:
- **Strict timing**: `tolerance=0.3` (±0.3s)
- **Normal**: `tolerance=0.5` (±0.5s) - default
- **Flexible**: `tolerance=1.0` (±1.0s)

### 4. Error Recovery

Always wrap generation in try-except:
```python
try:
    audio_paths = await generator.generate_all_voiceovers(script, am)
except VoiceoverGenerationError as e:
    logger.error(f"Voiceover generation failed: {e}")
    # Implement fallback or retry logic
```

### 5. Resource Cleanup

AssetManager handles cleanup, but ensure it's called:
```python
try:
    audio_paths = await generator.generate_all_voiceovers(script, am)
    # Use audio files
finally:
    await am.cleanup()  # Clean up temporary files
```

## Limitations

- **API Dependency**: Requires active internet connection and ElevenLabs API access
- **Cost**: ElevenLabs API has usage-based pricing
- **Character Limits**: ElevenLabs has character limits per request
- **Voice Availability**: Pre-made voices may change; use custom voices for production

## Future Enhancements

Potential improvements:
- [ ] Custom voice cloning support
- [ ] SSML (Speech Synthesis Markup Language) support for better control
- [ ] Multiple language support
- [ ] Voice emotion/tone customization
- [ ] Caching for repeated text
- [ ] Background music mixing
- [ ] Real-time streaming support

## Support

For issues or questions:
1. Check ElevenLabs API status: https://status.elevenlabs.io/
2. Review logs for detailed error messages
3. Verify API key and quota
4. Test with minimal text first

## References

- [ElevenLabs API Documentation](https://elevenlabs.io/docs)
- [ElevenLabs Python SDK](https://github.com/elevenlabs/elevenlabs-python)
- [Voice Library](https://elevenlabs.io/voice-library)
- [pydub Documentation](https://github.com/jiaaro/pydub)
