"""
Lipsync module for syncing audio to video using Replicate's Lipsync-2-Pro model.

This module provides functionality for lip-syncing audio to video using
Sync Labs' Lipsync-2-Pro model via Replicate API using the ReplicateClient wrapper.
"""

import os
import time
import uuid
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from io import BytesIO

import httpx
import structlog
from pydantic import BaseModel, Field

from config import settings
from services.replicate_client import ReplicateClient


class LipsyncRequest(BaseModel):
    """Request model for lipsync generation."""

    video_url: Optional[str] = Field(None, description="URL to the video file (scene). Required if project_id and sequence not provided.")
    audio_url: Optional[str] = Field(None, description="URL to the audio file. Required if project_id and sequence not provided.")
    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Control expressiveness of lip movements (0.0 = subtle, 1.0 = exaggerated)"
    )
    occlusion_detection_enabled: Optional[bool] = Field(
        None,
        description="Enable occlusion detection for complex scenes with obstructions (may slow processing)"
    )
    active_speaker_detection: Optional[bool] = Field(
        None,
        description="Automatically detect and sync the active speaker in multi-person videos"
    )
    project_id: Optional[str] = Field(
        None, description="Project UUID for DynamoDB integration (requires sequence)"
    )
    sequence: Optional[int] = Field(
        None, ge=1, description="Scene sequence number for DynamoDB integration (requires project_id)"
    )


class LipsyncResponse(BaseModel):
    """Response model for lipsync generation."""

    video_id: str = Field(..., description="UUID for video retrieval")
    video_url: str = Field(..., description="S3 URL to the lipsynced video")
    audio_url: str = Field(..., description="S3 URL to the audio file")
    metadata: dict = Field(..., description="Generation metadata")


logger = structlog.get_logger(__name__)


def generate_lipsync(
    video_url: str,
    audio_url: str,
    temperature: Optional[float] = None,
    occlusion_detection_enabled: Optional[bool] = None,
    active_speaker_detection: Optional[bool] = None,
) -> tuple[str, str, str, dict]:
    """
    Generate a lip-synced video using Replicate's Lipsync-2-Pro model.
    Uploads video and audio directly to S3 and returns S3 URLs.

    Args:
        video_url: URL to the video file (scene)
        audio_url: URL to the audio file
        temperature: Control expressiveness of lip movements (0.0-1.0)
        occlusion_detection_enabled: Enable occlusion detection for complex scenes
        active_speaker_detection: Auto-detect active speaker in multi-person videos

    Returns:
        Tuple of (video_id, video_s3_url, audio_s3_url, audio_s3_key, metadata)
        - video_id: UUID for the lipsync job
        - video_s3_url: S3 presigned URL for the lipsynced video
        - audio_s3_url: S3 presigned URL for the audio file
        - audio_s3_key: S3 key for the audio file (for DynamoDB storage)
        - metadata: Generation metadata

    Raises:
        ValueError: If API token is not configured or S3 is not configured
        Exception: If lipsync generation fails
    """
    # Build input parameters
    input_params = {
        "video": video_url,
        "audio": audio_url,
    }

    # Add optional parameters
    if temperature is not None:
        input_params["temperature"] = temperature
    if occlusion_detection_enabled is not None:
        input_params["occlusion_detection_enabled"] = occlusion_detection_enabled
    if active_speaker_detection is not None:
        input_params["active_speaker_detection"] = active_speaker_detection

    # Track processing time
    start_time = time.time()

    # Use ReplicateClient (MSP) for better error handling, retry logic, and logging
    model_id = "sync/lipsync-2-pro"
    client = ReplicateClient()
    
    logger.info(
        "running_lipsync_model",
        model_id=model_id,
        video_url=video_url[:100] + "..." if len(video_url) > 100 else video_url,
        audio_url=audio_url[:100] + "..." if len(audio_url) > 100 else audio_url,
    )
    
    # Use Replicate MSP (Model Service Provider) via ReplicateClient
    # This uses the Client's prediction API for better control and monitoring
    output = client.run_model(model_id, input_params, use_file_output=True)
    
    processing_time = time.time() - start_time

    # Handle output (can be single FileOutput or list)
    if isinstance(output, list):
        video_output = output[0]
    else:
        video_output = output

    # Read video data
    video_data = video_output.read()

    # Generate UUID for video
    video_id = str(uuid.uuid4())

    # Validate S3 is configured
    if not settings.STORAGE_BUCKET:
        raise ValueError(
            "STORAGE_BUCKET is not configured. S3 storage is required for lipsync videos."
        )

    # Upload video directly to S3 (no local save)
    from services.storage_backend import get_storage_backend
    import asyncio
    import concurrent.futures

    async def upload_video_and_audio_to_s3():
        """Upload video and audio to S3."""
        storage = get_storage_backend()
        
        # Use temporary file for video upload (required by storage_backend)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
            temp_video.write(video_data)
            temp_video_path = temp_video.name
        
        try:
            # Upload video to S3
            video_cloud_path = f"mv/jobs/{video_id}/lipsync.mp4"
            video_s3_url = await storage.upload_file(
                temp_video_path,
                video_cloud_path
            )
            
            logger.info(
                "lipsync_video_uploaded_to_s3",
                video_id=video_id,
                cloud_path=video_cloud_path
            )
            
            # Download audio from URL and upload to S3
            audio_s3_url = None
            audio_s3_key = None
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    audio_response = await client.get(audio_url)
                    audio_response.raise_for_status()
                    audio_data = audio_response.content
                
                # Determine audio file extension from URL or content type
                audio_ext = ".mp3"  # Default
                if ".mp3" in audio_url.lower():
                    audio_ext = ".mp3"
                elif ".wav" in audio_url.lower():
                    audio_ext = ".wav"
                elif ".m4a" in audio_url.lower():
                    audio_ext = ".m4a"
                elif ".ogg" in audio_url.lower():
                    audio_ext = ".ogg"
                
                # Use temporary file for audio upload
                with tempfile.NamedTemporaryFile(delete=False, suffix=audio_ext) as temp_audio:
                    temp_audio.write(audio_data)
                    temp_audio_path = temp_audio.name
                
                try:
                    # Upload audio to S3
                    audio_cloud_path = f"mv/jobs/{video_id}/audio{audio_ext}"
                    audio_s3_url = await storage.upload_file(
                        temp_audio_path,
                        audio_cloud_path
                    )
                    audio_s3_key = audio_cloud_path  # Store S3 key for DynamoDB
                    
                    logger.info(
                        "audio_uploaded_to_s3",
                        video_id=video_id,
                        cloud_path=audio_cloud_path
                    )
                finally:
                    # Clean up temporary audio file
                    if os.path.exists(temp_audio_path):
                        os.unlink(temp_audio_path)
                        
            except Exception as e:
                logger.warning(
                    "audio_upload_to_s3_failed",
                    video_id=video_id,
                    audio_url=audio_url[:100] if len(audio_url) > 100 else audio_url,
                    error=str(e)
                )
                # Continue without audio upload - video is still available
            
            # Return both S3 URL and S3 key for audio (key needed for DynamoDB)
            # Fallback to original URL if upload fails, but no S3 key in that case
            return video_s3_url, audio_s3_url or audio_url, audio_s3_key
            
        finally:
            # Clean up temporary video file
            if os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
    
    # Run async upload in separate thread to avoid event loop conflicts
    def run_upload():
        return asyncio.run(upload_video_and_audio_to_s3())
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_upload)
        video_s3_url, audio_s3_url, audio_s3_key = future.result(timeout=300)  # 5 min timeout

    # Build metadata
    metadata = {
        "input_video_url": video_url,
        "input_audio_url": audio_url,
        "model_used": model_id,
        "parameters_used": {
            "temperature": temperature,
            "occlusion_detection_enabled": occlusion_detection_enabled,
            "active_speaker_detection": active_speaker_detection,
        },
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "processing_time_seconds": round(processing_time, 2),
        "file_size_bytes": len(video_data),
    }

    return video_id, video_s3_url, audio_s3_url, audio_s3_key, metadata

