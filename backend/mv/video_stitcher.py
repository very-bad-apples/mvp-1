"""
Video stitching module for merging multiple video clips.

This module provides functionality for stitching multiple video clips into a single
video using MoviePy. Supports both local filesystem and S3 storage backends.
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from moviepy import VideoFileClip, concatenate_videoclips
from pydantic import BaseModel, Field

from config import settings

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


async def _download_video_from_s3(video_id: str, temp_dir: str) -> str:
    """
    Download a video from S3 to a temporary directory.

    Args:
        video_id: UUID of the video
        temp_dir: Temporary directory to save the video

    Returns:
        Path to the downloaded video file

    Raises:
        FileNotFoundError: If video doesn't exist in S3
    """
    from services.storage_backend import get_storage_backend

    storage = get_storage_backend()
    cloud_path = f"mv/jobs/{video_id}/video.mp4"

    # Check if video exists
    exists = await storage.exists(cloud_path)
    if not exists:
        raise FileNotFoundError(f"Video {video_id} not found in S3")

    # Download to temp directory
    local_path = os.path.join(temp_dir, f"{video_id}.mp4")
    await storage.download_file(cloud_path, local_path)

    if settings.MV_DEBUG_MODE:
        from mv.debug import log_stitch_s3_download
        log_stitch_s3_download(video_id, cloud_path, local_path)

    return local_path


def _retrieve_video_files(video_ids: list[str]) -> tuple[list[str], Optional[str]]:
    """
    Retrieve video files for stitching.

    Handles both local filesystem and S3 storage based on SERVE_FROM_CLOUD setting.

    Args:
        video_ids: List of video UUIDs

    Returns:
        Tuple of (list of video file paths, temp_dir to clean up or None)

    Raises:
        FileNotFoundError: If any video is not found
    """
    video_paths = []
    temp_dir = None

    if settings.SERVE_FROM_CLOUD and settings.STORAGE_BUCKET:
        # Download from S3
        temp_dir = tempfile.mkdtemp(prefix="stitch_")

        if settings.MV_DEBUG_MODE:
            from mv.debug import log_stitch_storage_mode
            log_stitch_storage_mode("s3", temp_dir)

        async def download_all():
            paths = []
            for video_id in video_ids:
                path = await _download_video_from_s3(video_id, temp_dir)
                paths.append(path)
            return paths

        # Run async downloads in a separate event loop
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: asyncio.run(download_all()))
            video_paths = future.result(timeout=600)  # 10 min timeout
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


async def _upload_to_s3(local_path: str, cloud_path: str) -> str:
    """
    Upload a file to S3.

    Args:
        local_path: Path to local file
        cloud_path: Destination path in S3

    Returns:
        Presigned URL for the uploaded file
    """
    from services.storage_backend import get_storage_backend

    storage = get_storage_backend()
    url = await storage.upload_file(local_path, cloud_path)

    return url


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

    # Create output directory
    job_dir = Path(__file__).parent / "outputs" / "jobs" / stitched_video_id
    os.makedirs(job_dir, exist_ok=True)

    # Also save to videos directory for backward compatibility
    videos_dir = Path(__file__).parent / "outputs" / "videos"
    os.makedirs(videos_dir, exist_ok=True)

    output_path = job_dir / "video.mp4"
    output_path_compat = videos_dir / f"{stitched_video_id}.mp4"

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

        # Merge videos with optional audio overlay
        merge_time, total_duration = _merge_video_clips(
            video_paths,
            str(output_path),
            audio_overlay_path=audio_overlay_path,
            suppress_video_audio=suppress_video_audio
        )

        # Copy to legacy location
        import shutil
        shutil.copy2(output_path, output_path_compat)

        # Build metadata
        total_processing_time = time.time() - total_start_time
        metadata = {
            "input_video_ids": video_ids,
            "num_videos_stitched": len(video_ids),
            "stitched_video_id": stitched_video_id,
            "merge_time_seconds": round(merge_time, 2),
            "total_processing_time_seconds": round(total_processing_time, 2),
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "local_path": str(output_path),
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

        # Save metadata
        metadata_path = job_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Upload to cloud storage if configured
        cloud_urls = {}
        if settings.STORAGE_BUCKET:
            try:
                async def upload_job_to_cloud():
                    urls = {}

                    # Upload video
                    urls["video"] = await _upload_to_s3(
                        str(output_path),
                        f"mv/jobs/{stitched_video_id}/video.mp4"
                    )

                    # Upload metadata
                    urls["metadata"] = await _upload_to_s3(
                        str(metadata_path),
                        f"mv/jobs/{stitched_video_id}/metadata.json"
                    )

                    return urls

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(lambda: asyncio.run(upload_job_to_cloud()))
                    cloud_urls = future.result(timeout=300)

                logger.info(f"Uploaded stitched video {stitched_video_id} to cloud storage")

                if settings.MV_DEBUG_MODE:
                    from mv.debug import log_stitch_upload_complete
                    log_stitch_upload_complete(stitched_video_id, cloud_urls)

            except Exception as e:
                logger.warning(f"Failed to upload stitched video to cloud: {e}")

        # Determine video URL based on storage mode
        if cloud_urls:
            metadata["cloud_urls"] = cloud_urls
            metadata["cloud_url"] = cloud_urls.get("video")
            video_url = cloud_urls.get("video")
        else:
            video_url = f"/api/mv/get_video/{stitched_video_id}"

        metadata["local_video_url"] = f"/api/mv/get_video/{stitched_video_id}"
        metadata["storage_backend"] = "s3" if cloud_urls else "local"

        if settings.MV_DEBUG_MODE:
            from mv.debug import log_stitch_result
            log_stitch_result({
                "video_id": stitched_video_id,
                "video_path": str(output_path),
                "video_url": video_url,
                "file_size_bytes": os.path.getsize(output_path),
                "storage_backend": metadata["storage_backend"],
                "audio_overlay_applied": audio_overlay_applied,
            })

        return (
            stitched_video_id,
            str(output_path),
            video_url,
            metadata,
            audio_overlay_applied,
            audio_overlay_warning
        )

    finally:
        # Clean up temp directory if created
        if temp_dir and os.path.exists(temp_dir):
            import shutil
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
