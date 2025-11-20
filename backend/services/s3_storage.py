"""
S3 storage service for Music Video projects.

Handles file uploads, retrieval, and presigned URL generation.
Uses existing Terraform-configured S3 bucket.
"""

import asyncio
import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO, List
from pathlib import Path
import structlog
from config import settings

logger = structlog.get_logger()


class S3StorageService:
    """
    Service for managing S3 file operations.
    """

    def __init__(self):
        """Initialize S3 client."""
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket_name = settings.STORAGE_BUCKET

        logger.info(
            "s3_storage_initialized",
            bucket=self.bucket_name,
            region=settings.AWS_REGION
        )

    def upload_file(
        self,
        file_data: BinaryIO,
        s3_key: str,
        content_type: str = None
    ) -> str:
        """
        Upload file to S3.

        Args:
            file_data: File-like object to upload
            s3_key: S3 object key (path within bucket)
            content_type: Optional MIME type

        Returns:
            S3 key of uploaded file

        Raises:
            Exception if upload fails
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.s3_client.upload_fileobj(
                file_data,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            logger.info(
                "s3_file_uploaded",
                bucket=self.bucket_name,
                s3_key=s3_key,
                content_type=content_type
            )

            return s3_key

        except ClientError as e:
            logger.error(
                "s3_upload_failed",
                s3_key=s3_key,
                error=str(e),
                exc_info=True
            )
            raise Exception(f"Failed to upload file to S3: {e}")

    def upload_file_from_path(
        self,
        file_path: str,
        s3_key: str,
        content_type: str = None
    ) -> str:
        """
        Upload file from filesystem path to S3.

        Args:
            file_path: Path to local file
            s3_key: S3 object key
            content_type: Optional MIME type

        Returns:
            S3 key of uploaded file
        """
        try:
            with open(file_path, 'rb') as f:
                return self.upload_file(f, s3_key, content_type)
        except Exception as e:
            logger.error(
                "s3_upload_from_path_failed",
                file_path=file_path,
                error=str(e),
                exc_info=True
            )
            raise

    def generate_presigned_url(
        self,
        s3_key: str,
        expiry: int = None
    ) -> str:
        """
        Generate presigned URL for S3 object.

        Args:
            s3_key: S3 object key
            expiry: URL expiration in seconds (default: from settings)

        Returns:
            Presigned URL string

        Raises:
            Exception if URL generation fails
        """
        if expiry is None:
            expiry = settings.PRESIGNED_URL_EXPIRY

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiry
            )

            logger.info(
                "s3_presigned_url_generated",
                s3_key=s3_key,
                expiry_seconds=expiry
            )

            return url

        except ClientError as e:
            logger.error(
                "s3_presigned_url_failed",
                s3_key=s3_key,
                error=str(e),
                exc_info=True
            )
            raise Exception(f"Failed to generate presigned URL: {e}")

    def download_file(self, s3_key: str, local_path: str) -> str:
        """
        Download file from S3 to local path.

        Args:
            s3_key: S3 object key
            local_path: Local filesystem path to save to

        Returns:
            Local path where file was saved

        Raises:
            Exception if download fails
        """
        try:
            # Ensure parent directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )

            logger.info(
                "s3_file_downloaded",
                s3_key=s3_key,
                local_path=local_path
            )

            return local_path

        except ClientError as e:
            logger.error(
                "s3_download_failed",
                s3_key=s3_key,
                local_path=local_path,
                error=str(e),
                exc_info=True
            )
            raise Exception(f"Failed to download file from S3: {e}")

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3.

        Args:
            s3_key: S3 object key

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            # Re-raise other errors
            logger.error(
                "s3_check_exists_failed",
                s3_key=s3_key,
                error=str(e),
                exc_info=True
            )
            raise

    def delete_file(self, s3_key: str) -> None:
        """
        Delete file from S3.

        Args:
            s3_key: S3 object key

        Raises:
            Exception if deletion fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            logger.info(
                "s3_file_deleted",
                bucket=self.bucket_name,
                s3_key=s3_key
            )

        except ClientError as e:
            logger.error(
                "s3_delete_failed",
                s3_key=s3_key,
                error=str(e),
                exc_info=True
            )
            raise Exception(f"Failed to delete file from S3: {e}")

    def copy_file(self, src_s3_key: str, dest_s3_key: str) -> str:
        """
        Copy file within S3.

        Args:
            src_s3_key: Source S3 object key
            dest_s3_key: Destination S3 object key

        Returns:
            Destination S3 key

        Raises:
            Exception if copy fails
        """
        try:
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': src_s3_key
            }

            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_s3_key
            )

            logger.info(
                "s3_file_copied",
                src_key=src_s3_key,
                dest_key=dest_s3_key
            )

            return dest_s3_key

        except ClientError as e:
            logger.error(
                "s3_copy_failed",
                src_key=src_s3_key,
                dest_key=dest_s3_key,
                error=str(e),
                exc_info=True
            )
            raise Exception(f"Failed to copy file in S3: {e}")

    def list_files(self, prefix: str) -> List[str]:
        """
        List files with given prefix in S3.

        Args:
            prefix: S3 key prefix to filter by

        Returns:
            List of S3 keys matching the prefix

        Raises:
            Exception if listing fails
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response:
                return []

            keys = [obj['Key'] for obj in response['Contents']]

            logger.info(
                "s3_files_listed",
                prefix=prefix,
                count=len(keys)
            )

            return keys

        except ClientError as e:
            logger.error(
                "s3_list_failed",
                prefix=prefix,
                error=str(e),
                exc_info=True
            )
            raise Exception(f"Failed to list files in S3: {e}")

    # Async wrappers for use in async contexts (e.g., AssetPersistenceService)

    async def upload_file_async(
        self,
        file_data: BinaryIO,
        s3_key: str,
        content_type: str = None
    ) -> str:
        """
        Async wrapper for upload_file.

        Runs the sync operation in a thread pool executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.upload_file,
            file_data,
            s3_key,
            content_type
        )

    async def upload_file_from_path_async(
        self,
        file_path: str,
        s3_key: str,
        content_type: str = None
    ) -> str:
        """
        Async wrapper for upload_file_from_path.

        Runs the sync operation in a thread pool executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.upload_file_from_path,
            file_path,
            s3_key,
            content_type
        )

    async def download_file_async(
        self,
        s3_key: str,
        local_path: str
    ) -> str:
        """
        Async wrapper for download_file.

        Runs the sync operation in a thread pool executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.download_file,
            s3_key,
            local_path
        )

    async def file_exists_async(self, s3_key: str) -> bool:
        """
        Async wrapper for file_exists.

        Runs the sync operation in a thread pool executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.file_exists,
            s3_key
        )

    async def delete_file_async(self, s3_key: str) -> None:
        """
        Async wrapper for delete_file.

        Runs the sync operation in a thread pool executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.delete_file,
            s3_key
        )

    async def copy_file_async(
        self,
        src_s3_key: str,
        dest_s3_key: str
    ) -> str:
        """
        Async wrapper for copy_file.

        Runs the sync operation in a thread pool executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.copy_file,
            src_s3_key,
            dest_s3_key
        )

    async def list_files_async(self, prefix: str) -> List[str]:
        """
        Async wrapper for list_files.

        Runs the sync operation in a thread pool executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.list_files,
            prefix
        )


def generate_s3_key(project_id: str, file_type: str, filename: str = None) -> str:
    """
    Generate standardized S3 key for project files.

    Args:
        project_id: Project UUID
        file_type: Type of file (character, product, audio, scene_video, etc.)
        filename: Optional specific filename

    Returns:
        S3 key string

    Examples:
        >>> generate_s3_key("123", "character")
        "mv/projects/123/character.png"
        >>> generate_s3_key("123", "scene_video", "scene_001.mp4")
        "mv/projects/123/scenes/scene_001.mp4"
    """
    base_path = f"mv/projects/{project_id}"

    # Map file types to paths and extensions
    file_type_map = {
        "character": ("character.png", base_path),
        "product": ("product.jpg", base_path),
        "audio": ("audio.mp3", base_path),
        "scene_video": (filename or "scene.mp4", f"{base_path}/scenes"),
        "scene_audio": (filename or "audio.mp3", f"{base_path}/scenes"),
        "final_video": ("final.mp4", base_path),
    }

    if file_type in file_type_map:
        filename, path = file_type_map[file_type]
        return f"{path}/{filename}"

    # Default: use file_type as filename if no mapping
    if filename:
        return f"{base_path}/{filename}"
    return f"{base_path}/{file_type}"


def generate_scene_s3_key(project_id: str, sequence: int, asset_type: str) -> str:
    """
    Generate S3 key for scene assets.

    Args:
        project_id: Project UUID
        sequence: Scene sequence number (1-indexed)
        asset_type: Type of asset (audio, video, lipsynced)

    Returns:
        S3 key string

    Examples:
        >>> generate_scene_s3_key("123", 1, "video")
        "mv/projects/123/scenes/001/video.mp4"
        >>> generate_scene_s3_key("123", 2, "lipsynced")
        "mv/projects/123/scenes/002/lipsynced.mp4"
    """
    base_path = f"mv/projects/{project_id}/scenes/{sequence:03d}"

    type_extensions = {
        "audio": "mp3",
        "video": "mp4",
        "lipsynced": "mp4"
    }

    ext = type_extensions.get(asset_type)
    if not ext:
        raise ValueError(f"Unknown scene asset type: {asset_type}. Supported types: {list(type_extensions.keys())}")

    return f"{base_path}/{asset_type}.{ext}"


def validate_s3_key(s3_key: Optional[str], field_name: str = "S3 key") -> Optional[str]:
    """
    Validate that an S3 key is not a URL.
    
    S3 keys should be paths like "mv/projects/{id}/file.ext", not URLs like
    "https://..." or "s3://...". This ensures we never accidentally save
    presigned URLs or full S3 URLs to the database.
    
    Args:
        s3_key: S3 key to validate (can be None)
        field_name: Name of the field for error messages
        
    Returns:
        The validated S3 key (or None if input was None)
        
    Raises:
        ValueError: If s3_key appears to be a URL instead of a key
    """
    if s3_key is None:
        return None
    
    s3_key = s3_key.strip()
    
    # Check for URL patterns
    if s3_key.startswith(("http://", "https://", "s3://")):
        raise ValueError(
            f"{field_name} must be an S3 key (e.g., 'mv/projects/{id}/file.ext'), "
            f"not a URL. Received: {s3_key[:50]}..."
        )
    
    # Check for presigned URL patterns (AWS signature parameters)
    if "?" in s3_key and ("X-Amz-" in s3_key or "AWSAccessKeyId" in s3_key):
        raise ValueError(
            f"{field_name} must be an S3 key, not a presigned URL. "
            f"Presigned URLs contain query parameters and expire. Received: {s3_key[:50]}..."
        )
    
    return s3_key


# Singleton instance
_s3_storage_service: Optional[S3StorageService] = None


def get_s3_storage_service() -> S3StorageService:
    """
    Get singleton S3 storage service instance.

    Returns:
        S3StorageService instance
    """
    global _s3_storage_service
    if _s3_storage_service is None:
        _s3_storage_service = S3StorageService()
    return _s3_storage_service

