"""
Asset persistence service for managing cloud storage of video generation assets.

Handles uploading and downloading of complete job asset sets including:
- Final videos
- Intermediate scenes
- Audio files
- Scripts and metadata
- Product images

Supports hybrid versioning with backup of replaced assets.
"""

import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
import asyncio

from .s3_storage import S3StorageService, get_s3_storage_service
from config import settings

logger = logging.getLogger(__name__)


class AssetPersistenceService:
    """
    Manages persisting video generation job assets to S3 storage.

    Provides methods to upload complete job workspaces, download assets
    for regeneration, and manage versioning/backups.

    Example:
        >>> service = AssetPersistenceService()
        >>> result = await service.persist_job_assets("job-123", "/tmp/video_jobs/job-123")
        >>> print(result["final_video"])
        'mv/projects/job-123/final/video.mp4'
    """

    def __init__(self, s3_service: Optional[S3StorageService] = None):
        """
        Initialize asset persistence service.

        Args:
            s3_service: Optional custom S3 service. If None, uses singleton.
        """
        self.s3_service = s3_service or get_s3_storage_service()
        logger.info("AssetPersistenceService initialized with S3StorageService")
    
    async def persist_job_assets(
        self,
        job_id: str,
        local_base_path: str
    ) -> Dict[str, any]:
        """
        Upload all job assets from local filesystem to cloud storage.
        
        Uploads complete job workspace including:
        - Final video
        - Scene videos/images
        - Audio files
        - Script and metadata JSONs
        - Product images
        
        Args:
            job_id: Unique job identifier
            local_base_path: Base path to job directory (e.g., "/tmp/video_jobs/job-123")
            
        Returns:
            Dict with cloud URLs for all assets:
            {
                "final_video": "https://...",
                "scenes": ["https://...", ...],
                "audio": ["https://...", ...],
                "metadata": "https://...",
                "script": "https://...",
                "uploads": ["https://...", ...]
            }
            
        Example:
            >>> urls = await service.persist_job_assets(
            ...     "job-123",
            ...     "/tmp/video_jobs/job-123"
            ... )
        """
        base_path = Path(local_base_path)
        
        if not base_path.exists():
            raise FileNotFoundError(f"Job directory not found: {local_base_path}")
        
        logger.info(f"Persisting assets for job {job_id} from {local_base_path}")
        
        result = {
            "final_video": None,
            "scenes": [],
            "audio": [],
            "metadata": None,
            "script": None,
            "uploads": [],
            "character_references": []
        }
        
        try:
            # Upload final video
            final_dir = base_path / "final"
            if final_dir.exists():
                result["final_video"] = await self._upload_directory(
                    job_id,
                    final_dir,
                    "final",
                    single_file=True
                )
            
            # Upload scenes
            scenes_dir = base_path / "scenes"
            if scenes_dir.exists():
                result["scenes"] = await self._upload_directory(
                    job_id,
                    scenes_dir,
                    "intermediate/scenes"
                )
            
            # Upload audio
            audio_dir = base_path / "audio"
            if audio_dir.exists():
                result["audio"] = await self._upload_directory(
                    job_id,
                    audio_dir,
                    "intermediate/audio"
                )
            
            # Upload product images
            uploads_dir = base_path / "uploads"
            if uploads_dir.exists():
                result["uploads"] = await self._upload_directory(
                    job_id,
                    uploads_dir,
                    "intermediate/uploads"
                )
            
            # Upload character reference images
            character_ref_dir = base_path / "character_reference"
            if character_ref_dir.exists():
                result["character_references"] = await self._upload_directory(
                    job_id,
                    character_ref_dir,
                    "intermediate/character_reference"
                )
            
            # Upload metadata if exists
            metadata_file = base_path / "metadata.json"
            if metadata_file.exists():
                result["metadata"] = await self.storage.upload_file(
                    str(metadata_file),
                    f"videos/{job_id}/intermediate/metadata.json"
                )
            
            # Upload script if exists
            script_file = base_path / "script.json"
            if script_file.exists():
                result["script"] = await self.storage.upload_file(
                    str(script_file),
                    f"videos/{job_id}/intermediate/script.json"
                )
            
            logger.info(f"Successfully persisted all assets for job {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to persist assets for job {job_id}: {e}")
            raise
    
    async def _upload_directory(
        self,
        job_id: str,
        local_dir: Path,
        cloud_subpath: str,
        single_file: bool = False
    ) -> any:
        """
        Upload all files from a directory to cloud storage.
        
        Args:
            job_id: Job identifier
            local_dir: Local directory to upload
            cloud_subpath: Subpath in cloud (e.g., "intermediate/scenes")
            single_file: If True, return single URL instead of list
            
        Returns:
            List of URLs or single URL if single_file=True
        """
        urls = []
        
        # Get all files in directory (non-recursive)
        files = [f for f in local_dir.iterdir() if f.is_file()]
        
        if not files:
            logger.warning(f"No files found in {local_dir}")
            return None if single_file else []
        
        # Upload files in parallel for speed
        upload_tasks = []
        for file in files:
            s3_key = f"videos/{job_id}/{cloud_subpath}/{file.name}"
            # Determine content type based on extension
            content_type = None
            if file.suffix in ['.mp4', '.mov', '.avi']:
                content_type = 'video/mp4'
            elif file.suffix in ['.mp3', '.wav', '.m4a']:
                content_type = 'audio/mpeg'
            elif file.suffix in ['.json']:
                content_type = 'application/json'
            elif file.suffix in ['.jpg', '.jpeg', '.png']:
                content_type = f'image/{file.suffix.lstrip(".")}'

            upload_tasks.append(
                self.s3_service.upload_file_from_path_async(
                    str(file),
                    s3_key,
                    content_type
                )
            )

        s3_keys = await asyncio.gather(*upload_tasks)

        if single_file:
            # For final video, generate presigned URL and return it
            if s3_keys:
                url = self.s3_service.generate_presigned_url(s3_keys[0])
                return url
            return None

        # For multiple files, return presigned URLs
        urls = [self.s3_service.generate_presigned_url(key) for key in s3_keys]
        return urls
    
    async def download_job_assets(
        self,
        job_id: str,
        local_base_path: str
    ) -> None:
        """
        Download all job assets from cloud storage for regeneration.
        
        Recreates the job workspace locally with all intermediate assets.
        
        Args:
            job_id: Job identifier
            local_base_path: Where to download (e.g., "/tmp/video_jobs/job-123")
            
        Example:
            >>> await service.download_job_assets("job-123", "/tmp/video_jobs/job-123")
            >>> # Now /tmp/video_jobs/job-123/ has all assets
        """
        base_path = Path(local_base_path)
        base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading assets for job {job_id} to {local_base_path}")
        
        try:
            # List all files for this job
            s3_keys = await self.s3_service.list_files_async(f"videos/{job_id}/")

            if not s3_keys:
                raise FileNotFoundError(f"No assets found for job {job_id}")

            # Download all files in parallel
            download_tasks = []
            for s3_key in s3_keys:
                # Determine local path based on cloud structure
                # videos/job-123/final/video.mp4 -> /tmp/video_jobs/job-123/final/video.mp4
                # videos/job-123/intermediate/scenes/scene_1.mp4 -> /tmp/.../scenes/scene_1.mp4

                rel_path = s3_key.replace(f"videos/{job_id}/", "")

                # Simplify path: intermediate/scenes/... -> scenes/...
                if rel_path.startswith("intermediate/"):
                    rel_path = rel_path.replace("intermediate/", "")

                local_path = base_path / rel_path
                local_path.parent.mkdir(parents=True, exist_ok=True)

                download_tasks.append(
                    self.s3_service.download_file_async(s3_key, str(local_path))
                )

            await asyncio.gather(*download_tasks)

            logger.info(f"Successfully downloaded {len(s3_keys)} assets for job {job_id}")

        except Exception as e:
            logger.error(f"Failed to download assets for job {job_id}: {e}")
            raise
    
    async def backup_asset(
        self,
        job_id: str,
        asset_type: str,
        asset_name: str
    ) -> str:
        """
        Create backup of an asset before replacing it.
        
        Copies the current asset to an "_original" version for rollback.
        
        Args:
            job_id: Job identifier
            asset_type: Type of asset ("scenes", "audio", "final")
            asset_name: Name of asset file (e.g., "scene_3.mp4")
            
        Returns:
            URL of the backup
            
        Example:
            >>> url = await service.backup_asset("job-123", "scenes", "scene_3.mp4")
            >>> # Now scene_3.mp4 AND scene_3_original.mp4 exist in cloud
        """
        # Determine paths based on asset type
        if asset_type == "final":
            src_path = f"videos/{job_id}/final/{asset_name}"
            # Backup final videos with version number (final_v1.mp4)
            name_parts = asset_name.rsplit(".", 1)
            backup_name = f"{name_parts[0]}_v1.{name_parts[1]}"
            dest_path = f"videos/{job_id}/final/{backup_name}"
        else:
            src_path = f"videos/{job_id}/intermediate/{asset_type}/{asset_name}"
            # Backup intermediate assets with _original suffix
            name_parts = asset_name.rsplit(".", 1)
            backup_name = f"{name_parts[0]}_original.{name_parts[1]}"
            dest_path = f"videos/{job_id}/intermediate/{asset_type}/{backup_name}"
        
        logger.info(f"Backing up {src_path} to {dest_path}")

        # Check if source exists
        if not await self.s3_service.file_exists_async(src_path):
            raise FileNotFoundError(f"Asset not found: {src_path}")

        # Copy to backup
        await self.s3_service.copy_file_async(src_path, dest_path)

        # Generate presigned URL for the backup
        backup_url = self.s3_service.generate_presigned_url(dest_path)

        logger.info(f"Backup created: {backup_url}")
        return backup_url
    
    async def backup_final_video(self, job_id: str) -> Optional[str]:
        """
        Backup current final video before replacing with new version.
        
        Args:
            job_id: Job identifier
            
        Returns:
            URL of backup, or None if no final video exists
        """
        # Find the final video (could be video.mp4, final_video.mp4, etc.)
        s3_keys = await self.s3_service.list_files_async(f"videos/{job_id}/final/")

        # Find the main video file (not a backup)
        video_file = None
        for s3_key in s3_keys:
            filename = s3_key.split("/")[-1]
            if not filename.endswith("_v1.mp4") and filename.endswith(".mp4"):
                video_file = filename
                break

        if not video_file:
            logger.warning(f"No final video found for job {job_id}")
            return None

        return await self.backup_asset(job_id, "final", video_file)
    
    async def get_asset_metadata(self, job_id: str) -> Optional[Dict]:
        """
        Get metadata for a job from cloud storage.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Metadata dict or None if not found
        """
        s3_key = f"videos/{job_id}/intermediate/metadata.json"

        if not await self.s3_service.file_exists_async(s3_key):
            return None

        # Download to temp location
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            await self.s3_service.download_file_async(s3_key, tmp_path)

            with open(tmp_path, 'r') as f:
                metadata = json.load(f)

            return metadata
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    async def update_metadata(
        self,
        job_id: str,
        metadata: Dict,
        local_path: Optional[str] = None
    ) -> str:
        """
        Update job metadata in cloud storage.
        
        Args:
            job_id: Job identifier
            metadata: Updated metadata dict
            local_path: Optional local path to save before uploading
            
        Returns:
            Cloud URL of updated metadata
        """
        import tempfile
        
        # If local path provided, save there
        if local_path:
            with open(local_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            upload_path = local_path
        else:
            # Otherwise use temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                json.dump(metadata, tmp, indent=2)
                upload_path = tmp.name
        
        try:
            s3_key = f"videos/{job_id}/intermediate/metadata.json"
            await self.s3_service.upload_file_from_path_async(
                upload_path,
                s3_key,
                content_type='application/json'
            )

            # Generate presigned URL
            url = self.s3_service.generate_presigned_url(s3_key)

            logger.info(f"Updated metadata for job {job_id}")
            return url
        finally:
            # Clean up temp file if we created one
            if not local_path and os.path.exists(upload_path):
                os.remove(upload_path)
    
    async def cleanup_old_backups(self, job_id: str) -> None:
        """
        Remove old backup versions beyond the configured limit.
        
        Keeps only the most recent backups according to ASSET_BACKUP_LIMIT.
        
        Args:
            job_id: Job identifier
        """
        limit = settings.ASSET_BACKUP_LIMIT
        
        logger.info(f"Cleaning up old backups for job {job_id} (limit: {limit})")
        
        try:
            # List all files for job
            s3_keys = await self.s3_service.list_files_async(f"videos/{job_id}/")

            # Find backup files (contain _v2, _v3, etc. or _original)
            # Only delete if we have more than the limit
            final_backups = [f for f in s3_keys if "/final/" in f and "_v" in f and f.endswith(".mp4")]

            # Sort by version number (newest first)
            final_backups.sort(reverse=True)

            # Delete old versions beyond limit
            if len(final_backups) > limit:
                to_delete = final_backups[limit:]

                for s3_key in to_delete:
                    logger.info(f"Deleting old backup: {s3_key}")
                    await self.s3_service.delete_file_async(s3_key)

                logger.info(f"Cleaned up {len(to_delete)} old backups")

        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
            # Don't raise - cleanup failure shouldn't break the main flow
    
    async def persist_character_reference(
        self,
        image_id: str,
        local_image_path: str,
        job_id: Optional[str] = None
    ) -> str:
        """
        Persist a single character reference image to cloud storage.
        
        Args:
            image_id: UUID of the image
            local_image_path: Path to local image file
            job_id: Optional job ID to associate with. If None, stores standalone.
        
        Returns:
            Cloud URL of uploaded image
            
        Example:
            >>> service = AssetPersistenceService()
            >>> url = await service.persist_character_reference(
            ...     "abc-123",
            ...     "/tmp/character_reference/abc-123.png",
            ...     job_id="job-456"
            ... )
        """
        if not os.path.exists(local_image_path):
            raise FileNotFoundError(f"Image file not found: {local_image_path}")
        
        # Determine cloud path based on whether it's associated with a job
        file_ext = Path(local_image_path).suffix
        if job_id:
            cloud_path = f"videos/{job_id}/intermediate/character_reference/{image_id}{file_ext}"
        else:
            cloud_path = f"character_references/{image_id}{file_ext}"
        
        logger.info(f"Persisting character reference {image_id} to {cloud_path}")

        try:
            # Determine content type
            content_type = None
            if file_ext in ['.jpg', '.jpeg']:
                content_type = 'image/jpeg'
            elif file_ext == '.png':
                content_type = 'image/png'
            elif file_ext == '.webp':
                content_type = 'image/webp'

            await self.s3_service.upload_file_from_path_async(
                local_image_path,
                cloud_path,
                content_type
            )

            # Generate presigned URL
            url = self.s3_service.generate_presigned_url(cloud_path)

            logger.info(f"Successfully persisted character reference {image_id}")
            return url
        except Exception as e:
            logger.error(f"Failed to persist character reference {image_id}: {e}")
            raise
    
    async def associate_character_images_with_job(
        self,
        job_id: str,
        image_ids: List[str],
        local_base_path: str
    ) -> List[str]:
        """
        Copy character reference images into job directory and upload to cloud.
        
        This method copies images from the standalone character_reference directory
        into a job-specific directory, then uploads them to cloud storage.
        
        Args:
            job_id: Job identifier
            image_ids: List of character reference image UUIDs
            local_base_path: Base path to job directory (e.g., "/tmp/video_jobs/job-123")
        
        Returns:
            List of cloud URLs for the uploaded images
            
        Example:
            >>> service = AssetPersistenceService()
            >>> urls = await service.associate_character_images_with_job(
            ...     "job-456",
            ...     ["abc-123", "def-456"],
            ...     "/tmp/video_jobs/job-456"
            ... )
        """
        import shutil
        
        base_path = Path(local_base_path)
        job_char_ref_dir = base_path / "character_reference"
        job_char_ref_dir.mkdir(parents=True, exist_ok=True)
        
        # Source directory where standalone character images are stored
        source_dir = Path(__file__).parent.parent / "mv" / "outputs" / "character_reference"
        
        urls = []
        
        logger.info(f"Associating {len(image_ids)} character images with job {job_id}")
        
        for image_id in image_ids:
            # Try to find the image with different extensions
            image_found = False
            for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                source_path = source_dir / f"{image_id}{ext}"
                if source_path.exists():
                    # Copy to job directory
                    dest_path = job_char_ref_dir / f"{image_id}{ext}"
                    shutil.copy2(source_path, dest_path)
                    
                    # Upload to cloud
                    s3_key = f"videos/{job_id}/intermediate/character_reference/{image_id}{ext}"

                    # Determine content type
                    content_type = None
                    if ext in ['.jpg', '.jpeg']:
                        content_type = 'image/jpeg'
                    elif ext == '.png':
                        content_type = 'image/png'
                    elif ext == '.webp':
                        content_type = 'image/webp'

                    await self.s3_service.upload_file_from_path_async(
                        str(dest_path),
                        s3_key,
                        content_type
                    )

                    # Generate presigned URL
                    url = self.s3_service.generate_presigned_url(s3_key)
                    urls.append(url)

                    logger.info(f"Associated character reference {image_id} with job {job_id}")
                    image_found = True
                    break
            
            if not image_found:
                logger.warning(f"Character reference image {image_id} not found in {source_dir}")
        
        logger.info(f"Successfully associated {len(urls)} character images with job {job_id}")
        return urls
    
    async def get_character_reference_url(
        self,
        image_id: str,
        job_id: Optional[str] = None,
        extension: str = "png"
    ) -> Optional[str]:
        """
        Generate presigned URL for character reference image.

        Args:
            image_id: UUID of the image
            job_id: Optional job ID if image is associated with a job
            extension: Image file extension (png, jpg, webp)

        Returns:
            Presigned URL or None if image doesn't exist

        Example:
            >>> service = AssetPersistenceService()
            >>> url = await service.get_character_reference_url(
            ...     "abc-123",
            ...     job_id="job-456",
            ...     extension="png"
            ... )
        """
        # Determine S3 key
        if job_id:
            s3_key = f"videos/{job_id}/intermediate/character_reference/{image_id}.{extension}"
        else:
            s3_key = f"character_references/{image_id}.{extension}"

        # Check if exists
        if not await self.s3_service.file_exists_async(s3_key):
            return None

        # Generate presigned URL
        return self.s3_service.generate_presigned_url(
            s3_key,
            expiry=settings.PRESIGNED_URL_EXPIRY
        )



