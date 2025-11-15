"""
Video generation pipeline package.

This package contains the core components for generating AI ad creative videos:
- Scene templates for different visual styles
- Asset management for file operations
- Error handling for robust pipeline execution
"""

__version__ = "0.1.0"

from .templates import get_scene_template, fill_template
from .asset_manager import AssetManager
from .error_handler import PipelineError, ErrorCode, should_retry

__all__ = [
    "get_scene_template",
    "fill_template",
    "AssetManager",
    "PipelineError",
    "ErrorCode",
    "should_retry",
]
