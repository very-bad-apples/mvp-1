"""
Video trimming utilities using moviepy.

Provides functions for:
- Trimming video clips to specified IN/OUT points
- Extracting video metadata (duration, size)
- Validating and clamping trim points
"""

import os
import json
import structlog
from typing import Dict, Any, Tuple
from moviepy import VideoFileClip

logger = structlog.get_logger()


class VideoTrimError(Exception):
    """Raised when video trim operation fails"""
    pass


def get_video_duration(video_path: str) -> float:
    """
    Extract video duration using moviepy.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds (float with millisecond precision)

    Raises:
        VideoTrimError: If unable to read video
    """
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()

        logger.debug(
            "video_duration_extracted",
            video_path=video_path,
            duration=duration
        )

        return duration

    except Exception as e:
        logger.error(
            "failed_to_extract_video_duration",
            video_path=video_path,
            error=str(e)
        )
        raise VideoTrimError(f"Failed to extract video duration: {e}")


def validate_and_clamp_trim_points(
    in_point: float,
    out_point: float,
    video_duration: float
) -> Tuple[float, float]:
    """
    Validate and clamp trim points to valid bounds.

    Ensures: 0 <= in < out <= duration
    Minimum clip length: 0.1 seconds

    Args:
        in_point: Requested start time in seconds
        out_point: Requested end time in seconds
        video_duration: Actual video duration in seconds

    Returns:
        Tuple of (clamped_in, clamped_out) with millisecond precision
    """
    # Clamp to valid range [0, duration]
    in_point = max(0.0, min(in_point, video_duration))
    out_point = max(0.0, min(out_point, video_duration))

    # Ensure in < out with minimum 0.1 second clip
    MIN_CLIP_DURATION = 0.1
    if out_point - in_point < MIN_CLIP_DURATION:
        out_point = min(in_point + MIN_CLIP_DURATION, video_duration)

    # Round to millisecond precision
    in_point = round(in_point, 3)
    out_point = round(out_point, 3)

    logger.debug(
        "trim_points_validated",
        original_in=in_point,
        original_out=out_point,
        clamped_in=in_point,
        clamped_out=out_point,
        video_duration=video_duration
    )

    return (in_point, out_point)


def trim_video(
    source_video_path: str,
    output_path: str,
    in_point: float,
    out_point: float
) -> Dict[str, Any]:
    """
    Trim video using moviepy.

    Args:
        source_video_path: Path to source video file
        output_path: Path for trimmed output
        in_point: Start time in seconds (millisecond precision)
        out_point: End time in seconds (millisecond precision)

    Returns:
        Dict with metadata: {
            "duration": float,
            "size_bytes": int,
            "in_point": float,
            "out_point": float
        }

    Raises:
        VideoTrimError: If trim operation fails
    """
    clip = None
    trimmed_clip = None

    try:
        logger.info(
            "starting_video_trim",
            source=source_video_path,
            output=output_path,
            in_point=in_point,
            out_point=out_point
        )

        # Load source video
        clip = VideoFileClip(source_video_path)
        original_duration = clip.duration

        # Validate and clamp trim points
        in_point, out_point = validate_and_clamp_trim_points(
            in_point, out_point, original_duration
        )

        # Trim video using subclip
        trimmed_clip = clip.subclip(in_point, out_point)
        trimmed_duration = trimmed_clip.duration

        logger.debug(
            "writing_trimmed_video",
            output_path=output_path,
            trimmed_duration=trimmed_duration
        )

        # Write trimmed video
        trimmed_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None  # Suppress moviepy verbose logging
        )

        # Get file size
        file_size = os.path.getsize(output_path)

        metadata = {
            "duration": trimmed_duration,
            "size_bytes": file_size,
            "in_point": in_point,
            "out_point": out_point
        }

        logger.info(
            "video_trim_complete",
            output_path=output_path,
            metadata=metadata
        )

        return metadata

    except Exception as e:
        logger.error(
            "video_trim_failed",
            source=source_video_path,
            output=output_path,
            error=str(e),
            exc_info=True
        )
        raise VideoTrimError(f"Failed to trim video: {e}")

    finally:
        # Clean up clips to free memory
        if clip:
            clip.close()
        if trimmed_clip:
            trimmed_clip.close()

