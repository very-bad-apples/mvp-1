"""
Image generation module for Music Video pipeline.
Ported from .ref-pipeline/src/image_generator.py:generate_character_reference_image
"""

import base64
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import replicate
import structlog
import yaml
from pydantic import BaseModel, Field

from config import settings
from mv.debug import (
    log_image_defaults_applied,
    log_image_prompt,
    log_image_request_args,
    log_replicate_response,
)

logger = structlog.get_logger()

# Module-level config storage (loaded at startup)
_image_params_config: dict = {}
_image_prompts_config: dict = {}


class GenerateCharacterReferenceRequest(BaseModel):
    """Request model for /api/mv/generate_character_reference endpoint."""
    character_description: str = Field(..., description="Visual description of the character")
    aspect_ratio: Optional[str] = Field(None, description="Image aspect ratio (e.g., '1:1', '16:9')")
    safety_filter_level: Optional[str] = Field(None, description="Content moderation level")
    person_generation: Optional[str] = Field(None, description="Person generation setting")
    output_format: Optional[str] = Field(None, description="Output image format (png, jpg, webp)")
    negative_prompt: Optional[str] = Field(None, description="Elements to exclude from the image")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")


class GenerateCharacterReferenceResponse(BaseModel):
    """Response model for /api/mv/generate_character_reference endpoint."""
    image_base64: str = Field(..., description="Base64-encoded image data")
    output_file: str = Field(..., description="Path to saved image file")
    metadata: dict = Field(..., description="Request metadata and parameters used")


def load_image_configs(config_dir: str = "mv/configs") -> None:
    """
    Load YAML configuration files for image generation at startup.

    Args:
        config_dir: Directory containing config YAML files
    """
    global _image_params_config, _image_prompts_config

    base_path = Path(__file__).parent / "configs"

    params_path = base_path / "image_params.yaml"
    prompts_path = base_path / "image_prompts.yaml"

    if params_path.exists():
        with open(params_path, "r") as f:
            _image_params_config = yaml.safe_load(f) or {}
        logger.info("mv_image_config_loaded", file="image_params.yaml", keys=list(_image_params_config.keys()))
    else:
        logger.warning("mv_image_config_not_found", file=str(params_path))
        _image_params_config = {}

    if prompts_path.exists():
        with open(prompts_path, "r") as f:
            _image_prompts_config = yaml.safe_load(f) or {}
        logger.info("mv_image_config_loaded", file="image_prompts.yaml", keys=list(_image_prompts_config.keys()))
    else:
        logger.warning("mv_image_config_not_found", file=str(prompts_path))
        _image_prompts_config = {}


def get_default_image_parameters() -> dict:
    """Get default image parameters from loaded config."""
    return {
        "model": _image_params_config.get("model", "google/imagen-4"),
        "aspect_ratio": _image_params_config.get("aspect_ratio", "1:1"),
        "safety_filter_level": _image_params_config.get("safety_filter_level", "block_medium_and_above"),
        "person_generation": _image_params_config.get("person_generation", "allow_adult"),
        "output_format": _image_params_config.get("output_format", "png"),
    }


def get_character_reference_prompt_template() -> str:
    """Get the character reference prompt template from loaded config."""
    return _image_prompts_config.get(
        "character_reference_prompt",
        "A full-body character reference image of {character_description}. Clear, well-lit, neutral background, professional quality, detailed features, front-facing view."
    )


def generate_character_reference_image(
    character_description: str,
    aspect_ratio: Optional[str] = None,
    safety_filter_level: Optional[str] = None,
    person_generation: Optional[str] = None,
    output_format: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    seed: Optional[int] = None,
) -> tuple[str, str, dict]:
    """
    Generate a character reference image using Replicate API.

    Args:
        character_description: Visual description of the character.
        aspect_ratio: Image aspect ratio.
        safety_filter_level: Content moderation level.
        person_generation: Person generation setting.
        output_format: Output image format.
        negative_prompt: Elements to exclude from the image.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (base64_encoded_image, output_file_path, metadata)

    Raises:
        ValueError: If REPLICATE_API_TOKEN is not configured
        Exception: If Replicate API call fails
    """
    # Log request arguments
    log_image_request_args({
        "character_description": character_description,
        "aspect_ratio": aspect_ratio,
        "safety_filter_level": safety_filter_level,
        "person_generation": person_generation,
        "output_format": output_format,
        "negative_prompt": negative_prompt,
        "seed": seed,
    })

    # Validate API token
    api_token = settings.REPLICATE_API_TOKEN or settings.REPLICATE_API_KEY
    if not api_token:
        raise ValueError("REPLICATE_API_TOKEN is not configured. Please set it in your environment.")

    # Set the token for replicate
    os.environ["REPLICATE_API_TOKEN"] = api_token

    # Apply defaults from config
    defaults = get_default_image_parameters()

    if aspect_ratio is None:
        aspect_ratio = defaults["aspect_ratio"]
    if safety_filter_level is None:
        safety_filter_level = defaults["safety_filter_level"]
    if person_generation is None:
        person_generation = defaults["person_generation"]
    if output_format is None:
        output_format = defaults["output_format"]

    model = defaults["model"]

    # Fixed output directory
    output_dir = Path(__file__).parent / "outputs" / "character_reference"

    # Log defaults applied
    applied_defaults = {
        k: v for k, v in {
            "aspect_ratio": aspect_ratio if aspect_ratio == defaults["aspect_ratio"] else None,
            "safety_filter_level": safety_filter_level if safety_filter_level == defaults["safety_filter_level"] else None,
            "person_generation": person_generation if person_generation == defaults["person_generation"] else None,
            "output_format": output_format if output_format == defaults["output_format"] else None,
        }.items() if v is not None
    }
    log_image_defaults_applied(applied_defaults)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Format the prompt
    prompt_template = get_character_reference_prompt_template()
    prompt = prompt_template.format(character_description=character_description).strip()

    log_image_prompt(prompt)

    # Build input parameters for Replicate
    input_params = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "safety_filter_level": safety_filter_level,
        "person_generation": person_generation,
        "output_format": output_format,
    }

    # Add optional parameters
    if negative_prompt:
        input_params["negative_prompt"] = negative_prompt

    if seed is not None:
        input_params["seed"] = seed

    logger.info(
        "replicate_request_started",
        model=model,
        aspect_ratio=aspect_ratio
    )

    # Run the model
    output = replicate.run(model, input=input_params)

    # Handle output - Replicate returns FileOutput objects
    if isinstance(output, list):
        image_output = output[0]
    else:
        image_output = output

    # Read the image data
    image_data = image_output.read()

    log_replicate_response({
        "model": model,
        "image_size_bytes": len(image_data),
    })

    # Generate timestamp-based filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"character_ref_{timestamp}.{output_format}"
    output_path = output_dir / filename

    # Save the image file
    with open(output_path, "wb") as f:
        f.write(image_data)

    logger.info(
        "replicate_request_completed",
        output_file=str(output_path),
        image_size_bytes=len(image_data)
    )

    # Encode to base64
    image_base64 = base64.b64encode(image_data).decode("utf-8")

    # Build metadata
    metadata = {
        "character_description": character_description,
        "model_used": model,
        "parameters_used": {
            "aspect_ratio": aspect_ratio,
            "safety_filter_level": safety_filter_level,
            "person_generation": person_generation,
            "output_format": output_format,
            "negative_prompt": negative_prompt,
            "seed": seed,
        },
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return image_base64, str(output_path), metadata
