# Testing Scripts

This directory contains testing and debugging scripts for the backend.

## Audio Overlay Testing

### Quick Test (Automatic)

Finds available videos and audio, then tests stitching:

```bash
cd backend
uv run python ../.devdocs/scripts/test_audio_overlay.py
```

This script will:
1. Find 1-2 existing video files
2. Find 1 existing audio file
3. Test stitching WITHOUT audio (baseline)
4. Test stitching WITH audio overlay
5. Verify the output has an audio stream

### Debug Test (Manual)

For detailed debugging with specific file IDs:

```bash
cd backend
uv run python ../.devdocs/scripts/debug_audio_overlay.py <video_id1> <video_id2> <audio_id>
```

Example:
```bash
uv run python ../.devdocs/scripts/debug_audio_overlay.py \
  abc-123-video1 \
  def-456-video2 \
  xyz-789-audio
```

This script will:
1. Verify all input files exist
2. Show detailed file information (duration, size)
3. Test moviepy AudioFileClip loading
4. Run stitch_videos() with debug mode enabled
5. Inspect the output for audio stream
6. Print comprehensive debugging information

### Finding File IDs

**List video IDs:**
```bash
# Job-based videos
ls backend/mv/outputs/jobs/

# Legacy videos
ls backend/mv/outputs/videos/*.mp4 | xargs -n1 basename | sed 's/.mp4//'
```

**List audio IDs:**
```bash
ls backend/mv/outputs/audio/*.mp3 | grep -v metadata | xargs -n1 basename | sed 's/.mp3//'
```

### Inspecting Output

**Check if video has audio:**
```bash
ffprobe -v error -select_streams a:0 -show_entries stream=codec_type -of default=noprint_wrappers=1:nokey=1 path/to/video.mp4
# Should output: audio
```

**Play video:**
```bash
ffplay path/to/video.mp4
```

**Full video info:**
```bash
ffprobe path/to/video.mp4
```

## Common Issues & Fixes

### Issue: "No audio stream in output"

**Possible causes:**
1. ❌ Wrong moviepy method name (`subclipped` vs `with_subclip`)
2. ❌ Wrong audio application method (`with_audio` vs `set_audio`)
3. ❌ Audio clip not properly loaded
4. ❌ Exception caught silently in audio overlay logic

**Check:**
- Run debug script to see detailed logs
- Check `MV_DEBUG_MODE=true` logs
- Verify audio file exists and is valid
- Test moviepy AudioFileClip loading separately

### Issue: "Audio file not found"

**Fix:**
```bash
# Download test audio
curl -X POST http://localhost:8000/api/audio/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### Issue: "Video files not found"

**Fix:**
```bash
# Generate test video
curl -X POST http://localhost:8000/api/mv/generate_video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A beautiful sunset over mountains"}'
```

## Manual Testing Checklist

- [ ] Test with 1 video + audio
- [ ] Test with 2+ videos + audio
- [ ] Test with audio longer than video (should trim)
- [ ] Test with audio shorter than video (should use as-is)
- [ ] Test without audio (backward compatibility)
- [ ] Test with missing audio file (should warn but succeed)
- [ ] Test with suppress_video_audio=false (keep original audio)
- [ ] Test with suppress_video_audio=true (overlay only)
- [ ] Verify output video plays correctly
- [ ] Verify audio quality is maintained
