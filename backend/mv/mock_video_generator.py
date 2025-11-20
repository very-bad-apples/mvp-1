"""
Mock video generator for testing without consuming API credits.

When MOCK_VID_GENS is enabled, this module provides mock video generation
functionality that simulates processing delay and returns pre-staged videos.
"""

import asyncio
import logging
import os
import random
import shutil
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

    The delay range is controlled by environment variables:
    - MOCK_VIDEO_DELAY_MIN: Minimum delay in seconds (default: 5.0)
    - MOCK_VIDEO_DELAY_MAX: Maximum delay in seconds (default: 10.0)

    Returns:
        The actual delay time in seconds.
    """
    delay = random.uniform(settings.MOCK_VIDEO_DELAY_MIN, settings.MOCK_VIDEO_DELAY_MAX)

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

    # Copy mock video to videos directory (no job directories in new approach)
    mock_dir = get_mock_videos_directory()
    mock_video_path = mock_dir / mock_video_filename

    videos_dir = Path(__file__).parent / "outputs" / "videos"
    os.makedirs(videos_dir, exist_ok=True)
    video_path = videos_dir / f"{video_id}.mp4"

    # Copy the mock video
    shutil.copy2(mock_video_path, video_path)

    video_url = f"/api/mv/get_video/{video_id}"

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
        "local_path": str(video_path),
        "video_id": video_id,
    }

    if negative_prompt:
        metadata["parameters_used"]["negative_prompt"] = negative_prompt
    if seed is not None:
        metadata["parameters_used"]["seed"] = seed
    if reference_image_base64:
        metadata["has_reference_image"] = True
        # Save reference image if provided
        try:
            import base64
            # Fix base64 padding if needed
            image_data = reference_image_base64
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',', 1)[1]
            # Add padding if needed
            missing_padding = len(image_data) % 4
            if missing_padding:
                image_data += '=' * (4 - missing_padding)
            
            ref_image_data = base64.b64decode(image_data)
            ref_image_path = videos_dir / f"{video_id}_reference.jpg"
            with open(ref_image_path, "wb") as f:
                f.write(ref_image_data)
            metadata["reference_image_path"] = str(ref_image_path)
        except Exception as e:
            logger.warning(f"Failed to save reference image: {e}")

    # Save metadata.json
    import json
    metadata_path = videos_dir / f"{video_id}_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Upload to S3 if configured
    cloud_urls = {}
    try:
        if settings.STORAGE_BUCKET:
            from services.s3_storage import get_s3_storage_service
            import concurrent.futures

            async def upload_job_to_cloud():
                s3_service = get_s3_storage_service()
                urls = {}

                # Upload video
                s3_key = f"mv/projects/{video_id}/video.mp4"
                await s3_service.upload_file_from_path_async(
                    str(video_path),
                    s3_key,
                    content_type="video/mp4"
                )
                urls["video"] = s3_service.generate_presigned_url(s3_key)

                # Upload metadata
                metadata_s3_key = f"mv/projects/{video_id}/metadata.json"
                await s3_service.upload_file_from_path_async(
                    str(metadata_path),
                    metadata_s3_key,
                    content_type="application/json"
                )
                urls["metadata"] = s3_service.generate_presigned_url(metadata_s3_key)

                return urls

            # Run async upload in separate thread
            def run_upload():
                return asyncio.run(upload_job_to_cloud())

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_upload)
                cloud_urls = future.result(timeout=300)  # 5 min timeout

            logger.info(f"Uploaded mock job {video_id} to S3 with {len(cloud_urls)} files")
    except Exception as e:
        logger.warning(f"Failed to upload mock job {video_id} to S3: {e}")
        # Continue without cloud upload - local files are still available
    
    # Add cloud URLs to metadata if upload succeeded
    if cloud_urls:
        metadata["cloud_urls"] = cloud_urls
        metadata["cloud_url"] = cloud_urls.get("video")  # Backward compatibility
        # Use cloud URL as primary video URL when available
        video_url = cloud_urls.get("video")
    else:
        # Fallback to local API endpoint if cloud upload failed or not configured
        video_url = f"/api/mv/get_video/{video_id}"
    
    # Also store local API endpoint for backward compatibility
    metadata["local_video_url"] = f"/api/mv/get_video/{video_id}"

    return video_id, str(video_path), video_url, metadata
