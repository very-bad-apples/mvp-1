"""
Mock video generator for testing without consuming API credits.

When MOCK_VID_GENS is enabled, this module provides mock video generation
functionality that simulates processing delay and returns pre-staged videos.
"""

import asyncio
import logging
import os
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


def get_mock_videos_directory() -> Path:
    """Get the path to the mock videos directory."""
    return Path(__file__).parent / "outputs" / "mock"


def list_available_mock_videos() -> list[str]:
    """
    List all available mock video files in the mock directory.

    Returns:
        List of MP4 filenames available for mock responses.
    """
    mock_dir = get_mock_videos_directory()
    if not mock_dir.exists():
        return []

    # Get all MP4 files
    videos = [f.name for f in mock_dir.glob("*.mp4")]
    return sorted(videos)


def select_random_mock_video() -> str:
    """
    Randomly select a mock video from available videos.

    Returns:
        Filename of the selected mock video.

    Raises:
        FileNotFoundError: If no mock videos are available.
    """
    videos = list_available_mock_videos()
    if not videos:
        raise FileNotFoundError(
            "No mock videos found in backend/mv/outputs/mock/. "
            "Please add at least one .mp4 file to use mock mode. "
            "See README.txt in that directory for instructions."
        )

    return random.choice(videos)


def simulate_processing_delay() -> float:
    """
    Simulate video generation processing time.

    Returns:
        The actual delay time in seconds (between 5-10 seconds).
    """
    delay = random.uniform(5.0, 10.0)

    if settings.MV_DEBUG_MODE:
        from mv.debug import log_mock_delay
        log_mock_delay(delay)

    time.sleep(delay)
    return delay


def generate_mock_video(
    prompt: str,
    negative_prompt: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    duration: Optional[int] = None,
    generate_audio: Optional[bool] = None,
    seed: Optional[int] = None,
    reference_image_base64: Optional[str] = None,
    video_rules_template: Optional[str] = None,
) -> tuple[str, str, str, dict]:
    """
    Generate a mock video response with simulated delay.

    This function:
    1. Logs mock mode activation
    2. Selects a random mock video
    3. Simulates processing delay (5-10 seconds)
    4. Generates UUID for the "video"
    5. Returns mock metadata

    Args:
        prompt: Original prompt from request
        negative_prompt: Negative prompt from request
        aspect_ratio: Aspect ratio from request (default: "16:9")
        duration: Duration from request (default: 8)
        generate_audio: Audio flag from request (default: True)
        seed: Seed from request
        reference_image_base64: Reference image from request
        video_rules_template: Rules template from request

    Returns:
        Tuple of (video_id, video_path, video_url, metadata)
    """
    if settings.MV_DEBUG_MODE:
        from mv.debug import log_mock_mode_enabled
        log_mock_mode_enabled()

    # Select a random mock video
    mock_video_filename = select_random_mock_video()

    if settings.MV_DEBUG_MODE:
        from mv.debug import log_mock_video_selected
        log_mock_video_selected(mock_video_filename)

    # Simulate processing delay
    actual_delay = simulate_processing_delay()

    # Generate UUID for this "video"
    video_id = str(uuid.uuid4())

    # Build paths (pointing to mock directory)
    mock_dir = get_mock_videos_directory()
    video_path = str(mock_dir / mock_video_filename)
    video_url = f"/api/mv/get_video/{video_id}"

    # Upload to cloud storage if configured
    cloud_url = None
    try:
        if settings.STORAGE_BUCKET:  # Only upload if cloud storage is configured
            from services.storage_backend import get_storage_backend
            
            async def upload_to_cloud():
                storage = get_storage_backend()
                cloud_path = f"mv/videos/{video_id}.mp4"
                return await storage.upload_file(
                    video_path,
                    cloud_path
                )
            
            # Run async upload in sync context
            cloud_url = asyncio.run(upload_to_cloud())
            logger.info(f"Uploaded mock video {video_id} to cloud storage: {cloud_url}")
    except Exception as e:
        logger.warning(f"Failed to upload mock video {video_id} to cloud storage: {e}")
        # Continue without cloud upload - local file is still available

    # Apply defaults
    if aspect_ratio is None:
        aspect_ratio = "16:9"
    if duration is None:
        duration = 8
    if generate_audio is None:
        generate_audio = True

    # Build metadata
    metadata = {
        "prompt": prompt,
        "backend_used": "mock",
        "model_used": "mock",
        "is_mock": True,
        "mock_video_source": mock_video_filename,
        "parameters_used": {
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "generate_audio": generate_audio,
        },
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "processing_time_seconds": round(actual_delay, 2),
        "local_path": video_path,
    }
    
    # Add cloud URL to metadata if upload succeeded
    if cloud_url:
        metadata["cloud_url"] = cloud_url

    if negative_prompt:
        metadata["parameters_used"]["negative_prompt"] = negative_prompt
    if seed is not None:
        metadata["parameters_used"]["seed"] = seed
    if reference_image_base64:
        metadata["has_reference_image"] = True

    return video_id, video_path, video_url, metadata
