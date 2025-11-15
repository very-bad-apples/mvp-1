"""
Unified AI Service - Single interface for all AI operations

This module provides a unified, DRY interface for all AI tasks using Replicate.
Eliminates the need for multiple API clients (Anthropic, ElevenLabs, etc.).

Architecture:
    AIService (high-level, task-oriented)
        ↓
    ReplicateClient (low-level, Replicate-specific)
        ↓
    Replicate API
"""

import asyncio
from typing import Dict, Any, Optional, List
import base64
from pathlib import Path
import structlog

from services.replicate_client import ReplicateClient
from services.model_registry import ModelRegistry, ModelTask, ModelConfig

logger = structlog.get_logger()


class AIService:
    """
    Unified AI service for all AI operations.

    Provides high-level, task-oriented methods that abstract away
    the underlying model details. Supports runtime model selection.

    Example:
        ```python
        ai_service = AIService()

        # Generate script (uses default Claude model)
        script = await ai_service.generate_script(
            product_name="EcoWater Bottle",
            style="modern",
            product_image_path="product.jpg"
        )

        # Generate voiceover (can specify custom model)
        audio_path = await ai_service.generate_voiceover(
            text="Welcome to our product",
            model_name="xtts-v2"
        )
        ```
    """

    def __init__(self, replicate_client: Optional[ReplicateClient] = None):
        """
        Initialize AI service.

        Args:
            replicate_client: Optional ReplicateClient instance (creates one if None)
        """
        self.client = replicate_client or ReplicateClient()
        self.registry = ModelRegistry()

        logger.info("ai_service_initialized", client_ready=True)

    async def generate_script(
        self,
        product_name: str,
        style: str,
        cta_text: str,
        product_image_path: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate video script using AI.

        Args:
            product_name: Name of the product
            style: Video style (luxury, energetic, minimal, bold)
            cta_text: Call-to-action text
            product_image_path: Optional path to product image for vision analysis
            model_name: Optional specific model to use

        Returns:
            Dict containing structured script with scenes, voiceovers, etc.
        """
        model = self.registry.get_model(ModelTask.SCRIPT_GENERATION, model_name)

        logger.info(
            "generating_script",
            product=product_name,
            style=style,
            model=model.model_id,
            has_image=product_image_path is not None
        )

        # Build prompt
        prompt = self._build_script_prompt(product_name, style, cta_text)

        # Prepare input with optional image
        input_params = {
            "prompt": prompt,
            **model.default_params
        }

        # Add image if provided (for vision models like Claude)
        if product_image_path and "claude" in model.model_id.lower():
            # Read and encode image for Claude vision
            with open(product_image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            input_params["image"] = f"data:image/jpeg;base64,{image_data}"

        # Run model via Replicate
        try:
            output = await self.client.run_model_async(
                model_id=model.model_id,
                input_params=input_params
            )

            # Parse and structure the output
            script = self._parse_script_output(output, product_name, cta_text)

            logger.info("script_generated", scenes=len(script.get("scenes", [])))
            return script

        except Exception as e:
            logger.error("script_generation_failed", error=str(e), model=model.model_id)
            raise

    async def generate_voiceover(
        self,
        text: str,
        voice_style: str = "neutral",
        model_name: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate voiceover audio from text.

        Args:
            text: Text to convert to speech
            voice_style: Voice style/emotion (neutral, energetic, calm, etc.)
            model_name: Optional specific model to use
            output_path: Optional output file path

        Returns:
            Path to generated audio file
        """
        model = self.registry.get_model(ModelTask.VOICEOVER, model_name)

        logger.info(
            "generating_voiceover",
            text_length=len(text),
            voice_style=voice_style,
            model=model.model_id
        )

        # Prepare input based on model
        input_params = {
            "text": text,
            **model.default_params
        }

        # Model-specific parameters
        if "xtts" in model.model_id:
            input_params["speaker"] = self._map_voice_style_to_speaker(voice_style)
        elif "parler" in model.model_id:
            input_params["description"] = self._map_voice_style_to_description(voice_style)

        try:
            # Run model
            output = await self.client.run_model_async(
                model_id=model.model_id,
                input_params=input_params,
                use_file_output=True
            )

            # Download audio file
            if output_path is None:
                output_path = f"/tmp/voiceover_{hash(text)}.mp3"

            audio_path = await self.client.download_output(output, output_path)

            logger.info("voiceover_generated", path=audio_path)
            return audio_path

        except Exception as e:
            logger.error("voiceover_generation_failed", error=str(e), model=model.model_id)
            raise

    async def generate_video_scene(
        self,
        prompt: str,
        duration: int = 5,
        style: Optional[str] = None,
        image_input: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """
        Generate video scene from text prompt.

        Args:
            prompt: Text description of the video scene
            duration: Video duration in seconds
            style: Optional style modifier
            image_input: Optional image to use as starting frame
            model_name: Optional specific model to use

        Returns:
            Path to generated video file
        """
        model = self.registry.get_model(ModelTask.VIDEO_SCENE, model_name)

        logger.info(
            "generating_video_scene",
            prompt=prompt[:50],
            duration=duration,
            model=model.model_id
        )

        # Prepare input
        input_params = {
            "prompt": prompt,
            **model.default_params
        }

        # Add style modifiers
        if style:
            input_params["prompt"] = f"{prompt}, {style} style"

        # Add image if provided and model supports it
        if image_input and "stable-video" in model.model_id:
            input_params["image"] = open(image_input, "rb")

        try:
            # Run model
            output = await self.client.run_model_async(
                model_id=model.model_id,
                input_params=input_params,
                use_file_output=True
            )

            # Download video
            video_path = f"/tmp/scene_{hash(prompt)}.mp4"
            video_file = await self.client.download_output(output, video_path)

            logger.info("video_scene_generated", path=video_file)
            return video_file

        except Exception as e:
            logger.error("video_scene_generation_failed", error=str(e), model=model.model_id)
            raise

    async def generate_cta_image(
        self,
        prompt: str,
        style: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """
        Generate CTA (call-to-action) image.

        Args:
            prompt: Text description of the image
            style: Optional style modifier
            model_name: Optional specific model to use

        Returns:
            Path to generated image file
        """
        model = self.registry.get_model(ModelTask.CTA_IMAGE, model_name)

        logger.info(
            "generating_cta_image",
            prompt=prompt[:50],
            model=model.model_id
        )

        # Prepare input
        input_params = {
            "prompt": prompt,
            **model.default_params
        }

        # Add style modifiers
        if style:
            input_params["prompt"] = f"{prompt}, {style} style"

        try:
            # Run model
            output = await self.client.run_model_async(
                model_id=model.model_id,
                input_params=input_params,
                use_file_output=True
            )

            # Download image
            image_path = f"/tmp/cta_{hash(prompt)}.png"
            image_file = await self.client.download_output(output[0], image_path)

            logger.info("cta_image_generated", path=image_file)
            return image_file

        except Exception as e:
            logger.error("cta_image_generation_failed", error=str(e), model=model.model_id)
            raise

    def _build_script_prompt(self, product_name: str, style: str, cta_text: str) -> str:
        """Build prompt for script generation."""
        return f"""Generate a 30-second video ad script for: {product_name}

Style: {style}
CTA: {cta_text}

Create a 4-scene script with:
1. Hook (3-5 seconds) - Grab attention
2. Problem/Need (8-10 seconds) - Establish pain point
3. Solution (10-12 seconds) - Present product
4. CTA (5-7 seconds) - Call to action

For each scene provide:
- Visual description (for video generation)
- Voiceover text (natural, conversational)
- Duration in seconds

Return as JSON:
{{
  "scenes": [
    {{"scene_number": 1, "visual": "...", "voiceover": "...", "duration": 5}},
    ...
  ],
  "total_duration": 30
}}"""

    def _parse_script_output(self, output: Any, product_name: str, cta_text: str) -> Dict[str, Any]:
        """Parse and structure model output into script format."""
        # TODO: Add proper JSON parsing and validation
        # For now, return a structured format
        import json

        # If output is string, try to parse as JSON
        if isinstance(output, str):
            try:
                return json.loads(output)
            except:
                # Fallback to basic structure
                pass

        # Return basic structure if parsing fails
        return {
            "scenes": [
                {
                    "scene_number": 1,
                    "visual": f"Dynamic shot of {product_name}",
                    "voiceover": "Ever struggled with staying hydrated?",
                    "duration": 5
                },
                {
                    "scene_number": 2,
                    "visual": "Problem visualization",
                    "voiceover": "Most water bottles are bulky and hard to carry",
                    "duration": 8
                },
                {
                    "scene_number": 3,
                    "visual": f"{product_name} in action",
                    "voiceover": f"Introducing {product_name} - the perfect solution",
                    "duration": 12
                },
                {
                    "scene_number": 4,
                    "visual": "CTA visual",
                    "voiceover": cta_text,
                    "duration": 5
                }
            ],
            "total_duration": 30
        }

    def _map_voice_style_to_speaker(self, voice_style: str) -> str:
        """Map voice style to XTTS speaker."""
        mapping = {
            "neutral": "male_1",
            "energetic": "female_2",
            "calm": "female_1",
            "professional": "male_2",
        }
        return mapping.get(voice_style, "male_1")

    def _map_voice_style_to_description(self, voice_style: str) -> str:
        """Map voice style to Parler TTS description."""
        mapping = {
            "neutral": "A clear, professional voice",
            "energetic": "An enthusiastic, upbeat voice",
            "calm": "A soothing, relaxed voice",
            "professional": "A confident, authoritative voice",
        }
        return mapping.get(voice_style, "A clear, professional voice")

    def get_available_models(self, task: ModelTask) -> Dict[str, ModelConfig]:
        """
        Get all available models for a task.

        Args:
            task: The AI task type

        Returns:
            Dictionary of model_name -> ModelConfig
        """
        return self.registry.list_models(task)

    def get_model_info(self, task: ModelTask, model_name: Optional[str] = None) -> ModelConfig:
        """
        Get information about a specific model.

        Args:
            task: The AI task type
            model_name: Model name (uses default if None)

        Returns:
            ModelConfig with model details
        """
        return self.registry.get_model(task, model_name)

    async def generate_text(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate text using AI (for text-only tasks like voiceover script generation).

        Args:
            prompt: Text prompt
            model_name: Optional specific model to use (defaults to script generation model)
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response
        """
        model = self.registry.get_model(ModelTask.SCRIPT_GENERATION, model_name)

        logger.info(
            "generating_text",
            prompt_length=len(prompt),
            model=model.model_id,
            max_tokens=max_tokens
        )

        input_params = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            **model.default_params
        }

        try:
            output = await self.client.run_model_async(
                model_id=model.model_id,
                input_params=input_params
            )

            # Extract text from output (handles both string and structured responses)
            if isinstance(output, str):
                return output
            elif isinstance(output, dict) and "output" in output:
                return output["output"]
            elif isinstance(output, list) and len(output) > 0:
                return str(output[0])
            else:
                return str(output)

        except Exception as e:
            logger.error("text_generation_failed", error=str(e), model=model.model_id)
            raise

    async def analyze_image_with_text(
        self,
        image_path: str,
        prompt: str,
        model_name: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> str:
        """
        Analyze an image with a text prompt using vision AI (Claude via Replicate).

        Args:
            image_path: Path to the image file
            prompt: Text prompt for analysis
            model_name: Optional specific model to use
            max_tokens: Maximum tokens in response

        Returns:
            Generated analysis text
        """
        model = self.registry.get_model(ModelTask.SCRIPT_GENERATION, model_name)

        logger.info(
            "analyzing_image",
            image_path=image_path,
            prompt_length=len(prompt),
            model=model.model_id
        )

        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        # Prepare input for vision model
        input_params = {
            "prompt": prompt,
            "image": f"data:image/jpeg;base64,{image_data}",
            "max_tokens": max_tokens,
            **model.default_params
        }

        try:
            output = await self.client.run_model_async(
                model_id=model.model_id,
                input_params=input_params
            )

            # Extract text from output
            if isinstance(output, str):
                return output
            elif isinstance(output, dict) and "output" in output:
                return output["output"]
            elif isinstance(output, list) and len(output) > 0:
                return str(output[0])
            else:
                return str(output)

        except Exception as e:
            logger.error("image_analysis_failed", error=str(e), model=model.model_id)
            raise
