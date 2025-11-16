"""
Replicate backend for video generation using Google Veo 3.1.
"""

import base64
import os
import tempfile
from typing import Optional

import replicate

from config import settings


def generate_video_replicate(
    prompt: str,
    negative_prompt: Optional[str] = None,
    aspect_ratio: str = "16:9",
    duration: int = 8,
    generate_audio: bool = True,
    seed: Optional[int] = None,
    reference_image_base64: Optional[str] = None,
    model: str = "google/veo-3.1",
    **kwargs,
) -> bytes:
    """
    Generate video using Replicate's Veo 3.1 model.

    Args:
        prompt: Full prompt with video rules applied
        negative_prompt: Description of elements to avoid
        aspect_ratio: Video aspect ratio
        duration: Video duration in seconds
        generate_audio: Whether to generate audio
        seed: Random seed for reproducibility
        reference_image_base64: Base64 encoded reference image
        model: Replicate model to use
        **kwargs: Additional parameters for forward compatibility

    Returns:
        Binary video data

    Raises:
        ValueError: If REPLICATE_API_TOKEN is not configured
        Exception: If video generation fails
    """
    # Validate API token
    api_token = settings.REPLICATE_API_TOKEN or settings.REPLICATE_API_KEY
    if not api_token:
        raise ValueError(
            "REPLICATE_API_TOKEN is not configured. "
            "Please set it in your .env file or environment variables."
        )

    # Set the API token for the replicate library
    os.environ["REPLICATE_API_TOKEN"] = api_token

    # Build input parameters
    input_params = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "generate_audio": generate_audio,
    }

    # Add optional parameters
    if negative_prompt:
        input_params["negative_prompt"] = negative_prompt
    if seed is not None:
        input_params["seed"] = seed

    # Handle reference image
    temp_file = None
    file_handle = None

    try:
        if reference_image_base64:
            # Decode base64 image and write to temp file
            image_data = base64.b64decode(reference_image_base64)
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".png", delete=False
            )
            temp_file.write(image_data)
            temp_file.flush()
            temp_file.close()  # Close to allow other processes to read

            # Open for reading and pass to API
            file_handle = open(temp_file.name, "rb")
            input_params["reference_images"] = [file_handle]

        # Run the model
        output = replicate.run(model, input=input_params)

        # Handle output (can be single FileOutput or list)
        if isinstance(output, list):
            video_output = output[0]
        else:
            video_output = output

        # Read video data
        video_data = video_output.read()

        return video_data

    finally:
        # Clean up file handles and temp files
        if file_handle:
            file_handle.close()
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
