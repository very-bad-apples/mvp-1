"""
Audio converter endpoint router

Converts YouTube videos to MP3 format in memory (no file saving).
"""

import subprocess
import structlog
from io import BytesIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter(prefix="/api/audio", tags=["Audio Converter"])


class ConvertYouTubeRequest(BaseModel):
    """Request model for YouTube to MP3 conversion."""
    url: str


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
            url
        ]

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

