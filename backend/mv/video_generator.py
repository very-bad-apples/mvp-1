"""
Video generator module for music video scene generation.

This module provides functionality for generating single video clips from text prompts
using either Replicate or Gemini backends. Designed to be called multiple times to
generate individual scene clips for a music video.
"""

import base64
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
    reference_image_base64: Optional[str] = Field(
        None, description="Base64 encoded reference image for character consistency"
    )
    video_rules_template: Optional[str] = Field(
        None, description="Custom template for video generation rules"
    )
    backend: Optional[str] = Field(
        "replicate", description="Backend to use: 'replicate' or 'gemini'"
    )


class GenerateVideoResponse(BaseModel):
    """Response model for video generation."""

    video_id: str = Field(..., description="UUID for video retrieval")
    video_path: str = Field(..., description="Filesystem path to generated video")
    video_url: str = Field(..., description="URL path to retrieve video")
    metadata: dict = Field(..., description="Generation metadata")


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
    reference_image_base64: Optional[str] = None,
    video_rules_template: Optional[str] = None,
    backend: str = "replicate",
) -> tuple[str, str, str, dict]:
    """
    Generate a single video clip from a text prompt.

    Args:
        prompt: Text prompt describing the video content
        negative_prompt: Description of elements to avoid
        aspect_ratio: Video aspect ratio (default from config)
        duration: Video duration in seconds (default from config)
        generate_audio: Whether to generate audio (default from config)
        seed: Random seed for reproducibility
        reference_image_base64: Base64 encoded reference image
        video_rules_template: Custom template for video rules
        backend: Backend to use ('replicate' or 'gemini')

    Returns:
        Tuple of (video_id, video_path, video_url, metadata)

    Raises:
        ValueError: If API token is not configured
        Exception: If video generation fails
    """
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
            "has_reference_image": reference_image_base64 is not None,
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
        reference_image_base64=reference_image_base64,
        model=model,
    )

    processing_time = time.time() - start_time

    # Generate UUID for video
    video_id = str(uuid.uuid4())

    # Save video to outputs directory
    output_dir = Path(__file__).parent / "outputs" / "videos"
    os.makedirs(output_dir, exist_ok=True)

    video_filename = f"{video_id}.mp4"
    video_path = output_dir / video_filename

    with open(video_path, "wb") as f:
        f.write(video_data)

    # Construct video URL
    video_url = f"/api/mv/get_video/{video_id}"

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
    }

    if negative_prompt:
        metadata["parameters_used"]["negative_prompt"] = negative_prompt
    if seed is not None:
        metadata["parameters_used"]["seed"] = seed
    if reference_image_base64:
        metadata["has_reference_image"] = True

    if settings.MV_DEBUG_MODE:
        from mv.debug import log_video_generation_result
        log_video_generation_result({
            "video_id": video_id,
            "video_path": str(video_path),
            "processing_time_seconds": metadata["processing_time_seconds"],
            "file_size_bytes": os.path.getsize(video_path),
        })

    return video_id, str(video_path), video_url, metadata
