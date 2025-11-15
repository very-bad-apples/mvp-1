"""
Video Scene Generator with Replicate/Kling Integration

Generates video scenes using ReplicateClient wrapper and various video generation models.
Supports multiple scene types, style coherence, and async batch generation.

Key Features:
- Multiple video model support (Minimax Video-01, LTX Video, Stable Video Diffusion)
- Style coherence (luxury, energetic, minimal, bold)
- Product image compositing for hero shots
- Async batch generation for all scenes
- Integration with ScriptGenerator and AssetManager
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

import structlog
from services.ai_service import AIService
from pipeline.asset_manager import AssetManager

logger = structlog.get_logger(__name__)


# Style-specific video generation parameters
STYLE_CONFIGS = {
    "luxury": {
        "prompt_suffix": "soft lighting, elegant camera movement, premium aesthetics, sophisticated, cinematic depth of field, refined composition, gentle pacing",
        "duration": 5,
        "fps": 24,
        "aspect_ratio": "9:16",
        "motion_intensity": "low",  # Smooth, subtle movements
    },
    "energetic": {
        "prompt_suffix": "dynamic transitions, vibrant colors, fast-paced, bold movements, energetic motion, exciting composition, high energy",
        "duration": 5,
        "fps": 30,
        "aspect_ratio": "9:16",
        "motion_intensity": "high",  # Fast, dynamic movements
    },
    "minimal": {
        "prompt_suffix": "clean composition, simple movements, muted palette, modern, minimal aesthetic, understated elegance, calm pacing",
        "duration": 5,
        "fps": 24,
        "aspect_ratio": "9:16",
        "motion_intensity": "low",  # Minimal, subtle movements
    },
    "bold": {
        "prompt_suffix": "strong contrasts, dramatic angles, impactful visuals, powerful composition, striking atmosphere, bold presentation",
        "duration": 5,
        "fps": 24,
        "aspect_ratio": "9:16",
        "motion_intensity": "medium",  # Confident, deliberate movements
    }
}


# Available video generation models on Replicate
VIDEO_MODELS = {
    # Minimax Video-01 - High quality text-to-video (recommended)
    "minimax": "minimax/video-01",

    # Seedance Models - ByteDance video generation
    "seedance-fast": "bytedance/seedance-1-pro-fast",  # Faster and cheaper
    "seedance-pro": "bytedance/seedance-1-pro",  # Cinematic quality

    # Hailuo - Minimax high-fidelity video generation
    "hailuo": "minimax/hailuo-2.3",
    "hailuo-fast": "minimax/hailuo-2.3-fast",

    # LTX Video - Fast text-to-video generation
    "ltxv": "fofr/ltxv",
    "ltx-2-fast": "lightricks/ltx-2-fast",  # Ideal for rapid ideation

    # Google Veo - Higher-fidelity with context-aware audio
    "veo": "google/veo-3.1",

    # OpenAI Sora - Flagship video generation with synced audio
    "sora": "openai/sora-2",

    # Stable Video Diffusion - Image-to-video (for product shots)
    "svd": "stability-ai/stable-video-diffusion",

    # Zeroscope V2 XL - Open source text-to-video
    "zeroscope": "anotherjesse/zeroscope-v2-xl",

    # Hotshot-XL - Fast image-to-video
    "hotshot": "lucataco/hotshot-xl",
}


class VideoGenerationError(Exception):
    """Raised when video generation fails"""
    pass


class VideoGenerator:
    """
    Generate video scenes using AIService with Replicate models.

    Features:
    - Multiple scene type support (product showcase, lifestyle, motion)
    - Style coherence (luxury, energetic, minimal, bold)
    - Product image compositing for hero shots
    - Async batch generation for all scenes
    - Integration with AIService for unified API access

    Example:
        >>> from services.ai_service import AIService
        >>> ai_service = AIService()
        >>> video_gen = VideoGenerator(ai_service)
        >>> scene_config = {"video_prompt_template": "Product showcase..."}
        >>> video_path = await video_gen.generate_scene(
        ...     scene_config,
        ...     style="luxury",
        ...     asset_manager=am
        ... )
    """

    def __init__(
        self,
        ai_service: Optional[AIService] = None,
        model_preference: str = "minimax"
    ):
        """
        Initialize VideoGenerator with AIService.

        Args:
            ai_service: Optional AIService instance (creates one if None)
            model_preference: Preferred video model (minimax, ltxv, svd, zeroscope, hotshot)

        Raises:
            ValueError: If model_preference is invalid
        """
        self.ai_service = ai_service or AIService()

        if model_preference not in VIDEO_MODELS:
            raise ValueError(
                f"Invalid model preference '{model_preference}'. "
                f"Available models: {', '.join(VIDEO_MODELS.keys())}"
            )

        self.model_id = VIDEO_MODELS[model_preference]
        self.model_preference = model_preference
        self.logger = structlog.get_logger().bind(
            service="video_generator",
            model=self.model_id
        )

        self.logger.info(
            "video_generator_initialized",
            model=self.model_id,
            preference=model_preference
        )

    def _prepare_video_prompt(
        self,
        template: str,
        style: str,
        product_name: Optional[str] = None
    ) -> str:
        """
        Prepare video generation prompt from template.

        Enhances template with style-specific parameters to ensure
        visual coherence across all scenes in the video.

        Args:
            template: Base video prompt template from scene config
            style: Video style (luxury, energetic, minimal, bold)
            product_name: Optional product name for context

        Returns:
            Enhanced prompt with style-specific parameters

        Example:
            >>> prompt = self._prepare_video_prompt(
            ...     "Product showcase with smooth camera movement",
            ...     "luxury",
            ...     "Premium Watch"
            ... )
            >>> print(prompt)
            Product showcase with smooth camera movement, soft lighting, elegant...
        """
        style_config = STYLE_CONFIGS.get(style, STYLE_CONFIGS["luxury"])

        # Start with base template
        enhanced_prompt = template

        # Add style-specific enhancements
        suffix = style_config["prompt_suffix"]
        enhanced_prompt = f"{enhanced_prompt}, {suffix}"

        # Add technical specifications
        enhanced_prompt = f"{enhanced_prompt}, {style_config['fps']} fps, high quality, professional"

        self.logger.debug(
            "prompt_prepared",
            style=style,
            template_length=len(template),
            enhanced_length=len(enhanced_prompt)
        )

        return enhanced_prompt

    def _get_model_input_params(
        self,
        prompt: str,
        style: str,
        product_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get model-specific input parameters.

        Different models have different input schemas. This method
        adapts the generic parameters to each model's requirements.

        Args:
            prompt: Video generation prompt
            style: Video style
            product_image_path: Optional product image for image-to-video models

        Returns:
            Dictionary of model-specific input parameters
        """
        style_config = STYLE_CONFIGS.get(style, STYLE_CONFIGS["luxury"])

        # Base parameters for most models
        base_params = {
            "prompt": prompt,
        }

        # Model-specific parameter adaptations
        if self.model_preference == "minimax":
            # Minimax Video-01 parameters
            return {
                "prompt": prompt,
                "prompt_optimizer": True,
            }

        elif self.model_preference == "ltxv":
            # LTX Video parameters
            return {
                "prompt": prompt,
                "num_frames": style_config["fps"] * style_config["duration"],
                "aspect_ratio": style_config["aspect_ratio"],
            }

        elif self.model_preference == "svd":
            # Stable Video Diffusion (image-to-video)
            if not product_image_path:
                raise VideoGenerationError(
                    "Stable Video Diffusion requires product_image_path for image-to-video generation"
                )
            return {
                "image": open(product_image_path, "rb"),
                "motion_bucket_id": 127 if style_config["motion_intensity"] == "high" else 50,
                "fps": style_config["fps"],
            }

        elif self.model_preference == "zeroscope":
            # Zeroscope V2 XL parameters
            return {
                "prompt": prompt,
                "num_frames": style_config["fps"] * style_config["duration"],
                "fps": style_config["fps"],
            }

        elif self.model_preference == "hotshot":
            # Hotshot-XL (image-to-video)
            if not product_image_path:
                raise VideoGenerationError(
                    "Hotshot-XL requires product_image_path for image-to-video generation"
                )
            return {
                "image": open(product_image_path, "rb"),
                "prompt": prompt,
            }

        # Fallback to base parameters
        return base_params

    async def generate_scene(
        self,
        scene_config: dict,
        style: str,
        product_image_path: Optional[str] = None,
        asset_manager: Optional[AssetManager] = None,
        scene_id: Optional[int] = None
    ) -> str:
        """
        Generate a single video scene.

        Args:
            scene_config: Scene configuration from script (includes video_prompt_template)
            style: Video style (luxury, energetic, minimal, bold)
            product_image_path: Optional product image for compositing
            asset_manager: AssetManager for file storage
            scene_id: Optional scene ID for filename

        Returns:
            Path to generated video file

        Raises:
            VideoGenerationError: If video generation fails

        Example:
            >>> scene_config = {
            ...     "id": 1,
            ...     "video_prompt_template": "Product showcase with elegant lighting",
            ...     "use_product_image": True
            ... }
            >>> video_path = await video_gen.generate_scene(
            ...     scene_config,
            ...     "luxury",
            ...     product_image_path="./product.jpg",
            ...     asset_manager=am
            ... )
        """
        self.logger.info(
            "generating_scene",
            scene_id=scene_id or scene_config.get("id"),
            style=style,
            has_product_image=product_image_path is not None
        )

        try:
            # Get video prompt template from scene config
            video_prompt_template = scene_config.get("video_prompt_template")
            if not video_prompt_template:
                raise VideoGenerationError(
                    f"Scene config missing 'video_prompt_template': {scene_config}"
                )

            # Prepare enhanced prompt with style parameters
            video_prompt = self._prepare_video_prompt(
                video_prompt_template,
                style
            )

            # Determine if this scene should use product image
            use_product_image = scene_config.get("use_product_image", False)
            image_path = product_image_path if use_product_image else None

            # Get model-specific input parameters
            input_params = self._get_model_input_params(
                video_prompt,
                style,
                product_image_path=image_path
            )

            self.logger.info(
                "running_model",
                model=self.model_id,
                prompt_length=len(video_prompt),
                use_product_image=use_product_image
            )

            # Generate video using AIService's ReplicateClient
            output = await self.ai_service.client.run_model_async(
                model_id=self.model_id,
                input_params=input_params
            )

            # Handle output based on model response format
            video_url = None
            if isinstance(output, list) and len(output) > 0:
                # Most models return a list with video URL
                video_url = output[0]
            elif hasattr(output, 'url'):
                # Some models return FileOutput object
                video_url = output.url()
            elif isinstance(output, str):
                # Some models return direct URL string
                video_url = output
            else:
                raise VideoGenerationError(
                    f"Unexpected output format from {self.model_id}: {type(output)}"
                )

            # Download video if asset manager provided
            if asset_manager:
                scene_filename = f"scene_{scene_id or scene_config.get('id', 'unknown')}.mp4"
                video_path = await asset_manager.download_with_retry(
                    url=video_url,
                    filename=scene_filename,
                    subdir="scenes"
                )

                # Validate downloaded file
                is_valid = await asset_manager.validate_file(
                    scene_filename,
                    subdir="scenes",
                    min_size=1024  # At least 1KB
                )

                if not is_valid:
                    raise VideoGenerationError(
                        f"Generated video file is invalid: {video_path}"
                    )

                self.logger.info(
                    "scene_generated_success",
                    scene_id=scene_id,
                    video_path=video_path
                )

                return video_path

            # Return URL if no asset manager
            self.logger.info(
                "scene_generated_url",
                scene_id=scene_id,
                video_url=video_url
            )
            return video_url

        except Exception as e:
            self.logger.error(
                "scene_generation_failed",
                scene_id=scene_id,
                error=str(e)
            )
            raise VideoGenerationError(
                f"Failed to generate scene {scene_id}: {e}"
            ) from e

    async def generate_all_scenes(
        self,
        script: dict,
        style: str,
        product_image_path: Optional[str] = None,
        asset_manager: Optional[AssetManager] = None
    ) -> List[str]:
        """
        Generate all video scenes from script in parallel.

        Uses asyncio.gather to generate multiple scenes concurrently,
        significantly reducing total generation time.

        Args:
            script: Complete script from ScriptGenerator
            style: Video style
            product_image_path: Optional product image
            asset_manager: AssetManager for file storage

        Returns:
            List of video file paths (or URLs if no asset_manager)

        Raises:
            VideoGenerationError: If any scene generation fails

        Example:
            >>> script = script_gen.generate_script(...)
            >>> video_paths = await video_gen.generate_all_scenes(
            ...     script,
            ...     "luxury",
            ...     product_image_path="./product.jpg",
            ...     asset_manager=am
            ... )
            >>> print(f"Generated {len(video_paths)} scenes")
        """
        self.logger.info(
            "generating_all_scenes",
            num_scenes=len(script.get("scenes", [])),
            style=style,
            has_product_image=product_image_path is not None
        )

        scenes = script.get("scenes", [])
        if not scenes:
            raise VideoGenerationError("Script contains no scenes")

        # Filter out scenes that are images (type="image")
        # We only generate videos here
        video_scenes = [s for s in scenes if s.get("type") == "video"]

        if not video_scenes:
            self.logger.warning("no_video_scenes_in_script")
            return []

        self.logger.info(
            "filtering_scenes",
            total_scenes=len(scenes),
            video_scenes=len(video_scenes)
        )

        try:
            # Generate all scenes in parallel using asyncio.gather
            tasks = [
                self.generate_scene(
                    scene_config=scene,
                    style=style,
                    product_image_path=product_image_path,
                    asset_manager=asset_manager,
                    scene_id=scene.get("id")
                )
                for scene in video_scenes
            ]

            # Wait for all scenes to complete
            video_paths = await asyncio.gather(*tasks)

            self.logger.info(
                "all_scenes_generated",
                num_scenes=len(video_paths),
                style=style
            )

            return video_paths

        except Exception as e:
            self.logger.error(
                "batch_generation_failed",
                error=str(e)
            )
            raise VideoGenerationError(
                f"Failed to generate all scenes: {e}"
            ) from e

    async def _composite_product_image(
        self,
        video_path: str,
        product_image_path: str,
        style: str
    ) -> str:
        """
        Composite product image into video frame.

        This is a placeholder for future implementation.
        For MVP, we rely on prompt-based integration or image-to-video models.

        Future implementation could use:
        - FFmpeg overlays
        - Image compositing libraries
        - Additional Replicate models for compositing

        Args:
            video_path: Path to generated video
            product_image_path: Path to product image
            style: Video style for compositing parameters

        Returns:
            Path to composited video
        """
        self.logger.warning(
            "product_compositing_not_implemented",
            video_path=video_path,
            product_image_path=product_image_path
        )

        # For now, just return the original video
        # In a full implementation, this would composite the product image
        return video_path


def create_video_generator(
    ai_service: Optional[AIService] = None,
    model_preference: str = "minimax"
) -> VideoGenerator:
    """
    Factory function to create a VideoGenerator instance.

    Args:
        ai_service: Optional AIService instance (creates one if None)
        model_preference: Preferred video model (minimax, ltxv, svd, zeroscope, hotshot)

    Returns:
        Configured VideoGenerator instance

    Example:
        >>> from services.ai_service import AIService
        >>> ai_service = AIService()
        >>> video_gen = create_video_generator(ai_service, model_preference="minimax")
    """
    return VideoGenerator(
        ai_service=ai_service,
        model_preference=model_preference
    )
