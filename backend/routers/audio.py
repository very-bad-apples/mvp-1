"""
Audio download endpoint router

Handles downloading audio from YouTube URLs and converting to MP3.
"""

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Optional
import os
import uuid
import subprocess

from schemas import AudioDownloadRequest, AudioDownloadResponse, AudioTrimRequest, AudioTrimResponse, ErrorResponse
from services.audio_downloader import AudioDownloader, AudioDownloadError
from pipeline.asset_manager import AssetManager
from config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/audio", tags=["Audio"])

# Initialize audio downloader service with optional FFmpeg path from config
# Note: AudioDownloader will work without FFmpeg, but will return original format instead of MP3
audio_downloader = AudioDownloader(ffmpeg_path=settings.FFMPEG_PATH)

# Base path for audio storage - use mv/outputs/audio directory
AUDIO_BASE_PATH = str(Path(__file__).parent.parent / "mv" / "outputs" / "audio")
# Ensure directory exists
Path(AUDIO_BASE_PATH).mkdir(parents=True, exist_ok=True)


@router.post(
    "/download",
    response_model=AudioDownloadResponse,
    status_code=200,
    responses={
        200: {"description": "Audio downloaded and converted successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error or download failure"}
    },
    summary="Download Audio from YouTube",
    description="""
Download audio from a YouTube URL and convert it to MP3 format.

This endpoint:
1. Validates the YouTube URL
2. Downloads the best quality audio stream
3. Converts to MP3 format using FFmpeg
4. Saves the file to temporary storage
5. Returns metadata and access URL

**Limitations:**
- Synchronous processing (may take 10-60+ seconds depending on video length)
- Requires FFmpeg to be installed on the system
- File-based storage (MP3 saved to filesystem)

**Required Fields:**
- url: YouTube video URL (e.g., https://www.youtube.com/watch?v=...)

**Optional Fields:**
- audio_quality: Audio quality in kbps (default: "192", options: "128", "192", "256", "320")
"""
)
async def download_audio(request: AudioDownloadRequest):
    """
    Download audio from YouTube URL and convert to MP3.

    **Example Request:**
    ```json
    {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "audio_quality": "192"
    }
    ```

    **Example Response:**
    ```json
    {
        "audio_id": "550e8400-e29b-41d4-a716-446655440000",
        "audio_path": "/tmp/audio_downloads/550e8400...mp3",
        "audio_url": "/api/audio/get/550e8400-e29b-41d4-a716-446655440000",
        "filename": "550e8400-e29b-41d4-a716-446655440000.mp3",
        "title": "Example Video Title",
        "duration": 180,
        "file_size_bytes": 3456789,
        "metadata": {
            "uploader": "Channel Name",
            "view_count": 1000000
        }
    }
    ```
    """
    try:
        logger.info(
            "audio_download_request_received",
            url=request.url[:100] if len(request.url) > 100 else request.url,
            audio_quality=request.audio_quality
        )

        # Validate URL
        if not request.url or not request.url.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "URL is required",
                    "details": "The 'url' field cannot be empty"
                }
            )

        # Basic YouTube URL validation
        url = request.url.strip()
        if "youtube.com" not in url and "youtu.be" not in url:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid YouTube URL",
                    "details": "URL must be a valid YouTube link (youtube.com or youtu.be)"
                }
            )

        # Validate audio quality
        valid_qualities = ["128", "192", "256", "320"]
        if request.audio_quality not in valid_qualities:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": f"Invalid audio quality: {request.audio_quality}",
                    "details": f"Valid qualities: {', '.join(valid_qualities)}"
                }
            )

        # Download audio
        result = await audio_downloader.download_audio(
            url=url,
            output_path=AUDIO_BASE_PATH,
            audio_quality=request.audio_quality
        )

        # Extract audio_id from filename (remove .mp3 extension)
        audio_id = Path(result['filename']).stem

        # Build response
        response = AudioDownloadResponse(
            audio_id=audio_id,
            audio_path=result['audio_path'],
            audio_url=f"/api/audio/get/{audio_id}",
            filename=result['filename'],
            format=result.get('format', 'mp3'),
            title=result['title'],
            duration=result.get('duration'),
            file_size_bytes=result['file_size_bytes'],
            metadata=result.get('metadata', {})
        )

        logger.info(
            "audio_download_completed",
            audio_id=audio_id,
            title=result['title'],
            file_size_bytes=result['file_size_bytes']
        )

        return response

    except AudioDownloadError as e:
        logger.error("audio_download_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "AudioDownloadError",
                "message": "Failed to download audio from YouTube",
                "details": str(e)
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("audio_download_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "An unexpected error occurred during audio download",
                "details": str(e)
            }
        )


@router.get(
    "/get/{audio_id}",
    responses={
        200: {"description": "Audio file", "content": {"audio/mpeg": {}}},
        404: {"description": "Audio file not found"}
    },
    summary="Get Downloaded Audio File",
    description="""
Retrieve a downloaded MP3 file by its ID.

Returns the MP3 file directly for download or playback.

**Example:**
```
GET /api/audio/get/550e8400-e29b-41d4-a716-446655440000
```
"""
)
async def get_audio(audio_id: str):
    """
    Retrieve a downloaded audio file by ID.

    This endpoint:
    1. Validates the audio_id format
    2. Searches for the MP3 file
    3. Returns the audio file as a streaming response
    """
    # Validate audio_id format (basic UUID validation)
    if not audio_id or len(audio_id) < 10:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Invalid audio_id format",
                "details": "audio_id must be a valid identifier"
            }
        )

    # Try to find audio file - prioritize MP3 since we always convert to MP3
    audio_path = None
    
    # Check MP3 first (since we always convert to MP3)
    mp3_path = Path(AUDIO_BASE_PATH) / f"{audio_id}.mp3"
    if mp3_path.exists():
        audio_path = mp3_path
    else:
        # Fallback to other formats (shouldn't happen, but just in case)
        for ext in ['m4a', 'opus', 'webm', 'ogg', 'aac']:
            potential_path = Path(AUDIO_BASE_PATH) / f"{audio_id}.{ext}"
            if potential_path.exists():
                audio_path = potential_path
                break
    
    if not audio_path:
        logger.warning("audio_file_not_found", audio_id=audio_id)
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NotFound",
                "message": f"Audio file with ID {audio_id} not found",
                "details": "The audio may have been deleted or the ID is incorrect"
            }
        )

    # Determine media type based on file extension
    media_type_map = {
        'mp3': 'audio/mpeg',
        'm4a': 'audio/mp4',
        'opus': 'audio/opus',
        'webm': 'audio/webm',
        'ogg': 'audio/ogg',
        'aac': 'audio/aac'
    }
    
    ext = audio_path.suffix[1:].lower()  # Remove the dot
    media_type = media_type_map.get(ext, 'audio/mpeg')
    
    # Always return as MP3 filename (since we always convert to MP3)
    # Use the actual file extension for media type, but force filename to .mp3
    filename = f"{audio_id}.mp3"
    
    logger.info("audio_file_serving", audio_id=audio_id, audio_path=str(audio_path), format=ext, filename=filename)

    return FileResponse(
        path=str(audio_path),
        media_type=media_type,
        filename=filename
    )


@router.get(
    "/info/{audio_id}",
    responses={
        200: {"description": "Audio file metadata"},
        404: {"description": "Audio file not found"}
    },
    summary="Get Audio File Information",
    description="""
Get metadata about a downloaded audio file without downloading it.

Returns information like file size, creation time, and whether the file exists.

**Example Response:**
```json
{
    "audio_id": "550e8400-e29b-41d4-a716-446655440000",
    "exists": true,
    "file_size_bytes": 3456789,
    "created_at": "2025-01-14T10:30:25Z"
}
```
"""
)
async def get_audio_info(audio_id: str):
    """
    Get metadata about a downloaded audio file.

    This endpoint:
    1. Validates the audio_id format
    2. Checks if the audio file exists
    3. Returns metadata about the file (size, creation time)
    """
    # Validate audio_id format
    if not audio_id or len(audio_id) < 10:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Invalid audio_id format",
                "details": "audio_id must be a valid identifier"
            }
        )

    # Try to find audio file with any common extension
    audio_extensions = ['mp3', 'm4a', 'opus', 'webm', 'ogg', 'aac']
    audio_path = None
    
    for ext in audio_extensions:
        potential_path = Path(AUDIO_BASE_PATH) / f"{audio_id}.{ext}"
        if potential_path.exists():
            audio_path = potential_path
            break

    if not audio_path:
        return {
            "audio_id": audio_id,
            "exists": False,
            "file_size_bytes": None,
            "created_at": None
        }

    # Get file stats
    stat = audio_path.stat()
    from datetime import datetime, timezone
    created_at = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()

    logger.info("audio_info_retrieved", audio_id=audio_id, file_size_bytes=stat.st_size)

    return {
        "audio_id": audio_id,
        "exists": True,
        "file_size_bytes": stat.st_size,
        "created_at": created_at
    }


def trim_audio_from_start(source_path: str, output_path: str, start_at: int) -> dict:
    """
    Trim audio file from start position to end using ffmpeg.

    Args:
        source_path: Path to source audio file
        output_path: Path for trimmed output file
        start_at: Start time in seconds (trim from this point to end)

    Returns:
        Dictionary with metadata about trimmed audio

    Raises:
        RuntimeError: If ffmpeg fails
    """
    try:
        # Use ffmpeg to trim audio from start_at to end of file
        cmd = [
            'ffmpeg',
            '-i', source_path,
            '-ss', str(start_at),
            '-acodec', 'copy',  # Copy codec for faster processing
            '-y',  # Overwrite output file
            output_path
        ]

        logger.info(
            "audio_trim_starting",
            source_path=source_path,
            output_path=output_path,
            start_at=start_at,
            command=' '.join(cmd)
        )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout for audio trimming
        )

        if result.returncode != 0:
            logger.error("ffmpeg_trim_failed", stderr=result.stderr, returncode=result.returncode)
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")

        # Get file size
        file_size = os.path.getsize(output_path)

        logger.info("audio_trim_completed", output_path=output_path, file_size_bytes=file_size)

        return {
            "file_size_bytes": file_size,
            "ffmpeg_command": ' '.join(cmd)
        }

    except subprocess.TimeoutExpired:
        logger.error("audio_trim_timeout", source_path=source_path, start_at=start_at)
        raise RuntimeError("Audio trimming timed out after 60 seconds")
    except Exception as e:
        logger.error("audio_trim_error", error=str(e), exc_info=True)
        raise RuntimeError(f"Audio trimming failed: {str(e)}")


@router.post(
    "/trim",
    response_model=AudioTrimResponse,
    status_code=200,
    responses={
        200: {"description": "Audio trimmed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        404: {"model": ErrorResponse, "description": "Audio file not found"},
        500: {"model": ErrorResponse, "description": "Internal server error or trimming failure"}
    },
    summary="Trim Audio from Start Position",
    description="""
Trim audio from a specified start position to the end of the file.

This endpoint:
1. Validates the source audio_id exists
2. Trims the audio from start_at seconds to end using ffmpeg
3. Generates a new UUID for the trimmed audio
4. Saves the trimmed file to storage
5. Uploads to S3 if cloud storage is configured (optional)
6. Returns metadata and access URL for the trimmed audio

**Important Notes:**
- The original audio file remains unchanged
- A new UUID is generated for each trim operation
- Trimming creates a new file from start_at to end of audio
- S3 upload failures are non-fatal (local file still available)

**Required Fields:**
- audio_id: UUID of the source audio file

**Optional Fields:**
- start_at: Start position in seconds (default: 0)

**Example Use Case:**
User wants to skip the first 30 seconds of a song to start from the chorus.
They set start_at=30, and the trimmed audio begins at the 30-second mark.
"""
)
async def trim_audio(request: AudioTrimRequest):
    """
    Trim audio from specified start position to end.

    Creates a new audio file with a new UUID, leaving the original unchanged.

    **Example Request:**
    ```json
    {
        "audio_id": "550e8400-e29b-41d4-a716-446655440000",
        "start_at": 30
    }
    ```

    **Example Response:**
    ```json
    {
        "audio_id": "def456-e29b-41d4-a716-446655440000",
        "audio_path": "/backend/mv/outputs/audio/def456.mp3",
        "audio_url": "/api/audio/get/def456-e29b-41d4-a716-446655440000",
        "original_audio_id": "550e8400-e29b-41d4-a716-446655440000",
        "start_at": 30,
        "duration": null,
        "file_size_bytes": 2400000,
        "metadata": {
            "cloud_url": "https://...",
            "ffmpeg_command": "ffmpeg -i input.mp3 -ss 30 -acodec copy -y output.mp3"
        }
    }
    ```
    """
    try:
        logger.info(
            "audio_trim_request_received",
            audio_id=request.audio_id,
            start_at=request.start_at
        )

        # Validate audio_id format
        if not request.audio_id or len(request.audio_id) < 10:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid audio_id format",
                    "details": "audio_id must be a valid identifier"
                }
            )

        # Find source audio file
        source_audio_path = None

        # Check MP3 first (most common)
        mp3_path = Path(AUDIO_BASE_PATH) / f"{request.audio_id}.mp3"
        if mp3_path.exists():
            source_audio_path = mp3_path
        else:
            # Try other formats
            for ext in ['m4a', 'opus', 'webm', 'ogg', 'aac']:
                potential_path = Path(AUDIO_BASE_PATH) / f"{request.audio_id}.{ext}"
                if potential_path.exists():
                    source_audio_path = potential_path
                    break

        if not source_audio_path:
            logger.warning("audio_trim_source_not_found", audio_id=request.audio_id)
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Audio file with ID {request.audio_id} not found",
                    "details": "The source audio may have been deleted or the ID is incorrect"
                }
            )

        # Generate new UUID for trimmed audio
        new_audio_id = str(uuid.uuid4())
        output_path = Path(AUDIO_BASE_PATH) / f"{new_audio_id}.mp3"

        # Trim audio using ffmpeg
        trim_metadata = trim_audio_from_start(
            source_path=str(source_audio_path),
            output_path=str(output_path),
            start_at=request.start_at
        )

        # Upload to S3 if configured (optional - failures are non-fatal)
        cloud_url = None
        try:
            if settings.STORAGE_BUCKET:
                from services.storage_backend import get_storage_backend
                storage = get_storage_backend()

                # Upload trimmed audio to S3
                import asyncio
                cloud_url = await storage.upload_file(
                    str(output_path),
                    f"mv/outputs/audio/{new_audio_id}.mp3"
                )

                logger.info(f"Uploaded trimmed audio {new_audio_id} to cloud storage")
                trim_metadata["cloud_url"] = cloud_url
        except Exception as e:
            logger.warning(f"Failed to upload trimmed audio {new_audio_id} to cloud storage: {e}")
            # Continue without cloud upload - local file is still available

        # Build response
        response = AudioTrimResponse(
            audio_id=new_audio_id,
            audio_path=str(output_path),
            audio_url=f"/api/audio/get/{new_audio_id}",
            original_audio_id=request.audio_id,
            start_at=request.start_at,
            duration=None,  # Could be extracted from ffmpeg output if needed
            file_size_bytes=trim_metadata["file_size_bytes"],
            metadata=trim_metadata
        )

        logger.info(
            "audio_trim_completed",
            original_audio_id=request.audio_id,
            new_audio_id=new_audio_id,
            start_at=request.start_at,
            file_size_bytes=trim_metadata["file_size_bytes"]
        )

        return response

    except HTTPException:
        raise

    except Exception as e:
        logger.error("audio_trim_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "An unexpected error occurred during audio trimming",
                "details": str(e)
            }
        )

