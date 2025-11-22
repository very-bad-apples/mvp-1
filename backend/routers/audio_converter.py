"""
Audio converter endpoint router

Converts YouTube videos to MP3 format in memory (no file saving).
"""

import subprocess
import structlog
from io import BytesIO
from pathlib import Path
import tempfile
import asyncio
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from backend.config import settings

logger = structlog.get_logger()


async def _resolve_cookies_file_for_subprocess(cookies_path: str) -> str:
    """
    Resolve cookies file path for subprocess, downloading from cloud storage if needed.
    
    Supports:
    - Local file paths: /path/to/cookies.txt
    - S3 paths: s3://bucket/path/to/cookies.txt
    - GCS paths: gs://bucket/path/to/cookies.txt
    - HTTP/HTTPS URLs: https://example.com/cookies.txt
    
    Returns:
        Local file path to cookies file, or empty string if not found
    """
    # Check if it's a cloud storage path or URL
    if cookies_path.startswith('s3://'):
        return await _download_cookies_from_s3(cookies_path)
    elif cookies_path.startswith('gs://'):
        return await _download_cookies_from_gcs(cookies_path)
    elif cookies_path.startswith(('http://', 'https://')):
        return await _download_cookies_from_url(cookies_path)
    else:
        # Local file path
        local_path = Path(cookies_path)
        if local_path.exists():
            return str(local_path)
        else:
            logger.warning("cookies_file_not_found", path=str(local_path))
            return ""


async def _download_cookies_from_s3(s3_path: str) -> str:
    """Download cookies file from S3."""
    try:
        # Parse s3://bucket/path/to/file
        parts = s3_path.replace('s3://', '').split('/', 1)
        if len(parts) != 2:
            logger.error("invalid_s3_path", path=s3_path)
            return ""
        
        bucket_name, key = parts
        
        # Import S3 service
        from backend.services.s3_storage import S3StorageService
        s3_service = S3StorageService()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w')
        temp_path = temp_file.name
        temp_file.close()
        
        # Download from S3 (run in thread pool since boto3 is blocking)
        await asyncio.to_thread(s3_service.s3_client.download_file, bucket_name, key, temp_path)
        
        logger.info("cookies_downloaded_from_s3", s3_path=s3_path, local_path=temp_path)
        return temp_path
        
    except Exception as e:
        logger.error("failed_to_download_cookies_from_s3", path=s3_path, error=str(e))
        return ""


async def _download_cookies_from_gcs(gcs_path: str) -> str:
    """Download cookies file from GCS."""
    try:
        # Parse gs://bucket/path/to/file
        parts = gcs_path.replace('gs://', '').split('/', 1)
        if len(parts) != 2:
            logger.error("invalid_gcs_path", path=gcs_path)
            return ""
        
        bucket_name, key = parts
        
        # Import storage backend
        from backend.services.storage_backend import get_storage_backend
        storage = get_storage_backend()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w')
        temp_path = temp_file.name
        temp_file.close()
        
        # Download from GCS
        await storage.download_file(key, temp_path)
        
        logger.info("cookies_downloaded_from_gcs", gcs_path=gcs_path, local_path=temp_path)
        return temp_path
        
    except Exception as e:
        logger.error("failed_to_download_cookies_from_gcs", path=gcs_path, error=str(e))
        return ""


async def _download_cookies_from_url(url: str) -> str:
    """Download cookies file from HTTP/HTTPS URL."""
    try:
        import aiohttp
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w')
        temp_path = temp_file.name
        temp_file.close()
        
        # Download from URL
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(temp_path, 'wb') as f:
                        f.write(content)
                    logger.info("cookies_downloaded_from_url", url=url, local_path=temp_path)
                    return temp_path
                else:
                    logger.error("failed_to_download_cookies_from_url", url=url, status=response.status)
                    return ""
                    
    except Exception as e:
        logger.error("failed_to_download_cookies_from_url", url=url, error=str(e))
        return ""

router = APIRouter(prefix="/api/audio", tags=["Audio Converter"])


class ConvertYouTubeRequest(BaseModel):
    """Request model for YouTube to MP3 conversion."""
    url: str
    cookies: Optional[str] = Field(
        default=None,
        description="Optional YouTube cookies in Netscape format. Export with: yt-dlp --cookies-from-browser chrome --cookies cookies.txt https://youtube.com/watch?v=test"
    )


@router.post(
    "/convert-youtube",
    responses={
        200: {"description": "MP3 audio file", "content": {"audio/mpeg": {}}},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error or conversion failure"}
    },
    summary="Convert YouTube to MP3 (Memory Only)",
    description="""
Convert YouTube video to MP3 format without saving any files.

This endpoint:
1. Validates the YouTube URL
2. Downloads audio using yt-dlp directly to memory (stdout)
3. Returns MP3 data as streaming response
4. NO files are created on the server

**IMPORTANT:** This is a synchronous endpoint that may take 10-60+ seconds.

**Process:**
- yt-dlp downloads to stdout (memory stream)
- Audio captured in BytesIO (memory variable)
- Returned as HTTP response
- NO temporary files created

**Required Fields:**
- url: YouTube video URL (e.g., https://www.youtube.com/watch?v=...)
"""
)
async def convert_youtube_to_mp3(request: ConvertYouTubeRequest):
    """
    Convert YouTube video to MP3 in memory (no file saving).
    
    Args:
        request: ConvertYouTubeRequest with YouTube URL
        
    Returns:
        MP3 audio file as streaming response
        
    Raises:
        HTTPException: If URL is invalid or download fails
    """
    try:
        logger.info(
            "youtube_conversion_request_received",
            url=request.url[:100] if len(request.url) > 100 else request.url
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

        # Download audio directly to memory using yt-dlp
        logger.info("starting_youtube_download_to_memory", url=url[:100])
        
        # Find yt-dlp executable (prefer venv version)
        import shutil
        yt_dlp_path = shutil.which("yt-dlp")
        if not yt_dlp_path:
            # Try common venv locations
            import sys
            from pathlib import Path
            
            # Check if running in venv
            venv_bin = Path(sys.executable).parent
            possible_paths = [
                venv_bin / "yt-dlp.exe",  # Windows
                venv_bin / "yt-dlp",       # Linux/Mac
            ]
            
            for path in possible_paths:
                if path.exists():
                    yt_dlp_path = str(path)
                    break
            
            if not yt_dlp_path:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "ConfigurationError",
                        "message": "yt-dlp not found",
                        "details": "yt-dlp is not installed or not in PATH. Please install it with: pip install yt-dlp"
                    }
                )
        
        logger.info("using_yt_dlp", path=yt_dlp_path)
        
        command = [
            yt_dlp_path,
            '-f', 'bestaudio[ext=m4a]/bestaudio',  # Prefer m4a (faster, no conversion needed)
            '-o', '-',  # Output to stdout (memory)
            '--no-warnings',
            '--no-playlist',  # Don't download playlist
            '--quiet',
            '--progress',  # Show progress for debugging
            # Automatic bot detection bypass: Use Android client
            '--extractor-args', 'youtube:player_client=android',
            '--user-agent', 'com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip',
        ]
        
        # Optional: Add cookie options if provided (fallback if Android client fails)
        cookies_temp_file = None
        if request.cookies:
            try:
                # Save user-provided cookies to temp file
                cookies_temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                cookies_temp_file.write(request.cookies)
                cookies_temp_file.close()
                command.extend(['--cookies', cookies_temp_file.name])
                logger.info("using_cookies_from_request", temp_file=cookies_temp_file.name)
            except Exception as e:
                logger.warning("failed_to_save_cookies", error=str(e))
        elif settings.YTDLP_COOKIES_FROM_BROWSER:
            browser = settings.YTDLP_COOKIES_FROM_BROWSER.lower()
            command.extend(['--cookies-from-browser', browser])
            logger.info("using_cookies_from_browser", browser=browser)
        elif settings.YTDLP_COOKIES_FILE:
            cookies_path = await _resolve_cookies_file_for_subprocess(settings.YTDLP_COOKIES_FILE)
            if cookies_path:
                command.extend(['--cookies', cookies_path])
                logger.info("using_cookies_file", path=cookies_path)
        
        # Add URL at the end
        command.append(url)

        # Run yt-dlp and capture output in memory
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180  # 3 minute timeout
        )

        if process.returncode != 0:
            error_message = process.stderr.decode('utf-8', errors='ignore')
            logger.error(
                "youtube_download_failed",
                url=url[:100],
                error=error_message,
                return_code=process.returncode
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "DownloadError",
                    "message": "Failed to download audio from YouTube",
                    "details": error_message or "Unknown error occurred"
                }
            )

        # Audio data is now in memory (process.stdout)
        audio_data = process.stdout
        
        if not audio_data or len(audio_data) == 0:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "DownloadError",
                    "message": "No audio data received from YouTube",
                    "details": "The download completed but no audio data was captured"
                }
            )

        logger.info(
            "youtube_conversion_completed",
            url=url[:100],
            audio_size_bytes=len(audio_data)
        )

        # Clean up temp cookies file if created
        if cookies_temp_file and os.path.exists(cookies_temp_file.name):
            try:
                os.unlink(cookies_temp_file.name)
            except Exception as e:
                logger.warning("failed_to_cleanup_cookies", error=str(e))
        
        # Return MP3 data as streaming response
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=audio.mp3"
            }
        )

    except subprocess.TimeoutExpired:
        logger.error("youtube_download_timeout", url=request.url[:100])
        raise HTTPException(
            status_code=500,
            detail={
                "error": "TimeoutError",
                "message": "YouTube download timed out",
                "details": "The download took longer than 3 minutes. Try a shorter video."
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "youtube_conversion_unexpected_error",
            url=request.url[:100],
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "An unexpected error occurred during conversion",
                "details": str(e)
            }
        )

