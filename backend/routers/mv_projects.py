"""
Music Video Projects API Router.

Implements CRUD endpoints for project management with DynamoDB.
"""

import uuid
import structlog
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional, List

from mv_schemas import (
    ProjectCreateResponse,
    ProjectResponse,
    ProjectUpdateRequest,
    ComposeRequest,
    ComposeResponse,
    FinalVideoResponse,
    SceneResponse,
)
from mv_models import (
    MVProjectItem,
    create_project_metadata,
)
from services.s3_storage import (
    get_s3_storage_service,
    generate_s3_key,
    validate_s3_key,
)
from config import settings
from pynamodb.exceptions import PutError, DoesNotExist
import json

logger = structlog.get_logger()

router = APIRouter(prefix="/api/mv", tags=["MV Projects"])


@router.post(
    "/projects",
    response_model=ProjectCreateResponse,
    status_code=201,
    summary="Create New Project",
    description="""
Create a new Music Video or Ad Creative project.

This endpoint:
1. Accepts form data with metadata and file uploads
2. Uploads files to S3 (character image, product image, audio)
3. Creates project metadata in DynamoDB
4. Returns project ID for subsequent operations

**Files:**
- `images[]`: Product images (ad-creative mode, required)
- `audio`: Music file (music-video mode, required)

**Form Data:**
- `mode`: "ad-creative" or "music-video"
- `prompt`: Video concept description
- `characterDescription`: Character/style description
- `characterReferenceImageId`: UUID of pre-generated character image (optional)
- `productDescription`: Product details (optional)
"""
)
async def create_project(
    mode: str = Form(...),
    prompt: str = Form(...),
    characterDescription: str = Form(...),
    characterReferenceImageId: Optional[str] = Form(None),
    productDescription: Optional[str] = Form(None),
    directorConfig: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
    audio: Optional[UploadFile] = File(None)
):
    """
    Create a new project with file uploads.

    Args:
        mode: Generation mode (ad-creative or music-video)
        prompt: Video concept description
        characterDescription: Character description
        characterReferenceImageId: Optional pre-generated character image UUID
        productDescription: Optional product description
        directorConfig: Optional director config name (e.g., "Wes-Anderson")
        images: Optional list of product images
        audio: Optional audio file

    Returns:
        ProjectCreateResponse with project ID
    """
    try:
        logger.info(
            "create_project_request",
            mode=mode,
            has_images=images is not None and len(images) > 0 if images else False,
            has_audio=audio is not None,
            has_character_ref=characterReferenceImageId is not None,
            director_config=directorConfig
        )

        # Validate mode
        if mode not in ['ad-creative', 'music-video']:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid mode",
                    "details": "mode must be 'ad-creative' or 'music-video'"
                }
            )

        # Validate mode-specific requirements
        if mode == 'ad-creative' and (not images or len(images) == 0):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Product images required for ad-creative mode",
                    "details": "At least one product image must be provided"
                }
            )

        if mode == 'music-video' and not audio:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Audio file required for music-video mode",
                    "details": "Music file must be provided"
                }
            )

        # Generate project ID
        project_id = str(uuid.uuid4())
        s3_service = get_s3_storage_service()

        # Upload files to S3
        character_image_s3_key = None
        product_image_s3_key = None
        audio_s3_key = None

        # Handle character reference image
        if characterReferenceImageId:
            # Reference to existing character image in character_reference directory
            # For now, store the reference path - actual copy can be done later if needed
            character_image_s3_key = f"mv/outputs/character_reference/{characterReferenceImageId}.png"

        # Upload product images
        if images and len(images) > 0:
            # For simplicity, use first image as primary
            product_image = images[0]
            product_image_s3_key = generate_s3_key(project_id, "product")

            # Determine content type
            content_type = product_image.content_type or "image/jpeg"

            # Reset file pointer to beginning
            await product_image.seek(0)
            s3_service.upload_file(
                product_image.file,
                product_image_s3_key,
                content_type=content_type
            )

            logger.info(
                "product_image_uploaded",
                project_id=project_id,
                s3_key=product_image_s3_key
            )

        # Upload audio file
        if audio:
            audio_s3_key = generate_s3_key(project_id, "audio")
            content_type = audio.content_type or "audio/mpeg"

            # Reset file pointer to beginning
            await audio.seek(0)
            s3_service.upload_file(
                audio.file,
                audio_s3_key,
                content_type=content_type
            )

            logger.info(
                "audio_uploaded",
                project_id=project_id,
                s3_key=audio_s3_key
            )

        # Create project metadata in DynamoDB
        project = create_project_metadata(
            project_id=project_id,
            concept_prompt=prompt,
            character_description=characterDescription,
            product_description=productDescription,
            character_image_s3_key=character_image_s3_key,
            product_image_s3_key=product_image_s3_key,
            audio_backing_track_s3_key=audio_s3_key,
            director_config=directorConfig
        )

        try:
            project.save()
            logger.info("project_created", project_id=project_id)
        except PutError as e:
            logger.error("project_save_failed", project_id=project_id, error=str(e))
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "DatabaseError",
                    "message": "Failed to create project",
                    "details": str(e)
                }
            )

        return ProjectCreateResponse(
            projectId=project_id,
            status="pending",
            message="Project created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_project_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to create project",
                "details": str(e)
            }
        )


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get Project Details",
    description="""
Retrieve project metadata and all associated scenes.

Returns:
- Project metadata with presigned S3 URLs
- All scenes ordered by sequence
- Current status and progress
"""
)
async def get_project(project_id: str):
    """
    Get project by ID with all scenes.

    Args:
        project_id: Project UUID

    Returns:
        ProjectResponse with metadata and scenes
    """
    try:
        logger.info("get_project_request", project_id=project_id)

        # Query project metadata
        pk = f"PROJECT#{project_id}"

        try:
            project_item = MVProjectItem.get(pk, "METADATA")
        except DoesNotExist:
            logger.warning("project_not_found", project_id=project_id)
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Project {project_id} not found",
                    "details": "The specified project does not exist"
                }
            )

        # Query all scenes for this project
        scenes = []
        scene_items = MVProjectItem.query(
            pk,
            MVProjectItem.SK.startswith("SCENE#")
        )

        s3_service = get_s3_storage_service()

        for scene_item in scene_items:
            # Generate presigned URLs for scene assets
            reference_urls = []
            if scene_item.referenceImageS3Keys:
                for key in scene_item.referenceImageS3Keys:
                    reference_urls.append(s3_service.generate_presigned_url(key))

            audio_url = None
            if scene_item.audioClipS3Key:
                audio_url = s3_service.generate_presigned_url(scene_item.audioClipS3Key)

            video_url = None
            if scene_item.videoClipS3Key:
                video_url = s3_service.generate_presigned_url(scene_item.videoClipS3Key)

            lipsynced_url = None
            if scene_item.lipSyncedVideoClipS3Key:
                lipsynced_url = s3_service.generate_presigned_url(scene_item.lipSyncedVideoClipS3Key)

            scenes.append(SceneResponse(
                sequence=scene_item.sequence,
                status=scene_item.status,
                prompt=scene_item.prompt,
                negativePrompt=scene_item.negativePrompt,
                duration=scene_item.duration,
                referenceImageUrls=reference_urls,
                audioClipUrl=audio_url,
                videoClipUrl=video_url,
                needsLipSync=scene_item.needsLipSync,
                lipSyncedVideoClipUrl=lipsynced_url,
                retryCount=scene_item.retryCount or 0,
                errorMessage=scene_item.errorMessage,
                createdAt=scene_item.createdAt,
                updatedAt=scene_item.updatedAt
            ))

        # Sort scenes by sequence
        scenes.sort(key=lambda s: s.sequence)

        # Generate presigned URLs for project assets
        character_url = None
        if project_item.characterImageS3Key:
            character_url = s3_service.generate_presigned_url(project_item.characterImageS3Key)

        product_url = None
        if project_item.productImageS3Key:
            product_url = s3_service.generate_presigned_url(project_item.productImageS3Key)

        audio_url = None
        if project_item.audioBackingTrackS3Key:
            audio_url = s3_service.generate_presigned_url(project_item.audioBackingTrackS3Key)

        final_url = None
        if project_item.finalOutputS3Key:
            final_url = s3_service.generate_presigned_url(project_item.finalOutputS3Key)

        response = ProjectResponse(
            projectId=project_id,
            status=project_item.status,
            conceptPrompt=project_item.conceptPrompt,
            characterDescription=project_item.characterDescription,
            characterImageUrl=character_url,
            productDescription=project_item.productDescription,
            productImageUrl=product_url,
            audioBackingTrackUrl=audio_url,
            finalOutputUrl=final_url,
            directorConfig=project_item.directorConfig,
            sceneCount=project_item.sceneCount or 0,
            completedScenes=project_item.completedScenes or 0,
            failedScenes=project_item.failedScenes or 0,
            scenes=scenes,
            createdAt=project_item.createdAt,
            updatedAt=project_item.updatedAt
        )

        logger.info(
            "get_project_success",
            project_id=project_id,
            scene_count=len(scenes)
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_project_error", project_id=project_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to retrieve project",
                "details": str(e)
            }
        )


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Update Project Metadata",
    description="""
Update project metadata and status.

Typical updates:
- Change status as processing progresses
- Set final output S3 key when composition completes
- Update counters (completed/failed scenes)
"""
)
async def update_project(project_id: str, update_data: ProjectUpdateRequest):
    """
    Update project metadata.

    Args:
        project_id: Project UUID
        update_data: Fields to update

    Returns:
        Updated ProjectResponse
    """
    try:
        logger.info(
            "update_project_request",
            project_id=project_id,
            updates=update_data.model_dump(exclude_none=True)
        )

        # Retrieve existing project
        pk = f"PROJECT#{project_id}"

        try:
            project_item = MVProjectItem.get(pk, "METADATA")
        except DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Project {project_id} not found"
                }
            )

        # Update fields
        updated = False

        if update_data.status:
            project_item.status = update_data.status
            project_item.GSI1PK = update_data.status
            updated = True

        if update_data.finalOutputS3Key:
            # Validate that it's an S3 key, not a URL
            project_item.finalOutputS3Key = validate_s3_key(
                update_data.finalOutputS3Key, 
                "finalOutputS3Key"
            )
            updated = True

        if updated:
            project_item.updatedAt = datetime.now(timezone.utc)
            project_item.save()
            logger.info("project_updated", project_id=project_id)

        # Return updated project (reuse get_project logic)
        return await get_project(project_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_project_error", project_id=project_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to update project",
                "details": str(e)
            }
        )


@router.post(
    "/projects/{project_id}/compose",
    response_model=ComposeResponse,
    summary="Compose Final Video",
    description="""
Queue final video composition job.

This endpoint:
1. Validates all scenes are completed
2. Queues composition job to Redis
3. Returns job ID for tracking

The worker process will:
1. Download scene videos from S3
2. Stitch them with moviepy
3. Add audio backing track
4. Upload final video to S3
5. Update project with final output S3 key
"""
)
async def compose_video(project_id: str, request: ComposeRequest):
    """
    Queue final video composition.

    Args:
        project_id: Project UUID
        request: Composition request (currently no additional params)

    Returns:
        ComposeResponse with job ID
    """
    try:
        logger.info("compose_request", project_id=project_id)

        # Retrieve project
        pk = f"PROJECT#{project_id}"

        try:
            project_item = MVProjectItem.get(pk, "METADATA")
        except DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Project {project_id} not found"
                }
            )

        # Validate all scenes are completed
        if (project_item.completedScenes or 0) < (project_item.sceneCount or 0):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Cannot compose video: not all scenes are completed",
                    "details": f"Completed: {project_item.completedScenes or 0}/{project_item.sceneCount or 0}"
                }
            )

        # Check for failed scenes
        if (project_item.failedScenes or 0) > 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Cannot compose video: some scenes failed",
                    "details": f"Failed scenes: {project_item.failedScenes or 0}"
                }
            )

        # Queue composition job to Redis
        from redis_client import redis_client

        job_id = f"compose_{project_id}"

        job_data = {
            "job_id": job_id,
            "project_id": project_id,
            "type": "compose",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Push to Redis queue using direct client access
        redis_conn = redis_client.get_client()
        redis_conn.lpush("video_composition_queue", json.dumps(job_data))
        logger.info("composition_job_queued", job_id=job_id, project_id=project_id)

        # Update project status
        project_item.status = "composing"
        project_item.GSI1PK = "composing"
        project_item.updatedAt = datetime.now(timezone.utc)
        project_item.save()

        return ComposeResponse(
            jobId=job_id,
            projectId=project_id,
            status="queued",
            message="Video composition job queued"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("compose_error", project_id=project_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to queue composition job",
                "details": str(e)
            }
        )


@router.get(
    "/projects/{project_id}/final-video",
    response_model=FinalVideoResponse,
    summary="Get Final Video URL",
    description="""
Retrieve presigned URL for final composed video.

Returns:
- Presigned S3 URL valid for configured duration (default 1 hour)
- URL expires after specified time

Returns 404 if video is not yet composed.
"""
)
async def get_final_video(project_id: str):
    """
    Get presigned URL for final video.

    Args:
        project_id: Project UUID

    Returns:
        FinalVideoResponse with presigned URL
    """
    try:
        logger.info("get_final_video_request", project_id=project_id)

        # Retrieve project
        pk = f"PROJECT#{project_id}"

        try:
            project_item = MVProjectItem.get(pk, "METADATA")
        except DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Project {project_id} not found"
                }
            )

        # Check if final output exists
        if not project_item.finalOutputS3Key:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": "Final video not yet available",
                    "details": f"Project status: {project_item.status}"
                }
            )

        # Generate presigned URL
        s3_service = get_s3_storage_service()
        video_url = s3_service.generate_presigned_url(project_item.finalOutputS3Key)

        logger.info(
            "final_video_url_generated",
            project_id=project_id,
            s3_key=project_item.finalOutputS3Key
        )

        return FinalVideoResponse(
            projectId=project_id,
            videoUrl=video_url,
            expiresInSeconds=settings.PRESIGNED_URL_EXPIRY
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_final_video_error", project_id=project_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to retrieve final video",
                "details": str(e)
            }
        )

