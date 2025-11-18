"""
S3 storage service for Music Video projects.

Handles file uploads, retrieval, and presigned URL generation.
Uses existing Terraform-configured S3 bucket.
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
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

