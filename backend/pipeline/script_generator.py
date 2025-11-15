"""
Script Generator with Claude Integration

Uses Claude 3.5 Sonnet API to analyze product images and generate
structured scene JSON with voiceovers, hooks, and CTAs.

This module integrates with the template system to create compelling
video scripts based on product information and visual analysis.
"""

import base64
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import time

from config import settings
from pipeline.templates import get_scene_template, fill_template, validate_template, get_available_styles
from services.ai_service import AIService

# Configure logging
logger = logging.getLogger(__name__)


class ScriptGenerationError(Exception):
    """Raised when script generation fails"""
    pass


class ScriptGenerator:
    """
    Generates video scripts using AIService with Claude via Replicate

    Features:
    - Product image analysis using Claude's vision capabilities via Replicate
    - Template-based scene generation
    - Automatic voiceover text generation
    - Hook and CTA creation
    - Retry logic built into AIService
    """

    def __init__(self, ai_service: Optional[AIService] = None):
        """
        Initialize the script generator

        Args:
            ai_service: Optional AIService instance (creates one if None)
        """
        self.ai_service = ai_service or AIService()
        logger.info("ScriptGenerator initialized with AIService")

    def _create_analysis_prompt(self, product_name: str, style: str) -> str:
        """Create prompt for product image analysis"""
        return f"""Analyze this product image for "{product_name}" to create a compelling video advertisement.

Style: {style}

Please provide:
1. Product description: What is this product? What are its key visual features?
2. Key benefits: What problems does it solve? What value does it provide?
3. Target audience: Who would use this product?
4. Unique selling points: What makes it stand out?
5. Emotional appeal: What emotions should the ad evoke?

Respond in JSON format:
{{
    "product_description": "detailed description",
    "key_benefits": ["benefit1", "benefit2", "benefit3"],
    "target_audience": "audience description",
    "unique_selling_points": ["usp1", "usp2"],
    "emotional_appeal": "emotion description"
}}"""

    def _create_voiceover_prompt(
        self,
        product_analysis: Dict[str, Any],
        product_name: str,
        style: str,
        scene_template: Dict[str, Any]
    ) -> str:
        """Create prompt for generating voiceover scripts"""
        benefits = "\n".join(f"- {b}" for b in product_analysis.get('key_benefits', []))
        usps = "\n".join(f"- {u}" for u in product_analysis.get('unique_selling_points', []))

        return f"""Generate voiceover scripts for a {style} style video ad for "{product_name}".

Product Analysis:
- Description: {product_analysis.get('product_description', '')}
- Target Audience: {product_analysis.get('target_audience', '')}
- Emotional Appeal: {product_analysis.get('emotional_appeal', '')}

Key Benefits:
{benefits}

Unique Selling Points:
{usps}

Create voiceover text for each scene following these templates:
Scene 1 (8s): {scene_template['scenes'][0]['voiceover_template']}
Scene 2 (8s): {scene_template['scenes'][1]['voiceover_template']}
Scene 3 (10s): {scene_template['scenes'][2]['voiceover_template']}
Scene 4 (4s): {scene_template['scenes'][3]['voiceover_template']}

Requirements:
- Scene 1: Hook that grabs attention immediately
- Scene 2: Highlight a key benefit (fill [benefit statement])
- Scene 3: Include social proof or credibility (fill [social proof])
- Scene 4: Strong call-to-action
- Each voiceover should match the {style} style
- Keep timing appropriate for scene duration
- Make it conversational and engaging

Respond in JSON format:
{{
    "scene_1_voiceover": "text for scene 1",
    "scene_2_voiceover": "text for scene 2",
    "scene_3_voiceover": "text for scene 3",
    "scene_4_voiceover": "text for scene 4",
    "hook": "compelling hook text",
    "cta": "strong call-to-action"
}}"""

    async def analyze_product_image(
        self,
        image_path: str,
        product_name: str,
        style: str
    ) -> Dict[str, Any]:
        """
        Analyze product image using Claude's vision API via Replicate

        Args:
            image_path: Path to product image
            product_name: Name of the product
            style: Visual style (luxury, energetic, minimal, bold)

        Returns:
            Dictionary containing product analysis

        Raises:
            ScriptGenerationError: If analysis fails
        """
        logger.info(f"Analyzing product image: {image_path}")

        try:
            # Create analysis prompt
            prompt = self._create_analysis_prompt(product_name, style)

            # Call AIService for vision analysis
            analysis_text = await self.ai_service.analyze_image_with_text(
                image_path=image_path,
                prompt=prompt,
                max_tokens=2048
            )

            # Parse JSON response
            analysis = json.loads(analysis_text)

            logger.info("Product image analysis completed successfully")
            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis JSON: {e}")
            raise ScriptGenerationError(f"Invalid JSON response from AI: {e}")
        except FileNotFoundError as e:
            logger.error(f"Image file not found: {e}")
            raise ScriptGenerationError(str(e))
        except Exception as e:
            logger.error(f"Product image analysis failed: {e}")
            raise ScriptGenerationError(f"Failed to analyze product image: {e}")

    async def generate_voiceovers(
        self,
        product_analysis: Dict[str, Any],
        product_name: str,
        style: str,
        scene_template: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate voiceover scripts using AIService

        Args:
            product_analysis: Analysis from analyze_product_image()
            product_name: Name of the product
            style: Visual style
            scene_template: Template from get_scene_template()

        Returns:
            Dictionary with voiceover texts and CTA

        Raises:
            ScriptGenerationError: If generation fails
        """
        logger.info(f"Generating voiceovers for {product_name} in {style} style")

        try:
            # Create voiceover prompt
            prompt = self._create_voiceover_prompt(
                product_analysis, product_name, style, scene_template
            )

            # Call AIService for text generation
            voiceover_text = await self.ai_service.generate_text(
                prompt=prompt,
                max_tokens=1024
            )

            # Parse JSON response
            voiceovers = json.loads(voiceover_text)

            logger.info("Voiceover generation completed successfully")
            return voiceovers

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse voiceover JSON: {e}")
            raise ScriptGenerationError(f"Invalid JSON response from AI: {e}")
        except Exception as e:
            logger.error(f"Voiceover generation failed: {e}")
            raise ScriptGenerationError(f"Failed to generate voiceovers: {e}")

    async def generate_script(
        self,
        product_name: str,
        style: str,
        cta_text: str,
        product_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate complete video script with AIService integration

        This is the main entry point that orchestrates:
        1. Load scene template for the specified style
        2. Analyze product image (if provided) using Claude vision via Replicate
        3. Generate voiceovers using Claude via Replicate
        4. Fill template with generated content
        5. Validate and return structured scene JSON

        Args:
            product_name: Name of the product
            style: Visual style (luxury, energetic, minimal, bold)
            cta_text: Call-to-action text (e.g., "Shop Now")
            product_image_path: Optional path to product image for analysis

        Returns:
            Dictionary containing complete scene specification:
            {
                "total_duration": 30,
                "style": "luxury",
                "product_name": "Premium Watch",
                "scenes": [...],
                "product_analysis": {...}  # if image provided
            }

        Raises:
            ScriptGenerationError: If script generation fails
            ValueError: If style is invalid

        Example:
            >>> generator = ScriptGenerator()
            >>> script = await generator.generate_script(
            ...     product_name="Premium Headphones",
            ...     style="luxury",
            ...     cta_text="Shop Now",
            ...     product_image_path="./product.jpg"
            ... )
            >>> print(script['scenes'][0]['voiceover_text'])
        """
        logger.info(
            f"Generating script for '{product_name}' in {style} style "
            f"(CTA: '{cta_text}')"
        )

        # Validate style
        available_styles = get_available_styles()
        if style not in available_styles:
            raise ValueError(
                f"Invalid style '{style}'. Available styles: {', '.join(available_styles)}"
            )

        try:
            # Step 1: Load scene template
            logger.info(f"Loading {style} template")
            template = get_scene_template(style)

            # Step 2: Analyze product image if provided
            product_analysis = None
            if product_image_path:
                logger.info("Analyzing product image with AIService")
                product_analysis = await self.analyze_product_image(
                    product_image_path, product_name, style
                )
            else:
                logger.info("No product image provided, using minimal analysis")
                # Create minimal analysis for voiceover generation
                product_analysis = {
                    "product_description": f"{product_name}",
                    "key_benefits": [
                        "Premium quality",
                        "Great value",
                        "Customer satisfaction"
                    ],
                    "target_audience": "Discerning customers",
                    "unique_selling_points": ["Quality craftsmanship", "Innovative design"],
                    "emotional_appeal": "Confidence and satisfaction"
                }

            # Step 3: Generate voiceovers with AIService
            logger.info("Generating voiceovers with AIService")
            voiceovers = await self.generate_voiceovers(
                product_analysis, product_name, style, template
            )

            # Step 4: Fill template with basic replacements
            filled_template = fill_template(template, product_name, cta_text)

            # Step 5: Update scenes with generated voiceovers
            filled_template['scenes'][0]['voiceover_text'] = voiceovers['scene_1_voiceover']
            filled_template['scenes'][1]['voiceover_text'] = voiceovers['scene_2_voiceover']
            filled_template['scenes'][2]['voiceover_text'] = voiceovers['scene_3_voiceover']
            filled_template['scenes'][3]['voiceover_text'] = voiceovers['scene_4_voiceover']

            # Add hook and CTA to metadata
            filled_template['hook'] = voiceovers.get('hook', voiceovers['scene_1_voiceover'])
            filled_template['cta'] = voiceovers.get('cta', cta_text)

            # Step 6: Add metadata
            filled_template['style'] = style
            filled_template['product_name'] = product_name
            if product_analysis:
                filled_template['product_analysis'] = product_analysis

            # Step 7: Validate template structure
            if not validate_template(filled_template):
                raise ScriptGenerationError("Generated template failed validation")

            logger.info(f"Script generation completed successfully for '{product_name}'")
            return filled_template

        except ScriptGenerationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during script generation: {e}")
            raise ScriptGenerationError(f"Script generation failed: {e}")


def create_script_generator(ai_service: Optional[AIService] = None) -> ScriptGenerator:
    """
    Factory function to create a ScriptGenerator instance

    Args:
        ai_service: Optional AIService instance (creates one if None)

    Returns:
        Configured ScriptGenerator instance

    Example:
        >>> generator = create_script_generator()
        >>> script = await generator.generate_script(...)
    """
    return ScriptGenerator(ai_service=ai_service)
