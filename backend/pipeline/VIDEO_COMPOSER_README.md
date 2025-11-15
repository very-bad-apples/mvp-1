# Video Composer - Documentation

## Overview

The `VideoComposer` class is the final step in the video generation pipeline. It assembles all generated assets (video scenes, voiceovers, CTA image, and optional background music) into a single, polished 9:16 vertical video optimized for social media platforms.

## Architecture

### Components

```
VideoComposer
├── Audio-Video Synchronization
│   ├── Load video and audio clips
│   ├── Match durations (trim or extend)
│   └── Sync audio tracks
├── Transitions
│   ├── Fade in/out between scenes
│   └── Smooth visual flow
├── CTA Integration
│   ├── Convert static image to video clip
│   ├── Add fade-in effect
│   └── Append as final scene
├── Background Music (Optional)
│   ├── Loop to match video duration
│   ├── Mix with voiceover at low volume
│   └── Create composite audio track
├── Aspect Ratio Enforcement
│   ├── Ensure 9:16 format (1080x1920)
│   ├── Resize clips as needed
│   └── Maintain consistency
└── Export
    ├── H.264 codec (libx264)
    ├── AAC audio codec
    ├── Optimized bitrate (5 Mbps video, 192k audio)
    └── Social media-ready MP4
```

## Dependencies

### Required

- **MoviePy** (2.2.1+): Core video editing library
  - `VideoFileClip`: Load video files
  - `AudioFileClip`: Load audio files
  - `ImageClip`: Create video from static images
  - `concatenate_videoclips`: Join clips
  - `CompositeAudioClip`: Mix audio tracks
  - Video effects (fadein, fadeout)

- **FFmpeg**: Required by MoviePy for encoding/decoding
  - Install: `brew install ffmpeg` (macOS)
  - Install: `apt-get install ffmpeg` (Ubuntu)
  - Verify: `ffmpeg -version`

### Optional

- **AssetManager**: For file path management and cleanup
- **structlog**: For structured logging

## Installation

```bash
# Install MoviePy
pip install moviepy==2.2.1

# Ensure FFmpeg is installed
ffmpeg -version

# If FFmpeg not installed (macOS)
brew install ffmpeg

# If FFmpeg not installed (Ubuntu)
sudo apt-get install ffmpeg
```

## Usage

### Basic Usage

```python
from pipeline.video_composer import VideoComposer, create_video_composer
from pipeline.asset_manager import AssetManager

# Initialize
am = AssetManager(job_id="job-123")
await am.create_job_directory()

composer = create_video_composer(asset_manager=am)

# Compose video
final_video = await composer.compose_video(
    video_scenes=[
        "/path/to/scene_1.mp4",
        "/path/to/scene_2.mp4",
        "/path/to/scene_3.mp4",
        "/path/to/scene_4.mp4"
    ],
    voiceovers=[
        "/path/to/scene_1_voiceover.mp3",
        "/path/to/scene_2_voiceover.mp3",
        "/path/to/scene_3_voiceover.mp3",
        "/path/to/scene_4_voiceover.mp3"
    ],
    cta_image_path="/path/to/cta_final.png",
    output_path="/path/to/final_video.mp4"
)

print(f"Video created: {final_video}")
```

### With Background Music

```python
final_video = await composer.compose_video(
    video_scenes=video_scenes,
    voiceovers=voiceovers,
    cta_image_path=cta_image,
    background_music_path="/path/to/background_music.mp3",
    background_music_volume=0.1  # 10% volume, subtle background
)
```

### Custom Transition Duration

```python
final_video = await composer.compose_video(
    video_scenes=video_scenes,
    voiceovers=voiceovers,
    cta_image_path=cta_image,
    transition_duration=0.8,  # Longer fades (default: 0.5s)
    cta_duration=5.0  # Display CTA for 5 seconds (default: 4.0s)
)
```

### Full Pipeline Integration

```python
from pipeline.script_generator import ScriptGenerator
from pipeline.voiceover_generator import VoiceoverGenerator
from pipeline.video_generator import VideoGenerator
from pipeline.cta_generator import CTAGenerator
from pipeline.video_composer import VideoComposer
from pipeline.asset_manager import AssetManager

async def generate_complete_video(product_data: dict, job_id: str):
    """Complete video generation pipeline."""

    # 1. Setup
    am = AssetManager(job_id=job_id)
    await am.create_job_directory()

    # 2. Generate script
    script_gen = ScriptGenerator()
    script = script_gen.generate_script(product_data, style="luxury")

    # 3. Generate voiceovers
    vo_gen = VoiceoverGenerator()
    voiceovers = await vo_gen.generate_all_voiceovers(
        script=script,
        asset_manager=am,
        style="luxury"
    )

    # 4. Generate video scenes
    from services.replicate_client import get_replicate_client
    video_gen = VideoGenerator(get_replicate_client())
    video_scenes = await video_gen.generate_all_scenes(
        script=script,
        style="luxury",
        asset_manager=am
    )

    # 5. Generate CTA
    cta_gen = CTAGenerator()
    cta_image = await cta_gen.generate_cta(
        script=script,
        asset_manager=am,
        style="luxury"
    )

    # 6. Compose final video
    composer = VideoComposer(asset_manager=am)
    final_video = await composer.compose_video(
        video_scenes=video_scenes,
        voiceovers=voiceovers,
        cta_image_path=cta_image
    )

    return final_video
```

## API Reference

### VideoComposer Class

#### `__init__(asset_manager: Optional[AssetManager] = None)`

Initialize VideoComposer.

**Parameters:**
- `asset_manager`: Optional AssetManager for file operations

#### `async compose_video(...) -> str`

Compose final video from all assets.

**Parameters:**
- `video_scenes: List[str]` - Paths to video scene files (MP4)
- `voiceovers: List[str]` - Paths to voiceover files (MP3)
- `cta_image_path: str` - Path to CTA image (PNG)
- `background_music_path: Optional[str]` - Optional background music path
- `output_path: Optional[str]` - Optional custom output path
- `transition_duration: float` - Fade transition duration (default: 0.5s)
- `cta_duration: float` - CTA display duration (default: 4.0s)
- `background_music_volume: float` - BGM volume level (default: 0.1)

**Returns:**
- `str`: Path to final composed video

**Raises:**
- `VideoCompositionError`: If composition fails

### Internal Methods

#### `_sync_audio_to_video(video_path: str, audio_path: str) -> VideoFileClip`

Synchronize voiceover audio with video clip.

**Strategy:**
- Video shorter than audio → Extend with freeze frame
- Video longer than audio → Trim to audio duration
- Set synced audio track

#### `_add_transitions(clips: List[VideoFileClip], transition_duration: float) -> List[VideoFileClip]`

Add fade in/out transitions between clips.

#### `_create_cta_scene(cta_image_path: str, duration: float) -> ImageClip`

Create video clip from static CTA image with proper aspect ratio.

#### `_add_background_music(video_clip: VideoFileClip, music_path: str, volume: float) -> VideoFileClip`

Mix background music with video audio.

#### `_ensure_aspect_ratio(video_clip: VideoFileClip) -> VideoFileClip`

Ensure 9:16 aspect ratio (1080x1920).

#### `_export_video(video_clip: VideoFileClip, output_path: str, ...) -> str`

Export final video with optimized settings.

## Export Settings

### Default Configuration

```python
default_settings = {
    "fps": 30,                      # Frames per second
    "codec": "libx264",             # H.264 video codec
    "audio_codec": "aac",           # AAC audio codec
    "preset": "medium",             # Encoding speed/quality balance
    "bitrate": "5000k",             # 5 Mbps video bitrate
    "audio_bitrate": "192k",        # 192 kbps audio bitrate
    "target_resolution": (1080, 1920),  # 9:16 vertical (width, height)
}
```

### Platform Recommendations

**Instagram Reels:**
- Resolution: 1080x1920 ✓ (default)
- Max duration: 90s
- Aspect ratio: 9:16 ✓ (default)

**TikTok:**
- Resolution: 1080x1920 ✓ (default)
- Max duration: 10 minutes
- Aspect ratio: 9:16 ✓ (default)

**YouTube Shorts:**
- Resolution: 1080x1920 ✓ (default)
- Max duration: 60s
- Aspect ratio: 9:16 ✓ (default)

## Performance Metrics

### Typical Processing Times

| Scenario | Duration | Processing Time |
|----------|----------|-----------------|
| 4 scenes, no music | 20-30s | 30-45s |
| 4 scenes + music | 20-30s | 35-50s |
| 6 scenes, no music | 30-40s | 45-60s |
| 6 scenes + music | 30-40s | 50-70s |

**Note:** Processing time depends on:
- Scene count and duration
- CPU cores (uses 4 threads)
- Disk I/O speed
- System memory

### Memory Usage

- **Baseline**: ~200 MB
- **Per scene**: +50-100 MB
- **Background music**: +20-50 MB
- **Peak usage**: 500 MB - 1 GB (4-6 scenes)

**Recommendation:** Monitor memory for large-scale deployments.

## Audio-Video Synchronization

### Duration Matching Strategies

#### 1. Video Shorter Than Audio
```
Video: [====] 3s
Audio: [========] 5s

Result: [====][XX] 5s  (X = freeze frame)
```
- Extracts last frame of video
- Creates static ImageClip for remaining duration
- Concatenates original video + freeze frame
- Maintains audio quality

#### 2. Video Longer Than Audio
```
Video: [========] 5s
Audio: [====] 3s

Result: [====] 3s (trimmed)
```
- Trims video to match audio duration
- Uses `subclip(0, audio_duration)`
- No quality loss

#### 3. Matching Durations
```
Video: [====] 4s
Audio: [====] 4s

Result: [====] 4s (no modification)
```
- No adjustment needed
- Direct audio attachment

## Transitions

### Fade Effects

**Fade In:**
- Applied to all clips except the first
- Duration: Configurable (default 0.5s)
- Effect: Opacity 0 → 1

**Fade Out:**
- Applied to all clips except the last
- Duration: Configurable (default 0.5s)
- Effect: Opacity 1 → 0

**Overlap:**
- Transitions create smooth blending
- No jarring cuts between scenes
- Professional appearance

### CTA Fade In

The CTA image gets a special fade-in effect:
```python
cta_clip = fadein(cta_clip, duration=0.5)
```
- Creates elegant entrance
- Draws attention to call-to-action
- 0.5s fade duration

## Background Music Integration

### Music Looping

If music is shorter than video:
```python
# Music: 15s, Video: 30s
# Result: Music loops twice to cover 30s
```

Process:
1. Load music file
2. Calculate loops needed: `ceil(video_duration / music_duration)`
3. Concatenate music clips
4. Trim to exact video duration

### Volume Mixing

Default volume: 10% (0.1)
```python
music = music.volumex(0.1)  # Reduce to 10%
```

**Rationale:**
- Background music should not overpower voiceover
- Subtle enhancement of mood
- Professional mixing standards

### Audio Compositing

```python
CompositeAudioClip([voiceover_audio, background_music])
```

- Mixes both tracks
- Maintains voiceover clarity
- Adds atmospheric depth

## Error Handling

### Common Errors

#### 1. Mismatched Scene/Voiceover Counts
```python
VideoCompositionError: Mismatch: 4 video scenes but 3 voiceovers
```
**Solution:** Ensure equal number of scenes and voiceovers

#### 2. Missing FFmpeg
```
FileNotFoundError: FFmpeg not found
```
**Solution:** Install FFmpeg (`brew install ffmpeg`)

#### 3. Invalid Video File
```
VideoCompositionError: Failed to load video scene1.mp4
```
**Solution:** Verify file exists and is valid MP4

#### 4. Export Failure
```
VideoCompositionError: Export failed: file not created
```
**Solution:** Check disk space and write permissions

### Non-Critical Errors

Background music failures are non-critical:
```python
# If music fails, composition continues without it
try:
    add_background_music(...)
except Exception:
    logger.warning("Music failed, continuing without")
    return original_clip  # No music, but video still created
```

## Testing

### Run Tests

```bash
# Run all tests
pytest backend/pipeline/test_video_composer.py

# Run specific test
pytest backend/pipeline/test_video_composer.py::TestVideoComposer::test_sync_audio_to_video_extend

# Run with coverage
pytest --cov=pipeline.video_composer backend/pipeline/test_video_composer.py
```

### Test Coverage

Tests cover:
- ✅ Audio-video synchronization (extend/trim)
- ✅ Transition effects
- ✅ CTA scene creation
- ✅ Background music mixing
- ✅ Aspect ratio enforcement
- ✅ Export settings
- ✅ Error handling
- ✅ Edge cases (empty lists, single clips, failures)

## Troubleshooting

### Issue: Video export is slow

**Cause:** High bitrate or slow encoding preset

**Solution:**
```python
composer._export_video(
    clip,
    output_path,
    preset="fast",  # Faster encoding (default: medium)
    bitrate="3000k"  # Lower bitrate (default: 5000k)
)
```

### Issue: Audio out of sync

**Cause:** Frame rate mismatch

**Solution:**
- Ensure all input videos have same FPS
- Check voiceover durations match scene durations
- Validate audio files are not corrupted

### Issue: Memory errors with many scenes

**Cause:** Too many clips loaded simultaneously

**Solution:**
```python
# Process in batches if needed
# Or increase system memory allocation
```

### Issue: CTA image appears stretched

**Cause:** Image aspect ratio doesn't match 9:16

**Solution:**
- Create CTA image at 1080x1920 resolution
- Or allow VideoComposer to resize (may crop/pad)

## Best Practices

### 1. Input File Quality
- Use high-quality source videos (1080p minimum)
- Use clear audio recordings (MP3 192kbps+)
- Use high-resolution CTA images (1080x1920)

### 2. Duration Planning
- Keep total video under 60s for YouTube Shorts
- Keep under 90s for Instagram Reels
- Aim for 4-6 scenes of 5-8 seconds each

### 3. Transition Tuning
- Use 0.5s transitions for fast-paced content
- Use 0.8-1.0s transitions for luxury/calm content
- Match transition style to brand personality

### 4. Background Music
- Choose music that matches brand style
- Keep volume at 5-15% (0.05-0.15)
- Ensure music license allows commercial use

### 5. Error Handling
- Always wrap composition in try/except
- Implement cleanup on failure
- Log errors for debugging

### 6. Resource Management
```python
# Clean up after composition
await asset_manager.cleanup()

# Or keep files for debugging
# (don't call cleanup)
```

## Future Enhancements

Potential improvements for future versions:

1. **Advanced Transitions**
   - Crossfade between clips
   - Custom transition effects (wipe, dissolve)
   - Transition library

2. **Text Overlays**
   - Animated text annotations
   - Subtitle support
   - Product name overlays

3. **Color Grading**
   - Apply LUTs (Look-Up Tables)
   - Consistent color palette
   - Style-specific color grading

4. **Smart Audio Ducking**
   - Automatically reduce music during voiceover
   - Intelligent volume balancing
   - Audio normalization

5. **Batch Processing**
   - Generate multiple variations
   - A/B testing support
   - Parallel composition

6. **Optimized Encoding**
   - GPU-accelerated encoding
   - Adaptive bitrate
   - Format-specific optimization

## License

Part of the Bad Apple Video Generator project.

## Support

For issues or questions:
1. Check this documentation
2. Review test files for examples
3. Check MoviePy documentation: https://zulko.github.io/moviepy/
4. File an issue in the project repository
