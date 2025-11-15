"""
Asset manager for handling file operations and cleanup.

Manages temporary files for video generation jobs including:
- Job directory structure creation
- File downloads with retry logic
- Cleanup of temporary resources
- File validation
"""

import os
import asyncio
import aiofiles
import aiohttp
from pathlib import Path
from typing import Optional, List
import shutil
import logging

logger = logging.getLogger(__name__)


class AssetManager:
    """
    Manages file operations for video generation jobs.

    Each job gets its own isolated directory structure:
    /tmp/video_jobs/{job_id}/
        scenes/     - Generated scene videos/images
        audio/      - Voiceover and music files
        final/      - Final composed video

    Example:
        >>> am = AssetManager("job-123")
        >>> await am.create_job_directory()
        >>> path = await am.download_file("https://example.com/image.png", "product.png")
        >>> await am.cleanup()
    """

    def __init__(self, job_id: str, base_path: str = "/tmp/video_jobs"):
        """
        Initialize asset manager for a specific job.

        Args:
            job_id: Unique identifier for this video generation job
            base_path: Base directory for all video jobs (default: /tmp/video_jobs)
        """
        self.job_id = job_id
        self.base_path = Path(base_path)
        self.job_dir = self.base_path / job_id

        # Subdirectories for different asset types
        self.scenes_dir = self.job_dir / "scenes"
        self.audio_dir = self.job_dir / "audio"
        self.final_dir = self.job_dir / "final"

    async def create_job_directory(self) -> None:
        """
        Create temporary directory structure for job.

        Creates:
        - Main job directory
        - scenes/ subdirectory
        - audio/ subdirectory
        - final/ subdirectory

        Example:
            >>> am = AssetManager("job-123")
            >>> await am.create_job_directory()
            >>> assert am.job_dir.exists()
        """
        try:
            # Create all directories (exists_ok=True prevents errors if already exists)
            self.job_dir.mkdir(parents=True, exist_ok=True)
            self.scenes_dir.mkdir(exist_ok=True)
            self.audio_dir.mkdir(exist_ok=True)
            self.final_dir.mkdir(exist_ok=True)

            logger.info(f"Created job directory structure for {self.job_id}")
        except Exception as e:
            logger.error(f"Failed to create job directory for {self.job_id}: {e}")
            raise

    async def download_file(
        self,
        url: str,
        filename: str,
        subdir: Optional[str] = None,
        timeout: int = 300
    ) -> str:
        """
        Download file from URL to job directory.

        Args:
            url: URL to download from
            filename: Local filename to save as
            subdir: Optional subdirectory (scenes/audio/final)
            timeout: Download timeout in seconds (default: 300)

        Returns:
            Absolute path to downloaded file

        Raises:
            aiohttp.ClientError: If download fails
            asyncio.TimeoutError: If download times out

        Example:
            >>> path = await am.download_file(
            ...     "https://example.com/video.mp4",
            ...     "scene1.mp4",
            ...     subdir="scenes"
            ... )
        """
        # Determine target directory
        if subdir == "scenes":
            target_dir = self.scenes_dir
        elif subdir == "audio":
            target_dir = self.audio_dir
        elif subdir == "final":
            target_dir = self.final_dir
        else:
            target_dir = self.job_dir

        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / filename

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as response:
                    response.raise_for_status()

                    # Download file in chunks to handle large files
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)

            logger.info(f"Downloaded {filename} to {file_path}")
            return str(file_path)

        except aiohttp.ClientError as e:
            logger.error(f"Failed to download {url}: {e}")
            # Clean up partial download
            if file_path.exists():
                file_path.unlink()
            raise
        except asyncio.TimeoutError as e:
            logger.error(f"Download timeout for {url}")
            # Clean up partial download
            if file_path.exists():
                file_path.unlink()
            raise

    async def download_with_retry(
        self,
        url: str,
        filename: str,
        subdir: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 300
    ) -> str:
        """
        Download with exponential backoff retry.

        Retries download on transient failures with exponential backoff:
        - Attempt 1: immediate
        - Attempt 2: wait 2 seconds
        - Attempt 3: wait 4 seconds

        Args:
            url: URL to download from
            filename: Local filename to save as
            subdir: Optional subdirectory (scenes/audio/final)
            max_retries: Maximum number of retry attempts (default: 3)
            timeout: Download timeout in seconds (default: 300)

        Returns:
            Absolute path to downloaded file

        Raises:
            Exception: If all retry attempts fail

        Example:
            >>> path = await am.download_with_retry(
            ...     "https://example.com/video.mp4",
            ...     "scene1.mp4",
            ...     max_retries=5
            ... )
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Download attempt {attempt + 1}/{max_retries} for {filename}")
                return await self.download_file(url, filename, subdir, timeout)

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == max_retries - 1:
                    # Last attempt failed, raise the error
                    logger.error(f"All {max_retries} download attempts failed for {filename}")
                    raise

                # Calculate exponential backoff delay
                delay = 2 ** attempt
                logger.warning(
                    f"Download attempt {attempt + 1} failed for {filename}, "
                    f"retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)

        # Should never reach here, but for type safety
        raise RuntimeError(f"Failed to download {filename} after {max_retries} attempts")

    async def save_file(
        self,
        content: bytes,
        filename: str,
        subdir: Optional[str] = None
    ) -> str:
        """
        Save binary content to file.

        Args:
            content: Binary content to save
            filename: Local filename to save as
            subdir: Optional subdirectory (scenes/audio/final)

        Returns:
            Absolute path to saved file

        Example:
            >>> content = b"video data..."
            >>> path = await am.save_file(content, "scene1.mp4", "scenes")
        """
        # Determine target directory
        if subdir == "scenes":
            target_dir = self.scenes_dir
        elif subdir == "audio":
            target_dir = self.audio_dir
        elif subdir == "final":
            target_dir = self.final_dir
        else:
            target_dir = self.job_dir

        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / filename

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        logger.info(f"Saved {len(content)} bytes to {file_path}")
        return str(file_path)

    async def get_file_path(
        self,
        filename: str,
        subdir: Optional[str] = None
    ) -> Path:
        """
        Get path to file in job directory.

        Args:
            filename: Filename to get path for
            subdir: Optional subdirectory (scenes/audio/final)

        Returns:
            Path object for the file

        Example:
            >>> path = await am.get_file_path("scene1.mp4", "scenes")
            >>> print(path)
            /tmp/video_jobs/job-123/scenes/scene1.mp4
        """
        if subdir == "scenes":
            return self.scenes_dir / filename
        elif subdir == "audio":
            return self.audio_dir / filename
        elif subdir == "final":
            return self.final_dir / filename
        else:
            return self.job_dir / filename

    async def list_files(self, subdir: Optional[str] = None) -> List[Path]:
        """
        List all files in a directory.

        Args:
            subdir: Optional subdirectory (scenes/audio/final)

        Returns:
            List of Path objects for files

        Example:
            >>> files = await am.list_files("scenes")
            >>> for f in files:
            ...     print(f.name)
        """
        if subdir == "scenes":
            target_dir = self.scenes_dir
        elif subdir == "audio":
            target_dir = self.audio_dir
        elif subdir == "final":
            target_dir = self.final_dir
        else:
            target_dir = self.job_dir

        if not target_dir.exists():
            return []

        return [f for f in target_dir.iterdir() if f.is_file()]

    async def validate_file(
        self,
        filename: str,
        subdir: Optional[str] = None,
        min_size: int = 100
    ) -> bool:
        """
        Validate that file exists and meets size requirements.

        Args:
            filename: Filename to validate
            subdir: Optional subdirectory (scenes/audio/final)
            min_size: Minimum file size in bytes (default: 100)

        Returns:
            True if file is valid, False otherwise

        Example:
            >>> valid = await am.validate_file("scene1.mp4", "scenes", min_size=1000)
        """
        file_path = await self.get_file_path(filename, subdir)

        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return False

        file_size = file_path.stat().st_size
        if file_size < min_size:
            logger.warning(f"File too small ({file_size} bytes): {file_path}")
            return False

        logger.info(f"File validated: {file_path} ({file_size} bytes)")
        return True

    async def cleanup(self) -> None:
        """
        Remove all temporary files for this job.

        Recursively deletes the entire job directory and all its contents.
        Safe to call even if directory doesn't exist.

        Example:
            >>> await am.cleanup()
            >>> assert not am.job_dir.exists()
        """
        try:
            if self.job_dir.exists():
                # Use shutil.rmtree for recursive deletion
                await asyncio.to_thread(shutil.rmtree, self.job_dir)
                logger.info(f"Cleaned up job directory: {self.job_id}")
            else:
                logger.info(f"Job directory does not exist, nothing to clean: {self.job_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup job directory {self.job_id}: {e}")
            raise

    async def get_disk_usage(self) -> int:
        """
        Calculate total disk usage for this job.

        Returns:
            Total size in bytes

        Example:
            >>> size = await am.get_disk_usage()
            >>> print(f"Job uses {size / 1024 / 1024:.2f} MB")
        """
        if not self.job_dir.exists():
            return 0

        total_size = 0
        for path in self.job_dir.rglob('*'):
            if path.is_file():
                total_size += path.stat().st_size

        return total_size

    def __repr__(self) -> str:
        return f"AssetManager(job_id='{self.job_id}', path='{self.job_dir}')"
