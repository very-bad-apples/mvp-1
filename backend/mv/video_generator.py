"""
Video generator module for music video scene generation.

This module provides functionality for generating single video clips from text prompts
using either Replicate or Gemini backends. Designed to be called multiple times to
generate individual scene clips for a music video.
"""

import asyncio
import base64
import logging
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from config import settings

logger = logging.getLogger(__name__)


# Config loading has been moved to config_manager.py
# Configs are now loaded per-request based on config_flavor parameter


class GenerateVideoRequest(BaseModel):
    """Request model for video generation."""

    prompt: str = Field(..., description="Text prompt describing the video content")
    negative_prompt: Optional[str] = Field(
        None, description="Description of elements to avoid in the video"
    )
    aspect_ratio: Optional[str] = Field(
        None, description="Video aspect ratio (e.g., '16:9', '9:16', '1:1')"
    )
    duration: Optional[int] = Field(
        None, description="Video duration in seconds"
    )
    generate_audio: Optional[bool] = Field(
        None, description="Whether to generate audio for the video"
    )
    seed: Optional[int] = Field(
        None, description="Random seed for reproducibility"
    )
    character_reference_id: Optional[str] = Field(
        None, description="UUID of character reference image for character consistency"
    )
    reference_image_base64: Optional[str] = Field(
        None, description="[DEPRECATED] Base64 encoded reference image. Use character_reference_id instead."
    )
    video_rules_template: Optional[str] = Field(
        None, description="Custom template for video generation rules"
    )
    backend: Optional[str] = Field(
        "replicate", description="Backend to use: 'replicate' or 'gemini'"
    )
    project_id: Optional[str] = Field(
        None, description="Project UUID for DynamoDB integration (requires sequence)"
    )
    sequence: Optional[int] = Field(
        None, ge=1, description="Scene sequence number for DynamoDB integration (requires project_id)"
    )
    config_flavor: Optional[str] = Field(
        None, description="Config flavor to use for generation (defaults to 'default')"
    )


class GenerateVideoResponse(BaseModel):
    """Response model for video generation."""

    video_id: str = Field(..., description="UUID for video retrieval")
    video_path: str = Field(..., description="Filesystem path to generated video")
    video_url: str = Field(..., description="URL path to retrieve video")
    metadata: dict = Field(..., description="Generation metadata")
    character_reference_warning: Optional[str] = Field(
        None, description="Warning message if character reference UUID was not found"
    )


class VideoGenerationError(BaseModel):
    """Error response model for video generation failures."""

    error: str = Field(..., description="Error type")
    error_code: str = Field(..., description="Error code from video service")
    message: str = Field(..., description="Error description")
    backend_used: str = Field(..., description="Backend that was used")
    timestamp: str = Field(..., description="Error timestamp")


# load_video_configs() has been deprecated - use config_manager.initialize_config_flavors() instead


def get_character_reference_image(character_reference_id: str) -> tuple[Optional[Path], bool]:
    """
    Resolve character reference UUID to file path.

    Args:
        character_reference_id: UUID of the character reference image

    Returns:
        Tuple of (file_path, exists) where file_path is Path object or None
    """
    base_dir = Path(__file__).parent / "outputs" / "character_reference"

    # Check common image extensions
    extensions = [".png", ".jpg", ".jpeg", ".webp"]

    for ext in extensions:
        file_path = base_dir / f"{character_reference_id}{ext}"
        if file_path.exists():
            logger.info(f"Found character reference: {file_path}")
            return file_path, True

    # Log all attempted paths
    attempted_paths = [str(base_dir / f"{character_reference_id}{ext}") for ext in extensions]
    logger.warning(
        f"Character reference UUID '{character_reference_id}' not found. "
        f"Attempted paths: {attempted_paths}"
    )

    return None, False


def get_default_video_parameters(config_flavor: Optional[str] = None) -> dict:
    """
    Get default video generation parameters.

    Args:
        config_flavor: Optional flavor name to use (defaults to 'default')

    Returns:
        Dictionary of default video parameters
    """
    from mv.config_manager import get_config

    image_params_config = get_config(config_flavor, "image_params")

    # Extract video-specific params (prefixed with video_)
    video_params = {
        k.replace("video_", ""): v
        for k, v in image_params_config.items()
        if k.startswith("video_")
    }

    # Return with fallback defaults
    return {
        "model": video_params.get("model", "google/veo-3.1"),
        "aspect_ratio": video_params.get("aspect_ratio", "16:9"),
        "duration": video_params.get("duration", 8),
        "generate_audio": video_params.get("generate_audio", True),
        "person_generation": video_params.get("person_generation", "allow_all"),
        "rules_template": video_params.get(
            "rules_template",
            "- No subtitles or camera directions.\n- The video should be in {aspect_ratio} aspect ratio.\n- Keep it short, visual, simple, cinematic."
        ),
    }


def generate_video(
    prompt: str,
    negative_prompt: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    duration: Optional[int] = None,
    generate_audio: Optional[bool] = None,
    seed: Optional[int] = None,
    character_reference_id: Optional[str] = None,
    reference_image_base64: Optional[str] = None,
    video_rules_template: Optional[str] = None,
    backend: str = "replicate",
    config_flavor: Optional[str] = None,
) -> tuple[str, str, str, dict, Optional[str]]:
    """
    Generate a single video clip from a text prompt.

    Args:
        prompt: Text prompt describing the video content
        negative_prompt: Description of elements to avoid
        aspect_ratio: Video aspect ratio (default from config)
        duration: Video duration in seconds (default from config)
        generate_audio: Whether to generate audio (default from config)
        seed: Random seed for reproducibility
        character_reference_id: UUID of character reference image (preferred)
        reference_image_base64: [DEPRECATED] Base64 encoded reference image
        video_rules_template: Custom template for video rules
        backend: Backend to use ('replicate' or 'gemini')
        config_flavor: Config flavor to use (defaults to 'default')

    Returns:
        Tuple of (video_id, video_path, video_url, metadata, character_reference_warning)

    Raises:
        ValueError: If API token is not configured
        Exception: If video generation fails
    """
    # Handle character reference resolution
    character_reference_path: Optional[str] = None
    character_reference_warning: Optional[str] = None

    # Prioritize character_reference_id over reference_image_base64
    if character_reference_id and reference_image_base64:
        logger.warning(
            f"Both character_reference_id and reference_image_base64 provided. "
            f"Using character_reference_id (UUID: {character_reference_id})"
        )

    if character_reference_id:
        file_path, exists = get_character_reference_image(character_reference_id)
        if exists and file_path:
            character_reference_path = str(file_path)
            logger.info(f"Using character reference: {character_reference_path}")
        else:
            character_reference_warning = f"Character reference image with UUID '{character_reference_id}' not found"
            logger.warning(character_reference_warning)

    # Check for mock mode first
    if settings.MOCK_VID_GENS:
        from mv.mock_video_generator import generate_mock_video
        result = generate_mock_video(
            prompt=prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            duration=duration,
            generate_audio=generate_audio,
            seed=seed,
            reference_image_base64=reference_image_base64,
            video_rules_template=video_rules_template,
        )
        # Append warning to result
        return (*result, character_reference_warning)

    from mv.video_backends import get_video_backend

    # Debug logging
    if settings.MV_DEBUG_MODE:
        from mv.debug import log_video_request_args
        log_video_request_args({
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "generate_audio": generate_audio,
            "seed": seed,
            "character_reference_id": character_reference_id,
            "character_reference_path": character_reference_path,
            "has_reference_image_base64": reference_image_base64 is not None,
            "video_rules_template": video_rules_template,
            "backend": backend,
        })

    # Get defaults from config (using specified flavor)
    defaults = get_default_video_parameters(config_flavor)

    # Apply defaults for unspecified parameters
    if aspect_ratio is None:
        aspect_ratio = defaults["aspect_ratio"]
    if duration is None:
        duration = defaults["duration"]
    if generate_audio is None:
        generate_audio = defaults["generate_audio"]
    if video_rules_template is None:
        video_rules_template = defaults["rules_template"]

    model = defaults["model"]

    if settings.MV_DEBUG_MODE:
        from mv.debug import log_video_defaults_applied
        log_video_defaults_applied({
            "model": model,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "generate_audio": generate_audio,
            "rules_template": video_rules_template,
        })

    # Apply video rules to prompt
    rules = video_rules_template.format(aspect_ratio=aspect_ratio)
    full_prompt = f"{prompt}\n\n{rules}"

    if settings.MV_DEBUG_MODE:
        from mv.debug import log_video_prompt
        log_video_prompt(full_prompt)

    # Get the appropriate backend
    backend_func = get_video_backend(backend)

    if settings.MV_DEBUG_MODE:
        from mv.debug import log_video_backend_selected
        log_video_backend_selected(backend)

    # Track processing time
    start_time = time.time()

    # Generate video using selected backend
    video_data = backend_func(
        prompt=full_prompt,
        negative_prompt=negative_prompt,
        aspect_ratio=aspect_ratio,
        duration=duration,
        generate_audio=generate_audio,
        seed=seed,
        character_reference_path=character_reference_path,
        reference_image_base64=reference_image_base64,
        model=model,
    )

    processing_time = time.time() - start_time

    # Generate UUID for video
    video_id = str(uuid.uuid4())

    # Create job directory structure for this video
    job_dir = Path(__file__).parent / "outputs" / "jobs" / video_id
    os.makedirs(job_dir, exist_ok=True)
    
    # Also save to videos directory for backward compatibility
    videos_dir = Path(__file__).parent / "outputs" / "videos"
    os.makedirs(videos_dir, exist_ok=True)

    video_filename = f"{video_id}.mp4"
    video_path = job_dir / "video.mp4"  # Save in job directory
    video_path_compat = videos_dir / video_filename  # Backward compatibility

    # Save video to both locations
    with open(video_path, "wb") as f:
        f.write(video_data)
    with open(video_path_compat, "wb") as f:
        f.write(video_data)

    # Build metadata
    metadata = {
        "prompt": prompt,
        "backend_used": backend,
        "model_used": model,
        "parameters_used": {
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "generate_audio": generate_audio,
        },
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "processing_time_seconds": round(processing_time, 2),
        "local_path": str(video_path),
        "video_id": video_id,
    }

    if negative_prompt:
        metadata["parameters_used"]["negative_prompt"] = negative_prompt
    if seed is not None:
        metadata["parameters_used"]["seed"] = seed

    # Store character reference ID if provided
    if character_reference_id:
        metadata["character_reference_id"] = character_reference_id
        if character_reference_path:
            metadata["character_reference_path"] = character_reference_path
        if character_reference_warning:
            metadata["character_reference_warning"] = character_reference_warning

    # Handle deprecated base64 reference image (backward compatibility)
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
            ref_image_path = job_dir / "reference_image.jpg"
            with open(ref_image_path, "wb") as f:
                f.write(ref_image_data)
            metadata["reference_image_path"] = str(ref_image_path)
        except Exception as e:
            logger.warning(f"Failed to save reference image: {e}")

    # Save metadata.json
    import json
    metadata_path = job_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Upload entire job directory to cloud storage if configured
    cloud_urls = {}
    try:
        if settings.STORAGE_BUCKET:  # Only upload if cloud storage is configured
            from services.storage_backend import get_storage_backend
            
            async def upload_job_to_cloud():
                storage = get_storage_backend()
                urls = {}
                
                # Upload video
                urls["video"] = await storage.upload_file(
                    str(video_path),
                    f"mv/jobs/{video_id}/video.mp4"
                )
                
                # Upload metadata
                urls["metadata"] = await storage.upload_file(
                    str(metadata_path),
                    f"mv/jobs/{video_id}/metadata.json"
                )
                
                # Upload reference image if exists
                ref_image_path = job_dir / "reference_image.jpg"
                if ref_image_path.exists():
                    urls["reference_image"] = await storage.upload_file(
                        str(ref_image_path),
                        f"mv/jobs/{video_id}/reference_image.jpg"
                    )
                
                return urls
            
            # Run async upload - handle both sync and async contexts
            # Use a separate thread with its own event loop to avoid conflicts
            import concurrent.futures
            
            def run_upload():
                return asyncio.run(upload_job_to_cloud())
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_upload)
                cloud_urls = future.result(timeout=300)  # 5 min timeout
            
            logger.info(f"Uploaded job {video_id} to cloud storage with {len(cloud_urls)} files")
    except Exception as e:
        logger.warning(f"Failed to upload job {video_id} to cloud storage: {e}")
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

    if settings.MV_DEBUG_MODE:
        from mv.debug import log_video_generation_result
        log_video_generation_result({
            "video_id": video_id,
            "video_path": str(video_path),
            "processing_time_seconds": metadata["processing_time_seconds"],
            "file_size_bytes": os.path.getsize(video_path),
            "character_reference_id": character_reference_id,
            "character_reference_path": character_reference_path,
        })

    return video_id, str(video_path), video_url, metadata, character_reference_warning
