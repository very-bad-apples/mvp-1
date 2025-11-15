"""
Model Registry - Centralized configuration for all AI models

This module provides a single source of truth for all AI model configurations,
supporting runtime model selection and easy model switching.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class ModelTask(str, Enum):
    """AI task types"""
    SCRIPT_GENERATION = "script_generation"
    VOICEOVER = "voiceover"
    VIDEO_SCENE = "video_scene"
    CTA_IMAGE = "cta_image"


class ModelConfig(BaseModel):
    """Configuration for a specific AI model"""
    model_id: str  # Replicate model ID (e.g., "meta/llama-2-70b-chat")
    version: Optional[str] = None  # Specific version hash (optional)
    display_name: str
    description: str
    default_params: Dict[str, Any] = {}
    cost_per_run: float = 0.0  # Estimated cost in USD
    avg_duration: float = 0.0  # Average duration in seconds


class ModelRegistry:
    """
    Registry of all available AI models organized by task type.

    Provides:
    - Model discovery and selection
    - Runtime model configuration
    - Default model fallbacks
    - Cost estimation
    """

    # Script Generation Models (Claude, Llama, etc. via Replicate)
    SCRIPT_MODELS: Dict[str, ModelConfig] = {
        "claude-3.5-sonnet": ModelConfig(
            model_id="anthropic/claude-3.5-sonnet",
            display_name="Claude 3.5 Sonnet",
            description="Best for creative, nuanced script generation with vision analysis",
            default_params={
                "max_tokens": 4096,
                "temperature": 0.7,
            },
            cost_per_run=0.015,
            avg_duration=5.0
        ),
        "llama-3.1-70b": ModelConfig(
            model_id="meta/meta-llama-3.1-70b-instruct",
            display_name="Llama 3.1 70B",
            description="Fast, cost-effective script generation",
            default_params={
                "max_tokens": 4096,
                "temperature": 0.7,
            },
            cost_per_run=0.0025,
            avg_duration=3.0
        ),
        "gpt-4-turbo": ModelConfig(
            model_id="openai/gpt-4-turbo",
            display_name="GPT-4 Turbo",
            description="Balanced performance and creativity",
            default_params={
                "max_tokens": 4096,
                "temperature": 0.7,
            },
            cost_per_run=0.01,
            avg_duration=4.0
        ),
    }

    # Voiceover/TTS Models (via Replicate)
    VOICEOVER_MODELS: Dict[str, ModelConfig] = {
        "xtts-v2": ModelConfig(
            model_id="cjwbw/xtts-v2",
            display_name="XTTS v2",
            description="High-quality multilingual TTS with voice cloning",
            default_params={
                "temperature": 0.7,
                "speed": 1.0,
            },
            cost_per_run=0.0001,
            avg_duration=2.0
        ),
        "parler-tts": ModelConfig(
            model_id="parler-tts/parler-tts-large-v1",
            display_name="Parler TTS Large",
            description="Natural sounding English TTS",
            default_params={
                "temperature": 0.7,
            },
            cost_per_run=0.0001,
            avg_duration=1.5
        ),
        "styletts2": ModelConfig(
            model_id="adirik/styletts2",
            display_name="StyleTTS 2",
            description="Expressive TTS with style control",
            default_params={
                "alpha": 0.3,
                "beta": 0.7,
            },
            cost_per_run=0.0002,
            avg_duration=2.5
        ),
    }

    # Video Scene Generation Models (via Replicate)
    VIDEO_MODELS: Dict[str, ModelConfig] = {
        "minimax-video-01": ModelConfig(
            model_id="minimax",
            display_name="Minimax Video-01 (Kling)",
            description="High-quality video generation (6s clips)",
            default_params={
                "duration": "6s",
                "aspect_ratio": "9:16",
            },
            cost_per_run=0.12,
            avg_duration=180.0
        ),
        "ltx-video": ModelConfig(
            model_id="ltxv",
            display_name="LTX Video",
            description="Fast video generation (5s clips)",
            default_params={
                "duration": 5,
                "aspect_ratio": "9:16",
            },
            cost_per_run=0.08,
            avg_duration=90.0
        ),
        "stable-video-diffusion": ModelConfig(
            model_id="svd",
            display_name="Stable Video Diffusion",
            description="Image-to-video generation",
            default_params={
                "frames": 25,
                "motion_bucket_id": 127,
            },
            cost_per_run=0.05,
            avg_duration=60.0
        ),
        "zeroscope-v2": ModelConfig(
            model_id="zeroscope",
            display_name="Zeroscope V2 XL",
            description="Text-to-video generation",
            default_params={
                "num_frames": 24,
                "fps": 8,
            },
            cost_per_run=0.03,
            avg_duration=45.0
        ),
    }

    # CTA Image Generation Models (via Replicate)
    CTA_IMAGE_MODELS: Dict[str, ModelConfig] = {
        "flux-schnell": ModelConfig(
            model_id="black-forest-labs/flux-schnell",
            display_name="FLUX.1 Schnell",
            description="Ultra-fast image generation (2-5s)",
            default_params={
                "num_outputs": 1,
                "aspect_ratio": "9:16",
                "output_format": "png",
            },
            cost_per_run=0.003,
            avg_duration=3.0
        ),
        "flux-dev": ModelConfig(
            model_id="black-forest-labs/flux-dev",
            display_name="FLUX.1 Dev",
            description="Higher quality, slower generation",
            default_params={
                "num_outputs": 1,
                "aspect_ratio": "9:16",
                "output_format": "png",
            },
            cost_per_run=0.0055,
            avg_duration=8.0
        ),
        "sdxl": ModelConfig(
            model_id="stability-ai/sdxl",
            display_name="Stable Diffusion XL",
            description="Versatile image generation",
            default_params={
                "num_outputs": 1,
                "aspect_ratio": "9:16",
            },
            cost_per_run=0.004,
            avg_duration=6.0
        ),
    }

    # Default models for each task
    DEFAULT_MODELS: Dict[ModelTask, str] = {
        ModelTask.SCRIPT_GENERATION: "claude-3.5-sonnet",
        ModelTask.VOICEOVER: "xtts-v2",
        ModelTask.VIDEO_SCENE: "minimax-video-01",
        ModelTask.CTA_IMAGE: "flux-schnell",
    }

    @classmethod
    def get_model(cls, task: ModelTask, model_name: Optional[str] = None) -> ModelConfig:
        """
        Get model configuration for a task.

        Args:
            task: The AI task type
            model_name: Specific model name (optional, uses default if None)

        Returns:
            ModelConfig for the requested model

        Raises:
            ValueError: If model not found
        """
        # Get the appropriate model registry
        registry_map = {
            ModelTask.SCRIPT_GENERATION: cls.SCRIPT_MODELS,
            ModelTask.VOICEOVER: cls.VOICEOVER_MODELS,
            ModelTask.VIDEO_SCENE: cls.VIDEO_MODELS,
            ModelTask.CTA_IMAGE: cls.CTA_IMAGE_MODELS,
        }

        registry = registry_map.get(task)
        if not registry:
            raise ValueError(f"Unknown task type: {task}")

        # Use default if no specific model requested
        if model_name is None:
            model_name = cls.DEFAULT_MODELS[task]

        # Get model config
        model_config = registry.get(model_name)
        if not model_config:
            available = list(registry.keys())
            raise ValueError(
                f"Model '{model_name}' not found for task '{task}'. "
                f"Available models: {available}"
            )

        logger.info(
            "model_selected",
            task=task.value,
            model_name=model_name,
            model_id=model_config.model_id,
            cost=model_config.cost_per_run
        )

        return model_config

    @classmethod
    def list_models(cls, task: ModelTask) -> Dict[str, ModelConfig]:
        """
        List all available models for a task.

        Args:
            task: The AI task type

        Returns:
            Dictionary of model name -> ModelConfig
        """
        registry_map = {
            ModelTask.SCRIPT_GENERATION: cls.SCRIPT_MODELS,
            ModelTask.VOICEOVER: cls.VOICEOVER_MODELS,
            ModelTask.VIDEO_SCENE: cls.VIDEO_MODELS,
            ModelTask.CTA_IMAGE: cls.CTA_IMAGE_MODELS,
        }

        return registry_map.get(task, {})

    @classmethod
    def get_default_model_name(cls, task: ModelTask) -> str:
        """Get the default model name for a task."""
        return cls.DEFAULT_MODELS.get(task, "")

    @classmethod
    def estimate_cost(cls, task: ModelTask, model_name: Optional[str] = None) -> float:
        """
        Estimate cost for running a model.

        Args:
            task: The AI task type
            model_name: Specific model name (optional)

        Returns:
            Estimated cost in USD
        """
        model = cls.get_model(task, model_name)
        return model.cost_per_run
