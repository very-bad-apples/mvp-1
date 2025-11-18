#!/usr/bin/env python3
"""
Simple debug script for audio overlay issues.

This script provides detailed debugging information about the audio overlay process.

Usage:
    cd backend
    uv run python ../.devdocs/scripts/debug_audio_overlay.py <video_id1> <video_id2> <audio_id>

Example:
    uv run python ../.devdocs/scripts/debug_audio_overlay.py abc-123 def-456 xyz-789
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

def main():
    if len(sys.argv) < 4:
        print("Usage: uv run python debug_audio_overlay.py <video_id1> <video_id2> <audio_id>")
        print()
        print("To list available files:")
        print("  Videos: ls backend/mv/outputs/jobs/")
        print("  Audio:  ls backend/mv/outputs/audio/*.mp3")
        return 1

    video_ids = [sys.argv[1], sys.argv[2]] if len(sys.argv) > 2 else [sys.argv[1]]
    audio_id = sys.argv[3] if len(sys.argv) > 3 else sys.argv[2]

    print("=" * 80)
    print("AUDIO OVERLAY DEBUG SCRIPT")
    print("=" * 80)
    print()

    # Enable debug mode
    from config import settings
    original_debug = settings.MV_DEBUG_MODE
    settings.MV_DEBUG_MODE = True
    print(f"✓ Debug mode enabled: {settings.MV_DEBUG_MODE}")
    print()

    # Import after setting debug mode
    from mv.video_stitcher import stitch_videos, _get_audio_file_path
    from moviepy import VideoFileClip, AudioFileClip
    from pydub import AudioSegment

    # Step 1: Verify inputs
    print("Step 1: Verifying inputs...")
    print("-" * 80)

    for i, vid in enumerate(video_ids, 1):
        video_dir = backend_dir / "mv" / "outputs" / "jobs" / vid
        video_file = video_dir / "video.mp4"
        if video_file.exists():
            print(f"✓ Video {i}: {vid}")
            print(f"  Path: {video_file}")
            try:
                clip = VideoFileClip(str(video_file))
                print(f"  Duration: {clip.duration:.2f}s")
                print(f"  Has audio: {clip.audio is not None}")
                clip.close()
            except Exception as e:
                print(f"  ❌ Error loading: {e}")
        else:
            print(f"❌ Video {i} not found: {vid}")
            return 1

    print()

    # Check audio
    audio_path = _get_audio_file_path(audio_id)
    if audio_path:
        print(f"✓ Audio: {audio_id}")
        print(f"  Path: {audio_path}")
        try:
            audio = AudioSegment.from_file(str(audio_path))
            duration = len(audio) / 1000.0
            print(f"  Duration: {duration:.2f}s")
            print(f"  Size: {audio_path.stat().st_size / 1024 / 1024:.2f} MB")
        except Exception as e:
            print(f"  ❌ Error loading: {e}")
    else:
        print(f"❌ Audio not found: {audio_id}")
        return 1

    print()
    print("=" * 80)

    # Step 2: Test audio clip loading with moviepy
    print("Step 2: Testing moviepy AudioFileClip...")
    print("-" * 80)
    try:
        audio_clip = AudioFileClip(str(audio_path))
        print(f"✓ AudioFileClip loaded successfully")
        print(f"  Duration: {audio_clip.duration:.2f}s")
        print(f"  FPS: {audio_clip.fps}")
        print(f"  Has data: {audio_clip.reader is not None}")
        audio_clip.close()
    except Exception as e:
        print(f"❌ Failed to load audio with moviepy: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print()
    print("=" * 80)

    # Step 3: Run stitch with audio overlay
    print("Step 3: Running stitch_videos with audio overlay...")
    print("-" * 80)
    print(f"Parameters:")
    print(f"  video_ids: {video_ids}")
    print(f"  audio_overlay_id: {audio_id}")
    print(f"  suppress_video_audio: True")
    print()

    try:
        video_id, video_path, video_url, metadata, audio_applied, audio_warning = stitch_videos(
            video_ids=video_ids,
            audio_overlay_id=audio_id,
            suppress_video_audio=True
        )

        print()
        print(f"✓ Stitch completed!")
        print(f"  Video ID: {video_id}")
        print(f"  Video Path: {video_path}")
        print(f"  Audio Applied: {audio_applied}")
        print(f"  Audio Warning: {audio_warning or 'None'}")
        print()

        # Step 4: Inspect output
        print("=" * 80)
        print("Step 4: Inspecting output video...")
        print("-" * 80)

        if Path(video_path).exists():
            print(f"✓ Output file exists")
            print(f"  Path: {video_path}")
            print(f"  Size: {Path(video_path).stat().st_size / 1024 / 1024:.2f} MB")

            try:
                output_clip = VideoFileClip(video_path)
                print(f"  Duration: {output_clip.duration:.2f}s")
                print(f"  Has audio: {output_clip.audio is not None}")

                if output_clip.audio:
                    print(f"  Audio FPS: {output_clip.audio.fps}")
                    print(f"  Audio Duration: {output_clip.audio.duration:.2f}s")
                    print()
                    print("✅ SUCCESS: Output video has audio!")
                else:
                    print()
                    print("❌ FAILURE: Output video has NO audio!")
                    print()
                    print("Debugging hints:")
                    print("  1. Check if audio_overlay_path was set correctly")
                    print("  2. Check if final_clip.set_audio() was called")
                    print("  3. Check moviepy logs above for errors")
                    print("  4. Try: ffprobe -v error -show_entries stream=codec_type output.mp4")

                output_clip.close()

            except Exception as e:
                print(f"❌ Error inspecting output: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"❌ Output file not found: {video_path}")

        print()
        print("=" * 80)
        print("Metadata:")
        print("-" * 80)
        for key, value in sorted(metadata.items()):
            print(f"  {key}: {value}")

        print()
        print("=" * 80)
        print(f"To play: ffplay '{video_path}'")
        print(f"To inspect: ffprobe '{video_path}'")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Stitch failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Restore debug mode
        settings.MV_DEBUG_MODE = original_debug

    return 0


if __name__ == "__main__":
    sys.exit(main())
