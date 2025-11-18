"""
Audio Trimming Service

Provides functionality for trimming audio files to specific time ranges.
Used primarily for matching audio duration to video duration in stitching operations.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from pydub import AudioSegment

from config import settings

logger = logging.getLogger(__name__)


class AudioTrimError(Exception):
    """Raised when audio trimming fails"""
    pass


def get_audio_file_path(audio_id: str) -> Optional[Path]:
    """
    Locate audio file by UUID.

    Args:
        audio_id: UUID of the audio file

    Returns:
        Path to audio file if found, None otherwise
    """
    audio_dir = Path(__file__).parent.parent / "mv" / "outputs" / "audio"

    # Check for .mp3 extension (primary format)
    audio_path = audio_dir / f"{audio_id}.mp3"
    if audio_path.exists():
        return audio_path

    # Fallback to other formats
    for ext in ['.m4a', '.opus', '.webm', '.ogg', '.aac']:
        audio_path = audio_dir / f"{audio_id}{ext}"
        if audio_path.exists():
            return audio_path

    return None


def trim_audio(
    audio_id: str,
    start_time: float,
    end_time: float,
    output_quality: str = "192k"
) -> Tuple[str, str, dict]:
    """
    Trim audio file to specific time range and save as new file.

    Creates a new audio file with a new UUID, preserving the original.

    Args:
        audio_id: UUID of source audio file
        start_time: Start time in seconds (float)
        end_time: End time in seconds (float)
        output_quality: Audio quality/bitrate (default: "192k")

    Returns:
        Tuple of (new_audio_id, new_audio_path, metadata)

    Raises:
        AudioTrimError: If audio file not found or trimming fails
        ValueError: If time range is invalid

    Example:
        >>> new_id, path, meta = trim_audio("abc-123", 0.0, 30.5)
        >>> print(f"Trimmed audio: {new_id}")
    """
    # Validate time range
    if start_time < 0:
        raise ValueError(f"start_time must be >= 0, got {start_time}")
    if end_time <= start_time:
        raise ValueError(f"end_time ({end_time}) must be > start_time ({start_time})")

    # Locate source audio file
    source_path = get_audio_file_path(audio_id)
    if source_path is None:
        raise AudioTrimError(f"Audio file with ID '{audio_id}' not found")

    if settings.MV_DEBUG_MODE:
        from mv.debug import debug_log
        debug_log(
            "audio_trim_started",
            audio_id=audio_id,
            source_path=str(source_path),
            start_time=start_time,
            end_time=end_time,
            output_quality=output_quality
        )

    try:
        # Load audio file
        logger.info(f"Loading audio file: {source_path}")
        audio = AudioSegment.from_file(str(source_path))

        # Get audio duration in seconds
        audio_duration_seconds = len(audio) / 1000.0

        # Validate times are within audio duration
        if start_time > audio_duration_seconds:
            raise ValueError(
                f"start_time ({start_time}s) exceeds audio duration ({audio_duration_seconds}s)"
            )
        if end_time > audio_duration_seconds:
            # Clamp end_time to audio duration instead of failing
            logger.warning(
                f"end_time ({end_time}s) exceeds audio duration ({audio_duration_seconds}s), "
                f"clamping to {audio_duration_seconds}s"
            )
            end_time = audio_duration_seconds

        # Convert to milliseconds for pydub
        start_ms = int(start_time * 1000)
        end_ms = int(end_time * 1000)

        # Extract segment
        logger.info(f"Extracting audio segment: {start_time}s to {end_time}s")
        trimmed_audio = audio[start_ms:end_ms]

        # Generate new UUID for trimmed audio
        new_audio_id = str(uuid.uuid4())

        # Save trimmed audio
        audio_dir = Path(__file__).parent.parent / "mv" / "outputs" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        output_path = audio_dir / f"{new_audio_id}.mp3"

        logger.info(f"Saving trimmed audio to: {output_path}")
        trimmed_audio.export(
            str(output_path),
            format="mp3",
            bitrate=output_quality
        )

        # Verify file was created
        if not output_path.exists():
            raise AudioTrimError(f"Failed to create trimmed audio file: {output_path}")

        file_size = output_path.stat().st_size

        # Build metadata
        metadata = {
            "source_audio_id": audio_id,
            "trimmed_audio_id": new_audio_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time,
            "source_duration": audio_duration_seconds,
            "output_quality": output_quality,
            "file_size_bytes": file_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Save metadata to JSON file
        metadata_path = audio_dir / f"{new_audio_id}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        if settings.MV_DEBUG_MODE:
            from mv.debug import debug_log
            debug_log(
                "audio_trim_completed",
                new_audio_id=new_audio_id,
                output_path=str(output_path),
                file_size_bytes=file_size,
                duration=metadata["duration"]
            )

        logger.info(
            f"Audio trimming completed: {audio_id} -> {new_audio_id} "
            f"({start_time}s to {end_time}s, {file_size} bytes)"
        )

        return new_audio_id, str(output_path), metadata

    except Exception as e:
        logger.error(f"Audio trimming failed: {e}", exc_info=True)
        if isinstance(e, (AudioTrimError, ValueError)):
            raise
        raise AudioTrimError(f"Failed to trim audio: {str(e)}")
