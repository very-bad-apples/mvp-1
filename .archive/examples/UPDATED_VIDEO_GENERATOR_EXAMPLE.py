"""
EXAMPLE: Updated VideoGenerator using the new parameter system

This shows how to integrate the video_model_params system into the existing VideoGenerator.
Replace the _get_model_input_params method with this approach.
"""

from typing import Dict, Any, Optional
import structlog
from services.video_model_params import (
    VideoModelParameters,
    VideoParameterAdapter,
    AspectRatio,
    get_model_spec,
    STYLE_CONFIGS  # You'll need to import this or define it
)

logger = structlog.get_logger(__name__)


class UpdatedVideoGenerator:
    """
    Example of how to update VideoGenerator to use the new parameter system.

    Key changes:
    1. Use VideoModelParameters as the unified parameter interface
    2. Use VideoParameterAdapter to translate to model-specific params
    3. Validate parameters against model capabilities
    """

    def __init__(self, ai_service, model_preference: str = "minimax"):
        self.ai_service = ai_service
        self.model_preference = model_preference

        # Get model spec to validate it exists
        self.model_spec = get_model_spec(model_preference)
        self.logger = structlog.get_logger().bind(
            service="video_generator",
            model=self.model_spec.model_id
        )

    def _prepare_unified_params(
        self,
        prompt: str,
        style: str,
        scene_config: dict,
        product_image_path: Optional[str] = None
    ) -> VideoModelParameters:
        """
        Create unified VideoModelParameters from scene configuration.

        This method translates our template-based scene configs into
        the new unified parameter format.
        """
        style_config = STYLE_CONFIGS.get(style, STYLE_CONFIGS["luxury"])

        # Determine if we should use product image
        use_product_image = scene_config.get("use_product_image", False)
        first_frame = product_image_path if use_product_image else None

        # Map style to aspect ratio
        aspect_ratio = AspectRatio(style_config.get("aspect_ratio", "9:16"))

        # Map motion intensity
        motion_intensity = style_config.get("motion_intensity", "medium")

        # Get duration from scene config or style config
        duration = scene_config.get("duration", style_config.get("duration", 5))

        # Create unified parameters
        params = VideoModelParameters(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            duration=duration,
            fps=style_config.get("fps", 24),
            first_frame_image=first_frame,
            motion_intensity=motion_intensity,
            prompt_optimizer=True,  # Enable for models that support it
            guidance_scale=7.5,
            num_inference_steps=50,
        )

        return params

    def _get_model_input_params(
        self,
        prompt: str,
        style: str,
        scene_config: dict,
        product_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        NEW IMPLEMENTATION: Get model-specific input parameters.

        This replaces the old hardcoded approach with the new adapter system.

        Args:
            prompt: Video generation prompt
            style: Video style (luxury, energetic, minimal, bold)
            scene_config: Scene configuration from template
            product_image_path: Optional product image for image-to-video models

        Returns:
            Dictionary of model-specific input parameters
        """

        # Step 1: Create unified parameters
        unified_params = self._prepare_unified_params(
            prompt, style, scene_config, product_image_path
        )

        # Step 2: Log the unified parameters
        self.logger.info(
            "preparing_model_params",
            model=self.model_preference,
            duration=unified_params.duration,
            aspect_ratio=unified_params.aspect_ratio,
            has_first_frame=unified_params.first_frame_image is not None
        )

        # Step 3: Adapt to model-specific parameters
        try:
            model_params = VideoParameterAdapter.adapt_for_model(
                self.model_preference,
                unified_params
            )

            self.logger.info(
                "model_params_adapted",
                model=self.model_preference,
                param_keys=list(model_params.keys())
            )

            return model_params

        except ValueError as e:
            # Log validation error and provide fallback
            self.logger.error(
                "param_validation_failed",
                model=self.model_preference,
                error=str(e)
            )

            # Fallback to basic parameters
            return {
                "prompt": prompt,
            }

    async def generate_scene(
        self,
        scene_config: dict,
        style: str,
        product_image_path: Optional[str] = None,
        asset_manager = None,
        scene_id: Optional[int] = None
    ) -> str:
        """
        Generate a single video scene using the new parameter system.

        This method now:
        1. Uses the unified parameter interface
        2. Automatically validates parameters against model capabilities
        3. Adapts parameters to model-specific requirements
        """

        self.logger.info(
            "generating_scene",
            scene_id=scene_id or scene_config.get("id"),
            style=style,
            model=self.model_preference
        )

        # Get video prompt from template
        video_prompt_template = scene_config.get("video_prompt_template")
        if not video_prompt_template:
            raise ValueError(f"Scene config missing 'video_prompt_template': {scene_config}")

        # Prepare enhanced prompt with style parameters
        enhanced_prompt = self._prepare_video_prompt(
            video_prompt_template,
            style
        )

        # Get model-specific parameters using NEW adapter system
        input_params = self._get_model_input_params(
            enhanced_prompt,
            style,
            scene_config,
            product_image_path
        )

        self.logger.info(
            "running_model",
            model=self.model_spec.model_id,
            params=input_params
        )

        # Generate video using AIService
        output = await self.ai_service.client.run_model_async(
            model_id=self.model_spec.model_id,
            input_params=input_params
        )

        # Download and return video path
        # ... rest of implementation ...

        return "path/to/video.mp4"

    def _prepare_video_prompt(self, template: str, style: str) -> str:
        """Enhance prompt with style-specific parameters"""
        style_config = STYLE_CONFIGS.get(style, STYLE_CONFIGS["luxury"])
        suffix = style_config["prompt_suffix"]
        return f"{template}, {suffix}"


# ==================== USAGE EXAMPLES ====================


async def example_usage():
    """Example of how to use the updated video generator"""

    from services.ai_service import AIService

    # Initialize with specific model
    ai_service = AIService()
    video_gen = UpdatedVideoGenerator(ai_service, model_preference="minimax")

    # Scene configuration from template
    scene_config = {
        "id": 1,
        "duration": 8,
        "type": "video",
        "video_prompt_template": "Close-up of premium watch, elegant lighting",
        "use_product_image": True,
    }

    # Generate scene - parameters are automatically adapted
    video_path = await video_gen.generate_scene(
        scene_config=scene_config,
        style="luxury",
        product_image_path="./product.jpg",
        scene_id=1
    )

    print(f"Generated video: {video_path}")


async def example_model_switching():
    """Example of switching between different video models"""

    from services.ai_service import AIService
    from services.video_model_params import get_model_info

    ai_service = AIService()

    # Compare different models
    models_to_try = ["minimax", "ltxv", "seedance-pro"]

    for model_name in models_to_try:
        # Get model capabilities
        info = get_model_info(model_name)
        print(f"\n{info['display_name']}:")
        print(f"  Max duration: {info['duration']['max_seconds']}s")
        print(f"  Cost per second: ${info['cost']['per_second_usd']:.3f}")
        print(f"  Supports image-to-video: {info['features']['image_to_video']}")

        # Create generator with this model
        video_gen = UpdatedVideoGenerator(ai_service, model_preference=model_name)

        # Generate scene - same interface, different model!
        # Parameters are automatically adapted to each model's requirements


async def example_direct_parameter_control():
    """
    Example of using VideoModelParameters directly for full control.

    This bypasses the template system for advanced use cases.
    """

    from services.video_model_params import VideoModelParameters, VideoParameterAdapter

    # Create custom parameters
    custom_params = VideoModelParameters(
        prompt="Cinematic shot of luxury watch rotating on pedestal",
        aspect_ratio=AspectRatio.PORTRAIT,
        duration=6.0,
        fps=25,
        first_frame_image="./product.jpg",
        guidance_scale=8.0,
        num_inference_steps=50,
        prompt_optimizer=True,
        motion_intensity="low",  # Smooth, subtle motion
        seed=42,  # Reproducible results
    )

    # Try with different models
    for model_name in ["minimax", "ltxv", "svd"]:
        try:
            model_params = VideoParameterAdapter.adapt_for_model(
                model_name,
                custom_params
            )
            print(f"\n{model_name} parameters:")
            print(model_params)
        except ValueError as e:
            print(f"\n{model_name}: {e}")


# ==================== MIGRATION GUIDE ====================

"""
MIGRATION GUIDE: How to update existing video_generator.py

1. Add import at the top:
   ```python
   from services.video_model_params import (
       VideoModelParameters,
       VideoParameterAdapter,
       AspectRatio,
       get_model_spec
   )
   ```

2. Update __init__ to get model spec:
   ```python
   def __init__(self, ai_service, model_preference: str = "minimax"):
       self.model_spec = get_model_spec(model_preference)
       self.model_id = self.model_spec.model_id
       # ... rest of init
   ```

3. Replace _get_model_input_params method with the new version from
   UpdatedVideoGenerator above.

4. Add _prepare_unified_params method from UpdatedVideoGenerator.

5. Optional: Expose model capabilities to users via API:
   ```python
   def get_model_capabilities(self):
       return self.model_spec.capabilities
   ```

BENEFITS:
- Single source of truth for model parameters
- Easy to add new models
- Automatic parameter validation
- Type safety with Pydantic
- Easy model switching
- Clear documentation of what each model supports
"""


if __name__ == "__main__":
    import asyncio

    # Run examples
    print("=" * 60)
    print("EXAMPLE: Model Information")
    print("=" * 60)

    from services.video_model_params import get_model_info, list_models

    # Show all available models
    print("\nAvailable models:")
    for name, spec in list_models().items():
        print(f"  - {name}: {spec.display_name}")

    # Show detailed info for minimax
    print("\n" + "=" * 60)
    print("EXAMPLE: Minimax Model Details")
    print("=" * 60)
    info = get_model_info("minimax")
    import json
    print(json.dumps(info, indent=2))

    # Show parameter adaptation
    print("\n" + "=" * 60)
    print("EXAMPLE: Parameter Adaptation")
    print("=" * 60)
    asyncio.run(example_direct_parameter_control())
