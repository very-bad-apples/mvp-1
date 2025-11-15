"""
CTA Image Generator with Replicate/FLUX

Generate CTA (Call-to-Action) images using Replicate's FLUX model with text overlay.

Features:
- Fast generation using FLUX.1-schnell (2-5 seconds)
- Text overlay using Pillow
- Style matching (luxury, energetic, minimal, bold)
- Product image integration
- 9:16 vertical format for mobile videos

Dependencies:
- ReplicateClient wrapper (backend/services/replicate_client.py)
- Pillow for text overlay
- ScriptGenerator for CTA text
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from PIL import Image, ImageDraw, ImageFont
import structlog

from services.ai_service import AIService
from pipeline.asset_manager import AssetManager


logger = structlog.get_logger(__name__)


# Style-specific configurations for CTA generation
STYLE_CONFIGS = {
    "luxury": {
        "background_prompt": (
            "elegant gradient background with gold accents, premium feel, "
            "sophisticated lighting, high-end luxury aesthetic, soft glow, "
            "refined and classy, expensive-looking, 9:16 vertical format"
        ),
        "font_family": "Arial",  # Use system font (cross-platform compatible)
        "font_size": 72,
        "font_color": (218, 165, 32),  # Gold
        "text_position": "center",
        "text_shadow": True,
        "shadow_color": (0, 0, 0),
        "shadow_offset": (2, 2),
    },
    "energetic": {
        "background_prompt": (
            "vibrant gradient background, bold colors, dynamic energy, exciting, "
            "electric atmosphere, neon vibes, high contrast, fast-paced feel, "
            "energetic and lively, 9:16 vertical format"
        ),
        "font_family": "Arial",
        "font_size": 80,
        "font_color": (255, 255, 255),  # White
        "text_position": "center",
        "text_shadow": True,
        "shadow_color": (0, 0, 0),
        "shadow_offset": (3, 3),
    },
    "minimal": {
        "background_prompt": (
            "clean white background, simple geometric shapes, modern minimalist, "
            "subtle gradients, elegant simplicity, balanced composition, "
            "minimal design, professional, 9:16 vertical format"
        ),
        "font_family": "Arial",
        "font_size": 64,
        "font_color": (0, 0, 0),  # Black
        "text_position": "center",
        "text_shadow": False,
        "shadow_color": None,
        "shadow_offset": None,
    },
    "bold": {
        "background_prompt": (
            "strong contrasts, dramatic lighting, high impact background, powerful, "
            "intense colors, striking visual, commanding presence, impactful design, "
            "bold statement, 9:16 vertical format"
        ),
        "font_family": "Arial",
        "font_size": 88,
        "font_color": (255, 0, 0),  # Red
        "text_position": "center",
        "text_shadow": True,
        "shadow_color": (0, 0, 0),
        "shadow_offset": (4, 4),
    }
}


class CTAGenerationError(Exception):
    """Raised when CTA image generation fails"""
    pass


class CTAGenerator:
    """
    Generate CTA images using AIService with Replicate's FLUX model.

    Features:
    - Fast generation using FLUX.1-schnell
    - Text overlay using Pillow
    - Style matching (luxury, energetic, minimal, bold)
    - Product image integration
    - 9:16 vertical format for mobile videos

    Example:
        >>> from services.ai_service import AIService
        >>> ai_service = AIService()
        >>> cta_gen = CTAGenerator(ai_service)
        >>> cta_path = await cta_gen.generate_cta(
        ...     cta_text="Shop Now",
        ...     style="luxury",
        ...     asset_manager=am
        ... )
    """

    def __init__(self, ai_service: Optional[AIService] = None):
        """
        Initialize with AIService.

        Args:
            ai_service: Optional AIService instance (creates one if None)
        """
        self.ai_service = ai_service or AIService()
        self.logger = structlog.get_logger(__name__)
        self.model_id = "black-forest-labs/flux-schnell"

        self.logger.info(
            "cta_generator_initialized",
            model_id=self.model_id
        )

    async def generate_cta(
        self,
        cta_text: str,
        style: str,
        product_image_path: Optional[str] = None,
        asset_manager: Optional[AssetManager] = None
    ) -> str:
        """
        Generate CTA image with text overlay.

        Args:
            cta_text: Call-to-action text (e.g., "Shop Now")
            style: Visual style (luxury, energetic, minimal, bold)
            product_image_path: Optional product image (not currently used, reserved for future)
            asset_manager: For file storage (required)

        Returns:
            Path to generated CTA image file

        Raises:
            CTAGenerationError: If generation fails
            ValueError: If style is invalid or asset_manager is missing

        Example:
            >>> cta_path = await cta_gen.generate_cta(
            ...     cta_text="Shop Now",
            ...     style="luxury",
            ...     asset_manager=am
            ... )
        """
        # Validate inputs
        if style not in STYLE_CONFIGS:
            raise ValueError(
                f"Invalid style '{style}'. "
                f"Available styles: {', '.join(STYLE_CONFIGS.keys())}"
            )

        if not asset_manager:
            raise ValueError("asset_manager is required for file storage")

        self.logger.info(
            "generating_cta",
            cta_text=cta_text,
            style=style,
            has_product_image=product_image_path is not None
        )

        try:
            # Step 1: Prepare prompt for background generation
            background_prompt = self._prepare_cta_prompt(cta_text, style)

            # Step 2: Generate background image with FLUX
            self.logger.info("generating_background_image", prompt=background_prompt)
            base_image_path = await self._generate_background_image(
                prompt=background_prompt,
                asset_manager=asset_manager
            )

            # Step 3: Add text overlay to image
            self.logger.info("adding_text_overlay", cta_text=cta_text)
            final_cta_path = self._add_text_overlay(
                image_path=base_image_path,
                cta_text=cta_text,
                style=style
            )

            self.logger.info(
                "cta_generation_complete",
                final_path=final_cta_path
            )

            return final_cta_path

        except Exception as e:
            self.logger.error(
                "cta_generation_failed",
                error=str(e),
                cta_text=cta_text,
                style=style
            )
            raise CTAGenerationError(f"Failed to generate CTA image: {e}")

    def _prepare_cta_prompt(
        self,
        cta_text: str,
        style: str,
        product_name: Optional[str] = None
    ) -> str:
        """
        Prepare image generation prompt for CTA.

        Style-specific prompts:
        - Luxury: "Elegant background with gold accents, premium feel"
        - Energetic: "Vibrant gradient background, bold colors"
        - Minimal: "Clean white background, simple geometric shapes"
        - Bold: "Strong contrasts, dramatic lighting, high impact"

        Note: Don't include actual text in prompt (added later with Pillow)

        Args:
            cta_text: CTA text (for context, not included in prompt)
            style: Visual style
            product_name: Optional product name (for context)

        Returns:
            Prompt string for FLUX model
        """
        config = STYLE_CONFIGS[style]
        base_prompt = config["background_prompt"]

        # Add quality modifiers
        quality_modifiers = (
            "high quality, professional design, commercial use, "
            "vertical format, mobile-friendly, modern design"
        )

        # Combine into final prompt
        # Note: We don't include the actual CTA text here - it's added via Pillow
        full_prompt = f"{base_prompt}, {quality_modifiers}"

        self.logger.debug(
            "prepared_cta_prompt",
            style=style,
            prompt_length=len(full_prompt)
        )

        return full_prompt

    async def _generate_background_image(
        self,
        prompt: str,
        asset_manager: AssetManager
    ) -> str:
        """
        Generate background image using FLUX.1-schnell.

        Args:
            prompt: Image generation prompt
            asset_manager: For file storage

        Returns:
            Path to generated background image

        Raises:
            CTAGenerationError: If generation fails
        """
        try:
            # Run FLUX.1-schnell model via AIService's ReplicateClient
            output = await self.ai_service.client.run_model_async(
                model_id=self.model_id,
                input_params={
                    "prompt": prompt,
                    "width": 1080,
                    "height": 1920,  # 9:16 vertical format
                    "num_outputs": 1,
                    "num_inference_steps": 4,  # Fast generation (schnell model)
                }
            )

            # Download the generated image
            # FLUX models return a list of FileOutput objects
            if not output or len(output) == 0:
                raise CTAGenerationError("FLUX model returned no output")

            # Create temp directory path
            temp_dir = Path(str(asset_manager.job_dir))
            temp_dir.mkdir(parents=True, exist_ok=True)

            base_image_path = temp_dir / "cta_base.png"

            # Download output to file
            downloaded_path = self.ai_service.client.download_output(
                output[0],
                str(base_image_path)
            )

            self.logger.info(
                "background_image_generated",
                path=downloaded_path
            )

            return downloaded_path

        except Exception as e:
            self.logger.error(
                "background_generation_failed",
                error=str(e),
                prompt=prompt
            )
            raise CTAGenerationError(f"Failed to generate background image: {e}")

    def _add_text_overlay(
        self,
        image_path: str,
        cta_text: str,
        style: str
    ) -> str:
        """
        Add text overlay to generated image using Pillow.

        Args:
            image_path: Path to base image from FLUX
            cta_text: Text to overlay
            style: Style for font/positioning

        Returns:
            Path to image with text overlay

        Raises:
            CTAGenerationError: If text overlay fails

        Example:
            >>> final_path = self._add_text_overlay(
            ...     "/tmp/cta_base.png",
            ...     "Shop Now",
            ...     "luxury"
            ... )
        """
        try:
            # Load image
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)

            # Get style config
            config = STYLE_CONFIGS[style]

            # Load font (use default if custom font not available)
            try:
                # Try to use system font
                font = ImageFont.truetype(config["font_family"], config["font_size"])
            except IOError:
                # Fallback to default font if specific font not found
                self.logger.warning(
                    "custom_font_not_found",
                    font_family=config["font_family"],
                    fallback="default"
                )
                # Use default font with size approximation
                font = ImageFont.load_default()

            # Calculate text bounding box
            bbox = draw.textbbox((0, 0), cta_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Calculate center position
            x = (img.width - text_width) / 2
            y = (img.height - text_height) / 2

            # Add shadow if configured
            if config.get("text_shadow", False):
                shadow_offset = config["shadow_offset"]
                shadow_color = config["shadow_color"]

                draw.text(
                    (x + shadow_offset[0], y + shadow_offset[1]),
                    cta_text,
                    font=font,
                    fill=shadow_color
                )

            # Draw main text
            draw.text(
                (x, y),
                cta_text,
                font=font,
                fill=config["font_color"]
            )

            # Save final image
            output_path = image_path.replace("_base.png", "_final.png")
            img.save(output_path)

            self.logger.info(
                "text_overlay_added",
                final_path=output_path,
                cta_text=cta_text,
                style=style
            )

            return output_path

        except Exception as e:
            self.logger.error(
                "text_overlay_failed",
                error=str(e),
                image_path=image_path,
                cta_text=cta_text
            )
            raise CTAGenerationError(f"Failed to add text overlay: {e}")


def create_cta_generator(ai_service: Optional[AIService] = None) -> CTAGenerator:
    """
    Factory function to create a CTAGenerator instance.

    Args:
        ai_service: Optional AIService instance (creates one if None)

    Returns:
        Configured CTAGenerator instance

    Example:
        >>> cta_gen = create_cta_generator()
        >>> cta_path = await cta_gen.generate_cta(...)
    """
    return CTAGenerator(ai_service=ai_service)
