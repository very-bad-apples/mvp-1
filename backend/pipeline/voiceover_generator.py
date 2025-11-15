"""
Voiceover Generator with AIService Integration

Generates professional voiceovers using unified AIService.
Integrates with ScriptGenerator to create audio for all scenes.

Features:
- High-quality TTS via Replicate
- Multiple voice options for different styles
- Duration validation
- Retry logic for API failures
- Async support for parallel generation
- Integration with AssetManager
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import time

from pydub import AudioSegment
from config import settings
from pipeline.asset_manager import AssetManager
from services.ai_service import AIService

# Configure logging
logger = logging.getLogger(__name__)


class VoiceoverGenerationError(Exception):
    """Raised when voiceover generation fails"""
    pass


class VoiceoverGenerator:
    """
    Generate voiceovers using AIService with Replicate.

    Features:
    - Text-to-speech with natural voice via Replicate
    - Multiple voice options for different styles
    - Duration validation
    - Audio format handling (MP3)
    - Retry logic built into AIService
    - Logging integration

    Voice Style Mapping:
    - luxury: neutral - Sophisticated, calm, professional
    - energetic: energetic - Upbeat, enthusiastic
    - minimal: calm - Clear, direct, neutral
    - bold: professional - Confident, powerful

    Example:
        >>> generator = VoiceoverGenerator()
        >>> audio_path = await generator.generate_voiceover(
        ...     text="Introducing the future of innovation",
        ...     target_duration=8.0,
        ...     asset_manager=am
        ... )
        >>> print(f"Generated: {audio_path}")
    """

    # Voice style mapping for AIService
    VOICE_STYLE_MAP = {
        "luxury": "neutral",
        "energetic": "energetic",
        "minimal": "calm",
        "bold": "professional",
        "default": "neutral",
    }

    def __init__(self, ai_service: Optional[AIService] = None):
        """
        Initialize the voiceover generator.

        Args:
            ai_service: Optional AIService instance (creates one if None)
        """
        self.ai_service = ai_service or AIService()
        self.max_retries = 3
        self.base_retry_delay = 1.0  # seconds

        logger.info("VoiceoverGenerator initialized with AIService")

    def get_voice_style(self, style: str) -> str:
        """
        Get voice style for AIService based on visual style.

        Args:
            style: Visual style (luxury, energetic, minimal, bold)

        Returns:
            Voice style string for AIService
        """
        voice_style = self.VOICE_STYLE_MAP.get(
            style.lower(),
            self.VOICE_STYLE_MAP["default"]
        )
        logger.debug(f"Selected voice style '{voice_style}' for visual style '{style}'")
        return voice_style

    async def generate_voiceover(
        self,
        text: str,
        asset_manager: AssetManager,
        target_duration: Optional[float] = None,
        voice_style: Optional[str] = None,
        scene_number: Optional[int] = None,
        tolerance: float = 0.5
    ) -> str:
        """
        Generate TTS audio from text using AIService.

        Args:
            text: Text to convert to speech
            asset_manager: AssetManager instance for saving files
            target_duration: Expected duration in seconds (optional)
            voice_style: Voice style to use (neutral, energetic, calm, professional)
            scene_number: Scene number for filename (optional)
            tolerance: Duration tolerance in seconds (default: 0.5)

        Returns:
            Absolute path to generated MP3 file

        Raises:
            VoiceoverGenerationError: If generation fails

        Example:
            >>> path = await generator.generate_voiceover(
            ...     text="Hello world",
            ...     asset_manager=am,
            ...     target_duration=2.0,
            ...     scene_number=1
            ... )
        """
        logger.info(f"Generating voiceover: '{text[:50]}...'")

        voice = voice_style or "neutral"

        try:
            # Generate filename
            timestamp = int(time.time())
            if scene_number is not None:
                filename = f"scene_{scene_number}_voiceover_{timestamp}.mp3"
            else:
                filename = f"voiceover_{timestamp}.mp3"

            # Generate output path for AIService
            output_path = await asset_manager.get_path(filename, subdir="audio")

            # Generate audio using AIService
            audio_path = await self.ai_service.generate_voiceover(
                text=text,
                voice_style=voice,
                output_path=output_path
            )

            logger.info(f"Saved voiceover to {audio_path}")

            # Validate duration if target provided
            if target_duration is not None:
                is_valid = await self._validate_audio_duration(
                    audio_path, target_duration, tolerance
                )
                if not is_valid:
                    logger.warning(
                        f"Audio duration does not match target. "
                        f"Target: {target_duration}s, Tolerance: ±{tolerance}s"
                    )

            return audio_path

        except Exception as e:
            logger.error(f"Voiceover generation failed: {e}")
            raise VoiceoverGenerationError(f"Failed to generate voiceover: {e}")

    async def generate_all_voiceovers(
        self,
        script: Dict[str, Any],
        asset_manager: AssetManager,
        style: Optional[str] = None
    ) -> List[str]:
        """
        Generate voiceovers for all scenes in a script.

        Processes all scenes in parallel for faster generation.

        Args:
            script: Script dictionary from ScriptGenerator
            asset_manager: AssetManager instance for saving files
            style: Optional style to select appropriate voice

        Returns:
            List of audio file paths in scene order

        Raises:
            VoiceoverGenerationError: If generation fails

        Example:
            >>> script = generator.generate_script(...)
            >>> audio_paths = await voiceover_gen.generate_all_voiceovers(
            ...     script=script,
            ...     asset_manager=am,
            ...     style="luxury"
            ... )
            >>> print(f"Generated {len(audio_paths)} voiceovers")
        """
        logger.info("Generating voiceovers for all scenes")

        scenes = script.get('scenes', [])
        if not scenes:
            raise VoiceoverGenerationError("No scenes found in script")

        # Determine voice style based on visual style
        voice_style = None
        if style:
            voice_style = self.get_voice_style(style)

        # Generate all voiceovers in parallel
        tasks = []
        for i, scene in enumerate(scenes, start=1):
            voiceover_text = scene.get('voiceover_text', '')
            duration = scene.get('duration', None)

            if not voiceover_text:
                logger.warning(f"Scene {i} has no voiceover text, skipping")
                continue

            task = self.generate_voiceover(
                text=voiceover_text,
                asset_manager=asset_manager,
                target_duration=duration,
                voice_style=voice_style,
                scene_number=i
            )
            tasks.append(task)

        try:
            # Run all generations in parallel
            audio_paths = await asyncio.gather(*tasks)
            logger.info(f"Successfully generated {len(audio_paths)} voiceovers")
            return list(audio_paths)

        except Exception as e:
            logger.error(f"Failed to generate all voiceovers: {e}")
            raise VoiceoverGenerationError(f"Batch voiceover generation failed: {e}")

    async def _validate_audio_duration(
        self,
        audio_path: str,
        target_duration: float,
        tolerance: float = 0.5
    ) -> bool:
        """
        Check if audio duration matches target within tolerance.

        Args:
            audio_path: Path to audio file
            target_duration: Expected duration in seconds
            tolerance: Acceptable variance in seconds

        Returns:
            True if duration is within tolerance, False otherwise
        """
        try:
            # Load audio file and get duration
            audio = await asyncio.to_thread(AudioSegment.from_mp3, audio_path)
            actual_duration = len(audio) / 1000.0  # Convert ms to seconds

            # Check if within tolerance
            diff = abs(actual_duration - target_duration)
            is_valid = diff <= tolerance

            if is_valid:
                logger.info(
                    f"Duration validation passed: {actual_duration:.2f}s "
                    f"(target: {target_duration}s, diff: {diff:.2f}s)"
                )
            else:
                logger.warning(
                    f"Duration validation failed: {actual_duration:.2f}s "
                    f"(target: {target_duration}s, diff: {diff:.2f}s)"
                )

            return is_valid

        except Exception as e:
            logger.error(f"Failed to validate audio duration: {e}")
            return False

    async def get_audio_duration(self, audio_path: str) -> float:
        """
        Get duration of audio file in seconds.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds

        Example:
            >>> duration = await generator.get_audio_duration("scene1.mp3")
            >>> print(f"Duration: {duration:.2f}s")
        """
        try:
            audio = await asyncio.to_thread(AudioSegment.from_mp3, audio_path)
            duration = len(audio) / 1000.0  # Convert ms to seconds
            logger.debug(f"Audio duration: {duration:.2f}s for {audio_path}")
            return duration
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            raise VoiceoverGenerationError(f"Failed to read audio file: {e}")


def create_voiceover_generator(
    ai_service: Optional[AIService] = None
) -> VoiceoverGenerator:
    """
    Factory function to create a VoiceoverGenerator instance.

    Args:
        ai_service: Optional AIService instance (creates one if None)

    Returns:
        Configured VoiceoverGenerator instance

    Example:
        >>> generator = create_voiceover_generator()
        >>> audio = await generator.generate_voiceover(...)
    """
    return VoiceoverGenerator(ai_service=ai_service)
