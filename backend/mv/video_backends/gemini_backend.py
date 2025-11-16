"""
Gemini backend for video generation using Google Veo 3.1.

Note: This is a basic implementation. Advanced parameters (duration, audio, reference images)
are not fully supported in this backend. Use Replicate backend for full feature support.
"""

import time
from typing import Optional

from config import settings


def generate_video_gemini(
    prompt: str,
    negative_prompt: Optional[str] = None,
    aspect_ratio: str = "16:9",
    duration: int = 8,
    generate_audio: bool = True,
    seed: Optional[int] = None,
    reference_image_base64: Optional[str] = None,
    model: str = "veo-3.1-fast-generate-preview",
    **kwargs,
) -> bytes:
    """
    Generate video using Gemini's Veo 3.1 model.

    Note: This is a basic implementation. The following parameters are NOT supported
    in this backend and will be ignored:
    - duration (Gemini controls this)
    - generate_audio (Gemini controls this)
    - seed (not supported by Gemini API)
    - reference_image_base64 (not supported by Gemini API)

    Args:
        prompt: Full prompt with video rules applied
        negative_prompt: Description of elements to avoid
        aspect_ratio: Video aspect ratio (currently only "16:9" fully supported)
        duration: Ignored in Gemini backend
        generate_audio: Ignored in Gemini backend
        seed: Ignored in Gemini backend
        reference_image_base64: Ignored in Gemini backend
        model: Gemini model to use (default: veo-3.1-fast-generate-preview)
        **kwargs: Additional parameters (ignored for compatibility)

    Returns:
        Binary video data

    Raises:
        ValueError: If GEMINI_API_KEY is not configured
        Exception: If video generation fails
    """
    # Validate API key
    if not settings.GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not configured. "
            "Please set it in your .env file or environment variables."
        )

    # Import Gemini client
    try:
        import google.genai as genai
    except ImportError:
        raise ImportError(
            "google-genai package is required for Gemini backend. "
            "Install it with: pip install google-genai"
        )

    # Create client
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Build config
    # Note: Gemini API has limited aspect ratio support
    # Currently hardcoded to 16:9 as it's the most stable
    config = genai.types.GenerateVideosConfig(
        aspect_ratio="16:9",  # Limited support for other ratios
        person_generation="allow_all",
        negative_prompt=negative_prompt,
    )

    # Generate video (async operation with polling)
    operation = client.models.generate_videos(
        model=model,
        prompt=prompt,
        config=config,
    )

    # Poll for completion
    poll_interval = 10  # seconds
    max_wait_time = 600  # 10 minutes max
    elapsed_time = 0

    while not operation.done and elapsed_time < max_wait_time:
        time.sleep(poll_interval)
        elapsed_time += poll_interval
        # Refresh operation status
        operation = client.operations.get(operation)

    if not operation.done:
        raise TimeoutError(
            f"Video generation timed out after {max_wait_time} seconds"
        )

    # Check for errors
    if operation.error:
        raise Exception(f"Video generation failed: {operation.error}")

    # Get the generated video
    result = operation.result
    if not result or not result.generated_videos:
        raise Exception("No video was generated")

    # Download the video
    video = result.generated_videos[0]
    video_file = client.files.download(video.video)

    # Read video bytes
    video_bytes = video_file.read()

    return video_bytes
