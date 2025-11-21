"""
Music Video Projects API Router.

Implements CRUD endpoints for project management with DynamoDB.
"""

import uuid
import os
import asyncio
import structlog
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional, List

from mv_schemas import (
    ProjectCreateResponse,
    ProjectResponse,
    ProjectUpdateRequest,
    SceneUpdateRequest,
    ComposeRequest,
    ComposeResponse,
    FinalVideoResponse,
    SceneResponse,
)
from mv_models import (
    MVProjectItem,
    create_project_metadata,
    create_scene_item,
)
from mv.scene_generator import generate_scenes
from mv.video_generator import generate_video
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


async def generate_scenes_and_videos_background(
    project_id: str,
    concept_prompt: str,
    character_description: str,
    character_image_s3_key: Optional[str] = None
):
    """
    Background task to generate scenes and then videos for a project.
    
    This function:
    1. Generates scene descriptions using Gemini (may take 10-30+ seconds)
    2. Creates scene records in DynamoDB
    3. Triggers video generation for each scene
    """
    try:
        logger.info(
            "background_scene_generation_started",
            project_id=project_id
        )

        # Generate scenes using existing logic
        # Use None to let generate_scenes use config defaults (from parameters.yaml)
        scenes, _output_files = generate_scenes(
            idea=concept_prompt,
            character_description=character_description,
            number_of_scenes=None,  # Will use default from config (typically 1 or 4)
        )

        # Validate scenes were generated
        if not scenes or len(scenes) == 0:
            logger.error("no_scenes_generated", project_id=project_id)
            pk = f"PROJECT#{project_id}"
            try:
                project_item = MVProjectItem.get(pk, "METADATA")
                project_item.status = "failed"
                project_item.GSI1PK = "failed"
                project_item.updatedAt = datetime.now(timezone.utc)
                project_item.save()
            except DoesNotExist:
                logger.error("project_not_found_for_failure_status", project_id=project_id)
            return

        # Create scene items in DynamoDB
        scenes_created = 0
        reference_image_s3_keys = []
        if character_image_s3_key:
            reference_image_s3_keys = [character_image_s3_key]

        for i, scene_data in enumerate(scenes, start=1):
            scene_item = create_scene_item(
                project_id=project_id,
                sequence=i,
                prompt=scene_data.description,
                negative_prompt=scene_data.negative_description,
                duration=8.0,  # Default duration
                needs_lipsync=True,  # TODO: Determine based on mode
                reference_image_s3_keys=reference_image_s3_keys
            )

            try:
                scene_item.save()
                scenes_created += 1
                logger.info(
                    "scene_created",
                    project_id=project_id,
                    sequence=i
                )
            except PutError as e:
                logger.error(
                    "scene_save_failed",
                    project_id=project_id,
                    sequence=i,
                    error=str(e)
                )
                # Continue with other scenes even if one fails

        # Update project with scene count
        pk = f"PROJECT#{project_id}"
        try:
            project_item = MVProjectItem.get(pk, "METADATA")
            project_item.sceneCount = scenes_created
            project_item.updatedAt = datetime.now(timezone.utc)
            project_item.save()
        except DoesNotExist:
            logger.error("project_not_found_for_scene_count_update", project_id=project_id)

        logger.info(
            "scenes_created",
            project_id=project_id,
            scenes_created=scenes_created
        )

        # Extract character reference ID from S3 key if available
        character_reference_id = None
        if character_image_s3_key:
            # Extract UUID from S3 key (format: mv/outputs/character_reference/{uuid}.png)
            try:
                parts = character_image_s3_key.split('/')
                if len(parts) >= 4 and parts[-2] == 'character_reference':
                    character_reference_id = parts[-1].split('.')[0]  # Remove extension
            except Exception:
                pass  # If extraction fails, character_reference_id stays None

        # Start background tasks for video generation
        for i, scene_data in enumerate(scenes[:scenes_created], start=1):
            sequence_num = i  # Capture in local variable to avoid closure issue
            task = asyncio.create_task(
                generate_scene_video_background(
                    project_id=project_id,
                    sequence=sequence_num,
                    prompt=scene_data.description,
                    negative_prompt=scene_data.negative_description,
                    character_reference_id=character_reference_id,
                    duration=8.0
                )
            )
            # Add error callback to log any unhandled exceptions
            def task_done_callback(t, seq=sequence_num, proj_id=project_id):
                try:
                    t.result()  # This will raise if task had an exception
                except Exception as e:
                    logger.error(
                        "video_generation_task_failed",
                        project_id=proj_id,
                        sequence=seq,
                        error=str(e),
                        exc_info=True
                    )
            task.add_done_callback(task_done_callback)
            logger.info(
                "video_generation_queued",
                project_id=project_id,
                sequence=sequence_num
            )

    except Exception as e:
        logger.error(
            "background_scene_generation_failed",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )
        # Mark project as failed
        try:
            pk = f"PROJECT#{project_id}"
            project_item = MVProjectItem.get(pk, "METADATA")
            project_item.status = "failed"
            project_item.GSI1PK = "failed"
            project_item.updatedAt = datetime.now(timezone.utc)
            project_item.save()
        except Exception as update_error:
            logger.error(
                "failed_to_update_project_status_on_error",
                project_id=project_id,
                error=str(update_error),
                exc_info=True
            )


async def generate_scene_video_background(
    project_id: str,
    sequence: int,
    prompt: str,
    negative_prompt: Optional[str],
    character_reference_id: Optional[str] = None,
    duration: float = 8.0
):
    """
    Background task to generate video for a single scene.
    
    This function:
    1. Calls generate_video with project_id and sequence
    2. The generate_video endpoint will handle status updates
    3. Errors are logged but don't break the workflow
    """
    try:
        logger.info(
            "background_video_generation_started",
            project_id=project_id,
            sequence=sequence
        )
        
        # Mark scene as processing before generation starts
        pk = f"PROJECT#{project_id}"
        sk = f"SCENE#{sequence:03d}"
        try:
            scene_item = MVProjectItem.get(pk, sk)
            scene_item.status = "processing"
            scene_item.updatedAt = datetime.now(timezone.utc)
            scene_item.save()
            logger.info(
                "scene_marked_as_processing",
                project_id=project_id,
                sequence=sequence
            )
        except DoesNotExist:
            logger.warning(
                "scene_not_found_for_processing",
                project_id=project_id,
                sequence=sequence
            )
            return  # Can't proceed if scene doesn't exist
        
        # Import here to avoid circular dependency
        from mv.video_generator import generate_video
        from services.s3_storage import get_s3_storage_service
        
        logger.info(
            "starting_video_generation",
            project_id=project_id,
            sequence=sequence,
            has_character_reference=character_reference_id is not None,
            character_reference_id=character_reference_id
        )
        
        # Generate video (this is synchronous, so run in thread pool)
        try:
            video_id, video_path, video_url, metadata, character_reference_warning = await asyncio.to_thread(
                generate_video,
                prompt=prompt,
                negative_prompt=negative_prompt,
                duration=int(duration),
                character_reference_id=character_reference_id,
                backend="replicate",
            )
            logger.info(
                "video_generation_completed",
                project_id=project_id,
                sequence=sequence,
                video_id=video_id,
                video_path=video_path,
                has_video_url=video_url is not None
            )
        except Exception as gen_error:
            logger.error(
                "video_generation_exception",
                project_id=project_id,
                sequence=sequence,
                error=str(gen_error),
                exc_info=True
            )
            raise  # Re-raise to be caught by outer exception handler
        
        # Upload to S3 if configured
        s3_service = get_s3_storage_service()
        if s3_service and video_path and os.path.exists(video_path):
            try:
                # Generate S3 key for scene video
                from services.s3_storage import generate_scene_s3_key
                s3_key = generate_scene_s3_key(
                    project_id=project_id,
                    sequence=sequence,
                    asset_type="video"
                )
                
                # Upload video to S3 (using upload_file_from_path for simplicity)
                s3_service.upload_file_from_path(
                    file_path=video_path,
                    s3_key=s3_key,
                    content_type="video/mp4"
                )
                
                logger.info(
                    "scene_video_uploaded_to_s3",
                    project_id=project_id,
                    sequence=sequence,
                    s3_key=s3_key
                )
                
                # Update scene record with S3 key
                pk = f"PROJECT#{project_id}"
                sk = f"SCENE#{sequence:03d}"
                
                try:
                    scene_item = MVProjectItem.get(pk, sk)
                    scene_item.videoClipS3Key = s3_key
                    scene_item.status = "completed"
                    scene_item.updatedAt = datetime.now(timezone.utc)
                    scene_item.save()
                    
                    # Increment completed scenes counter
                    from mv_models import increment_completed_scene
                    increment_completed_scene(project_id)
                    
                    logger.info(
                        "scene_video_generation_completed",
                        project_id=project_id,
                        sequence=sequence,
                        s3_key=s3_key
                    )
                except DoesNotExist:
                    logger.warning(
                        "scene_not_found_for_video_update",
                        project_id=project_id,
                        sequence=sequence
                    )
                    
            except Exception as e:
                logger.error(
                    "failed_to_upload_scene_video",
                    project_id=project_id,
                    sequence=sequence,
                    error=str(e),
                    exc_info=True
                )
                # Mark scene as failed
                try:
                    pk = f"PROJECT#{project_id}"
                    sk = f"SCENE#{sequence:03d}"
                    scene_item = MVProjectItem.get(pk, sk)
                    scene_item.status = "failed"
                    scene_item.errorMessage = f"Failed to upload video: {str(e)}"
                    scene_item.updatedAt = datetime.now(timezone.utc)
                    scene_item.save()
                    
                    from mv_models import increment_failed_scene
                    increment_failed_scene(project_id)
                except Exception:
                    pass
        else:
            # No S3 configured, just update status to completed
            try:
                pk = f"PROJECT#{project_id}"
                sk = f"SCENE#{sequence:03d}"
                scene_item = MVProjectItem.get(pk, sk)
                scene_item.status = "completed"
                scene_item.updatedAt = datetime.now(timezone.utc)
                scene_item.save()
                
                from mv_models import increment_completed_scene
                increment_completed_scene(project_id)
                
                logger.info(
                    "scene_video_generation_completed_no_s3",
                    project_id=project_id,
                    sequence=sequence,
                    video_url=video_url
                )
            except DoesNotExist:
                logger.warning(
                    "scene_not_found_for_completion",
                    project_id=project_id,
                    sequence=sequence
                )
                
    except Exception as e:
        logger.error(
            "background_video_generation_failed",
            project_id=project_id,
            sequence=sequence,
            error=str(e),
            exc_info=True
        )
        
        # Mark scene as failed
        try:
            pk = f"PROJECT#{project_id}"
            sk = f"SCENE#{sequence:03d}"
            scene_item = MVProjectItem.get(pk, sk)
            scene_item.status = "failed"
            scene_item.errorMessage = f"Video generation failed: {str(e)}"
            scene_item.updatedAt = datetime.now(timezone.utc)
            scene_item.save()
            
            from mv_models import increment_failed_scene
            increment_failed_scene(project_id)
        except Exception as update_error:
            logger.error(
                "failed_to_update_scene_status_on_error",
                project_id=project_id,
                sequence=sequence,
                error=str(update_error),
                exc_info=True
            )


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


@router.patch(
    "/projects/{project_id}/scenes/{sequence}",
    response_model=SceneResponse,
    summary="Update Scene",
    description="""
Update a specific scene's editable fields (prompt, negative prompt).

This endpoint allows manual editing of scene descriptions without regenerating
the entire scene or video.
"""
)
async def update_scene(
    project_id: str,
    sequence: int,
    update_data: SceneUpdateRequest
):
    """
    Update a scene's editable fields.

    Args:
        project_id: Project UUID
        sequence: Scene sequence number (1-based)
        update_data: Fields to update

    Returns:
        Updated SceneResponse
    """
    try:
        logger.info(
            "update_scene_request",
            project_id=project_id,
            sequence=sequence,
            updates=update_data.model_dump(exclude_none=True)
        )

        # Validate project_id format
        try:
            project_id = str(uuid.UUID(project_id))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid project ID format",
                    "details": "Project ID must be a valid UUID"
                }
            )

        # Validate sequence
        if sequence < 1:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid sequence number",
                    "details": "Sequence must be >= 1"
                }
            )

        # Retrieve the scene
        pk = f"PROJECT#{project_id}"
        sk = f"SCENE#{sequence:03d}"

        try:
            scene_item = MVProjectItem.get(pk, sk)
        except DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Scene {sequence} not found in project {project_id}",
                    "details": "The specified scene does not exist"
                }
            )

        # Update fields
        updated = False

        if update_data.prompt is not None:
            scene_item.prompt = update_data.prompt.strip()
            updated = True

        if update_data.negativePrompt is not None:
            scene_item.negativePrompt = update_data.negativePrompt.strip()
            updated = True

        # Save if any updates were made
        if updated:
            scene_item.updatedAt = datetime.now(timezone.utc)
            scene_item.save()
            logger.info(
                "scene_updated",
                project_id=project_id,
                sequence=sequence
            )

        # Generate presigned URLs for response
        s3_service = get_s3_storage_service()

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

        return SceneResponse(
            sequence=scene_item.sequence,
            status=scene_item.status,
            prompt=scene_item.prompt,
            negativePrompt=scene_item.negativePrompt,
            duration=scene_item.duration,
            referenceImageUrls=reference_urls,
            audioClipUrl=audio_url,
            videoClipUrl=video_url,
            needsLipSync=scene_item.needsLipSync or False,
            lipSyncedVideoClipUrl=lipsynced_url,
            retryCount=scene_item.retryCount or 0,
            errorMessage=scene_item.errorMessage,
            createdAt=scene_item.createdAt,
            updatedAt=scene_item.updatedAt
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "update_scene_error",
            project_id=project_id,
            sequence=sequence,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to update scene",
                "details": str(e)
            }
        )


@router.post(
    "/projects/{project_id}/generate",
    response_model=ProjectResponse,
    summary="Start Project Generation",
    description="""
Start the generation workflow for a project.

This endpoint:
1. Validates the project exists
2. Checks if scenes already exist (returns error if they do)
3. Updates project status to "processing" immediately
4. Returns the updated project immediately (for UI responsiveness)
5. Generates scene descriptions using Gemini in the background
6. Creates scene records in DynamoDB
7. Triggers video generation for each scene

**Note:** This endpoint returns immediately. Scene generation and video generation
happen asynchronously in the background. Use polling to track progress.
"""
)
async def start_generation(project_id: str):
    """
    Start generation workflow for a project.

    Args:
        project_id: Project UUID

    Returns:
        ProjectResponse with generated scenes
    """
    try:
        logger.info("start_generation_request", project_id=project_id)

        # Validate project_id format
        try:
            project_id = str(uuid.UUID(project_id))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid project ID format",
                    "details": "Project ID must be a valid UUID"
                }
            )

        # Retrieve project metadata
        pk = f"PROJECT#{project_id}"

        try:
            project_item = MVProjectItem.get(pk, "METADATA")
        except DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Project {project_id} not found",
                    "details": "The specified project does not exist"
                }
            )

        # Check if scenes already exist
        existing_scenes = MVProjectItem.query(
            pk,
            MVProjectItem.SK.startswith("SCENE#")
        )
        scene_count = sum(1 for _ in existing_scenes)

        if scene_count > 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Scenes already exist for this project",
                    "details": f"Project already has {scene_count} scene(s). Generation can only be started once."
                }
            )

        # Check if project is in valid state
        if project_item.status not in ["pending", "failed"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": f"Project is in '{project_item.status}' status",
                    "details": "Generation can only be started for projects in 'pending' or 'failed' status"
                }
            )

        # Update project status to processing IMMEDIATELY
        # This allows the UI to update before the long-running Gemini call
        project_item.status = "processing"
        project_item.GSI1PK = "processing"
        project_item.updatedAt = datetime.now(timezone.utc)
        project_item.save()

        logger.info(
            "generation_started_status_updated",
            project_id=project_id,
            status="processing"
        )

        # Return updated project IMMEDIATELY so UI can show "processing" state
        # Scene generation will happen in background
        response = await get_project(project_id)

        # Start background task for scene generation and video generation
        # This runs asynchronously so the endpoint can return immediately
        task = asyncio.create_task(
            generate_scenes_and_videos_background(
                project_id=project_id,
                concept_prompt=project_item.conceptPrompt,
                character_description=project_item.characterDescription,
                character_image_s3_key=project_item.characterImageS3Key
            )
        )

        # Add error callback to log any unhandled exceptions
        def main_task_done_callback(t):
            try:
                t.result()  # This will raise if task had an exception
            except Exception as e:
                logger.error(
                    "main_background_generation_task_failed",
                    project_id=project_id,
                    error=str(e),
                    exc_info=True
                )
        task.add_done_callback(main_task_done_callback)

        logger.info(
            "background_generation_queued",
            project_id=project_id
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("start_generation_error", project_id=project_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to start generation",
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

