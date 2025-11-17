"""
Cloud storage abstraction layer for Firebase Storage and AWS S3.

Provides a unified interface for uploading, downloading, and managing files
across different cloud storage providers using fsspec.

Usage:
    >>> storage = get_storage_backend()
    >>> url = await storage.upload_file("/tmp/video.mp4", "videos/job-123/final.mp4")
    >>> await storage.download_file("videos/job-123/final.mp4", "/tmp/download.mp4")
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
import fsspec
import asyncio
from functools import partial
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """
    Abstract interface for cloud storage operations.
    
    Provides provider-agnostic methods for file operations that work
    with both Firebase Storage (GCS) and AWS S3.
    """
    
    @abstractmethod
    async def upload_file(self, local_path: str, cloud_path: str) -> str:
        """
        Upload file from local filesystem to cloud storage.
        
        Args:
            local_path: Path to local file
            cloud_path: Destination path in cloud (e.g., "videos/job-123/final.mp4")
            
        Returns:
            Public URL to access the file
            
        Raises:
            FileNotFoundError: If local file doesn't exist
            Exception: If upload fails
        """
        pass
    
    @abstractmethod
    async def download_file(self, cloud_path: str, local_path: str) -> str:
        """
        Download file from cloud storage to local filesystem.
        
        Args:
            cloud_path: Path in cloud storage
            local_path: Destination path on local filesystem
            
        Returns:
            Local file path where file was saved
            
        Raises:
            FileNotFoundError: If cloud file doesn't exist
            Exception: If download fails
        """
        pass
    
    @abstractmethod
    async def copy_file(self, src_path: str, dest_path: str) -> str:
        """
        Copy/rename file within cloud storage (for creating backups).
        
        Args:
            src_path: Source path in cloud storage
            dest_path: Destination path in cloud storage
            
        Returns:
            Public URL to the new file
            
        Example:
            >>> await storage.copy_file(
            ...     "videos/job-123/final.mp4",
            ...     "videos/job-123/final_v1.mp4"
            ... )
        """
        pass
    
    @abstractmethod
    async def exists(self, cloud_path: str) -> bool:
        """
        Check if file exists in cloud storage.
        
        Args:
            cloud_path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete_file(self, cloud_path: str) -> None:
        """
        Delete file from cloud storage.
        
        Args:
            cloud_path: Path to file to delete
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        pass
    
    @abstractmethod
    async def list_files(self, prefix: str) -> List[str]:
        """
        List all files with given prefix.
        
        Args:
            prefix: Path prefix to filter by (e.g., "videos/job-123/")
            
        Returns:
            List of file paths matching the prefix
        """
        pass


class FirebaseStorageBackend(StorageBackend):
    """
    Firebase Storage implementation using Google Cloud Storage (gcsfs).
    
    Firebase Storage is built on Google Cloud Storage, so we use the
    'gs' filesystem from gcsfs.
    
    Example:
        >>> storage = FirebaseStorageBackend(
        ...     bucket="my-app.appspot.com",
        ...     credentials_path="./serviceAccountKey.json"
        ... )
        >>> url = await storage.upload_file("/tmp/video.mp4", "videos/job-123/final.mp4")
    """
    
    def __init__(self, bucket: str, credentials_path: str):
        """
        Initialize Firebase Storage backend.
        
        Args:
            bucket: GCS bucket name (e.g., "my-app.appspot.com")
            credentials_path: Path to Firebase service account JSON
        """
        self.bucket = bucket
        self.credentials_path = credentials_path
        
        # Initialize gcsfs filesystem
        # token parameter accepts path to service account key
        self.fs = fsspec.filesystem('gs', token=credentials_path)
        
        logger.info(f"Initialized Firebase Storage backend with bucket: {bucket}")
    
    def _get_full_path(self, cloud_path: str) -> str:
        """Convert cloud path to full GCS path."""
        return f"{self.bucket}/{cloud_path}"
    
    def _get_public_url(self, cloud_path: str) -> str:
        """Get public URL for a file."""
        return f"https://storage.googleapis.com/{self.bucket}/{cloud_path}"
    
    async def upload_file(self, local_path: str, cloud_path: str) -> str:
        """Upload file to Firebase Storage."""
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        full_path = self._get_full_path(cloud_path)
        
        logger.info(f"Uploading {local_path} to gs://{full_path}")
        
        try:
            # Run blocking I/O in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self.fs.put, local_path, full_path)
            )
            
            url = self._get_public_url(cloud_path)
            logger.info(f"Upload successful: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise
    
    async def download_file(self, cloud_path: str, local_path: str) -> str:
        """Download file from Firebase Storage."""
        full_path = self._get_full_path(cloud_path)
        
        # Check if file exists
        if not await self.exists(cloud_path):
            raise FileNotFoundError(f"Cloud file not found: gs://{full_path}")
        
        logger.info(f"Downloading gs://{full_path} to {local_path}")
        
        try:
            # Create parent directory if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Run blocking I/O in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self.fs.get, full_path, local_path)
            )
            
            logger.info(f"Download successful: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
    
    async def copy_file(self, src_path: str, dest_path: str) -> str:
        """Copy file within Firebase Storage."""
        src_full = self._get_full_path(src_path)
        dest_full = self._get_full_path(dest_path)
        
        logger.info(f"Copying gs://{src_full} to gs://{dest_full}")
        
        try:
            # Run blocking I/O in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self.fs.copy, src_full, dest_full)
            )
            
            url = self._get_public_url(dest_path)
            logger.info(f"Copy successful: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Copy failed: {e}")
            raise
    
    async def exists(self, cloud_path: str) -> bool:
        """Check if file exists in Firebase Storage."""
        full_path = self._get_full_path(cloud_path)
        
        try:
            loop = asyncio.get_event_loop()
            exists = await loop.run_in_executor(
                None,
                partial(self.fs.exists, full_path)
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False
    
    async def delete_file(self, cloud_path: str) -> None:
        """Delete file from Firebase Storage."""
        full_path = self._get_full_path(cloud_path)
        
        logger.info(f"Deleting gs://{full_path}")
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self.fs.rm, full_path)
            )
            logger.info(f"Delete successful: gs://{full_path}")
            
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            raise
    
    async def list_files(self, prefix: str) -> List[str]:
        """List files with prefix in Firebase Storage."""
        full_prefix = self._get_full_path(prefix)
        
        logger.info(f"Listing files with prefix: gs://{full_prefix}")
        
        try:
            loop = asyncio.get_event_loop()
            files = await loop.run_in_executor(
                None,
                partial(self.fs.ls, full_prefix)
            )
            
            # Remove bucket prefix from paths
            relative_paths = [
                f.replace(f"{self.bucket}/", "") for f in files
            ]
            
            logger.info(f"Found {len(relative_paths)} files")
            return relative_paths
            
        except Exception as e:
            logger.error(f"List files failed: {e}")
            return []


class S3StorageBackend(StorageBackend):
    """
    AWS S3 storage implementation using s3fs.
    
    Example:
        >>> storage = S3StorageBackend(
        ...     bucket="my-video-bucket",
        ...     aws_access_key="AKIA...",
        ...     aws_secret_key="...",
        ...     region="us-east-1"
        ... )
        >>> url = await storage.upload_file("/tmp/video.mp4", "videos/job-123/final.mp4")
    """
    
    def __init__(
        self,
        bucket: str,
        aws_access_key: str,
        aws_secret_key: str,
        region: str = "us-east-1"
    ):
        """
        Initialize S3 storage backend.
        
        Args:
            bucket: S3 bucket name
            aws_access_key: AWS access key ID
            aws_secret_key: AWS secret access key
            region: AWS region (default: us-east-1)
        """
        self.bucket = bucket
        self.region = region
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        
        # Initialize s3fs filesystem for file operations
        self.fs = fsspec.filesystem(
            's3',
            key=aws_access_key,
            secret=aws_secret_key,
            client_kwargs={'region_name': region}
        )
        
        # Initialize boto3 client for presigned URL generation
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        
        logger.info(f"Initialized S3 storage backend with bucket: {bucket}")
    
    def _get_full_path(self, cloud_path: str) -> str:
        """Convert cloud path to full S3 path."""
        return f"{self.bucket}/{cloud_path}"
    
    def _get_public_url(self, cloud_path: str) -> str:
        """Get public URL for a file."""
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{cloud_path}"
    
    def generate_presigned_url(self, cloud_path: str, expiry: int = 3600) -> str:
        """
        Generate a presigned URL for secure, time-limited access to an S3 object.
        
        Args:
            cloud_path: Path to the file in cloud storage (e.g., "mv/jobs/{id}/video.mp4")
            expiry: URL expiration time in seconds (default: 3600 = 1 hour)
            
        Returns:
            Presigned URL with AWS signature for authenticated access
            
        Raises:
            ClientError: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': cloud_path
                },
                ExpiresIn=expiry
            )
            logger.debug(f"Generated presigned URL for {cloud_path} (expires in {expiry}s)")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {cloud_path}: {e}")
            raise
    
    async def upload_file(self, local_path: str, cloud_path: str) -> str:
        """Upload file to S3."""
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        full_path = self._get_full_path(cloud_path)
        
        logger.info(f"Uploading {local_path} to s3://{full_path}")
        
        try:
            # Run blocking I/O in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self.fs.put, local_path, full_path)
            )
            
            # Generate presigned URL for secure, time-limited access
            from config import settings
            url = self.generate_presigned_url(cloud_path, expiry=settings.PRESIGNED_URL_EXPIRY)
            logger.info(f"Upload successful with presigned URL (expires in {settings.PRESIGNED_URL_EXPIRY}s)")
            return url
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise
    
    async def download_file(self, cloud_path: str, local_path: str) -> str:
        """Download file from S3."""
        full_path = self._get_full_path(cloud_path)
        
        # Check if file exists
        if not await self.exists(cloud_path):
            raise FileNotFoundError(f"Cloud file not found: s3://{full_path}")
        
        logger.info(f"Downloading s3://{full_path} to {local_path}")
        
        try:
            # Create parent directory if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Run blocking I/O in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self.fs.get, full_path, local_path)
            )
            
            logger.info(f"Download successful: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
    
    async def copy_file(self, src_path: str, dest_path: str) -> str:
        """Copy file within S3."""
        src_full = self._get_full_path(src_path)
        dest_full = self._get_full_path(dest_path)
        
        logger.info(f"Copying s3://{src_full} to s3://{dest_full}")
        
        try:
            # Run blocking I/O in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self.fs.copy, src_full, dest_full)
            )
            
            url = self._get_public_url(dest_path)
            logger.info(f"Copy successful: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Copy failed: {e}")
            raise
    
    async def exists(self, cloud_path: str) -> bool:
        """Check if file exists in S3."""
        full_path = self._get_full_path(cloud_path)
        
        try:
            loop = asyncio.get_event_loop()
            exists = await loop.run_in_executor(
                None,
                partial(self.fs.exists, full_path)
            )
            return exists
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False
    
    async def delete_file(self, cloud_path: str) -> None:
        """Delete file from S3."""
        full_path = self._get_full_path(cloud_path)
        
        logger.info(f"Deleting s3://{full_path}")
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self.fs.rm, full_path)
            )
            logger.info(f"Delete successful: s3://{full_path}")
            
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            raise
    
    async def list_files(self, prefix: str) -> List[str]:
        """List files with prefix in S3."""
        full_prefix = self._get_full_path(prefix)
        
        logger.info(f"Listing files with prefix: s3://{full_prefix}")
        
        try:
            loop = asyncio.get_event_loop()
            files = await loop.run_in_executor(
                None,
                partial(self.fs.ls, full_prefix)
            )
            
            # Remove bucket prefix from paths
            relative_paths = [
                f.replace(f"{self.bucket}/", "") for f in files
            ]
            
            logger.info(f"Found {len(relative_paths)} files")
            return relative_paths
            
        except Exception as e:
            logger.error(f"List files failed: {e}")
            return []


def get_storage_backend() -> StorageBackend:
    """
    Factory function to get storage backend based on environment configuration.
    
    Reads STORAGE_BACKEND env var and returns appropriate implementation.
    
    Returns:
        StorageBackend instance (Firebase or S3)
        
    Raises:
        ValueError: If storage backend is invalid or required config is missing
        
    Example:
        >>> # In .env: STORAGE_BACKEND=firebase
        >>> storage = get_storage_backend()
        >>> isinstance(storage, FirebaseStorageBackend)
        True
    """
    from config import settings
    
    backend_type = settings.STORAGE_BACKEND.lower()
    
    if backend_type == "firebase":
        if not settings.STORAGE_BUCKET:
            raise ValueError("STORAGE_BUCKET environment variable is required")
        if not settings.FIREBASE_CREDENTIALS_PATH:
            raise ValueError("FIREBASE_CREDENTIALS_PATH environment variable is required")
        
        return FirebaseStorageBackend(
            bucket=settings.STORAGE_BUCKET,
            credentials_path=settings.FIREBASE_CREDENTIALS_PATH
        )
    
    elif backend_type == "s3":
        if not settings.STORAGE_BUCKET:
            raise ValueError("STORAGE_BUCKET environment variable is required")
        if not settings.AWS_ACCESS_KEY_ID:
            raise ValueError("AWS_ACCESS_KEY_ID environment variable is required")
        if not settings.AWS_SECRET_ACCESS_KEY:
            raise ValueError("AWS_SECRET_ACCESS_KEY environment variable is required")
        
        return S3StorageBackend(
            bucket=settings.STORAGE_BUCKET,
            aws_access_key=settings.AWS_ACCESS_KEY_ID,
            aws_secret_key=settings.AWS_SECRET_ACCESS_KEY,
            region=settings.AWS_REGION
        )
    
    else:
        raise ValueError(
            f"Invalid STORAGE_BACKEND: {backend_type}. "
            f"Must be 'firebase' or 's3'"
        )



