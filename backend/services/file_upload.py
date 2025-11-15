"""
File Upload Handling Service

Handles file uploads with validation, thumbnail generation, and temporary storage.
Supports PNG, JPG, and WebP image formats with size limits up to 10MB.
"""

import os
import asyncio
import aiofiles
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import io
import logging
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class FileUploadError(Exception):
    """Custom exception for file upload errors"""
    pass


class FileUploadService:
    """
    Service for handling file uploads with validation and processing.

    Features:
    - File format validation (PNG, JPG, WebP)
    - File size validation (max 10MB)
    - Thumbnail generation
    - Temporary storage management
    - Automatic cleanup

    Example:
        >>> service = FileUploadService()
        >>> result = await service.process_upload(
        ...     file_content=image_bytes,
        ...     filename="product.jpg"
        ... )
        >>> print(result["file_path"])
        /tmp/uploads/abc123/product.jpg
    """

    # Subtask 1: File Format Validation - Supported formats
    SUPPORTED_FORMATS = {"PNG", "JPEG", "WEBP"}
    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

    # Subtask 3: File Size Validation - Max file size
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

    # Subtask 2: Thumbnail Generation - Thumbnail configuration
    THUMBNAIL_SIZE = (300, 300)  # Width x Height
    THUMBNAIL_QUALITY = 85  # JPEG quality for thumbnails

    # Subtask 4: Temporary Storage Management
    DEFAULT_UPLOAD_DIR = "/tmp/uploads"

    def __init__(self, upload_dir: str = DEFAULT_UPLOAD_DIR):
        """
        Initialize file upload service.

        Args:
            upload_dir: Base directory for uploaded files
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileUploadService initialized with upload_dir: {self.upload_dir}")

    # Subtask 1: Implement File Format Validation
    async def validate_format(self, file_content: bytes, filename: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate file format by checking both extension and actual image format.

        Args:
            file_content: Binary content of the uploaded file
            filename: Original filename

        Returns:
            Tuple of (is_valid, format, error_message)

        Example:
            >>> valid, fmt, err = await service.validate_format(image_bytes, "test.jpg")
            >>> if valid:
            ...     print(f"Valid {fmt} image")
        """
        try:
            # Check file extension
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.SUPPORTED_EXTENSIONS:
                return False, None, (
                    f"Unsupported file extension: {file_ext}. "
                    f"Supported extensions: {', '.join(self.SUPPORTED_EXTENSIONS)}"
                )

            # Verify actual image format using Pillow
            image_stream = io.BytesIO(file_content)
            try:
                with Image.open(image_stream) as img:
                    # Verify the image format
                    img_format = img.format

                    if img_format not in self.SUPPORTED_FORMATS:
                        return False, None, (
                            f"Unsupported image format: {img_format}. "
                            f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
                        )

                    # Additional validation: check if image can be loaded
                    img.verify()

                    logger.info(
                        f"File format validated: {filename} - "
                        f"Format: {img_format}, Size: {img.size}, Mode: {img.mode}"
                    )

                    return True, img_format, None

            except Exception as e:
                return False, None, f"Invalid or corrupted image file: {str(e)}"

        except Exception as e:
            logger.error(f"Format validation error for {filename}: {e}")
            return False, None, f"Format validation failed: {str(e)}"

    # Subtask 3: Implement File Size Validation
    async def validate_size(self, file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file size is within acceptable limits.

        Args:
            file_content: Binary content of the uploaded file
            filename: Original filename

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> valid, err = await service.validate_size(image_bytes, "test.jpg")
            >>> if not valid:
            ...     print(f"Error: {err}")
        """
        file_size = len(file_content)

        if file_size == 0:
            return False, "File is empty"

        if file_size > self.MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            return False, (
                f"File size ({size_mb:.2f}MB) exceeds maximum allowed size ({max_mb:.2f}MB)"
            )

        size_kb = file_size / 1024
        logger.info(f"File size validated: {filename} - {size_kb:.2f}KB")
        return True, None

    # Subtask 2: Develop Thumbnail Generation
    async def generate_thumbnail(
        self,
        file_content: bytes,
        thumbnail_path: Path,
        size: Tuple[int, int] = THUMBNAIL_SIZE
    ) -> str:
        """
        Generate a thumbnail from the uploaded image.

        Uses Pillow's thumbnail() method which maintains aspect ratio.

        Args:
            file_content: Binary content of the original image
            thumbnail_path: Path where thumbnail should be saved
            size: Thumbnail dimensions (width, height)

        Returns:
            Absolute path to the generated thumbnail

        Raises:
            FileUploadError: If thumbnail generation fails

        Example:
            >>> thumb_path = await service.generate_thumbnail(
            ...     image_bytes,
            ...     Path("/tmp/uploads/abc123/thumb_product.jpg")
            ... )
        """
        try:
            # Open image from bytes
            image_stream = io.BytesIO(file_content)

            with Image.open(image_stream) as img:
                # Convert RGBA to RGB if needed (for JPEG compatibility)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create a white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')

                # Create thumbnail (maintains aspect ratio)
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Save thumbnail
                thumbnail_path.parent.mkdir(parents=True, exist_ok=True)

                # Save as JPEG for consistent format
                img.save(
                    thumbnail_path,
                    format='JPEG',
                    quality=self.THUMBNAIL_QUALITY,
                    optimize=True
                )

                logger.info(
                    f"Thumbnail generated: {thumbnail_path} - "
                    f"Size: {img.size}, Original requested: {size}"
                )

                return str(thumbnail_path)

        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            raise FileUploadError(f"Failed to generate thumbnail: {str(e)}")

    # Subtask 4: Manage Temporary Storage for Uploaded Files
    async def save_to_storage(
        self,
        file_content: bytes,
        filename: str,
        session_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Save uploaded file to temporary storage with unique session directory.

        Creates a session-specific directory for organizing uploads.

        Args:
            file_content: Binary content of the file
            filename: Original filename
            session_id: Optional session ID, auto-generated if not provided

        Returns:
            Tuple of (file_path, session_id)

        Example:
            >>> file_path, session = await service.save_to_storage(
            ...     image_bytes,
            ...     "product.jpg",
            ...     session_id="user123"
            ... )
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                file_hash = hashlib.md5(file_content[:1024]).hexdigest()[:8]
                session_id = f"{timestamp}_{file_hash}"

            # Create session directory
            session_dir = self.upload_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            # Sanitize filename
            safe_filename = self._sanitize_filename(filename)
            file_path = session_dir / safe_filename

            # Save file asynchronously
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)

            logger.info(
                f"File saved to storage: {file_path} - "
                f"Size: {len(file_content)} bytes, Session: {session_id}"
            )

            return str(file_path), session_id

        except Exception as e:
            logger.error(f"Failed to save file to storage: {e}")
            raise FileUploadError(f"Storage save failed: {str(e)}")

    async def cleanup_session(self, session_id: str) -> None:
        """
        Clean up all files in a session directory.

        Args:
            session_id: Session ID to clean up

        Example:
            >>> await service.cleanup_session("20241114_a1b2c3d4")
        """
        try:
            session_dir = self.upload_dir / session_id

            if session_dir.exists():
                # Remove all files in directory
                for file_path in session_dir.iterdir():
                    if file_path.is_file():
                        file_path.unlink()
                        logger.debug(f"Deleted file: {file_path}")

                # Remove directory
                session_dir.rmdir()
                logger.info(f"Cleaned up session directory: {session_id}")
            else:
                logger.warning(f"Session directory not found: {session_id}")

        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
            raise FileUploadError(f"Cleanup failed: {str(e)}")

    async def get_session_files(self, session_id: str) -> list:
        """
        List all files in a session directory.

        Args:
            session_id: Session ID to query

        Returns:
            List of file paths
        """
        session_dir = self.upload_dir / session_id

        if not session_dir.exists():
            return []

        return [str(f) for f in session_dir.iterdir() if f.is_file()]

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal and other security issues.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Get just the filename, no path components
        safe_name = Path(filename).name

        # Remove or replace dangerous characters
        dangerous_chars = ['..', '/', '\\', '\0', '\n', '\r']
        for char in dangerous_chars:
            safe_name = safe_name.replace(char, '_')

        # Ensure filename is not empty
        if not safe_name or safe_name == '_':
            safe_name = f"upload_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        return safe_name

    async def process_upload(
        self,
        file_content: bytes,
        filename: str,
        session_id: Optional[str] = None,
        generate_thumbnail: bool = True
    ) -> dict:
        """
        Process complete file upload with all validations and storage.

        This is the main entry point that orchestrates all subtasks:
        1. Validate file format
        2. Validate file size
        3. Save to storage
        4. Generate thumbnail (optional)

        Args:
            file_content: Binary content of the uploaded file
            filename: Original filename
            session_id: Optional session ID
            generate_thumbnail: Whether to generate a thumbnail

        Returns:
            Dictionary with upload results:
            {
                "success": bool,
                "file_path": str,
                "thumbnail_path": str or None,
                "session_id": str,
                "format": str,
                "size_bytes": int,
                "error": str or None
            }

        Example:
            >>> result = await service.process_upload(
            ...     file_content=image_bytes,
            ...     filename="product.jpg",
            ...     generate_thumbnail=True
            ... )
            >>> if result["success"]:
            ...     print(f"Uploaded to: {result['file_path']}")
        """
        try:
            # Subtask 3: Validate file size
            size_valid, size_error = await self.validate_size(file_content, filename)
            if not size_valid:
                return {
                    "success": False,
                    "file_path": None,
                    "thumbnail_path": None,
                    "session_id": None,
                    "format": None,
                    "size_bytes": len(file_content),
                    "error": size_error
                }

            # Subtask 1: Validate file format
            format_valid, img_format, format_error = await self.validate_format(
                file_content, filename
            )
            if not format_valid:
                return {
                    "success": False,
                    "file_path": None,
                    "thumbnail_path": None,
                    "session_id": None,
                    "format": None,
                    "size_bytes": len(file_content),
                    "error": format_error
                }

            # Subtask 4: Save to temporary storage
            file_path, session_id = await self.save_to_storage(
                file_content, filename, session_id
            )

            # Subtask 2: Generate thumbnail
            thumbnail_path = None
            if generate_thumbnail:
                try:
                    thumb_filename = f"thumb_{Path(filename).stem}.jpg"
                    thumb_path = Path(file_path).parent / thumb_filename
                    thumbnail_path = await self.generate_thumbnail(
                        file_content, thumb_path
                    )
                except Exception as e:
                    logger.warning(f"Thumbnail generation failed (non-fatal): {e}")
                    # Continue without thumbnail

            logger.info(
                f"Upload processed successfully: {filename} - "
                f"Path: {file_path}, Thumbnail: {thumbnail_path}"
            )

            return {
                "success": True,
                "file_path": file_path,
                "thumbnail_path": thumbnail_path,
                "session_id": session_id,
                "format": img_format,
                "size_bytes": len(file_content),
                "error": None
            }

        except FileUploadError as e:
            logger.error(f"Upload processing failed: {e}")
            return {
                "success": False,
                "file_path": None,
                "thumbnail_path": None,
                "session_id": None,
                "format": None,
                "size_bytes": len(file_content),
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error during upload processing: {e}")
            return {
                "success": False,
                "file_path": None,
                "thumbnail_path": None,
                "session_id": None,
                "format": None,
                "size_bytes": len(file_content),
                "error": f"Internal error: {str(e)}"
            }
