"""
Lipsync module for syncing audio to video using Replicate's Lipsync-2-Pro model.

This module provides functionality for lip-syncing audio to video using
Sync Labs' Lipsync-2-Pro model via Replicate API.
"""

import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import replicate
import httpx
from pydantic import BaseModel, Field

from config import settings


class LipsyncRequest(BaseModel):
    """Request model for lipsync generation."""

    video_url: str = Field(..., description="URL to the video file (scene)")
    audio_url: str = Field(..., description="URL to the audio file")
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


def generate_lipsync(
    video_url: str,
    audio_url: str,
    temperature: Optional[float] = None,
    occlusion_detection_enabled: Optional[bool] = None,
    active_speaker_detection: Optional[bool] = None,
) -> tuple[str, str, str, dict]:
    """
    Generate a lip-synced video using Replicate's Lipsync-2-Pro model.

    Args:
        video_url: URL to the video file (scene)
        audio_url: URL to the audio file
        temperature: Control expressiveness of lip movements (0.0-1.0)
        occlusion_detection_enabled: Enable occlusion detection for complex scenes
        active_speaker_detection: Auto-detect active speaker in multi-person videos

    Returns:
        Tuple of (video_id, video_path, video_url, metadata)

    Raises:
        ValueError: If API token is not configured
        Exception: If lipsync generation fails
    """
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
    start_time = time.time()

    # Configure httpx default timeout before replicate.run() creates its client
    # Lipsync can take several minutes, so we need a longer timeout (10 minutes)
    # Save original timeout and restore after
    original_default_timeout = getattr(httpx, '_default_timeout', None)
    httpx._default_timeout = httpx.Timeout(600.0, connect=30.0)  # 10 minutes
    
    try:
        # Run the model (using same pattern as other replicate backends)
        model_id = "sync/lipsync-2-pro"
        output = replicate.run(model_id, input=input_params)
    finally:
        # Restore original timeout
        if original_default_timeout is not None:
            httpx._default_timeout = original_default_timeout
        elif hasattr(httpx, '_default_timeout'):
            delattr(httpx, '_default_timeout')
    
    processing_time = time.time() - start_time

    # Handle output (can be single FileOutput or list)
    if isinstance(output, list):
        video_output = output[0]
    else:
        video_output = output

    # Read video data
    video_data = video_output.read()

    # Generate UUID for video
    video_id = str(uuid.uuid4())

    # Save video to outputs directory (use same videos directory as other endpoints)
    output_dir = Path(__file__).parent / "outputs" / "videos"
    os.makedirs(output_dir, exist_ok=True)

    video_filename = f"{video_id}.mp4"
    video_path = output_dir / video_filename

    with open(video_path, "wb") as f:
        f.write(video_data)

    # Construct video URL
    video_url_path = f"/api/mv/get_video/{video_id}"

    # Build metadata
    metadata = {
        "video_url": video_url,
        "audio_url": audio_url,
        "model_used": model_id,
        "parameters_used": {
            "temperature": temperature,
            "occlusion_detection_enabled": occlusion_detection_enabled,
            "active_speaker_detection": active_speaker_detection,
        },
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "processing_time_seconds": round(processing_time, 2),
        "file_size_bytes": os.path.getsize(video_path),
    }

    return video_id, str(video_path), video_url_path, metadata

