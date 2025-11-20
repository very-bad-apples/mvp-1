"""
Video stitching module for merging multiple video clips.

This module provides functionality for stitching multiple video clips into a single
video using MoviePy. Supports both local filesystem and S3 storage backends.
"""

import json
import logging
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional

from moviepy import VideoFileClip, concatenate_videoclips
from pydantic import BaseModel, Field

from config import settings
from services.s3_file_cache import get_s3_file_cache

logger = logging.getLogger(__name__)


class StitchVideosRequest(BaseModel):
    """Request model for video stitching."""

    video_ids: list[str] = Field(
        ..., description="List of video UUIDs to stitch together in order"
    )
    audio_overlay_id: Optional[str] = Field(
        None, description="Optional UUID of audio file to overlay on stitched video"
    )
    suppress_video_audio: Optional[bool] = Field(
        False, description="Whether to remove audio from video clips (default: False)"
    )


class StitchVideosResponse(BaseModel):
    """Response model for video stitching."""

    video_id: str = Field(..., description="UUID for the stitched video")
    video_path: str = Field(..., description="Filesystem path to stitched video")
    video_url: str = Field(..., description="URL path to retrieve stitched video")
    metadata: dict = Field(..., description="Stitching metadata")
    audio_overlay_applied: bool = Field(
        False, description="Whether audio overlay was successfully applied"
    )
    audio_overlay_warning: Optional[str] = Field(
        None, description="Warning message if audio overlay failed or was skipped"
    )


def _get_audio_file_path(audio_id: str) -> Optional[Path]:
    """
    Get the local filesystem path for an audio file by UUID.

    Args:
        audio_id: UUID of the audio file

    Returns:
        Path to audio file if found, None otherwise
    """
    audio_dir = Path(__file__).parent / "outputs" / "audio"

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


def _get_local_video_path(video_id: str) -> Optional[Path]:
    """
    Get the local filesystem path for a video ID.

    Checks both the job directory and legacy videos directory.

    Args:
        video_id: UUID of the video

    Returns:
        Path to the video file if found, None otherwise
    """
    # Check job directory first (newer structure)
    job_path = Path(__file__).parent / "outputs" / "jobs" / video_id / "video.mp4"
    if job_path.exists():
        return job_path

    # Check legacy videos directory
    legacy_path = Path(__file__).parent / "outputs" / "videos" / f"{video_id}.mp4"
    if legacy_path.exists():
        return legacy_path

    return None


def _get_cached_video_from_s3(video_id: str) -> str:
    """
    Get a video from S3 using the file cache.

    Downloads from S3 on first access and caches locally.
    Subsequent accesses return cached path without re-downloading.

    Args:
        video_id: UUID of the video

    Returns:
        Path to the cached video file

    Raises:
        FileNotFoundError: If video doesn't exist in S3
        Exception: If download fails
    """
    cache = get_s3_file_cache()
    s3_key = f"mv/projects/{video_id}/video.mp4"

    if settings.MV_DEBUG_MODE:
        from mv.debug import debug_log
        debug_log("stitch_cache_access", video_id=video_id, s3_key=s3_key)

    try:
        # Cache handles download if needed
        local_path = cache.get_file(s3_key)

        if settings.MV_DEBUG_MODE:
            from mv.debug import log_stitch_s3_download
            log_stitch_s3_download(video_id, s3_key, local_path)

        return local_path

    except Exception as e:
        logger.error(f"Failed to get video {video_id} from cache: {e}")
        raise FileNotFoundError(f"Video {video_id} not found in S3") from e


def _retrieve_video_files(video_ids: list[str]) -> tuple[list[str], Optional[str]]:
    """
    Retrieve video files for stitching.

    Handles both local filesystem and S3 storage based on SERVE_FROM_CLOUD setting.
    When using S3, videos are cached locally and reused across stitching operations.

    Args:
        video_ids: List of video UUIDs

    Returns:
        Tuple of (list of video file paths, temp_dir to clean up or None)
        Note: temp_dir is always None when using S3 cache (cache handles cleanup via LRU)

    Raises:
        FileNotFoundError: If any video is not found
    """
    video_paths = []
    temp_dir = None  # No temp dir needed - cache handles storage

    if settings.SERVE_FROM_CLOUD and settings.STORAGE_BUCKET:
        # Get from S3 using cache (downloads only if not cached)
        if settings.MV_DEBUG_MODE:
            from mv.debug import log_stitch_storage_mode
            log_stitch_storage_mode("s3_cache", None)

        for video_id in video_ids:
            # Cache handles download if needed, returns cached path
            path = _get_cached_video_from_s3(video_id)
            video_paths.append(path)
    else:
        # Local filesystem
        if settings.MV_DEBUG_MODE:
            from mv.debug import log_stitch_storage_mode
            log_stitch_storage_mode("local", None)

        for video_id in video_ids:
            path = _get_local_video_path(video_id)
            if path is None:
                raise FileNotFoundError(f"Video {video_id} not found in local storage")
            video_paths.append(str(path))

    return video_paths, temp_dir


def _merge_video_clips(
    video_paths: list[str],
    output_path: str,
    audio_overlay_path: Optional[str] = None,
    suppress_video_audio: bool = False
) -> tuple[float, float]:
    """
    Merge multiple video clips into a single video with optional audio overlay.

    Args:
        video_paths: List of paths to video files
        output_path: Path to save the merged video
        audio_overlay_path: Optional path to audio file to overlay
        suppress_video_audio: Whether to remove audio from video clips

    Returns:
        Tuple of (processing_time_seconds, total_video_duration_seconds)
    """
    start_time = time.time()

    if settings.MV_DEBUG_MODE:
        from mv.debug import log_stitch_merge_start
        log_stitch_merge_start(video_paths)

    # Load video clips
    clips = [VideoFileClip(path) for path in video_paths]

    # Remove audio from clips if requested
    if suppress_video_audio:
        if settings.MV_DEBUG_MODE:
            from mv.debug import debug_log
            debug_log("video_audio_suppression", enabled=True)
        clips = [clip.without_audio() for clip in clips]

    try:
        # Concatenate clips
        final_clip = concatenate_videoclips(clips)

        # Calculate total video duration
        total_duration = final_clip.duration

        # Apply audio overlay if provided
        if audio_overlay_path:
            from moviepy import AudioFileClip

            if settings.MV_DEBUG_MODE:
                from mv.debug import debug_log
                debug_log(
                    "audio_overlay_applying",
                    audio_path=audio_overlay_path,
                    video_duration=total_duration
                )

            try:
                audio_clip = AudioFileClip(audio_overlay_path)

                # Set audio duration to match video duration (trim if needed)
                if audio_clip.duration > total_duration:
                    audio_clip = audio_clip.with_subclip(0, total_duration)

                # Apply audio to video (moviepy 2.0.0 uses with_audio)
                final_clip = final_clip.with_audio(audio_clip)

                if settings.MV_DEBUG_MODE:
                    from mv.debug import debug_log
                    debug_log("audio_overlay_applied", audio_duration=audio_clip.duration)

            except Exception as e:
                logger.error(f"Failed to apply audio overlay: {e}")
                # Continue without audio overlay
                if settings.MV_DEBUG_MODE:
                    from mv.debug import debug_log
                    debug_log("audio_overlay_failed", error=str(e))

        # Write the final video
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            logger=None  # Suppress MoviePy's progress bar
        )

        processing_time = time.time() - start_time

        if settings.MV_DEBUG_MODE:
            from mv.debug import log_stitch_merge_complete
            log_stitch_merge_complete(output_path, processing_time)

        return processing_time, total_duration
    finally:
        # Clean up clips
        for clip in clips:
            clip.close()
        if 'final_clip' in locals():
            final_clip.close()


async def _upload_to_s3(local_path: str, s3_key: str, content_type: str = None) -> str:
    """
    Upload a file to S3.

    Args:
        local_path: Path to local file
        s3_key: Destination S3 key
        content_type: Optional content type

    Returns:
        Presigned URL for the uploaded file
    """
    from services.s3_storage import get_s3_storage_service

    s3_service = get_s3_storage_service()
    await s3_service.upload_file_from_path_async(local_path, s3_key, content_type)

    # Return presigned URL
    return s3_service.generate_presigned_url(s3_key)


def stitch_videos(
    video_ids: list[str],
    audio_overlay_id: Optional[str] = None,
    suppress_video_audio: bool = False
) -> tuple[str, str, str, dict, bool, Optional[str]]:
    """
    Stitch multiple video clips into a single video with optional audio overlay.

    This function:
    1. Validates video IDs
    2. Retrieves video files (from local or S3)
    3. Optionally retrieves and trims audio overlay
    4. Merges videos using MoviePy with audio overlay
    5. Saves to appropriate storage (local or S3)
    6. Returns video ID, path, URL, metadata, and audio status

    Args:
        video_ids: List of video UUIDs to stitch in order
        audio_overlay_id: Optional UUID of audio file to overlay
        suppress_video_audio: Whether to remove audio from video clips (default: False)

    Returns:
        Tuple of (video_id, video_path, video_url, metadata, audio_overlay_applied, audio_overlay_warning)

    Raises:
        ValueError: If video_ids is empty
        FileNotFoundError: If any video is not found
    """
    if not video_ids:
        raise ValueError("video_ids list cannot be empty")

    if settings.MV_DEBUG_MODE:
        from mv.debug import log_stitch_request, debug_log
        log_stitch_request(video_ids)
        if audio_overlay_id or suppress_video_audio:
            debug_log(
                "stitch_audio_params",
                audio_overlay_id=audio_overlay_id,
                suppress_video_audio=suppress_video_audio
            )

    # Track audio overlay status
    audio_overlay_applied = False
    audio_overlay_warning = None
    audio_overlay_path = None
    trimmed_audio_path = None

    # Track total processing time
    total_start_time = time.time()

    # Retrieve video files
    video_paths, temp_dir = _retrieve_video_files(video_ids)

    # Generate UUID for stitched video
    stitched_video_id = str(uuid.uuid4())

    # Use temporary file ONLY during stitching (MoviePy needs file path)
    temp_output_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    temp_output_path = temp_output_file.name
    temp_output_file.close()  # Close so MoviePy can write to it

    try:
        # Handle audio overlay if requested
        if audio_overlay_id:
            # Retrieve audio file
            audio_path = _get_audio_file_path(audio_overlay_id)

            if audio_path is None:
                audio_overlay_warning = f"Audio file with ID '{audio_overlay_id}' not found"
                logger.warning(audio_overlay_warning)

                if settings.MV_DEBUG_MODE:
                    from mv.debug import debug_log
                    debug_log("audio_overlay_not_found", audio_id=audio_overlay_id)
            else:
                # Calculate total video duration first (need to load clips briefly)
                from moviepy import VideoFileClip
                total_video_duration = sum(VideoFileClip(path).duration for path in video_paths)

                # Check if audio needs trimming
                from pydub import AudioSegment
                audio = AudioSegment.from_file(str(audio_path))
                audio_duration = len(audio) / 1000.0  # Convert to seconds

                if audio_duration > total_video_duration:
                    # Trim audio to match video duration
                    from services.audio_trimmer import trim_audio

                    try:
                        logger.info(
                            f"Trimming audio {audio_overlay_id} from {audio_duration}s to {total_video_duration}s"
                        )

                        trimmed_id, trimmed_path, trim_metadata = trim_audio(
                            audio_overlay_id,
                            start_time=0.0,
                            end_time=total_video_duration
                        )

                        audio_overlay_path = trimmed_path
                        trimmed_audio_path = trimmed_path  # Track for cleanup

                        if settings.MV_DEBUG_MODE:
                            from mv.debug import debug_log
                            debug_log(
                                "audio_trimmed_for_overlay",
                                original_duration=audio_duration,
                                trimmed_duration=total_video_duration,
                                trimmed_audio_id=trimmed_id
                            )
                    except Exception as e:
                        audio_overlay_warning = f"Failed to trim audio: {str(e)}"
                        logger.error(audio_overlay_warning, exc_info=True)
                        audio_overlay_path = None
                else:
                    # Use audio as-is
                    audio_overlay_path = str(audio_path)

                if audio_overlay_path:
                    audio_overlay_applied = True

        # Merge videos with optional audio overlay to temp file
        merge_time, total_duration = _merge_video_clips(
            video_paths,
            temp_output_path,
            audio_overlay_path=audio_overlay_path,
            suppress_video_audio=suppress_video_audio
        )

        # Build metadata
        total_processing_time = time.time() - total_start_time
        metadata = {
            "input_video_ids": video_ids,
            "num_videos_stitched": len(video_ids),
            "stitched_video_id": stitched_video_id,
            "merge_time_seconds": round(merge_time, 2),
            "total_processing_time_seconds": round(total_processing_time, 2),
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "video_duration_seconds": round(total_duration, 2),
        }

        # Add audio overlay metadata if used
        if audio_overlay_id:
            metadata["audio_overlay_id"] = audio_overlay_id
            metadata["audio_overlay_applied"] = audio_overlay_applied
            metadata["video_audio_suppressed"] = suppress_video_audio
            if audio_overlay_warning:
                metadata["audio_overlay_warning"] = audio_overlay_warning
            if audio_overlay_applied and audio_overlay_path:
                # Get audio duration
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_file(audio_overlay_path)
                    metadata["audio_overlay_duration_seconds"] = round(len(audio) / 1000.0, 2)
                except Exception:
                    pass

        # Upload to S3 if configured
        if settings.STORAGE_BUCKET:
            from services.s3_storage import get_s3_storage_service

            s3_service = get_s3_storage_service()

            # Upload video from temp file
            video_s3_key = s3_service.upload_file_from_path(
                temp_output_path,
                f"mv/projects/{stitched_video_id}/video.mp4",
                content_type="video/mp4"
            )

            # Upload metadata from memory
            metadata_json = json.dumps(metadata, indent=2).encode('utf-8')
            s3_service.upload_file(
                BytesIO(metadata_json),
                f"mv/projects/{stitched_video_id}/metadata.json",
                content_type="application/json"
            )

            # Generate presigned URL
            video_url = s3_service.generate_presigned_url(video_s3_key)
            metadata["cloud_url"] = video_url
            metadata["storage_backend"] = "s3"
            video_path = None  # No local path when using S3

            logger.info(f"Uploaded stitched video {stitched_video_id} directly to S3")

            if settings.MV_DEBUG_MODE:
                from mv.debug import log_stitch_upload_complete
                log_stitch_upload_complete(stitched_video_id, {"video": video_url})

        else:
            # Fallback for local dev
            videos_dir = Path(__file__).parent / "outputs" / "videos"
            videos_dir.mkdir(parents=True, exist_ok=True)

            local_path = videos_dir / f"{stitched_video_id}.mp4"
            shutil.copy2(temp_output_path, local_path)

            video_url = f"/api/mv/get_video/{stitched_video_id}"
            metadata["local_path"] = str(local_path)
            metadata["storage_backend"] = "local"
            video_path = str(local_path)

        if settings.MV_DEBUG_MODE:
            from mv.debug import log_stitch_result
            debug_info = {
                "video_id": stitched_video_id,
                "video_path": video_path,
                "video_url": video_url,
                "storage_backend": metadata["storage_backend"],
                "audio_overlay_applied": audio_overlay_applied,
            }
            # Only include file size if we have a local path
            if video_path and os.path.exists(video_path):
                debug_info["file_size_bytes"] = os.path.getsize(video_path)
            elif os.path.exists(temp_output_path):
                debug_info["file_size_bytes"] = os.path.getsize(temp_output_path)
            log_stitch_result(debug_info)

        return (
            stitched_video_id,
            video_path,
            video_url,
            metadata,
            audio_overlay_applied,
            audio_overlay_warning
        )

    finally:
        # Clean up temp output file
        if os.path.exists(temp_output_path):
            try:
                os.unlink(temp_output_path)
                if settings.MV_DEBUG_MODE:
                    from mv.debug import log_stitch_cleanup
                    log_stitch_cleanup(temp_output_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_output_path}: {e}")

        # Clean up temp directory if created (S3 cache creates temp dirs for downloads)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

            if settings.MV_DEBUG_MODE:
                from mv.debug import log_stitch_cleanup
                log_stitch_cleanup(temp_dir)

        # Clean up trimmed audio file if created
        if trimmed_audio_path and os.path.exists(trimmed_audio_path):
            try:
                os.unlink(trimmed_audio_path)
                if settings.MV_DEBUG_MODE:
                    from mv.debug import debug_log
                    debug_log("trimmed_audio_cleanup", path=trimmed_audio_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup trimmed audio: {e}")
