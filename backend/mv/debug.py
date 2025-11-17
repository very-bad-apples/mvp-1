"""
Debug logging utilities for Music Video module.
"""

import structlog
from config import settings

logger = structlog.get_logger()


def debug_log(event: str, **kwargs):
    """
    Log debug information only when MV_DEBUG_MODE is enabled.

    Args:
        event: Event name for structured logging
        **kwargs: Additional key-value pairs to log
    """
    if settings.MV_DEBUG_MODE:
        logger.info(f"mv_debug_{event}", **kwargs)


def log_request_args(request_data: dict):
    """Log the request arguments received."""
    debug_log("request_args_received", **request_data)


def log_defaults_applied(defaults: dict):
    """Log the default arguments that were applied."""
    debug_log("defaults_applied", **defaults)


def log_config_params(config_params: dict):
    """Log the configuration parameters loaded from YAML."""
    debug_log("config_params_loaded", **config_params)


def log_full_prompt(prompt: str):
    """Log the full prompt that will be sent to Gemini."""
    debug_log("full_prompt", prompt=prompt)


def log_gemini_response(response_text: str):
    """Log the raw response from Gemini."""
    debug_log("gemini_response", response=response_text)


# Image generation specific debug logging

def log_image_request_args(request_data: dict):
    """Log the image generation request arguments received."""
    debug_log("image_request_args_received", **request_data)


def log_image_defaults_applied(defaults: dict):
    """Log the default image parameters that were applied."""
    debug_log("image_defaults_applied", **defaults)


def log_image_prompt(prompt: str):
    """Log the full prompt that will be sent to Replicate."""
    debug_log("image_full_prompt", prompt=prompt)


def log_replicate_response(response_info: dict):
    """Log information about the Replicate API response."""
    debug_log("replicate_response", **response_info)


# Video generation specific debug logging

def log_video_request_args(request_data: dict):
    """Log the video generation request arguments received."""
    debug_log("video_request_args_received", **request_data)


def log_video_defaults_applied(defaults: dict):
    """Log the default video parameters that were applied."""
    debug_log("video_defaults_applied", **defaults)


def log_video_prompt(prompt: str):
    """Log the full prompt with video rules applied."""
    debug_log("video_full_prompt", prompt=prompt)


def log_video_backend_selected(backend: str):
    """Log which video generation backend was selected."""
    debug_log("video_backend_selected", backend=backend)


def log_video_generation_result(result_info: dict):
    """Log the result of video generation."""
    debug_log("video_generation_result", **result_info)


# Mock video generation specific debug logging

def log_mock_mode_enabled():
    """Log when mock mode is active."""
    debug_log("mock_mode_enabled", message="Using mock video generation mode")


def log_mock_video_selected(video_filename: str):
    """Log which mock video was selected."""
    debug_log("mock_video_selected", video_filename=video_filename)


def log_mock_delay(delay_seconds: float):
    """Log simulated processing delay."""
    debug_log("mock_delay", delay_seconds=round(delay_seconds, 2))


# Batch image generation specific debug logging

def log_batch_image_request(num_images: int):
    """Log batch image generation request."""
    debug_log("batch_image_request", num_images=num_images)


def log_batch_image_result(num_requested: int, num_generated: int, image_ids: list):
    """Log batch image generation results."""
    debug_log(
        "batch_image_result",
        num_requested=num_requested,
        num_generated=num_generated,
        image_ids=image_ids
    )
