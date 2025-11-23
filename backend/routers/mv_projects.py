"""
Music Video Projects API Router.

Implements CRUD endpoints for project management with DynamoDB.
"""

import uuid
import os
import asyncio
import structlog
import tempfile
import time
import shutil
import requests
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import Optional, List
from pathlib import Path

from mv_schemas import (
    ProjectCreateResponse,
    ProjectResponse,
    ProjectUpdateRequest,
    SceneUpdateRequest,
    TrimSceneRequest,
    AddSceneRequest,
    AddSceneResponse,
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
from mv.scene_generator import generate_scenes, generate_scenes_legacy
from mv.video_generator import generate_video
from services.s3_storage import (
    get_s3_storage_service,
    generate_s3_key,
    validate_s3_key,
)
from config import settings
from pynamodb.exceptions import PutError, DoesNotExist

logger = structlog.get_logger()

router = APIRouter(prefix="/api/mv", tags=["MV Projects"])


async def get_next_scene_sequence(project_id: str) -> int:
    """
    Get the next sequence number for a new scene in a project.
    
    Queries all existing scenes for the project and returns max(sequence) + 1.
    Returns 1 if no scenes exist.
    
    Args:
        project_id: Project UUID
        
    Returns:
        Next sequence number (1-indexed)
        
    Raises:
        DoesNotExist: If project doesn't exist (should be checked before calling)
    """
    pk = f"PROJECT#{project_id}"
    
    try:
        # Query all scenes for this project
        scenes = MVProjectItem.query(
            pk,
            MVProjectItem.SK.startswith("SCENE#")
        )
        
        # Extract sequence numbers
        sequences = [scene.sequence for scene in scenes if hasattr(scene, 'sequence') and scene.sequence is not None]
        
        if not sequences:
            logger.info(
                "no_existing_scenes",
                project_id=project_id,
                next_sequence=1
            )
            return 1
        
        next_sequence = max(sequences) + 1
        logger.info(
            "next_scene_sequence_calculated",
            project_id=project_id,
            max_sequence=max(sequences),
            next_sequence=next_sequence
        )
        return next_sequence
        
    except Exception as e:
        logger.error(
            "failed_to_get_next_scene_sequence",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )
        # Default to 1 if query fails (edge case)
        return 1


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
        # Retrieve director config and mode from project metadata
        pk = f"PROJECT#{project_id}"
        director_config = None
        project_mode = None
        try:
            project_item = MVProjectItem.get(pk, "METADATA")
            director_config = project_item.directorConfig  # May be None
            project_mode = project_item.mode  # May be None
        except DoesNotExist:
            logger.warning(
                "project_not_found_for_director_config",
                project_id=project_id
            )
            # Continue without director config (graceful fallback)

        logger.info(
            "background_scene_generation_started",
            project_id=project_id,
            director_config=director_config,
            project_mode=project_mode
        )

        # Generate scenes using new simplified API or legacy fallback
        if project_mode and project_mode in ["music-video", "ad-creative"]:
            # Use new mode-based template system
            logger.info(
                "using_new_scene_generator",
                project_id=project_id,
                mode=project_mode
            )
            scenes, _output_files = generate_scenes(
                mode=project_mode,
                concept_prompt=concept_prompt,
                personality_profile=character_description,
                director_config=director_config,
            )
        else:
            # Fallback to legacy generator for projects without mode (backward compatibility)
            logger.warning(
                "using_legacy_scene_generator",
                project_id=project_id,
                project_mode=project_mode,
                reason="Mode not set or invalid, using legacy generator"
            )
            scenes, _output_files = generate_scenes_legacy(
                idea=concept_prompt,
                character_description=character_description,
                number_of_scenes=None,  # Will use default from config
                director_config=director_config,
                project_mode=project_mode,  # May be None
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
            # Extract UUID from S3 key (format: character_references/{uuid}.{ext})
            try:
                parts = character_image_s3_key.split('/')
                if len(parts) >= 2 and parts[-2] == 'character_references':
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
                
                # Extract video duration before upload
                from mv.video_trimmer import get_video_duration
                actual_duration = get_video_duration(video_path)
                
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
                    s3_key=s3_key,
                    duration=actual_duration
                )
                
                # Update scene record with video clip fields
                pk = f"PROJECT#{project_id}"
                sk = f"SCENE#{sequence:03d}"
                
                try:
                    scene_item = MVProjectItem.get(pk, sk)
                    # Initialize video clip fields
                    scene_item.originalVideoClipS3Key = s3_key
                    scene_item.workingVideoClipS3Key = s3_key  # Same as original initially
                    scene_item.trimPoints = json.dumps({"in": 0.0, "out": actual_duration})  # Full clip
                    scene_item.duration = actual_duration  # Actual duration
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
- `audio`: Music file (music-video mode required, ad-creative mode optional)

**Form Data:**
- `mode`: "ad-creative" or "music-video"
- `prompt`: Video concept description
- `characterDescription`: Character/style description
- `characterReferenceImageId`: UUID of pre-generated character image (optional)
- `productDescription`: Product details (optional)

**Audio:**
- For music-video mode, audio file is required
- Audio should be converted from YouTube on frontend using `/api/audio/convert-youtube`
- Audio is uploaded to S3 and S3 key saved to `audioBackingTrackS3Key` in DynamoDB
"""
)
async def create_project(
    mode: str = Form(...),
    prompt: str = Form(...),
    characterDescription: Optional[str] = Form(None),
    characterReferenceImageId: Optional[str] = Form(None),
    productDescription: Optional[str] = Form(None),
    productReferenceImageId: Optional[str] = Form(None),
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
        audio: Optional audio file (MP3 format, converted from YouTube on frontend)

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
        if mode == 'music-video' and not audio:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Audio file required for music-video mode",
                    "details": "Please provide an audio file (converted from YouTube or uploaded)"
                }
            )

        # Generate project ID
        project_id = str(uuid.uuid4())
        s3_service = get_s3_storage_service()

        # Upload files to S3
        character_image_s3_key = None
        product_image_s3_key = None
        audio_s3_key = None

        # Handle character reference image (for music-video mode)
        if characterReferenceImageId:
            # Validate UUID format
            try:
                uuid.UUID(characterReferenceImageId)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "Invalid character reference ID format",
                        "details": "Character reference ID must be a valid UUID"
                    }
                )
            # Reference to existing character image in character_references directory
            # Determine actual file extension by checking which file exists in S3
            character_image_s3_key = None
            for ext in ["png", "jpg", "jpeg", "webp"]:
                test_key = f"character_references/{characterReferenceImageId}.{ext}"
                if s3_service.file_exists(test_key):
                    character_image_s3_key = test_key
                    logger.info(
                        "character_reference_extension_found",
                        character_reference_id=characterReferenceImageId,
                        extension=ext,
                        s3_key=test_key
                    )
                    break

            # If no file found, default to .png for backward compatibility
            if not character_image_s3_key:
                character_image_s3_key = f"character_references/{characterReferenceImageId}.png"
                logger.warning(
                    "character_reference_not_found_defaulting_to_png",
                    character_reference_id=characterReferenceImageId,
                    s3_key=character_image_s3_key
                )

        # Handle product reference image (for ad-creative mode)
        if productReferenceImageId:
            # Validate UUID format
            try:
                uuid.UUID(productReferenceImageId)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "Invalid product reference ID format",
                        "details": "Product reference ID must be a valid UUID"
                    }
                )
            # Reference to existing product image in character_references directory
            # (we reuse the same directory for both character and product references)
            product_image_s3_key = f"character_references/{productReferenceImageId}.png"

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

        # Upload audio file to S3 if provided
        audio_s3_key = None
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
            director_config=directorConfig,
            mode=mode
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

            # Video clip URLs (NEW)
            original_video_url = None
            if scene_item.originalVideoClipS3Key:
                original_video_url = s3_service.generate_presigned_url(scene_item.originalVideoClipS3Key)

            working_video_url = None
            if scene_item.workingVideoClipS3Key:
                working_video_url = s3_service.generate_presigned_url(scene_item.workingVideoClipS3Key)

            lipsynced_url = None
            if scene_item.lipSyncedVideoClipS3Key:
                lipsynced_url = s3_service.generate_presigned_url(scene_item.lipSyncedVideoClipS3Key)

            # Parse trim points
            trim_points = None
            if scene_item.trimPoints:
                trim_points = json.loads(scene_item.trimPoints)

            scenes.append(SceneResponse(
                sequence=scene_item.sequence,
                status=scene_item.status,
                prompt=scene_item.prompt,
                negativePrompt=scene_item.negativePrompt,
                duration=scene_item.duration,
                referenceImageUrls=reference_urls,
                audioClipUrl=audio_url,
                originalVideoClipUrl=original_video_url,
                workingVideoClipUrl=working_video_url,
                videoClipUrl=working_video_url,  # Backward compatibility
                trimPoints=trim_points,
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
            mode=project_item.mode,
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

        # Video clip URLs (NEW)
        original_video_url = None
        if scene_item.originalVideoClipS3Key:
            original_video_url = s3_service.generate_presigned_url(scene_item.originalVideoClipS3Key)

        working_video_url = None
        if scene_item.workingVideoClipS3Key:
            working_video_url = s3_service.generate_presigned_url(scene_item.workingVideoClipS3Key)

        lipsynced_url = None
        if scene_item.lipSyncedVideoClipS3Key:
            lipsynced_url = s3_service.generate_presigned_url(scene_item.lipSyncedVideoClipS3Key)

        # Parse trim points
        trim_points = None
        if scene_item.trimPoints:
            trim_points = json.loads(scene_item.trimPoints)

        return SceneResponse(
            sequence=scene_item.sequence,
            status=scene_item.status,
            prompt=scene_item.prompt,
            negativePrompt=scene_item.negativePrompt,
            duration=scene_item.duration,
            referenceImageUrls=reference_urls,
            audioClipUrl=audio_url,
            originalVideoClipUrl=original_video_url,
            workingVideoClipUrl=working_video_url,
            videoClipUrl=working_video_url,  # Backward compatibility
            trimPoints=trim_points,
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
    "/projects/{project_id}/scenes",
    response_model=AddSceneResponse,
    status_code=201,
    summary="Add New Scene to Project",
    description="""
Generate and add a single new scene to an existing project with automatic video generation.

This endpoint:
1. Validates project exists and is in valid state (completed or processing)
2. Gets next sequence number for the new scene
3. Generates a single scene using project's context (mode, director config, reference images)
4. Creates scene item in DynamoDB with new sequence
5. Triggers video generation in background
6. Returns the newly created scene

**Project State Requirements:**
- Project must exist and be in "completed" or "processing" status
- Cannot add scenes to "pending" (initial generation in progress)
- Cannot add scenes to "failed" (needs retry of original generation)
- Cannot add scenes to "composing" (final video generation in progress)

**Scene Generation:**
- Uses project's existing mode (music-video or ad-creative)
- Uses project's director config (if set)
- Uses project's character reference image (if exists)
- Uses project's character description as personality profile

**Example Request:**
```json
{
  "sceneConcept": "A dramatic close-up of the artist performing with intense emotion"
}
```
"""
)
async def add_scene(
    project_id: str,
    request: AddSceneRequest
):
    """
    Add a new scene to an existing project.

    Args:
        project_id: Project UUID
        request: Scene concept description

    Returns:
        AddSceneResponse with newly created scene

    Raises:
        404: Project not found
        400: Invalid project state or scene concept validation failed
        500: Scene generation or creation failed
    """
    try:
        logger.info(
            "add_scene_request",
            project_id=project_id,
            scene_concept_preview=request.sceneConcept[:50] if request.sceneConcept else ""
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

        # Retrieve and validate project exists
        pk = f"PROJECT#{project_id}"
        try:
            project_item = MVProjectItem.get(pk, "METADATA")
        except DoesNotExist:
            logger.warning("project_not_found_for_add_scene", project_id=project_id)
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Project {project_id} not found",
                    "details": "The specified project does not exist"
                }
            )

        # Validate project state - only allow adding scenes to completed or processing projects
        if project_item.status not in ["completed", "processing"]:
            logger.warning(
                "invalid_project_state_for_add_scene",
                project_id=project_id,
                current_status=project_item.status
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": f"Cannot add scene: project is in '{project_item.status}' status",
                    "details": "Scenes can only be added to projects with 'completed' or 'processing' status"
                }
            )

        # Get project context for scene generation
        project_mode = project_item.mode or "music-video"  # Default to music-video if not set
        director_config = project_item.directorConfig
        character_description = project_item.characterDescription or ""
        character_image_s3_key = project_item.characterImageS3Key
        product_image_s3_key = project_item.productImageS3Key

        logger.info(
            "project_context_retrieved",
            project_id=project_id,
            mode=project_mode,
            has_director_config=director_config is not None,
            has_character_image=character_image_s3_key is not None,
            has_product_image=product_image_s3_key is not None
        )

        # Get next sequence number
        next_sequence = await get_next_scene_sequence(project_id)
        logger.info(
            "next_sequence_calculated",
            project_id=project_id,
            next_sequence=next_sequence
        )

        # Generate single scene using project's context
        try:
            scenes, _output_files = generate_scenes(
                mode=project_mode,
                concept_prompt=request.sceneConcept,
                personality_profile=character_description,
                director_config=director_config,
                number_of_scenes_override=1
            )
        except Exception as gen_error:
            logger.error(
                "scene_generation_failed",
                project_id=project_id,
                error=str(gen_error),
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "GenerationError",
                    "message": "Failed to generate scene",
                    "details": str(gen_error)
                }
            )

        # Validate exactly one scene was generated
        if not scenes or len(scenes) != 1:
            logger.error(
                "invalid_scene_count",
                project_id=project_id,
                expected=1,
                actual=len(scenes) if scenes else 0
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "GenerationError",
                    "message": f"Expected 1 scene, got {len(scenes) if scenes else 0}",
                    "details": "Scene generation returned unexpected number of scenes"
                }
            )

        generated_scene = scenes[0]

        # Prepare reference image S3 keys
        # Use product image for ad-creative mode, character image for music-video mode
        reference_image_s3_keys = []
        if project_mode == "ad-creative" and product_image_s3_key:
            reference_image_s3_keys = [product_image_s3_key]
        elif character_image_s3_key:
            reference_image_s3_keys = [character_image_s3_key]

        logger.info(
            "preparing_scene_creation",
            project_id=project_id,
            sequence=next_sequence,
            mode=project_mode,
            has_reference_images=len(reference_image_s3_keys) > 0,
            reference_image_s3_keys=reference_image_s3_keys,
            using_product_image=project_mode == "ad-creative" and product_image_s3_key is not None
        )

        # Create scene item in DynamoDB
        try:
            scene_item = create_scene_item(
                project_id=project_id,
                sequence=next_sequence,
                prompt=generated_scene.description,
                negative_prompt=generated_scene.negative_description,
                duration=8.0,  # Default duration
                needs_lipsync=True,  # TODO: Determine based on mode
                reference_image_s3_keys=reference_image_s3_keys
            )
            scene_item.save()
            
            # Reload scene item to ensure we have the latest saved values
            pk = f"PROJECT#{project_id}"
            sk = f"SCENE#{next_sequence:03d}"
            scene_item = MVProjectItem.get(pk, sk)
            
            logger.info(
                "scene_item_created",
                project_id=project_id,
                sequence=next_sequence,
                reference_image_count=len(scene_item.referenceImageS3Keys) if scene_item.referenceImageS3Keys else 0
            )
        except Exception as create_error:
            logger.error(
                "scene_item_creation_failed",
                project_id=project_id,
                sequence=next_sequence,
                error=str(create_error),
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "DatabaseError",
                    "message": "Failed to create scene item",
                    "details": str(create_error)
                }
            )

        # Update project's sceneCount
        try:
            project_item.sceneCount = (project_item.sceneCount or 0) + 1
            project_item.updatedAt = datetime.now(timezone.utc)
            project_item.save()
            logger.info(
                "project_scene_count_updated",
                project_id=project_id,
                new_count=project_item.sceneCount
            )
        except Exception as update_error:
            logger.warning(
                "failed_to_update_scene_count",
                project_id=project_id,
                error=str(update_error),
                exc_info=True
            )
            # Non-fatal error, continue

        # Extract character/product reference ID from S3 key if exists
        # Use product image ID for ad-creative mode, character image ID for music-video mode
        character_reference_id = None
        reference_s3_key = None
        if project_mode == "ad-creative" and product_image_s3_key:
            reference_s3_key = product_image_s3_key
        elif character_image_s3_key:
            reference_s3_key = character_image_s3_key
        
        if reference_s3_key:
            # Extract UUID from S3 key (format: character_references/{uuid}.{ext})
            try:
                parts = reference_s3_key.split('/')
                if len(parts) >= 2 and parts[-2] == 'character_references':
                    character_reference_id = parts[-1].split('.')[0]  # Remove extension
            except Exception:
                pass  # If extraction fails, character_reference_id stays None

        # Trigger video generation in background
        try:
            asyncio.create_task(
                generate_scene_video_background(
                    project_id=project_id,
                    sequence=next_sequence,
                    prompt=generated_scene.description,
                    negative_prompt=generated_scene.negative_description,
                    character_reference_id=character_reference_id,
                    duration=8.0
                )
            )
            logger.info(
                "video_generation_queued",
                project_id=project_id,
                sequence=next_sequence
            )
        except Exception as task_error:
            logger.error(
                "failed_to_queue_video_generation",
                project_id=project_id,
                sequence=next_sequence,
                error=str(task_error),
                exc_info=True
            )
            # Non-fatal error, scene is created but video generation will need manual trigger

        # Build response with presigned URLs
        s3_service = get_s3_storage_service()

        reference_urls = []
        if scene_item.referenceImageS3Keys:
            for key in scene_item.referenceImageS3Keys:
                reference_urls.append(s3_service.generate_presigned_url(key))

        audio_url = None
        if scene_item.audioClipS3Key:
            audio_url = s3_service.generate_presigned_url(scene_item.audioClipS3Key)

        # Video clip URLs (will be None for new scene)
        original_video_url = None
        if scene_item.originalVideoClipS3Key:
            original_video_url = s3_service.generate_presigned_url(scene_item.originalVideoClipS3Key)

        working_video_url = None
        if scene_item.workingVideoClipS3Key:
            working_video_url = s3_service.generate_presigned_url(scene_item.workingVideoClipS3Key)

        lipsynced_url = None
        if scene_item.lipSyncedVideoClipS3Key:
            lipsynced_url = s3_service.generate_presigned_url(scene_item.lipSyncedVideoClipS3Key)

        # Parse trim points
        trim_points = None
        if scene_item.trimPoints:
            trim_points = json.loads(scene_item.trimPoints)

        scene_response = SceneResponse(
            sequence=scene_item.sequence,
            status=scene_item.status,
            prompt=scene_item.prompt,
            negativePrompt=scene_item.negativePrompt,
            duration=scene_item.duration,
            referenceImageUrls=reference_urls,
            audioClipUrl=audio_url,
            originalVideoClipUrl=original_video_url,
            workingVideoClipUrl=working_video_url,
            videoClipUrl=working_video_url,  # Backward compatibility
            trimPoints=trim_points,
            needsLipSync=scene_item.needsLipSync or False,
            lipSyncedVideoClipUrl=lipsynced_url,
            retryCount=scene_item.retryCount or 0,
            errorMessage=scene_item.errorMessage,
            createdAt=scene_item.createdAt,
            updatedAt=scene_item.updatedAt
        )

        return AddSceneResponse(
            scene=scene_response,
            message="Scene added successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "add_scene_error",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to add scene",
                "details": str(e)
            }
        )


@router.post(
    "/projects/{project_id}/scenes/{sequence}/trim",
    response_model=SceneResponse,
    summary="Trim Scene Video",
    description="""
Trim a scene's video clip to specified IN/OUT points.

This endpoint:
1. Validates trim points (clamps to valid range: 0 to video duration)
2. Downloads original clip from S3 to temporary file
3. Trims video using moviepy
4. Deletes old working clip from S3 (if different from original)
5. Uploads new trimmed clip to S3 with versioned filename
6. Updates scene with new workingVideoClipS3Key and trimPoints
7. Updates scene duration to reflect trimmed clip duration

**Note:** This is a synchronous operation. Response returns when trim is complete.

**Trim Points:**
- IN point: Start time in seconds (millisecond precision)
- OUT point: End time in seconds (millisecond precision)
- Automatically clamped to valid range [0, video_duration]
- Minimum clip duration: 0.1 seconds

**Example Request:**
```json
{
  "trimPoints": {
    "in": 1.5,
    "out": 7.2
  }
}
```
"""
)
async def trim_scene_video(
    project_id: str,
    sequence: int,
    trim_request: TrimSceneRequest
):
    """
    Trim a scene's video clip.

    Args:
        project_id: Project UUID
        sequence: Scene sequence number (1-based)
        trim_request: Trim points (in, out)

    Returns:
        Updated SceneResponse with new working clip URL

    Raises:
        404: Project or scene not found
        400: Invalid trim points or missing original clip
        500: Trim operation failed
    """
    try:
        logger.info(
            "trim_scene_request",
            project_id=project_id,
            sequence=sequence,
            trim_points=trim_request.trimPoints
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

        # Retrieve scene
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

        # Validate original clip exists
        if not scene_item.originalVideoClipS3Key:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Cannot trim scene: original video clip not available",
                    "details": "Scene must have a generated video clip before trimming"
                }
            )

        # Extract trim points
        in_point = trim_request.trimPoints["in"]
        out_point = trim_request.trimPoints["out"]

        # Import dependencies
        from mv.video_trimmer import trim_video, get_video_duration
        from services.s3_storage import get_s3_storage_service, generate_working_clip_s3_key

        s3_service = get_s3_storage_service()

        # Download original clip from S3 to temp file
        temp_dir = tempfile.mkdtemp()
        try:
            original_video_path = os.path.join(temp_dir, "original.mp4")

            logger.debug("downloading_original_clip", s3_key=scene_item.originalVideoClipS3Key)
            # Download using presigned URL
            original_video_url = s3_service.generate_presigned_url(scene_item.originalVideoClipS3Key)
            response = requests.get(original_video_url, stream=True)
            response.raise_for_status()
            with open(original_video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Get video duration for validation
            video_duration = get_video_duration(original_video_path)
            logger.debug("original_video_duration", duration=video_duration)

            # Trim video
            trimmed_video_path = os.path.join(temp_dir, "trimmed.mp4")
            trim_metadata = trim_video(
                source_video_path=original_video_path,
                output_path=trimmed_video_path,
                in_point=in_point,
                out_point=out_point
            )

            logger.info("video_trimmed", metadata=trim_metadata)

            # Generate new working clip S3 key with timestamp
            timestamp = int(time.time())
            new_working_clip_s3_key = generate_working_clip_s3_key(
                project_id=project_id,
                sequence=sequence,
                timestamp=timestamp
            )

            # Delete old working clip from S3 (if different from original)
            if scene_item.workingVideoClipS3Key and scene_item.workingVideoClipS3Key != scene_item.originalVideoClipS3Key:
                try:
                    logger.debug("deleting_old_working_clip", s3_key=scene_item.workingVideoClipS3Key)
                    s3_service.delete_s3_object(scene_item.workingVideoClipS3Key)
                except Exception as del_error:
                    logger.warning("failed_to_delete_old_working_clip", error=str(del_error))
                    # Non-critical error, continue

            # Upload trimmed clip to S3
            logger.debug("uploading_trimmed_clip", s3_key=new_working_clip_s3_key)
            s3_service.upload_file_from_path(
                file_path=trimmed_video_path,
                s3_key=new_working_clip_s3_key,
                content_type="video/mp4"
            )

            # Update scene record
            scene_item.workingVideoClipS3Key = new_working_clip_s3_key
            scene_item.trimPoints = json.dumps({
                "in": trim_metadata["in_point"],
                "out": trim_metadata["out_point"]
            })
            scene_item.duration = trim_metadata["duration"]  # Update to trimmed duration
            scene_item.updatedAt = datetime.now(timezone.utc)
            scene_item.save()

            logger.info(
                "scene_trim_complete",
                project_id=project_id,
                sequence=sequence,
                working_clip_s3_key=new_working_clip_s3_key,
                duration=trim_metadata["duration"]
            )

        finally:
            # Clean up temp files
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning("temp_cleanup_failed", error=str(cleanup_error))

        # Generate presigned URLs for response
        reference_urls = []
        if scene_item.referenceImageS3Keys:
            for key in scene_item.referenceImageS3Keys:
                reference_urls.append(s3_service.generate_presigned_url(key))

        audio_url = None
        if scene_item.audioClipS3Key:
            audio_url = s3_service.generate_presigned_url(scene_item.audioClipS3Key)

        original_video_url = None
        if scene_item.originalVideoClipS3Key:
            original_video_url = s3_service.generate_presigned_url(scene_item.originalVideoClipS3Key)

        working_video_url = None
        if scene_item.workingVideoClipS3Key:
            working_video_url = s3_service.generate_presigned_url(scene_item.workingVideoClipS3Key)

        lipsynced_url = None
        if scene_item.lipSyncedVideoClipS3Key:
            lipsynced_url = s3_service.generate_presigned_url(scene_item.lipSyncedVideoClipS3Key)

        trim_points = None
        if scene_item.trimPoints:
            trim_points = json.loads(scene_item.trimPoints)

        return SceneResponse(
            sequence=scene_item.sequence,
            status=scene_item.status,
            prompt=scene_item.prompt,
            negativePrompt=scene_item.negativePrompt,
            duration=scene_item.duration,
            referenceImageUrls=reference_urls,
            audioClipUrl=audio_url,
            originalVideoClipUrl=original_video_url,
            workingVideoClipUrl=working_video_url,
            videoClipUrl=working_video_url,  # Backward compatibility
            trimPoints=trim_points,
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
            "trim_scene_error",
            project_id=project_id,
            sequence=sequence,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to trim scene video",
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

        # Validate that project has mode field (required for new system)
        if not project_item.mode or project_item.mode not in ["music-video", "ad-creative"]:
            logger.warning(
                "start_generation_missing_mode",
                project_id=project_id,
                mode=project_item.mode
            )
            # For legacy projects without mode, we'll use legacy generator as fallback
            # But log a warning
            if project_item.mode:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": f"Invalid mode: {project_item.mode}",
                        "details": "Project mode must be 'music-video' or 'ad-creative'"
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
Start final video composition process.

This endpoint:
1. Validates all scenes are completed
2. Starts background composition task
3. Returns immediately with job ID for tracking

The background task will:
1. Download scene videos from S3
2. Stitch them with moviepy
3. Add audio backing track
4. Upload final video to S3
5. Update project with final output S3 key

Poll GET /projects/{project_id} to check when finalOutputUrl is available.
"""
)
async def compose_video(project_id: str, request: ComposeRequest, background_tasks: BackgroundTasks):
    """
    Start final video composition in background.

    Args:
        project_id: Project UUID
        request: Composition request (currently no additional params)
        background_tasks: FastAPI background tasks

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

        # Generate job ID for tracking
        job_id = f"compose_{project_id}"

        # Update project status immediately
        project_item.status = "composing"
        project_item.GSI1PK = "composing"
        project_item.updatedAt = datetime.now(timezone.utc)
        project_item.save()

        # Import composition function
        from workers.compose_worker import process_composition_job

        # Start background composition task
        background_tasks.add_task(process_composition_job, project_id)
        logger.info("composition_job_started", job_id=job_id, project_id=project_id)

        return ComposeResponse(
            jobId=job_id,
            projectId=project_id,
            status="composing",
            message="Video composition started"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("compose_error", project_id=project_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to start composition",
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



