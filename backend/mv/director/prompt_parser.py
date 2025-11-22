"""
Prompt parser for creative direction configs.

This module loads YAML/JSON config files from backend/mv/director/configs/
and fills in the prompt template from backend/mv/director/prompt-template.txt
with the config values.
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

import structlog
import yaml

logger = structlog.get_logger()

# Base directory for director configs
DIRECTOR_DIR = Path(__file__).parent
CONFIGS_DIR = DIRECTOR_DIR / "configs"
TEMPLATE_FILE = DIRECTOR_DIR / "prompt-template.txt"


def load_config(config_name: str) -> dict:
    """
    Load a config file (YAML or JSON) from the configs directory.

    Args:
        config_name: Name of the config file (without extension)

    Returns:
        Config dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid YAML/JSON
    """
    # Try YAML first, then JSON
    yaml_path = CONFIGS_DIR / f"{config_name}.yaml"
    json_path = CONFIGS_DIR / f"{config_name}.json"

    if yaml_path.exists():
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            logger.info("config_loaded", config_name=config_name, format="yaml")
            return config
        except yaml.YAMLError as e:
            logger.error("yaml_parse_error", config_name=config_name, error=str(e))
            raise ValueError(f"Invalid YAML in config file: {e}")

    elif json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                config = json.load(f) or {}
            logger.info("config_loaded", config_name=config_name, format="json")
            return config
        except json.JSONDecodeError as e:
            logger.error("json_parse_error", config_name=config_name, error=str(e))
            raise ValueError(f"Invalid JSON in config file: {e}")

    else:
        logger.error("config_not_found", config_name=config_name)
        raise FileNotFoundError(
            f"Config file not found: {config_name} "
            f"(checked {yaml_path} and {json_path})"
        )


def load_template() -> str:
    """
    Load the prompt template file.

    Returns:
        Template string

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    if not TEMPLATE_FILE.exists():
        logger.error("template_not_found", path=str(TEMPLATE_FILE))
        raise FileNotFoundError(f"Template file not found: {TEMPLATE_FILE}")

    try:
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            template = f.read()
        logger.info("template_loaded", path=str(TEMPLATE_FILE))
        return template
    except Exception as e:
        logger.error("template_load_error", path=str(TEMPLATE_FILE), error=str(e))
        raise


def get_nested_value(data: dict, path: str) -> Optional[Any]:
    """
    Get a value from a nested dictionary using dot notation.

    Args:
        data: Dictionary to search
        path: Dot-separated path (e.g., "camera.shotType")

    Returns:
        Value at path, or None if path doesn't exist
    """
    if not path:
        return None

    keys = path.split(".")
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return None
        if key not in current:
            return None
        current = current[key]

    return current


def format_array_value(value: Any) -> str:
    """
    Format an array value as a comma-separated string.

    Args:
        value: Value to format (list, or other type)

    Returns:
        Comma-separated string if value is a list, otherwise string representation
    """
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value) if value is not None else ""


def parse_template(template: str, config: dict) -> str:
    """
    Parse a template string and replace placeholders with config values.

    Placeholder format: {{path.to.value}}
    - Simple: {{camera.shotType}}
    - Nested: {{audio.dialogue.tone}}
    - Arrays: {{quality.negativePrompts}} (formatted as comma-separated)

    Args:
        template: Template string with {{...}} placeholders
        config: Config dictionary with values

    Returns:
        Parsed template with placeholders replaced
    """
    # Find all placeholders: {{...}}
    pattern = r"\{\{([^}]+)\}\}"
    placeholders = re.findall(pattern, template)

    result = template

    for placeholder in placeholders:
        # Get value from config using dot notation
        value = get_nested_value(config, placeholder.strip())

        # Format value (handle arrays)
        if isinstance(value, list):
            formatted_value = format_array_value(value)
        else:
            formatted_value = str(value) if value is not None else ""

        # Replace placeholder in template
        result = result.replace(f"{{{{{placeholder}}}}}", formatted_value)

        # Log missing values
        if value is None:
            logger.warning("missing_config_value", placeholder=placeholder)

    return result


def generate_prompt(config_name: str) -> str:
    """
    Generate a prompt from a config file name.

    This is the main public API for generating prompts.

    Args:
        config_name: Name of the config file (without extension)

    Returns:
        Generated prompt string

    Raises:
        FileNotFoundError: If config or template file doesn't exist
        ValueError: If config file is invalid
    """
    # Load config
    config = load_config(config_name)

    # Load template
    template = load_template()

    # Parse template with config
    prompt = parse_template(template, config)

    logger.info("prompt_generated", config_name=config_name, prompt_length=len(prompt))

    return prompt


def discover_director_configs() -> list[str]:
    """
    Discover all director config files (YAML and JSON) in the configs directory.

    Returns:
        List of config names (without extension), sorted alphabetically
    """
    if not CONFIGS_DIR.exists():
        logger.warning("director_configs_directory_not_found", path=str(CONFIGS_DIR))
        return []

    configs = []
    for file_path in CONFIGS_DIR.iterdir():
        if file_path.is_file():
            # Check for YAML/JSON extensions
            if file_path.suffix in ['.yaml', '.yml', '.json']:
                # Get name without extension
                config_name = file_path.stem
                configs.append(config_name)

    # Remove duplicates and sort
    configs = sorted(list(set(configs)))
    logger.info("director_configs_discovered", count=len(configs), configs=configs)

    return configs


def extract_signature_style(config_name: Optional[str]) -> Optional[str]:
    """
    Extract the signature style comment from a director config YAML file.

    The signature style is expected to be on line 2 of the YAML file in the format:
    # Signature Style: [description]

    Args:
        config_name: Name of director config (e.g., "Wes-Anderson") or None

    Returns:
        Signature style string or None if not found/invalid

    Example:
        >>> extract_signature_style("Wes-Anderson")
        "Symmetrical compositions, pastel color palettes, planimetric framing, whimsical precision"
    """
    if not config_name:
        return None

    # Sanitize config_name to prevent path traversal attacks
    # Remove path separators and parent directory references
    if '/' in config_name or '\\' in config_name or '..' in config_name:
        logger.warning(
            "invalid_config_name_path_traversal_attempt",
            config_name=config_name
        )
        return None

    # Try YAML first, then JSON
    yaml_path = CONFIGS_DIR / f"{config_name}.yaml"
    yml_path = CONFIGS_DIR / f"{config_name}.yml"
    json_path = CONFIGS_DIR / f"{config_name}.json"

    file_path = None
    if yaml_path.exists():
        file_path = yaml_path
    elif yml_path.exists():
        file_path = yml_path
    elif json_path.exists():
        # JSON files don't have comments, so return None
        logger.warning("signature_style_not_supported_for_json", config_name=config_name)
        return None

    if not file_path:
        logger.warning("config_not_found_for_signature_style", config_name=config_name)
        return None

    # Additional safety check: ensure resolved path is within CONFIGS_DIR
    try:
        # Verify the resolved path is within CONFIGS_DIR
        resolved_configs_dir = CONFIGS_DIR.resolve()
        resolved_file_path = file_path.resolve()
        
        # Check if CONFIGS_DIR is a parent of the file path
        if resolved_configs_dir not in resolved_file_path.parents and resolved_file_path != resolved_configs_dir:
            logger.error(
                "path_traversal_detected",
                config_name=config_name,
                resolved_path=str(resolved_file_path)
            )
            return None
    except (OSError, ValueError) as e:
        logger.error(
            "path_resolution_error",
            config_name=config_name,
            error=str(e)
        )
        return None

    try:
        # Read file line by line to extract comment from line 2
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Check if we have at least 2 lines
        if len(lines) < 2:
            logger.warning("config_too_short_for_signature_style", config_name=config_name)
            return None

        # Line 2 (index 1) should contain the signature style comment
        line_2 = lines[1].strip()

        # Pattern: # Signature Style: [description]
        # Handle variations: "# Signature Style:", "#Signature Style:", etc.
        pattern = r"#\s*Signature\s+Style\s*:\s*(.+)"
        match = re.search(pattern, line_2, re.IGNORECASE)

        if match:
            signature_style = match.group(1).strip()
            logger.info(
                "signature_style_extracted",
                config_name=config_name,
                style_preview=signature_style[:50]
            )
            return signature_style
        else:
            logger.warning(
                "signature_style_not_found",
                config_name=config_name,
                line_2_preview=line_2[:50]
            )
            return None

    except FileNotFoundError:
        logger.error("config_file_not_found", config_name=config_name, path=str(file_path))
        return None
    except Exception as e:
        logger.error(
            "signature_style_extraction_error",
            config_name=config_name,
            error=str(e)
        )
        return None

