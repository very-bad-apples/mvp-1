"""
Video generator module for music video scene generation.

This module provides functionality for generating single video clips from text prompts
using either Replicate or Gemini backends. Designed to be called multiple times to
generate individual scene clips for a music video.
"""

import base64
import json
import logging
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from config import settings

logger = logging.getLogger(__name__)


# Module-level config storage (loaded at startup)
_video_params_config: dict = {}


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


def load_video_configs() -> None:
    """
    Load video generation configuration from YAML files.
    Called at application startup.
    """
    global _video_params_config

    config_dir = Path(__file__).parent / "configs"
    params_file = config_dir / "image_params.yaml"  # Video params are in the same file

    if params_file.exists():
        with open(params_file) as f:
            all_config = yaml.safe_load(f) or {}
            # Extract video-specific params
            _video_params_config = {
                k.replace("video_", ""): v
                for k, v in all_config.items()
                if k.startswith("video_")
            }
            if settings.MV_DEBUG_MODE:
                from mv.debug import debug_log
                debug_log("video_configs_loaded", **_video_params_config)


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


def get_default_video_parameters() -> dict:
    """
    Get default video generation parameters.
    Returns config values if loaded, otherwise returns hardcoded defaults.
    """
    if _video_params_config:
        return {
            "model": _video_params_config.get("model", "google/veo-3.1"),
            "aspect_ratio": _video_params_config.get("aspect_ratio", "16:9"),
            "duration": _video_params_config.get("duration", 8),
            "generate_audio": _video_params_config.get("generate_audio", True),
            "person_generation": _video_params_config.get("person_generation", "allow_all"),
            "rules_template": _video_params_config.get(
                "rules_template",
                "- No subtitles or camera directions.\n- The video should be in {aspect_ratio} aspect ratio.\n- Keep it short, visual, simple, cinematic."
            ),
        }

    # Fallback defaults
    return {
        "model": "google/veo-3.1",
        "aspect_ratio": "16:9",
        "duration": 8,
        "generate_audio": True,
        "person_generation": "allow_all",
        "rules_template": "- No subtitles or camera directions.\n- The video should be in {aspect_ratio} aspect ratio.\n- Keep it short, visual, simple, cinematic.",
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

    # Get defaults from config
    defaults = get_default_video_parameters()

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

    # Upload directly to S3 if configured
    if settings.STORAGE_BUCKET:
        from services.s3_storage import get_s3_storage_service

        s3_service = get_s3_storage_service()

        # Upload video from memory
        video_s3_key = s3_service.upload_file(
            BytesIO(video_data),
            f"mv/projects/{video_id}/video.mp4",
            content_type="video/mp4"
        )

        # Upload metadata from memory
        metadata_json = json.dumps(metadata, indent=2).encode('utf-8')
        s3_service.upload_file(
            BytesIO(metadata_json),
            f"mv/projects/{video_id}/metadata.json",
            content_type="application/json"
        )

        # Upload reference image if exists (from base64)
        if reference_image_base64:
            try:
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
                s3_service.upload_file(
                    BytesIO(ref_image_data),
                    f"mv/projects/{video_id}/reference_image.jpg",
                    content_type="image/jpeg"
                )
                metadata["has_reference_image"] = True
            except Exception as e:
                logger.warning(f"Failed to upload reference image: {e}")

        # Generate presigned URL for response
        video_url = s3_service.generate_presigned_url(video_s3_key)

        metadata["cloud_url"] = video_url
        metadata["storage_backend"] = "s3"
        video_path = None  # No local path when using S3

        logger.info(f"Uploaded video {video_id} directly to S3")

    else:
        # Fallback for local dev without S3
        videos_dir = Path(__file__).parent / "outputs" / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)

        video_path = videos_dir / f"{video_id}.mp4"
        with open(video_path, "wb") as f:
            f.write(video_data)

        video_url = f"/api/mv/get_video/{video_id}"
        metadata["local_path"] = str(video_path)
        metadata["storage_backend"] = "local"
        video_path = str(video_path)

    if settings.MV_DEBUG_MODE:
        from mv.debug import log_video_generation_result
        debug_info = {
            "video_id": video_id,
            "video_path": video_path,
            "processing_time_seconds": metadata["processing_time_seconds"],
            "storage_backend": metadata["storage_backend"],
            "character_reference_id": character_reference_id,
            "character_reference_path": character_reference_path,
        }
        # Only include file size if we have a local path
        if video_path and os.path.exists(video_path):
            debug_info["file_size_bytes"] = os.path.getsize(video_path)
        log_video_generation_result(debug_info)

    return video_id, video_path, video_url, metadata, character_reference_warning
