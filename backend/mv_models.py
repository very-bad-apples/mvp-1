"""
PynamoDB models for Music Video projects.

Uses single-table design with composite sort key pattern:
- Partition Key: projectId
- Sort Key: entityType#identifier (METADATA or SCENE#sequence)
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    UTCDateTimeAttribute,
    BooleanAttribute,
    ListAttribute,
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.exceptions import DoesNotExist
from config import settings
from dynamodb_config import BaseDynamoModel
from services.s3_storage import validate_s3_key
import structlog

logger = structlog.get_logger()


class StatusIndex(GlobalSecondaryIndex):
    """
    Global Secondary Index for querying projects by status.
    """

    class Meta:
        index_name = 'status-created-index'
        read_capacity_units = 5
        write_capacity_units = 5
        projection = AllProjection()
        # Region and credentials are inherited from parent MVProjectItem model

    GSI1PK = UnicodeAttribute(hash_key=True)  # status
    GSI1SK = UnicodeAttribute(range_key=True)  # createdAt


class MVProjectItem(BaseDynamoModel):
    """
    DynamoDB model for both Project metadata and Scene items.

    Uses single-table design with composite sort key:
    - Project metadata: SK = "METADATA"
    - Scene items: SK = "SCENE#<sequence>"

    Item Types:
    1. Project Metadata (entityType="project", SK="METADATA")
    2. Scene (entityType="scene", SK="SCENE#001", etc.)
    """

    class Meta:
        table_name = settings.DYNAMODB_TABLE_NAME
        region = settings.DYNAMODB_REGION
        # For local DynamoDB, explicit credentials are required
        # Note: DynamoDB Local requires explicit credentials (even fake ones).
        # Fake credentials (fakeAccessKey/fakeSecretKey) are ONLY used when
        # USE_LOCAL_DYNAMODB=true. In production, these are NOT set, and PynamoDB
        # uses boto3 credential chain (environment variables, IAM roles, credentials file).
        # This conditional ensures credentials are NEVER set in production code path.
        if settings.USE_LOCAL_DYNAMODB:
            host = settings.DYNAMODB_ENDPOINT
            aws_access_key_id = settings.dynamodb_access_key_id
            aws_secret_access_key = settings.dynamodb_secret_access_key

    # Primary Keys
    PK = UnicodeAttribute(hash_key=True)  # PROJECT#<uuid>
    SK = UnicodeAttribute(range_key=True)  # METADATA or SCENE#<sequence>

    # Common Attributes
    entityType = UnicodeAttribute()  # "project" or "scene"
    projectId = UnicodeAttribute()
    status = UnicodeAttribute()  # pending, processing, completed, failed
    createdAt = UTCDateTimeAttribute()
    updatedAt = UTCDateTimeAttribute()

    # GSI for status queries
    GSI1PK = UnicodeAttribute(null=True)  # status (for GSI)
    GSI1SK = UnicodeAttribute(null=True)  # createdAt ISO string (for GSI)
    status_index = StatusIndex()

    # Project-specific Attributes (only for entityType="project")
    # NOTE: All *S3Key fields store S3 object keys (e.g., "mv/projects/{id}/file.ext"),
    # NOT presigned URLs or full S3 URLs. Presigned URLs are generated on-demand
    # when serving API responses.
    conceptPrompt = UnicodeAttribute(null=True)
    characterDescription = UnicodeAttribute(null=True)
    characterImageS3Key = UnicodeAttribute(null=True)  # S3 key, not URL
    productDescription = UnicodeAttribute(null=True)
    configFlavor = UnicodeAttribute(null=True)  # Config flavor for scene generation
    productImageS3Key = UnicodeAttribute(null=True)  # S3 key, not URL
    audioBackingTrackS3Key = UnicodeAttribute(null=True)  # S3 key, not URL
    finalOutputS3Key = UnicodeAttribute(null=True)  # S3 key, not URL
    sceneCount = NumberAttribute(null=True, default=0)
    completedScenes = NumberAttribute(null=True, default=0)
    failedScenes = NumberAttribute(null=True, default=0)

    # Scene-specific Attributes (only for entityType="scene")
    # NOTE: All *S3Key fields store S3 object keys, NOT presigned URLs
    sequence = NumberAttribute(null=True)
    prompt = UnicodeAttribute(null=True)
    negativePrompt = UnicodeAttribute(null=True)
    referenceImageS3Keys = ListAttribute(of=UnicodeAttribute, null=True)  # List of S3 keys, not URLs
    duration = NumberAttribute(null=True)
    audioClipS3Key = UnicodeAttribute(null=True)  # S3 key, not URL
    videoClipS3Key = UnicodeAttribute(null=True)  # S3 key, not URL
    needsLipSync = BooleanAttribute(null=True)
    lipSyncedVideoClipS3Key = UnicodeAttribute(null=True)  # S3 key, not URL
    videoGenerationJobId = UnicodeAttribute(null=True)
    lipsyncJobId = UnicodeAttribute(null=True)
    retryCount = NumberAttribute(null=True, default=0)
    errorMessage = UnicodeAttribute(null=True)

    def update_status(self, new_status: str) -> None:
        """
        Update status and GSI fields atomically to keep them in sync.
        
        Args:
            new_status: New status value (pending, processing, completed, failed)
        """
        self.status = new_status
        # Keep GSI in sync with status (only for project metadata items)
        if self.entityType == "project":
            self.GSI1PK = new_status
        self.updatedAt = datetime.now(timezone.utc)
        self.save()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary for API responses.

        Returns:
            Dict with model attributes
        """
        result = {
            "projectId": self.projectId,
            "entityType": self.entityType,
            "status": self.status,
            "createdAt": self.createdAt.isoformat() if self.createdAt else None,
            "updatedAt": self.updatedAt.isoformat() if self.updatedAt else None,
        }

        if self.entityType == "project":
            result.update({
                "conceptPrompt": self.conceptPrompt,
                "characterDescription": self.characterDescription,
                "characterImageS3Key": self.characterImageS3Key,
                "productDescription": self.productDescription,
                "configFlavor": self.configFlavor,
                "productImageS3Key": self.productImageS3Key,
                "audioBackingTrackS3Key": self.audioBackingTrackS3Key,
                "finalOutputS3Key": self.finalOutputS3Key,
                "sceneCount": self.sceneCount,
                "completedScenes": self.completedScenes,
                "failedScenes": self.failedScenes,
            })
        elif self.entityType == "scene":
            result.update({
                "sequence": self.sequence,
                "prompt": self.prompt,
                "negativePrompt": self.negativePrompt,
                "referenceImageS3Keys": list(self.referenceImageS3Keys) if self.referenceImageS3Keys is not None else [],
                "duration": self.duration,
                "audioClipS3Key": self.audioClipS3Key,
                "videoClipS3Key": self.videoClipS3Key,
                "needsLipSync": self.needsLipSync,
                "lipSyncedVideoClipS3Key": self.lipSyncedVideoClipS3Key,
                "videoGenerationJobId": self.videoGenerationJobId,
                "lipsyncJobId": self.lipsyncJobId,
                "retryCount": self.retryCount,
                "errorMessage": self.errorMessage,
            })

        return result


def create_project_metadata(
    project_id: str,
    concept_prompt: str,
    character_description: str,
    product_description: Optional[str] = None,
    config_flavor: Optional[str] = None,
    character_image_s3_key: Optional[str] = None,
    product_image_s3_key: Optional[str] = None,
    audio_backing_track_s3_key: Optional[str] = None,
) -> MVProjectItem:
    """
    Create a new project metadata item.

    Args:
        project_id: Unique project UUID
        concept_prompt: User's video concept description
        character_description: Character description
        product_description: Optional product description
        character_image_s3_key: S3 object key for character reference image 
            (e.g., "mv/projects/{id}/character.png"), NOT a URL
        product_image_s3_key: S3 object key for product image, NOT a URL
        audio_backing_track_s3_key: S3 object key for audio file, NOT a URL

    Returns:
        MVProjectItem instance
        
    Raises:
        ValueError: If any S3 key parameter is a URL instead of a key
    """
    now = datetime.now(timezone.utc)

    item = MVProjectItem()
    item.PK = f"PROJECT#{project_id}"
    item.SK = "METADATA"
    item.entityType = "project"
    item.projectId = project_id
    item.status = "pending"
    item.createdAt = now
    item.updatedAt = now
    item.conceptPrompt = concept_prompt
    item.characterDescription = character_description
    item.productDescription = product_description
    item.configFlavor = config_flavor or "default"
    # Validate S3 keys to ensure they're keys, not URLs
    item.characterImageS3Key = validate_s3_key(character_image_s3_key, "character_image_s3_key")
    item.productImageS3Key = validate_s3_key(product_image_s3_key, "product_image_s3_key")
    item.audioBackingTrackS3Key = validate_s3_key(audio_backing_track_s3_key, "audio_backing_track_s3_key")
    item.sceneCount = 0
    item.completedScenes = 0
    item.failedScenes = 0

    # GSI attributes
    item.GSI1PK = "pending"
    item.GSI1SK = now.isoformat()

    return item


def create_scene_item(
    project_id: str,
    sequence: int,
    prompt: str,
    negative_prompt: Optional[str] = None,
    duration: float = 8.0,
    needs_lipsync: bool = False,
    reference_image_s3_keys: Optional[List[str]] = None,
) -> MVProjectItem:
    """
    Create a new scene item.

    Args:
        project_id: Parent project UUID
        sequence: Scene order (1-indexed)
        prompt: Scene description for video generation
        negative_prompt: Negative prompt for video generation
        duration: Scene duration in seconds
        needs_lipsync: Whether scene requires lip sync processing
        reference_image_s3_keys: List of S3 object keys for reference images
            (e.g., ["mv/projects/{id}/ref1.png"]), NOT URLs

    Returns:
        MVProjectItem instance configured as scene
        
    Raises:
        ValueError: If any S3 key in reference_image_s3_keys is a URL instead of a key
    """
    now = datetime.now(timezone.utc)

    item = MVProjectItem()
    item.PK = f"PROJECT#{project_id}"
    item.SK = f"SCENE#{sequence:03d}"
    item.entityType = "scene"
    item.projectId = project_id
    item.sequence = sequence
    item.status = "pending"
    item.createdAt = now
    item.updatedAt = now
    item.prompt = prompt
    item.negativePrompt = negative_prompt
    item.duration = duration
    item.needsLipSync = needs_lipsync
    # Validate S3 keys in list to ensure they're keys, not URLs
    if reference_image_s3_keys:
        item.referenceImageS3Keys = [validate_s3_key(key, f"reference_image_s3_keys[{i}]") 
                                     for i, key in enumerate(reference_image_s3_keys) if key]
    else:
        item.referenceImageS3Keys = []
    item.retryCount = 0

    # GSI attributes are only for project metadata items, not scenes
    # Note: To query failed scenes across projects, must scan or query per-project
    item.GSI1PK = None
    item.GSI1SK = None

    return item


def increment_completed_scene(project_id: str) -> None:
    """
    Atomically increment the completedScenes counter for a project.
    
    Args:
        project_id: Project UUID
        
    Raises:
        DoesNotExist: If project not found
    """
    pk = f"PROJECT#{project_id}"
    try:
        project_item = MVProjectItem.get(pk, "METADATA")
        if project_item.completedScenes is None:
            project_item.completedScenes = 0
        project_item.completedScenes += 1
        project_item.updatedAt = datetime.now(timezone.utc)
        project_item.save()
        logger.info(
            "project_completed_scene_incremented",
            project_id=project_id,
            completed_scenes=project_item.completedScenes
        )
    except DoesNotExist:
        logger.error("project_not_found_for_counter", project_id=project_id)
        raise


def increment_failed_scene(project_id: str) -> None:
    """
    Atomically increment the failedScenes counter for a project.
    
    Args:
        project_id: Project UUID
        
    Raises:
        DoesNotExist: If project not found
    """
    pk = f"PROJECT#{project_id}"
    try:
        project_item = MVProjectItem.get(pk, "METADATA")
        if project_item.failedScenes is None:
            project_item.failedScenes = 0
        project_item.failedScenes += 1
        project_item.updatedAt = datetime.now(timezone.utc)
        project_item.save()
        logger.info(
            "project_failed_scene_incremented",
            project_id=project_id,
            failed_scenes=project_item.failedScenes
        )
    except DoesNotExist:
        logger.error("project_not_found_for_counter", project_id=project_id)
        raise


def decrement_completed_scene(project_id: str) -> None:
    """
    Atomically decrement the completedScenes counter for a project.
    Used when a scene transitions from completed to failed.
    
    Args:
        project_id: Project UUID
        
    Raises:
        DoesNotExist: If project not found
    """
    pk = f"PROJECT#{project_id}"
    try:
        project_item = MVProjectItem.get(pk, "METADATA")
        if project_item.completedScenes is None or project_item.completedScenes <= 0:
            logger.warning(
                "project_completed_scene_decrement_below_zero",
                project_id=project_id,
                current_count=project_item.completedScenes
            )
            return
        project_item.completedScenes -= 1
        project_item.updatedAt = datetime.now(timezone.utc)
        project_item.save()
        logger.info(
            "project_completed_scene_decremented",
            project_id=project_id,
            completed_scenes=project_item.completedScenes
        )
    except DoesNotExist:
        logger.error("project_not_found_for_counter", project_id=project_id)
        raise

