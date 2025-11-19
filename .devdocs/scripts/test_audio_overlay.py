#!/usr/bin/env python3
"""
Test script for video stitching with audio overlay.

This script tests the audio overlay functionality by:
1. Finding existing video files in the outputs directory
2. Finding an existing audio file
3. Calling stitch_videos() with audio overlay parameters
4. Verifying the output has audio

Usage:
    cd backend
    uv run python ../.devdocs/scripts/test_audio_overlay.py

Requirements:
    - At least 1-2 video files in backend/mv/outputs/videos/ or backend/mv/outputs/jobs/
    - At least 1 audio file in backend/mv/outputs/audio/
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

os.chdir(backend_dir)

from mv.video_stitcher import stitch_videos
from config import settings
import subprocess


def find_video_files(limit=2):
    """Find existing video files in the outputs directory."""
    video_ids = []

    # Check jobs directory
    jobs_dir = backend_dir / "mv" / "outputs" / "jobs"
    if jobs_dir.exists():
        for job_dir in jobs_dir.iterdir():
            if job_dir.is_dir():
                video_file = job_dir / "video.mp4"
                if video_file.exists():
                    video_ids.append(job_dir.name)
                    print(f"✓ Found video: {job_dir.name}")
                    if len(video_ids) >= limit:
                        break

    # Check legacy videos directory if needed
    if len(video_ids) < limit:
        videos_dir = backend_dir / "mv" / "outputs" / "videos"
        if videos_dir.exists():
            for video_file in videos_dir.glob("*.mp4"):
                video_id = video_file.stem
                if video_id not in video_ids:
                    video_ids.append(video_id)
                    print(f"✓ Found video: {video_id}")
                    if len(video_ids) >= limit:
                        break

    return video_ids


def find_audio_file():
    """Find an existing audio file in the outputs directory."""
    audio_dir = backend_dir / "mv" / "outputs" / "audio"
    if not audio_dir.exists():
        return None

    # Look for MP3 files
    for audio_file in audio_dir.glob("*.mp3"):
        # Skip metadata and trimmed files
        if "_metadata" not in audio_file.name:
            audio_id = audio_file.stem
            print(f"✓ Found audio: {audio_id}")
            return audio_id

    return None


def check_video_has_audio(video_path):
    """Check if a video file has an audio stream using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path)
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        return result.stdout.strip() == "audio"
    except Exception as e:
        print(f"⚠ Could not check audio stream: {e}")
        return None


def main():
    print("=" * 60)
    print("Testing Audio Overlay in Video Stitching")
    print("=" * 60)
    print()

    # Find test files
    print("Step 1: Finding test files...")
    print("-" * 60)

    video_ids = find_video_files(limit=2)
    if not video_ids:
        print("❌ ERROR: No video files found!")
        print("   Please generate some videos first using /api/mv/generate_video")
        return 1

    if len(video_ids) < 2:
        print(f"⚠ WARNING: Only found {len(video_ids)} video(s). Will stitch with what's available.")

    audio_id = find_audio_file()
    if not audio_id:
        print("❌ ERROR: No audio files found!")
        print("   Please download audio using /api/audio/download")
        return 1

    print()
    print(f"✅ Found {len(video_ids)} video(s) and 1 audio file")
    print()

    # Test 1: Stitch WITHOUT audio overlay (baseline)
    print("=" * 60)
    print("Test 1: Stitching WITHOUT audio overlay (baseline)")
    print("=" * 60)
    print()

    try:
        print(f"Stitching videos: {video_ids}")

        video_id, video_path, video_url, metadata, audio_applied, audio_warning = stitch_videos(
            video_ids=video_ids,
            audio_overlay_id=None,
            suppress_video_audio=False
        )

        print(f"✅ Stitch completed (no audio overlay)")
        print(f"   Video ID: {video_id}")
        print(f"   Video Path: {video_path}")
        print(f"   Duration: {metadata.get('video_duration_seconds')}s")
        print(f"   Audio Overlay Applied: {audio_applied}")

        # Check if baseline has audio
        has_audio = check_video_has_audio(video_path)
        if has_audio is not None:
            print(f"   Has Audio Stream: {has_audio}")

        print()

    except Exception as e:
        print(f"❌ ERROR: Baseline stitch failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test 2: Stitch WITH audio overlay
    print("=" * 60)
    print("Test 2: Stitching WITH audio overlay")
    print("=" * 60)
    print()

    try:
        print(f"Stitching videos: {video_ids}")
        print(f"Audio overlay: {audio_id}")
        print(f"Suppress video audio: True")
        print()

        video_id, video_path, video_url, metadata, audio_applied, audio_warning = stitch_videos(
            video_ids=video_ids,
            audio_overlay_id=audio_id,
            suppress_video_audio=True
        )

        print(f"✅ Stitch completed (with audio overlay)")
        print(f"   Video ID: {video_id}")
        print(f"   Video Path: {video_path}")
        print(f"   Duration: {metadata.get('video_duration_seconds')}s")
        print(f"   Audio Overlay Applied: {audio_applied}")
        print(f"   Audio Overlay Warning: {audio_warning or 'None'}")
        print(f"   Video Audio Suppressed: {metadata.get('video_audio_suppressed')}")
        print()

        # Check if video has audio
        has_audio = check_video_has_audio(video_path)
        if has_audio is not None:
            print(f"   Has Audio Stream: {has_audio}")
            if not has_audio:
                print("   ❌ ERROR: Video should have audio but doesn't!")
                print("   This indicates the audio overlay failed.")
            else:
                print("   ✅ SUCCESS: Video has audio stream!")

        print()
        print("Metadata:")
        print("-" * 60)
        for key, value in metadata.items():
            print(f"   {key}: {value}")

        print()
        print("=" * 60)
        print("Test Results")
        print("=" * 60)

        if audio_applied and has_audio:
            print("✅ ALL TESTS PASSED!")
            print(f"   The stitched video at {video_path} has audio overlay.")
            print(f"   You can play it to verify audio quality.")
        elif not audio_applied:
            print("❌ FAILED: Audio overlay was not applied")
            if audio_warning:
                print(f"   Warning: {audio_warning}")
        elif audio_applied and not has_audio:
            print("❌ FAILED: Audio overlay reported as applied but video has no audio stream")
            print("   This suggests an issue with moviepy audio integration.")

        print()
        print(f"Play the video with: ffplay '{video_path}'")
        print(f"Inspect with: ffprobe '{video_path}'")

        return 0 if (audio_applied and has_audio) else 1

    except Exception as e:
        print(f"❌ ERROR: Audio overlay stitch failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
