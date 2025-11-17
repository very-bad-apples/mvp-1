"""
Audio Download Service

Downloads audio from YouTube URLs and converts to MP3 format.
Uses yt-dlp for downloading and FFmpeg for audio extraction/conversion.
"""

import asyncio
import structlog
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

import yt_dlp

# pydub is optional - only needed if FFmpeg is available for conversion
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None

logger = structlog.get_logger()


class AudioDownloadError(Exception):
    """Raised when audio download fails"""
    pass


class AudioDownloader:
    """
    Service for downloading audio from YouTube URLs and converting to MP3.

    Features:
    - Downloads best quality audio from YouTube
    - Converts to MP3 format
    - Extracts metadata (title, duration, etc.)
    - Handles errors gracefully

    Example:
        >>> downloader = AudioDownloader()
        >>> result = await downloader.download_audio(
        ...     url="https://www.youtube.com/watch?v=...",
        ...     output_path="/tmp/audio"
        ... )
        >>> print(result["audio_path"])
    """

    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        Initialize the audio downloader service.
        
        Args:
            ffmpeg_path: Optional path to ffmpeg executable. If not provided,
                        will check system PATH.
        """
        self.ffmpeg_path = ffmpeg_path
        self._check_ffmpeg()
        logger.info("AudioDownloader initialized", ffmpeg_available=self.ffmpeg_available)

    def _check_ffmpeg(self) -> None:
        """
        Check if FFmpeg is available. If not, we'll download in original format.
        
        Sets self.ffmpeg_available flag instead of raising error.
        """
        self.ffmpeg_available = False
        
        # Check if custom path provided
        if self.ffmpeg_path:
            ffmpeg_exe = Path(self.ffmpeg_path)
            if ffmpeg_exe.exists():
                self.ffmpeg_available = True
                logger.info("ffmpeg_found_at_custom_path", path=self.ffmpeg_path)
                return

        # Check system PATH
        ffmpeg_cmd = shutil.which("ffmpeg")
        ffprobe_cmd = shutil.which("ffprobe")
        
        if ffmpeg_cmd and ffprobe_cmd:
            self.ffmpeg_available = True
            logger.info("ffmpeg_found_in_path", ffmpeg=ffmpeg_cmd, ffprobe=ffprobe_cmd)
        else:
            logger.warning(
                "ffmpeg_not_found",
                message="FFmpeg not found. Will download audio in original format (m4a/opus). "
                        "To enable MP3 conversion, install FFmpeg."
            )

    async def download_audio(
        self,
        url: str,
        output_path: str,
        audio_quality: str = "192"
    ) -> Dict[str, Any]:
        """
        Download audio from YouTube URL and convert to MP3.

        Args:
            url: YouTube video URL
            output_path: Directory where MP3 file should be saved
            audio_quality: Audio quality in kbps (default: "192")

        Returns:
            Dictionary containing:
            - audio_path: Path to downloaded MP3 file
            - filename: Name of the MP3 file
            - title: Video title
            - duration: Duration in seconds (if available)
            - file_size_bytes: Size of the MP3 file
            - metadata: Additional metadata from YouTube

        Raises:
            AudioDownloadError: If download or conversion fails

        Example:
            >>> result = await downloader.download_audio(
            ...     url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            ...     output_path="/tmp/audio"
            ... )
        """
        logger.info("audio_download_started", url=url[:100], output_path=output_path)

        # Ensure output directory exists
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename to avoid conflicts
        audio_id = str(uuid.uuid4())
        output_template = str(output_dir / f"{audio_id}.%(ext)s")

        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'quiet': True,  # Suppress yt-dlp output
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': True,  # Only download single video, not playlists
        }
        
        # Add FFmpeg path if specified
        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path
        elif self.ffmpeg_available:
            # If FFmpeg is in PATH, yt-dlp will find it automatically
            # But we can also explicitly set it if needed
            ffmpeg_cmd = shutil.which("ffmpeg")
            if ffmpeg_cmd:
                # Extract directory from full path (remove ffmpeg.exe)
                ffmpeg_dir = str(Path(ffmpeg_cmd).parent)
                ydl_opts['ffmpeg_location'] = ffmpeg_dir
        
        # Always try to convert to MP3 if FFmpeg is available
        # If not available, we'll try pydub conversion after download
        if self.ffmpeg_available:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_quality,
            }]

        try:
            # Run yt-dlp in thread pool to avoid blocking
            result = await asyncio.to_thread(self._download_with_ytdlp, url, ydl_opts)

            # Find the downloaded audio file (could be mp3, m4a, opus, webm, etc.)
            audio_extensions = ['mp3', 'm4a', 'opus', 'webm', 'ogg', 'aac']
            audio_path = None
            downloaded_format = None
            
            for ext in audio_extensions:
                files = list(output_dir.glob(f"{audio_id}.{ext}"))
                if files:
                    audio_path = files[0]
                    downloaded_format = ext
                    break
            
            if not audio_path:
                raise AudioDownloadError(f"Audio file not found after download. Expected: {audio_id}.[mp3|m4a|opus|webm]")

            # If not MP3, try to convert using pydub (if FFmpeg and pydub are available)
            if downloaded_format != 'mp3':
                if self.ffmpeg_available and PYDUB_AVAILABLE:
                    logger.info("converting_audio_to_mp3", format=downloaded_format)
                    audio_path = await self._convert_to_mp3(audio_path, audio_id, output_dir, audio_quality)
                    if audio_path.suffix == '.mp3':
                        downloaded_format = 'mp3'
                    else:
                        logger.warning(
                            "conversion_failed_keeping_original",
                            format=downloaded_format,
                            message="MP3 conversion failed, keeping original format"
                        )
                else:
                    logger.warning(
                        "cannot_convert_to_mp3",
                        format=downloaded_format,
                        message="FFmpeg or pydub not available. Install FFmpeg to enable MP3 conversion."
                    )

            file_size = audio_path.stat().st_size

            logger.info(
                "audio_download_completed",
                url=url[:100],
                audio_path=str(audio_path),
                file_size_bytes=file_size,
                title=result.get('title', 'Unknown')
            )

            return {
                'audio_path': str(audio_path),
                'filename': audio_path.name,
                'format': downloaded_format or 'mp3',
                'title': result.get('title', 'Unknown'),
                'duration': result.get('duration'),
                'file_size_bytes': file_size,
                'metadata': {
                    'uploader': result.get('uploader'),
                    'upload_date': result.get('upload_date'),
                    'view_count': result.get('view_count'),
                    'thumbnail': result.get('thumbnail'),
                    'original_format': downloaded_format,
                    'converted_to_mp3': downloaded_format != 'mp3' and self.ffmpeg_available
                }
            }

        except Exception as e:
            logger.error("audio_download_failed", url=url[:100], error=str(e), exc_info=True)
            raise AudioDownloadError(f"Failed to download audio: {str(e)}")

    async def _convert_to_mp3(
        self,
        input_path: Path,
        audio_id: str,
        output_dir: Path,
        quality: str
    ) -> Path:
        """
        Convert audio file to MP3 using pydub.
        
        Args:
            input_path: Path to input audio file
            audio_id: Audio ID for output filename
            output_dir: Output directory
            quality: Audio quality (bitrate)
            
        Returns:
            Path to converted MP3 file (or original if conversion fails)
        """
        if not PYDUB_AVAILABLE:
            logger.warning("pydub_not_available", message="Cannot convert to MP3 - pydub not installed")
            return input_path
        
        if not self.ffmpeg_available:
            logger.warning("ffmpeg_not_available", message="Cannot convert to MP3 - FFmpeg not installed")
            return input_path
            
        output_path = output_dir / f"{audio_id}.mp3"
        
        try:
            # Load audio file
            logger.info("loading_audio_for_conversion", input_path=str(input_path))
            audio = await asyncio.to_thread(AudioSegment.from_file, str(input_path))
            
            # Convert to MP3
            bitrate = f"{quality}k"
            logger.info("exporting_audio_to_mp3", output_path=str(output_path), bitrate=bitrate)
            await asyncio.to_thread(audio.export, str(output_path), format="mp3", bitrate=bitrate)
            
            # Verify MP3 file was created
            if output_path.exists() and output_path.stat().st_size > 0:
                # Delete original file only if conversion succeeded
                input_path.unlink()
                logger.info(
                    "audio_converted_to_mp3",
                    input_format=input_path.suffix,
                    output_path=str(output_path),
                    file_size_bytes=output_path.stat().st_size
                )
                return output_path
            else:
                logger.error("mp3_file_not_created", output_path=str(output_path))
                return input_path
            
        except Exception as e:
            logger.error("audio_conversion_failed", error=str(e), exc_info=True)
            # If conversion fails, return original file
            return input_path

    def _download_with_ytdlp(self, url: str, ydl_opts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download audio using yt-dlp (runs in thread pool).

        Args:
            url: YouTube URL
            ydl_opts: yt-dlp configuration options

        Returns:
            Dictionary with video metadata
        """
        info = {}
        
        def progress_hook(d):
            """Progress hook for yt-dlp (currently unused but can be extended)"""
            if d['status'] == 'finished':
                info.update(d)

        ydl_opts['progress_hooks'] = [progress_hook]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first to get metadata
            video_info = ydl.extract_info(url, download=True)
            
            # Update info with video metadata
            info.update({
                'title': video_info.get('title'),
                'duration': video_info.get('duration'),
                'uploader': video_info.get('uploader'),
                'upload_date': video_info.get('upload_date'),
                'view_count': video_info.get('view_count'),
                'thumbnail': video_info.get('thumbnail'),
            })

        return info

    async def get_audio_info(self, url: str) -> Dict[str, Any]:
        """
        Get audio metadata without downloading.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary with video metadata (title, duration, etc.)

        Example:
            >>> info = await downloader.get_audio_info("https://www.youtube.com/watch?v=...")
            >>> print(info["title"])
        """
        logger.info("audio_info_requested", url=url[:100])

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': True,
        }

        try:
            def extract_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return {
                        'title': info.get('title'),
                        'duration': info.get('duration'),
                        'uploader': info.get('uploader'),
                        'thumbnail': info.get('thumbnail'),
                        'view_count': info.get('view_count'),
                    }

            info = await asyncio.to_thread(extract_info)
            logger.info("audio_info_retrieved", url=url[:100], title=info.get('title'))
            return info

        except Exception as e:
            logger.error("audio_info_failed", url=url[:100], error=str(e))
            raise AudioDownloadError(f"Failed to get audio info: {str(e)}")

