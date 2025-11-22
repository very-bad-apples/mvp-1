"""
Mode-based template loading system.

Replaces the config_flavor system with simple mode-based templates.
"""

from pathlib import Path
from typing import Dict, Any
import yaml
import structlog

logger = structlog.get_logger()

TEMPLATE_DIR = Path(__file__).parent / "templates"

MODE_TEMPLATE_MAP = {
    "music-video": "music_video_scene_prompt.yaml",
    "ad-creative": "ad_creative_scene_prompt.yaml",
}


class TemplateError(Exception):
    """Raised when template loading or validation fails."""
    pass


def load_mode_template(mode: str) -> Dict[str, Any]:
    """
    Load template configuration for specified mode.

    Args:
        mode: Project mode ("music-video" or "ad-creative")

    Returns:
        Template configuration dictionary

    Raises:
        TemplateError: If mode invalid or template not found
    """
    if mode not in MODE_TEMPLATE_MAP:
        raise TemplateError(
            f"Invalid mode: {mode}. Must be one of: {list(MODE_TEMPLATE_MAP.keys())}"
        )

    template_file = TEMPLATE_DIR / MODE_TEMPLATE_MAP[mode]

    if not template_file.exists():
        raise TemplateError(f"Template file not found: {template_file}")

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            template = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise TemplateError(f"Failed to parse template YAML: {e}")
    except Exception as e:
        raise TemplateError(f"Failed to load template file: {e}")

    # Validate required fields
    validate_template(template, mode)

    logger.info("template_loaded", mode=mode, template_file=str(template_file))
    return template


def validate_template(template: Dict[str, Any], mode: str) -> None:
    """
    Validate that template contains all required fields.

    Args:
        template: Template dictionary to validate
        mode: Mode for context in error messages

    Raises:
        TemplateError: If required fields are missing or invalid
    """
    if template is None:
        raise TemplateError(f"Template for mode '{mode}' is None or empty")

    required_fields = [
        "prompt_template",
        "number_of_scenes",
        "video_characteristics",
        "camera_angle",
        "duration_per_scene",
    ]

    missing = [field for field in required_fields if field not in template]

    if missing:
        raise TemplateError(
            f"Template for mode '{mode}' missing required fields: {missing}"
        )

    # Type validation
    if not isinstance(template["prompt_template"], str):
        raise TemplateError("prompt_template must be a string")

    if not isinstance(template["number_of_scenes"], int):
        raise TemplateError("number_of_scenes must be an integer")

    if template["number_of_scenes"] < 1:
        raise TemplateError("number_of_scenes must be >= 1")

    if not isinstance(template["duration_per_scene"], (int, float)):
        raise TemplateError("duration_per_scene must be a number")

    if template["duration_per_scene"] <= 0:
        raise TemplateError("duration_per_scene must be > 0")

    # Validate prompt_template contains required placeholders
    prompt_template = template["prompt_template"]
    required_placeholders = [
        "{concept_prompt}",
        "{personality_profile}",
        "{video_characteristics}",
        "{camera_angle}",
        "{number_of_scenes}",
        "{duration_per_scene}",
        "{director_style_section}",
    ]

    missing_placeholders = [
        p for p in required_placeholders if p not in prompt_template
    ]

    if missing_placeholders:
        raise TemplateError(
            f"Template for mode '{mode}' missing required placeholders in prompt_template: {missing_placeholders}"
        )


def get_available_modes() -> list[str]:
    """
    Get list of available project modes.

    Returns:
        List of mode names
    """
    return list(MODE_TEMPLATE_MAP.keys())

