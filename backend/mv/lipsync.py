"""
Lipsync module for syncing audio to video using Replicate's Lipsync-2-Pro model.

This module provides functionality for lip-syncing audio to video using
Sync Labs' Lipsync-2-Pro model via Replicate API.
"""

import os
import time
import uuid
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import replicate
import httpx
from pydantic import BaseModel, Field

from config import settings


class LipsyncRequest(BaseModel):
    """Request model for lipsync generation."""

    video_url: Optional[str] = Field(None, description="URL to the video file (scene)")
    audio_url: Optional[str] = Field(None, description="URL to the audio file")
    video_id: Optional[str] = Field(None, description="Video ID to lookup URL (alternative to video_url)")
    audio_id: Optional[str] = Field(None, description="Audio ID to lookup URL (alternative to audio_url)")
    start_time: Optional[float] = Field(None, ge=0.0, description="Start time in seconds for audio clipping")
    end_time: Optional[float] = Field(None, ge=0.0, description="End time in seconds for audio clipping")
    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Control expressiveness of lip movements (0.0 = subtle, 1.0 = exaggerated)"
    )
    occlusion_detection_enabled: Optional[bool] = Field(
        None,
        description="Enable occlusion detection for complex scenes with obstructions (may slow processing)"
    )
    active_speaker_detection: Optional[bool] = Field(
        None,
        description="Automatically detect and sync the active speaker in multi-person videos"
    )
    project_id: Optional[str] = Field(
        None, description="Project UUID for DynamoDB integration (requires sequence)"
    )
    sequence: Optional[int] = Field(
        None, ge=1, description="Scene sequence number for DynamoDB integration (requires project_id)"
    )


class LipsyncResponse(BaseModel):
    """Response model for lipsync generation."""

    video_id: str = Field(..., description="UUID for video retrieval")
    video_path: str = Field(..., description="Filesystem path to generated video")
    video_url: str = Field(..., description="URL path to retrieve video")
    metadata: dict = Field(..., description="Generation metadata")


def get_video_url_from_id(video_id: str) -> str:
    """
    Lookup video URL from video ID.

    Args:
        video_id: Video UUID

    Returns:
        Full file path to the video

    Raises:
        FileNotFoundError: If video file not found
    """
    # Look in the videos output directory
    video_dir = Path(__file__).parent / "outputs" / "videos"
    video_path = video_dir / f"{video_id}.mp4"

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found for ID: {video_id}")

    return str(video_path)


def get_audio_url_from_id(audio_id: str) -> str:
    """
    Lookup audio URL from audio ID.

    Args:
        audio_id: Audio UUID

    Returns:
        Full file path to the audio

    Raises:
        FileNotFoundError: If audio file not found
    """
    # Audio files are stored in backend/mv/outputs/audio
    # Check multiple extensions as per audio.py:get_audio logic
    audio_base_path = Path(__file__).parent / "outputs" / "audio"

    # Try MP3 first (most common)
    mp3_path = audio_base_path / f"{audio_id}.mp3"
    if mp3_path.exists():
        return str(mp3_path)

    # Try other formats
    for ext in ['m4a', 'opus', 'webm', 'ogg', 'aac']:
        audio_path = audio_base_path / f"{audio_id}.{ext}"
        if audio_path.exists():
            return str(audio_path)

    raise FileNotFoundError(f"Audio file not found for ID: {audio_id}")


def clip_audio(audio_path: str, start_time: float, end_time: float) -> str:
    """
    Clip audio file to specified time range using ffmpeg.

    Args:
        audio_path: Path to source audio file
        start_time: Start time in seconds
        end_time: End time in seconds

    Returns:
        Path to clipped audio file (temporary file)

    Raises:
        RuntimeError: If ffmpeg fails
    """
    # Create temporary file for clipped audio
    temp_fd, temp_path = tempfile.mkstemp(suffix='.mp3')
    os.close(temp_fd)  # Close file descriptor, ffmpeg will write to it

    try:
        # Use ffmpeg to clip audio
        duration = end_time - start_time
        cmd = [
            'ffmpeg',
            '-i', audio_path,
            '-ss', str(start_time),
            '-t', str(duration),
            '-acodec', 'copy',  # Copy codec for faster processing
            '-y',  # Overwrite output file
            temp_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout for audio clipping
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")

        return temp_path

    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise RuntimeError(f"Audio clipping failed: {str(e)}")


def generate_lipsync(
    video_url: Optional[str] = None,
    audio_url: Optional[str] = None,
    video_id: Optional[str] = None,
    audio_id: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    temperature: Optional[float] = None,
    occlusion_detection_enabled: Optional[bool] = None,
    active_speaker_detection: Optional[bool] = None,
) -> tuple[str, str, str, dict]:
    """
    Generate a lip-synced video using Replicate's Lipsync-2-Pro model.

    Args:
        video_url: URL to the video file (scene) - optional if video_id provided
        audio_url: URL to the audio file - optional if audio_id provided
        video_id: Video ID to lookup URL - optional if video_url provided
        audio_id: Audio ID to lookup URL - optional if audio_url provided
        start_time: Start time in seconds for audio clipping
        end_time: End time in seconds for audio clipping
        temperature: Control expressiveness of lip movements (0.0-1.0)
        occlusion_detection_enabled: Enable occlusion detection for complex scenes
        active_speaker_detection: Auto-detect active speaker in multi-person videos

    Returns:
        Tuple of (video_id, video_path, video_url, metadata)

    Raises:
        ValueError: If required parameters are missing or invalid
        FileNotFoundError: If video_id or audio_id not found
        RuntimeError: If audio clipping fails
        Exception: If lipsync generation fails
    """
    # Resolve video URL from ID if provided
    if video_id and not video_url:
        video_url = get_video_url_from_id(video_id)
    elif not video_url:
        raise ValueError("Either video_url or video_id must be provided")

    # Resolve audio URL from ID if provided
    clipped_audio_path = None
    if audio_id and not audio_url:
        audio_url = get_audio_url_from_id(audio_id)
    elif not audio_url:
        raise ValueError("Either audio_url or audio_id must be provided")

    # Clip audio if start_time and end_time are provided
    if start_time is not None and end_time is not None:
        if end_time <= start_time:
            raise ValueError("end_time must be greater than start_time")

        # Clip the audio
        clipped_audio_path = clip_audio(audio_url, start_time, end_time)
        # Use the clipped audio for lipsync
        audio_url = clipped_audio_path
    # Build input parameters
    input_params = {
        "video": video_url,
        "audio": audio_url,
    }

    # Add optional parameters
    if temperature is not None:
        input_params["temperature"] = temperature
    if occlusion_detection_enabled is not None:
        input_params["occlusion_detection_enabled"] = occlusion_detection_enabled
    if active_speaker_detection is not None:
        input_params["active_speaker_detection"] = active_speaker_detection

    # Track processing time
    start_time_ts = time.time()

    # Configure httpx default timeout before replicate.run() creates its client
    # Lipsync can take several minutes, so we need a longer timeout (10 minutes)
    # Save original timeout and restore after
    original_default_timeout = getattr(httpx, '_default_timeout', None)
    httpx._default_timeout = httpx.Timeout(600.0, connect=30.0)  # 10 minutes

    try:
        # Run the model (using same pattern as other replicate backends)
        model_id = "sync/lipsync-2-pro"
        output = replicate.run(model_id, input=input_params)

        processing_time = time.time() - start_time_ts

        # Handle output (can be single FileOutput or list)
        if isinstance(output, list):
            video_output = output[0]
        else:
            video_output = output

        # Read video data
        video_data = video_output.read()

        # Generate UUID for video
        output_video_id = str(uuid.uuid4())

        # Save video to outputs directory (use same videos directory as other endpoints)
        output_dir = Path(__file__).parent / "outputs" / "videos"
        os.makedirs(output_dir, exist_ok=True)

        video_filename = f"{output_video_id}.mp4"
        video_path = output_dir / video_filename

        with open(video_path, "wb") as f:
            f.write(video_data)

        # Construct video URL
        video_url_path = f"/api/mv/get_video/{output_video_id}"

        # Build metadata
        metadata = {
            "video_url": video_url,
            "audio_url": audio_url,
            "model_used": model_id,
            "parameters_used": {
                "temperature": temperature,
                "occlusion_detection_enabled": occlusion_detection_enabled,
                "active_speaker_detection": active_speaker_detection,
                "start_time": start_time,
                "end_time": end_time,
            },
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "processing_time_seconds": round(processing_time, 2),
            "file_size_bytes": os.path.getsize(video_path),
        }

        return output_video_id, str(video_path), video_url_path, metadata

    finally:
        # Restore original timeout
        if original_default_timeout is not None:
            httpx._default_timeout = original_default_timeout
        elif hasattr(httpx, '_default_timeout'):
            delattr(httpx, '_default_timeout')

        # Clean up temporary clipped audio file if it was created
        if clipped_audio_path and os.path.exists(clipped_audio_path):
            try:
                os.unlink(clipped_audio_path)
            except Exception:
                pass  # Ignore cleanup errors

