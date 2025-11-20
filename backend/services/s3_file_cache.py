"""
S3 File Cache Service for optimizing repeated S3 downloads.

Provides LRU-based local file caching for S3 objects to reduce bandwidth
and latency when the same files are accessed multiple times (e.g., video stitching).
"""

import time
import shutil
from collections import OrderedDict
from pathlib import Path
from typing import Optional
from s3fs import S3FileSystem
import structlog
from config import settings

logger = structlog.get_logger()


class S3FileCacheService:
    """
    Local file cache for S3 objects with LRU eviction.

    Downloads files from S3 on first access and caches them locally.
    Subsequent accesses return the cached file path without re-downloading.
    When cache size exceeds the limit, oldest (least recently used) files are evicted.

    Example usage:
        cache = get_s3_file_cache()

        # First access - downloads from S3
        video_path = cache.get_file("mv/projects/abc123/video.mp4")

        # Second access - returns cached path, no download
        same_path = cache.get_file("mv/projects/abc123/video.mp4")
    """

    def __init__(
        self,
        cache_dir: str = "/tmp/s3_cache",
        max_size_bytes: int = 5 * 1024 * 1024 * 1024  # 5GB default
    ):
        """
        Initialize S3 file cache.

        Args:
            cache_dir: Local directory for cached files (default: /tmp/s3_cache)
            max_size_bytes: Maximum cache size in bytes (default: 5GB)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_bytes

        # LRU tracking: {s3_key: last_access_timestamp}
        # OrderedDict maintains insertion order, oldest first
        self.access_tracker = OrderedDict()

        # Initialize s3fs for file operations
        self.s3fs = S3FileSystem(
            key=settings.AWS_ACCESS_KEY_ID,
            secret=settings.AWS_SECRET_ACCESS_KEY,
            client_kwargs={'region_name': settings.AWS_REGION}
        )
        self.bucket = settings.STORAGE_BUCKET

        logger.info(
            "s3_cache_initialized",
            cache_dir=str(self.cache_dir),
            max_size_mb=max_size_bytes / (1024 * 1024),
            bucket=self.bucket
        )

    def get_file(self, s3_key: str) -> str:
        """
        Get local path to file. Downloads from S3 if not in cache.

        Args:
            s3_key: S3 key like "mv/projects/{video_id}/video.mp4"

        Returns:
            Absolute path to local cached file

        Process:
            1. Check if file exists in cache at /tmp/s3_cache/{s3_key}
            2. If exists, update LRU access time and return path
            3. If not in cache, download from S3 to cache directory
            4. Check total cache size, evict oldest files if over limit
            5. Return local path
        """
        local_path = self.cache_dir / s3_key

        # Cache hit - file already downloaded
        if local_path.exists():
            logger.info("s3_cache_hit", s3_key=s3_key, path=str(local_path))
            self._update_lru(s3_key)
            return str(local_path)

        # Cache miss - download from S3
        logger.info("s3_cache_miss", s3_key=s3_key)
        self._download_to_cache(s3_key)
        self._evict_if_needed()
        self._update_lru(s3_key)

        return str(local_path)

    def _download_to_cache(self, s3_key: str) -> None:
        """
        Download file from S3 using s3fs.

        Args:
            s3_key: S3 object key

        Raises:
            Exception if download fails
        """
        local_path = self.cache_dir / s3_key
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Download using s3fs
        s3_path = f"{self.bucket}/{s3_key}"

        try:
            self.s3fs.get(s3_path, str(local_path))

            file_size = local_path.stat().st_size
            logger.info(
                "s3_file_downloaded",
                s3_key=s3_key,
                local_path=str(local_path),
                size_mb=file_size / (1024 * 1024)
            )

        except Exception as e:
            logger.error(
                "s3_download_failed",
                s3_key=s3_key,
                s3_path=s3_path,
                error=str(e),
                exc_info=True
            )
            # Clean up partial download if it exists
            if local_path.exists():
                local_path.unlink()
            raise Exception(f"Failed to download {s3_key} from S3: {e}")

    def _update_lru(self, s3_key: str) -> None:
        """
        Mark file as recently used in LRU tracker.

        Moves the s3_key to the end of the OrderedDict (most recently used position).

        Args:
            s3_key: S3 object key
        """
        # Move to end (most recently used)
        if s3_key in self.access_tracker:
            self.access_tracker.move_to_end(s3_key)
        else:
            self.access_tracker[s3_key] = time.time()

    def _evict_if_needed(self) -> None:
        """
        Evict oldest files from cache if total size exceeds limit.

        Removes files in LRU order (oldest first) until cache size is under max_size_bytes.
        """
        current_size = self._get_cache_size()

        # Evict oldest files until under limit
        while current_size > self.max_size_bytes and self.access_tracker:
            # Get oldest (first in OrderedDict)
            oldest_key = next(iter(self.access_tracker))
            oldest_path = self.cache_dir / oldest_key

            if oldest_path.exists():
                file_size = oldest_path.stat().st_size
                oldest_path.unlink()
                current_size -= file_size

                logger.info(
                    "s3_cache_evicted",
                    s3_key=oldest_key,
                    size_mb=file_size / (1024 * 1024),
                    new_cache_size_mb=current_size / (1024 * 1024)
                )

            # Remove from tracker regardless of file existence
            del self.access_tracker[oldest_key]

    def _get_cache_size(self) -> int:
        """
        Calculate total size of all files in cache.

        Returns:
            Total cache size in bytes
        """
        total_size = 0

        for s3_key in self.access_tracker.keys():
            file_path = self.cache_dir / s3_key
            if file_path.exists() and file_path.is_file():
                total_size += file_path.stat().st_size

        return total_size

    def clear_cache(self) -> None:
        """
        Remove all cached files (for testing or manual cleanup).

        Deletes the entire cache directory and recreates it empty.
        """
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.access_tracker.clear()

            logger.info("s3_cache_cleared", cache_dir=str(self.cache_dir))


# Singleton instance
_s3_file_cache: Optional[S3FileCacheService] = None


def get_s3_file_cache(
    cache_dir: str = "/tmp/s3_cache",
    max_size_bytes: int = 5 * 1024 * 1024 * 1024
) -> S3FileCacheService:
    """
    Get singleton S3 file cache instance.

    Args:
        cache_dir: Local directory for cached files (only used on first call)
        max_size_bytes: Maximum cache size in bytes (only used on first call)

    Returns:
        S3FileCacheService instance
    """
    global _s3_file_cache
    if _s3_file_cache is None:
        _s3_file_cache = S3FileCacheService(
            cache_dir=cache_dir,
            max_size_bytes=max_size_bytes
        )
    return _s3_file_cache
