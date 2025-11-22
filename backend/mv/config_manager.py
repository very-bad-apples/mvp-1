"""
Config flavor management for MV pipeline.

This module handles loading and querying multiple configuration "flavors"
from the backend/mv/configs/ directory. Each flavor is a subdirectory containing
YAML config files for prompts and parameters.

All flavors are loaded into memory at application startup and queried at runtime
based on the config_flavor parameter passed to API endpoints.
"""

import os
from pathlib import Path
from typing import Optional

import structlog
import yaml

logger = structlog.get_logger()

# Module-level storage for all config flavors
# Structure: _flavors[flavor_name][config_type] = config_dict
_flavors: dict[str, dict[str, dict]] = {}

# Track which flavors were discovered at startup
_discovered_flavors: list[str] = []

# Config file names and their corresponding keys
CONFIG_FILES = {
    "image_params": "image_params.yaml",
    "image_prompts": "image_prompts.yaml",
    "scene_prompts": "scene_prompts.yaml",
    "parameters": "parameters.yaml",
}


def discover_flavors() -> list[str]:
    """
    Discover all flavor subdirectories in the configs directory.

    Returns:
        List of flavor names (directory names)
    """
    configs_dir = Path(__file__).parent / "configs"

    if not configs_dir.exists():
        logger.warning("configs_directory_not_found", path=str(configs_dir))
        return []

    flavors = []
    for item in configs_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            flavors.append(item.name)

    return sorted(flavors)


def load_flavor_config(flavor_name: str, config_type: str) -> Optional[dict]:
    """
    Load a specific config file for a specific flavor.

    Args:
        flavor_name: Name of the flavor directory
        config_type: Type of config (e.g., 'image_params', 'scene_prompts')

    Returns:
        Config dict if file exists and loads successfully, None otherwise
    """
    if config_type not in CONFIG_FILES:
        logger.warning(
            "unknown_config_type",
            config_type=config_type,
            valid_types=list(CONFIG_FILES.keys())
        )
        return None

    config_file = CONFIG_FILES[config_type]
    config_path = Path(__file__).parent / "configs" / flavor_name / config_file

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
        return config
    except Exception as e:
        logger.error(
            "config_load_error",
            flavor=flavor_name,
            config_type=config_type,
            path=str(config_path),
            error=str(e)
        )
        return None


def load_all_flavors() -> None:
    """
    Load all config files for all discovered flavors into memory.
    Called once at application startup.
    """
    global _flavors, _discovered_flavors

    _discovered_flavors = discover_flavors()

    if not _discovered_flavors:
        logger.error("no_flavors_discovered")
        return

    for flavor in _discovered_flavors:
        _flavors[flavor] = {}

        for config_type in CONFIG_FILES.keys():
            config = load_flavor_config(flavor, config_type)
            if config is not None:
                _flavors[flavor][config_type] = config
            else:
                # Log missing config file
                logger.debug(
                    "flavor_config_missing",
                    flavor=flavor,
                    config_type=config_type
                )

    logger.info(
        "config_flavors_loaded",
        flavors=_discovered_flavors,
        total_flavors=len(_discovered_flavors)
    )


def get_config(
    flavor: Optional[str],
    config_type: str,
    fallback_to_default: bool = True
) -> dict:
    """
    Get configuration for a specific flavor and config type.

    Args:
        flavor: Flavor name (None or empty string defaults to 'default')
        config_type: Type of config to retrieve
        fallback_to_default: Whether to fall back to 'default' flavor on error

    Returns:
        Config dictionary

    Raises:
        ValueError: If config cannot be found and fallback is disabled
    """
    from config import settings

    # Default to 'default' flavor if not specified
    if not flavor:
        flavor = "default"

    # Check if flavor exists
    if flavor not in _flavors:
        warning_msg = f"Flavor '{flavor}' not found"

        if fallback_to_default and flavor != "default":
            logger.warning(
                "flavor_not_found_fallback",
                requested_flavor=flavor,
                fallback="default"
            )
            flavor = "default"
        else:
            logger.error("flavor_not_found", flavor=flavor)
            raise ValueError(f"{warning_msg}. Available flavors: {_discovered_flavors}")

    # Check if config type exists for this flavor
    if config_type not in _flavors[flavor]:
        warning_msg = f"Config type '{config_type}' not found in flavor '{flavor}'"

        if fallback_to_default and flavor != "default":
            logger.warning(
                "config_type_not_found_fallback",
                flavor=flavor,
                config_type=config_type,
                fallback="default"
            )

            if "default" in _flavors and config_type in _flavors["default"]:
                config = _flavors["default"][config_type]
            else:
                logger.error("config_type_not_in_default", config_type=config_type)
                return {}
        else:
            logger.error(
                "config_type_not_found",
                flavor=flavor,
                config_type=config_type
            )
            return {}
    else:
        config = _flavors[flavor][config_type]

    # Debug logging if enabled
    if settings.MV_DEBUG_MODE:
        from mv.debug import debug_log
        debug_log(
            "config_flavor_loaded",
            flavor=flavor,
            config_type=config_type,
            config_keys=list(config.keys()) if isinstance(config, dict) else None
        )

    return config


def get_discovered_flavors() -> list[str]:
    """
    Get list of flavors discovered at startup.

    Returns:
        List of flavor names
    """
    return _discovered_flavors.copy()


def initialize_config_flavors() -> None:
    """
    Initialize the config flavor system.
    Should be called once at application startup.
    """
    from config import settings

    logger.info("initializing_config_flavors")
    load_all_flavors()

    # Debug logging if enabled
    if settings.MV_DEBUG_MODE:
        from mv.debug import debug_log
        debug_log("config_flavors_discovered", flavors=_discovered_flavors)

        # Log what's available in each flavor
        for flavor in _discovered_flavors:
            available_configs = list(_flavors.get(flavor, {}).keys())
            debug_log(
                "flavor_configs_available",
                flavor=flavor,
                configs=available_configs
            )

    logger.info(
        "config_flavors_initialized",
        flavors=_discovered_flavors,
        default_available="default" in _flavors
    )
