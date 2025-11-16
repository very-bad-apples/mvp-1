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
