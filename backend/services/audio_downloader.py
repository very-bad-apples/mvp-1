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
import tempfile
import os

import yt_dlp
from backend.config import settings

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
        logger.info(
            "AudioDownloader initialized",
            ffmpeg_available=self.ffmpeg_available,
            cookies_from_browser=settings.YTDLP_COOKIES_FROM_BROWSER,
            cookies_file=settings.YTDLP_COOKIES_FILE
        )

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

    async def _get_cookie_options(self) -> Dict[str, Any]:
        """
        Get cookie configuration for yt-dlp to bypass YouTube bot detection.
        
        Supports:
        - Browser cookie extraction (local development only)
        - Local file paths
        - S3 paths (s3://bucket/path/to/cookies.txt)
        - GCS paths (gs://bucket/path/to/cookies.txt)
        - HTTP/HTTPS URLs
        
        Returns:
            Dictionary with cookie options to add to ydl_opts
        """
        cookie_opts = {}
        
        # Priority 1: Use cookies from browser (automatic extraction)
        # NOTE: Only works in local development, not in containers/serverless
        if settings.YTDLP_COOKIES_FROM_BROWSER:
            browser = settings.YTDLP_COOKIES_FROM_BROWSER.lower()
            cookie_opts['cookiesfrombrowser'] = (browser,)
            logger.info("using_cookies_from_browser", browser=browser)
        
        # Priority 2: Use cookies file (local, S3, GCS, or HTTP)
        elif settings.YTDLP_COOKIES_FILE:
            cookies_path = await self._resolve_cookies_file(settings.YTDLP_COOKIES_FILE)
            if cookies_path:
                cookie_opts['cookiefile'] = cookies_path
                logger.info("using_cookies_file", path=cookies_path)
            else:
                logger.warning(
                    "cookies_file_not_found",
                    path=settings.YTDLP_COOKIES_FILE,
                    message="Cookies file specified but not found. Downloads may fail."
                )
        
        # No cookies configured - yt-dlp will try without cookies
        # This may fail with bot detection errors
        if not cookie_opts:
            logger.warning(
                "no_cookies_configured",
                message="No cookies configured. YouTube may block downloads. "
                        "Set YTDLP_COOKIES_FROM_BROWSER (local only) or YTDLP_COOKIES_FILE environment variable."
            )
        
        return cookie_opts
    
    async def _resolve_cookies_file(self, cookies_path: str) -> Optional[str]:
        """
        Resolve cookies file path, downloading from cloud storage if needed.
        
        Supports:
        - Local file paths: /path/to/cookies.txt
        - S3 paths: s3://bucket/path/to/cookies.txt
        - GCS paths: gs://bucket/path/to/cookies.txt
        - HTTP/HTTPS URLs: https://example.com/cookies.txt
        
        Returns:
            Local file path to cookies file, or None if not found
        """
        # Check if it's a cloud storage path or URL
        if cookies_path.startswith('s3://'):
            return await self._download_cookies_from_s3(cookies_path)
        elif cookies_path.startswith('gs://'):
            return await self._download_cookies_from_gcs(cookies_path)
        elif cookies_path.startswith(('http://', 'https://')):
            return await self._download_cookies_from_url(cookies_path)
        else:
            # Local file path
            local_path = Path(cookies_path)
            if local_path.exists():
                return str(local_path)
            else:
                logger.warning("cookies_file_not_found", path=str(local_path))
                return None
    
    async def _download_cookies_from_s3(self, s3_path: str) -> Optional[str]:
        """Download cookies file from S3."""
        try:
            # Parse s3://bucket/path/to/file
            parts = s3_path.replace('s3://', '').split('/', 1)
            if len(parts) != 2:
                logger.error("invalid_s3_path", path=s3_path)
                return None
            
            bucket_name, key = parts
            
            # Import S3 service
            from backend.services.s3_storage import S3StorageService
            s3_service = S3StorageService()
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w')
            temp_path = temp_file.name
            temp_file.close()
            
            # Download from S3
            s3_service.s3_client.download_file(bucket_name, key, temp_path)
            
            logger.info("cookies_downloaded_from_s3", s3_path=s3_path, local_path=temp_path)
            return temp_path
            
        except Exception as e:
            logger.error("failed_to_download_cookies_from_s3", path=s3_path, error=str(e))
            return None
    
    async def _download_cookies_from_gcs(self, gcs_path: str) -> Optional[str]:
        """Download cookies file from GCS."""
        try:
            # Parse gs://bucket/path/to/file
            parts = gcs_path.replace('gs://', '').split('/', 1)
            if len(parts) != 2:
                logger.error("invalid_gcs_path", path=gcs_path)
                return None
            
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
            return None
    
    async def _download_cookies_from_url(self, url: str) -> Optional[str]:
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
                        return None
                        
        except Exception as e:
            logger.error("failed_to_download_cookies_from_url", url=url, error=str(e))
            return None

    async def download_audio(
        self,
        url: str,
        output_path: str,
        audio_quality: str = "192",
        cookies: Optional[str] = None
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
        
        # Automatic bot detection bypass: Use Android client to avoid bot detection
        # This makes requests look like they're from the YouTube mobile app
        ydl_opts['extractor_args'] = {
            'youtube': {
                'player_client': ['android'],  # Use Android client (less bot detection)
                'player_skip': ['webpage'],  # Skip webpage parsing
            }
        }
        
        # Add realistic user agent for Android
        ydl_opts['user_agent'] = 'com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip'
        
        # Add cookie options to bypass YouTube bot detection (optional fallback)
        # Priority: Use cookies from request if provided
        cookies_temp_file = None
        if cookies:
            try:
                # Save user-provided cookies to temp file
                cookies_temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                cookies_temp_file.write(cookies)
                cookies_temp_file.close()
                ydl_opts['cookiefile'] = cookies_temp_file.name
                logger.info("using_cookies_from_request", temp_file=cookies_temp_file.name)
            except Exception as e:
                logger.warning("failed_to_save_cookies", error=str(e))
        else:
            # Fall back to environment-based cookies (if configured)
            cookie_opts = await self._get_cookie_options()
            ydl_opts.update(cookie_opts)
        
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
            # Try with Android client first (best for avoiding bot detection)
            try:
                result = await asyncio.to_thread(self._download_with_ytdlp, url, ydl_opts)
            except Exception as android_error:
                # If Android client fails, try iOS client as fallback
                logger.warning(
                    "android_client_failed",
                    error=str(android_error),
                    message="Trying iOS client as fallback"
                )
                ydl_opts['extractor_args'] = {
                    'youtube': {
                        'player_client': ['ios'],  # Try iOS client
                        'player_skip': ['webpage'],
                    }
                }
                ydl_opts['user_agent'] = 'com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)'
                result = await asyncio.to_thread(self._download_with_ytdlp, url, ydl_opts)

            # Find the downloaded audio file (check MP3 first, then other formats)
            # Priority: MP3 first (if yt-dlp converted it), then other formats
            audio_extensions = ['mp3', 'm4a', 'opus', 'webm', 'ogg', 'aac']
            audio_path = None
            downloaded_format = None
            
            # Check for MP3 first (preferred)
            mp3_files = list(output_dir.glob(f"{audio_id}.mp3"))
            if mp3_files:
                audio_path = mp3_files[0]
                downloaded_format = 'mp3'
                logger.info("mp3_file_found_after_download", audio_path=str(audio_path))
            else:
                # Check other formats
                for ext in ['m4a', 'opus', 'webm', 'ogg', 'aac']:
                    files = list(output_dir.glob(f"{audio_id}.{ext}"))
                    if files:
                        audio_path = files[0]
                        downloaded_format = ext
                        logger.info("audio_downloaded_in_format", format=ext, audio_path=str(audio_path))
                        break
            
            if not audio_path:
                raise AudioDownloadError(f"Audio file not found after download. Expected: {audio_id}.[mp3|m4a|opus|webm]")

            # ALWAYS convert to MP3 if not already MP3 (and FFmpeg is available)
            if downloaded_format != 'mp3':
                original_format = downloaded_format
                if self.ffmpeg_available and PYDUB_AVAILABLE:
                    logger.info("converting_audio_to_mp3", format=original_format, audio_path=str(audio_path))
                    audio_path = await self._convert_to_mp3(audio_path, audio_id, output_dir, audio_quality)
                    if audio_path.suffix == '.mp3':
                        downloaded_format = 'mp3'
                        logger.info("successfully_converted_to_mp3", original_format=original_format)
                    else:
                        logger.error(
                            "conversion_failed_keeping_original",
                            format=original_format,
                            message="MP3 conversion failed, keeping original format"
                        )
                        # Raise error if conversion failed - we want MP3!
                        raise AudioDownloadError(
                            f"Failed to convert audio to MP3. Downloaded format: {original_format}. "
                            "Please ensure FFmpeg and pydub are properly installed."
                        )
                else:
                    # If FFmpeg/pydub not available, raise error - we require MP3
                    raise AudioDownloadError(
                        "FFmpeg or pydub not available. MP3 conversion is required. "
                        "Please install FFmpeg to enable MP3 conversion."
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
        finally:
            # Clean up temp cookies file if created
            if cookies_temp_file and os.path.exists(cookies_temp_file.name):
                try:
                    os.unlink(cookies_temp_file.name)
                except Exception as e:
                    logger.warning("failed_to_cleanup_cookies", error=str(e))

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
        
        # Add cookie options to bypass YouTube bot detection
        cookie_opts = await self._get_cookie_options()
        ydl_opts.update(cookie_opts)

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

