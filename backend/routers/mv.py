"""
Music Video (MV) endpoint router.

Handles scene generation and related music video pipeline operations.
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File as FileParam
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from mv.scene_generator import (
    CreateScenesRequest,
    CreateScenesResponse,
    generate_scenes,
)
from mv.image_generator import (
    GenerateCharacterReferenceRequest,
    GenerateCharacterReferenceResponse,
    generate_character_reference_image,
)
from mv.video_generator import (
    GenerateVideoRequest,
    GenerateVideoResponse,
    generate_video,
)
from mv.lipsync import (
    LipsyncRequest,
    LipsyncResponse,
    generate_lipsync,
)
from mv.video_stitcher import (
    StitchVideosRequest,
    StitchVideosResponse,
    stitch_videos,
)
from config import settings
from mv_models import (
    MVProjectItem,
    create_scene_item,
    increment_completed_scene,
    increment_failed_scene,
)
from services.s3_storage import (
    get_s3_storage_service,
    generate_scene_s3_key,
    validate_s3_key,
    S3StorageService,
)
from pynamodb.exceptions import DoesNotExist, PutError

logger = structlog.get_logger()

router = APIRouter(prefix="/api/mv", tags=["Music Video"])


@router.get(
    "/get_config_flavors",
    response_model=dict,
    status_code=200,
    summary="[DEPRECATED] Get Available Config Flavors",
    description="""
DEPRECATED: This endpoint is deprecated as of the config simplification refactor.

Config flavors have been replaced with mode-based templates.
Use the mode parameter ("music-video" or "ad-creative") in project creation instead.

This endpoint is kept for backward compatibility only and will be removed in a future version.

**Example Response:**
```json
{
    "flavors": ["default", "example", "cinematic"]
}
```
"""
)
async def get_config_flavors():
    """
    DEPRECATED: Get list of available configuration flavors.
    
    This endpoint is deprecated. Config flavors have been replaced with
    mode-based templates. New code should use mode parameter instead.

    Returns:
        Dictionary with 'flavors' key containing list of available flavor names
    """
    import warnings
    warnings.warn(
        "get_config_flavors endpoint is deprecated. Use mode-based templates instead.",
        DeprecationWarning,
        stacklevel=2
    )
    try:
        from mv.config_manager import get_discovered_flavors

        flavors = get_discovered_flavors()

        logger.warning("config_flavors_requested_deprecated", flavors=flavors)

        return {"flavors": flavors}
    except Exception as e:
        logger.error("get_config_flavors_error", error=str(e), exc_info=True)
        # Return default as fallback
        return {"flavors": ["default"]}


@router.get(
    "/get_director_configs",
    response_model=dict,
    status_code=200,
    summary="Get Available Director Configs",
    description="""
Get list of available director configuration files.

Returns an array of director config names (without extension) that are
available in backend/mv/director/configs/. These configs can be used
for creative direction in video generation.

**Example Response:**
```json
{
    "configs": ["Wes-Anderson", "David-Lynch", "Quentin-Tarantino"]
}
```
"""
)
async def get_director_configs():
    """
    Get list of available director configuration files.

    Returns:
        Dictionary with 'configs' key containing list of available director config names
    """
    try:
        from mv.director.prompt_parser import discover_director_configs

        configs = discover_director_configs()

        logger.info("director_configs_requested", configs=configs)

        return {"configs": configs}
    except Exception as e:
        logger.error("get_director_configs_error", error=str(e), exc_info=True)
        # Return empty list as fallback
        return {"configs": []}


@router.get(
    "/config/debug",
    summary="Debug Configuration",
    description="Shows current configuration values for troubleshooting"
)
async def debug_config():
    """Debug endpoint to check current configuration."""
    return {
        "SERVE_FROM_CLOUD": settings.SERVE_FROM_CLOUD,
        "STORAGE_BACKEND": settings.STORAGE_BACKEND,
        "STORAGE_BUCKET": settings.STORAGE_BUCKET,
        "PRESIGNED_URL_EXPIRY": settings.PRESIGNED_URL_EXPIRY,
        "cloud_serving_enabled": settings.SERVE_FROM_CLOUD and bool(settings.STORAGE_BUCKET)
    }


@router.post(
    "/create_scenes",
    response_model=CreateScenesResponse,
    status_code=200,
    responses={
        200: {"description": "Scenes generated successfully"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error or API failure"}
    },
    summary="Generate Scene Descriptions",
    description="""
Generate scene descriptions for a music video based on an idea and character.

This endpoint uses Google's Gemini model to generate structured scene prompts
that can be used for video generation. Each scene includes a description and
negative prompts for what to exclude.

**Database Integration:**
- If `project_id` is provided, scenes will be saved to DynamoDB and associated with the project
- If `project_id` is not provided, scenes are saved to filesystem only (backward compatible)

**Limitations:**
- Synchronous processing (may take 10-30+ seconds)
- File-based storage always occurs (for backward compatibility)

**Required Fields:**
- idea: The core concept or topic of the video
- character_description: Visual description of the main character

**Optional Fields (defaults from config):**
- project_id: UUID of existing project to associate scenes with (saves to DynamoDB)
- character_characteristics: Personality traits
- number_of_scenes: Number of scenes to generate (default: 4)
- video_type: Type of video (default: "video")
- video_characteristics: Visual style (default: "vlogging, realistic, 4k, cinematic")
- camera_angle: Camera perspective (default: "front")
"""
)
async def create_scenes(request: CreateScenesRequest):
    """
    Generate scene descriptions for a music video.

    This endpoint:
    1. Validates the request parameters
    2. Validates project_id format if provided (must be valid UUID)
    3. Applies defaults from YAML config for optional fields
    4. Generates scene prompts using Gemini 2.5 Pro
    5. Saves scenes to files (JSON and Markdown) - always occurs
    6. If project_id provided: Creates scene records in DynamoDB and updates project
    7. Returns the generated scenes and file paths

    **Example Request (without project_id - backward compatible):**
    ```json
    {
        "idea": "Tourist exploring Austin, Texas",
        "character_description": "Silver metallic humanoid robot with a red shield"
    }
    ```

    **Example Request (with project_id - database integration):**
    ```json
    {
        "idea": "Tourist exploring Austin, Texas",
        "character_description": "Silver metallic humanoid robot with a red shield",
        "project_id": "550e8400-e29b-41d4-a716-446655440000"
    }
    ```

    **Example Response (with project_id):**
    ```json
    {
        "scenes": [
            {
                "description": "A medium shot of a silver metallic humanoid robot...",
                "negative_description": "No other people, no music."
            }
        ],
        "output_files": {
            "json": "/path/to/scenes.json",
            "markdown": "/path/to/scenes.md"
        },
        "metadata": {
            "idea": "Tourist exploring Austin, Texas",
            "number_of_scenes": 4,
            "project_id": "550e8400-e29b-41d4-a716-446655440000",
            "scenes_created_in_db": 4,
            "db_integration": "success",
            "parameters_used": {...}
        }
    }
    ```
    """
    try:
        logger.info(
            "create_scenes_request_received",
            idea=request.idea,
            character_description=request.character_description[:100] + "..." if len(request.character_description) > 100 else request.character_description,
            number_of_scenes=request.number_of_scenes
        )

        # Validate required fields
        if not request.idea or not request.idea.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Idea is required",
                    "details": "The 'idea' field cannot be empty"
                }
            )

        if not request.character_description or not request.character_description.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Character description is required",
                    "details": "The 'character_description' field cannot be empty"
                }
            )

        # Validate project_id format if provided
        project_id = None
        if request.project_id:
            try:
                # Validate UUID format
                uuid.UUID(request.project_id)
                project_id = request.project_id
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "Invalid project_id format",
                        "details": "project_id must be a valid UUID"
                    }
                )

        # Generate scenes
        scenes, output_files = generate_scenes(
            idea=request.idea.strip(),
            character_description=request.character_description.strip(),
            character_characteristics=request.character_characteristics.strip() if request.character_characteristics else None,
            number_of_scenes=request.number_of_scenes,
            video_type=request.video_type.strip() if request.video_type else None,
            video_characteristics=request.video_characteristics.strip() if request.video_characteristics else None,
            camera_angle=request.camera_angle.strip() if request.camera_angle else None,
            config_flavor=request.config_flavor,
        )

        # If project_id provided, create scene records in DynamoDB
        scenes_created_in_db = 0
        if project_id:
            try:
                logger.info(
                    "create_scenes_with_project",
                    project_id=project_id,
                    scene_count=len(scenes)
                )

                # Retrieve project from DynamoDB
                pk = f"PROJECT#{project_id}"
                try:
                    project_item = MVProjectItem.get(pk, "METADATA")
                except DoesNotExist:
                    logger.warning("create_scenes_project_not_found", project_id=project_id)
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "NotFound",
                            "message": f"Project {project_id} not found",
                            "details": "The specified project does not exist in the database"
                        }
                    )

                # Log warning if character description doesn't match (but proceed)
                if project_item.characterDescription and project_item.characterDescription.strip() != request.character_description.strip():
                    logger.warning(
                        "create_scenes_character_mismatch",
                        project_id=project_id,
                        project_character=project_item.characterDescription[:100],
                        request_character=request.character_description[:100]
                    )

                # Create scene items in DynamoDB
                reference_image_s3_keys = []
                if project_item.characterImageS3Key:
                    reference_image_s3_keys = [project_item.characterImageS3Key]

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
                        scenes_created_in_db += 1
                        logger.info(
                            "scene_created_in_db",
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
                        # Partial success is acceptable

                # Update project with scene count
                project_item.sceneCount = len(scenes)
                project_item.status = "pending"
                project_item.GSI1PK = "pending"
                project_item.updatedAt = datetime.now(timezone.utc)
                project_item.save()

                logger.info(
                    "create_scenes_db_integration_complete",
                    project_id=project_id,
                    scenes_created=scenes_created_in_db,
                    total_scenes=len(scenes)
                )

            except HTTPException:
                # Re-raise HTTP exceptions (like 404)
                raise
            except Exception as e:
                # Log error but don't fail the request - scenes were generated successfully
                logger.error(
                    "create_scenes_db_integration_error",
                    project_id=project_id,
                    error=str(e),
                    exc_info=True
                )
                # Continue - file-based storage still works

        # Build metadata
        metadata = {
            "idea": request.idea.strip(),
            "number_of_scenes": len(scenes),
            "parameters_used": {
                "character_characteristics": request.character_characteristics or "default from config",
                "video_type": request.video_type or "default from config",
                "video_characteristics": request.video_characteristics or "default from config",
                "camera_angle": request.camera_angle or "default from config",
            }
        }

        # Add database integration info to metadata if project_id was provided
        if project_id:
            metadata["project_id"] = project_id
            metadata["scenes_created_in_db"] = scenes_created_in_db
            metadata["db_integration"] = "success" if scenes_created_in_db == len(scenes) else "partial"

        response = CreateScenesResponse(
            scenes=scenes,
            output_files=output_files,
            metadata=metadata
        )

        logger.info(
            "create_scenes_request_completed",
            scenes_count=len(scenes),
            output_json=output_files.get("json"),
            output_markdown=output_files.get("markdown")
        )

        return response

    except ValueError as e:
        # Handle configuration errors (e.g., missing API key)
        logger.error("create_scenes_config_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ConfigurationError",
                "message": str(e),
                "details": "Check your environment configuration"
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("create_scenes_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "An unexpected error occurred during scene generation",
                "details": str(e)
            }
        )


@router.post(
    "/test_scenes/{project_id}",
    response_model=CreateScenesResponse,
    status_code=200,
    summary="Test Scene Generation from Project",
    description="""
Test scene generation using an existing project's data.

This endpoint:
1. Retrieves project metadata from DynamoDB
2. Uses the project's mode, description, and director config to generate scenes
3. Optionally saves scenes to database (controlled by write_to_db parameter)
4. Returns the generated scenes for review

**Query Parameters:**
- `write_to_db`: Boolean (default: false). If true, scenes will be saved to database and associated with the project.

**Use Case:** Testing how scenes will be generated for a specific project, with option to commit if satisfied.
"""
)
async def test_scenes_from_project(project_id: str, write_to_db: bool = False):
    """
    Test scene generation using existing project data.

    Args:
        project_id: UUID of existing project
        write_to_db: If True, save scenes to database. Default: False (test only)

    Returns:
        CreateScenesResponse with generated scenes
    """
    try:
        logger.info("test_scenes_request", project_id=project_id)

        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid project ID format",
                    "details": "Project ID must be a valid UUID"
                }
            )

        # Retrieve project from database
        from pynamodb.exceptions import DoesNotExist
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

        # Extract project data
        mode = project_item.mode
        concept_prompt = project_item.conceptPrompt
        director_config = project_item.directorConfig

        # Get personality profile based on mode
        personality_profile = None
        if mode == "music-video":
            personality_profile = project_item.characterDescription
        elif mode == "ad-creative":
            personality_profile = project_item.productDescription

        if not personality_profile:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Project missing required description field",
                    "details": f"Mode '{mode}' requires {'characterDescription' if mode == 'music-video' else 'productDescription'}"
                }
            )

        logger.info(
            "generating_test_scenes",
            project_id=project_id,
            mode=mode,
            has_director=director_config is not None,
            write_to_db=write_to_db
        )

        # Generate scenes using the new simplified API
        scenes, output_files = generate_scenes(
            mode=mode,
            concept_prompt=concept_prompt,
            personality_profile=personality_profile,
            director_config=director_config,
        )

        logger.info(
            "test_scenes_generated",
            project_id=project_id,
            scene_count=len(scenes)
        )

        # Optionally save scenes to database
        scenes_created_in_db = 0
        db_status = "disabled"

        if write_to_db:
            # Get character reference image if available
            character_image_s3_key = None
            if mode == "music-video" and project_item.characterImageS3Key:
                character_image_s3_key = project_item.characterImageS3Key
            elif mode == "ad-creative" and project_item.productImageS3Key:
                character_image_s3_key = project_item.productImageS3Key

            reference_image_s3_keys = []
            if character_image_s3_key:
                reference_image_s3_keys = [character_image_s3_key]

            # Create scene items in DynamoDB
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
                    scenes_created_in_db += 1
                    logger.info(
                        "scene_saved_to_db",
                        project_id=project_id,
                        sequence=i
                    )
                except Exception as save_error:
                    logger.error(
                        "scene_save_failed",
                        project_id=project_id,
                        sequence=i,
                        error=str(save_error)
                    )

            # Update project scene count
            try:
                project_item.sceneCount = scenes_created_in_db
                project_item.updatedAt = datetime.now(timezone.utc)
                project_item.save()
                db_status = "success"
                logger.info(
                    "project_updated_with_scenes",
                    project_id=project_id,
                    scene_count=scenes_created_in_db
                )
            except Exception as update_error:
                logger.error(
                    "project_update_failed",
                    project_id=project_id,
                    error=str(update_error)
                )
                db_status = "partial"

        # Return response
        return CreateScenesResponse(
            scenes=scenes,
            output_files=output_files,
            metadata={
                "project_id": project_id,
                "mode": mode,
                "scenes_generated": len(scenes),
                "director_config": director_config,
                "write_to_db": write_to_db,
                "scenes_created_in_db": scenes_created_in_db,
                "db_integration": db_status
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "test_scenes_error",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to generate test scenes",
                "details": str(e)
            }
        )


@router.post(
    "/generate_scene_video/{project_id}/{scene_sequence}",
    status_code=200,
    summary="Generate Video for Scene",
    description="""
Generate a video clip for a specific scene in a project.

**Path Parameters:**
- `project_id`: Project identifier
- `scene_sequence`: Scene sequence number (1, 2, 3, etc.)

**Query Parameters:**
- `write_to_db`: Boolean (default: true). If true, video will be saved to database.
- `backend`: Video generation backend to use (default: "gemini")
  - "gemini": Google Veo 3.1 via Gemini API
  - "replicate": Google Veo 3.1 via Replicate API

**Process:**
1. Retrieves scene data from database
2. Generates video using scene prompt and reference images
3. Uploads video to S3
4. Optionally updates scene record with video URL

**Returns:**
- videoUrl: Presigned S3 URL for the generated video
- s3Key: S3 object key for the video
- metadata: Generation metadata (backend, duration, etc.)
"""
)
async def generate_scene_video(
    project_id: str,
    scene_sequence: int,
    write_to_db: bool = True,
    backend: str = "gemini"
):
    """
    Generate video for a specific scene.

    This endpoint:
    1. Retrieves scene from database
    2. Gets project reference images
    3. Generates video using specified backend
    4. Uploads video to S3
    5. Optionally updates scene with video S3 key
    """
    try:
        logger.info(
            "generate_scene_video_request",
            project_id=project_id,
            scene_sequence=scene_sequence,
            backend=backend,
            write_to_db=write_to_db
        )

        # Get scene from database
        scene_sk = f"SCENE#{scene_sequence:03d}"
        try:
            scene_item = MVProjectItem.get(f"PROJECT#{project_id}", scene_sk)
        except DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Scene {scene_sequence} not found in project {project_id}",
                    "details": "Scene does not exist in database"
                }
            )

        # Verify it's a scene item
        if scene_item.entityType != "scene":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid scene item",
                    "details": f"Item is not a scene (entityType={scene_item.entityType})"
                }
            )

        # Get project metadata for reference images
        try:
            project_item = MVProjectItem.get(f"PROJECT#{project_id}", "METADATA")
        except DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": f"Project {project_id} not found",
                    "details": "Project metadata does not exist"
                }
            )

        # Prepare reference image (use scene's reference images or project's character/product image)
        reference_image_base64 = None
        reference_s3_key = None

        # First try scene-specific reference images
        if scene_item.referenceImageS3Keys and len(scene_item.referenceImageS3Keys) > 0:
            reference_s3_key = scene_item.referenceImageS3Keys[0]
        # Fall back to project-level reference image based on mode
        elif project_item.mode == "music-video" and project_item.characterImageS3Key:
            reference_s3_key = project_item.characterImageS3Key
        elif project_item.mode == "ad-creative" and project_item.productImageS3Key:
            reference_s3_key = project_item.productImageS3Key

        # Download and encode reference image if available
        if reference_s3_key:
            try:
                import boto3
                import base64
                from io import BytesIO

                s3_client = boto3.client(
                    's3',
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )

                # Download image from S3
                image_obj = s3_client.get_object(
                    Bucket=settings.STORAGE_BUCKET,
                    Key=reference_s3_key
                )
                image_bytes = image_obj['Body'].read()
                reference_image_base64 = base64.b64encode(image_bytes).decode('utf-8')

                logger.info(
                    "reference_image_loaded",
                    s3_key=reference_s3_key,
                    size_bytes=len(image_bytes)
                )
            except Exception as e:
                logger.warning(
                    "reference_image_load_failed",
                    s3_key=reference_s3_key,
                    error=str(e)
                )
                # Continue without reference image

        # Generate video using specified backend
        video_bytes = None

        if backend == "gemini":
            from mv.video_backends.gemini_backend import generate_video_gemini

            video_bytes = generate_video_gemini(
                prompt=scene_item.prompt,
                negative_prompt=scene_item.negativePrompt,
                aspect_ratio="16:9",
                duration=int(scene_item.duration or 8),
                generate_audio=True,
                reference_image_base64=reference_image_base64,
            )
        elif backend == "replicate":
            from mv.video_backends.replicate_backend import generate_video_replicate

            video_bytes = generate_video_replicate(
                prompt=scene_item.prompt,
                negative_prompt=scene_item.negativePrompt,
                aspect_ratio="16:9",
                duration=int(scene_item.duration or 8),
                generate_audio=True,
                reference_image_base64=reference_image_base64,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": f"Invalid backend: {backend}",
                    "details": "Supported backends: gemini, replicate"
                }
            )

        if not video_bytes:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "VideoGenerationError",
                    "message": "Video generation returned no data",
                    "details": f"Backend {backend} did not return video bytes"
                }
            )

        logger.info(
            "video_generated",
            backend=backend,
            size_bytes=len(video_bytes)
        )

        # Upload video to S3
        from io import BytesIO
        s3_storage = S3StorageService()

        video_s3_key = f"mv/projects/{project_id}/scenes/{scene_sequence:03d}/video.mp4"
        video_file = BytesIO(video_bytes)

        s3_storage.upload_file(
            file_data=video_file,
            s3_key=video_s3_key,
            content_type="video/mp4"
        )

        logger.info(
            "video_uploaded_to_s3",
            s3_key=video_s3_key
        )

        # Update scene in database if requested
        if write_to_db:
            # Track if scene was already completed
            was_completed = scene_item.status == "completed"

            scene_item.videoClipS3Key = video_s3_key
            scene_item.status = "completed"
            scene_item.updatedAt = datetime.now(timezone.utc)
            scene_item.save()

            # Update project completed scenes count only if scene wasn't already completed
            if not was_completed:
                project_item.completedScenes = (project_item.completedScenes or 0) + 1
                project_item.updatedAt = datetime.now(timezone.utc)
                project_item.save()

            logger.info(
                "scene_updated_in_db",
                project_id=project_id,
                scene_sequence=scene_sequence,
                s3_key=video_s3_key,
                was_already_completed=was_completed
            )

        # Generate presigned URL for video
        video_url = s3_storage.generate_presigned_url(video_s3_key)

        return {
            "videoUrl": video_url,
            "s3Key": video_s3_key,
            "metadata": {
                "project_id": project_id,
                "scene_sequence": scene_sequence,
                "backend": backend,
                "duration": scene_item.duration,
                "prompt": scene_item.prompt,
                "write_to_db": write_to_db,
                "reference_image_used": reference_s3_key is not None,
                "video_size_bytes": len(video_bytes)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "generate_scene_video_error",
            project_id=project_id,
            scene_sequence=scene_sequence,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to generate scene video",
                "details": str(e)
            }
        )


@router.post(
    "/generate_character_reference",
    response_model=GenerateCharacterReferenceResponse,
    status_code=200,
    responses={
        200: {"description": "Character reference images generated successfully"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error or API failure"}
    },
    summary="Generate Character Reference Images",
    description="""
Generate 1-4 character reference images using Google Imagen 4 via Replicate API.

This endpoint creates full-body character reference images based on a visual
description, suitable for maintaining character consistency across video scenes.
Multiple images allow users to select the best representation.

**Limitations:**
- Synchronous processing (may take 10-60+ seconds)
- File-based storage (images saved to filesystem with UUID filenames)
- Large response size (base64 encoded images)

**Required Fields:**
- character_description: Visual description of the character

**Optional Fields (defaults from config):**
- num_images: Number of images to generate (1-4, default: 4)
- aspect_ratio: Image aspect ratio (default: "1:1")
- safety_filter_level: Content moderation level (default: "block_medium_and_above")
- person_generation: Person generation setting (default: "allow_adult")
- output_format: Output format (default: "png")
- negative_prompt: Elements to exclude from the image
- seed: Random seed for reproducibility
"""
)
async def generate_character_reference(request: GenerateCharacterReferenceRequest):
    """
    Generate character reference images.

    This endpoint:
    1. Validates the request parameters
    2. Applies defaults from YAML config for optional fields
    3. Generates images using Replicate API with Google Imagen 4
    4. Saves images to files with UUID-based filenames
    5. Returns list of images with IDs, paths, and base64 data

    **Example Request:**
    ```json
    {
        "character_description": "Silver metallic humanoid robot with a red shield",
        "num_images": 4
    }
    ```

    **Example Response:**
    ```json
    {
        "images": [
            {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "path": "/path/to/a1b2c3d4...png",
                "base64": "iVBORw0KGgoAAAANSUhEUgAA..."
            },
            ...
        ],
        "metadata": {
            "character_description": "Silver metallic humanoid robot...",
            "model_used": "google/imagen-4",
            "num_images_requested": 4,
            "num_images_generated": 4,
            "parameters_used": {...},
            "generation_timestamp": "2025-11-15T14:30:25Z"
        }
    }
    ```
    """
    try:
        logger.info(
            "generate_character_reference_request_received",
            character_description=request.character_description[:100] + "..." if len(request.character_description) > 100 else request.character_description,
            num_images=request.num_images,
            aspect_ratio=request.aspect_ratio
        )

        # Validate required fields
        if not request.character_description or not request.character_description.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Character description is required",
                    "details": "The 'character_description' field cannot be empty"
                }
            )

        # Generate character reference images
        images, metadata = generate_character_reference_image(
            character_description=request.character_description.strip(),
            num_images=request.num_images,
            aspect_ratio=request.aspect_ratio.strip() if request.aspect_ratio else None,
            safety_filter_level=request.safety_filter_level.strip() if request.safety_filter_level else None,
            person_generation=request.person_generation.strip() if request.person_generation else None,
            output_format=request.output_format.strip() if request.output_format else None,
            negative_prompt=request.negative_prompt.strip() if request.negative_prompt else None,
            seed=request.seed,
            config_flavor=request.config_flavor,
        )

        # Upload to S3 if cloud storage is configured (follows video_generator.py pattern)
        cloud_urls = {}
        try:
            if settings.STORAGE_BUCKET:
                from services.storage_backend import get_storage_backend
                import asyncio
                import concurrent.futures
                
                async def upload_images_to_cloud():
                    """Upload character reference images to cloud storage."""
                    storage = get_storage_backend()
                    urls = {}
                    
                    for image in images:
                        try:
                            # Determine file extension from path
                            from pathlib import Path
                            ext = Path(image.path).suffix.lstrip('.')
                            
                            cloud_path = f"character_references/{image.id}.{ext}"
                            url = await storage.upload_file(
                                image.path,
                                cloud_path
                            )
                            
                            # Update image with cloud URL
                            image.cloud_url = url
                            urls[image.id] = url
                            
                            logger.info(
                                "character_image_uploaded_to_cloud",
                                image_id=image.id,
                                cloud_path=cloud_path
                            )
                        except Exception as e:
                            logger.warning(
                                "character_image_upload_failed",
                                image_id=image.id,
                                error=str(e)
                            )
                            # Continue with other images
                    
                    return urls
                
                # Run async upload in separate thread to avoid event loop conflicts
                def run_upload():
                    return asyncio.run(upload_images_to_cloud())
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_upload)
                    cloud_urls = future.result(timeout=120)  # 2 min timeout for multiple images
                
                logger.info(
                    "character_images_uploaded_to_cloud",
                    num_images=len(cloud_urls),
                    image_ids=list(cloud_urls.keys())
                )
        except Exception as e:
            logger.warning(
                "character_images_cloud_upload_failed",
                error=str(e)
            )
            # Continue without cloud upload - local files are still available

        response = GenerateCharacterReferenceResponse(
            images=images,
            metadata=metadata
        )

        logger.info(
            "generate_character_reference_request_completed",
            num_images_requested=request.num_images,
            num_images_generated=len(images),
            num_images_uploaded=len(cloud_urls),
            image_ids=[img.id for img in images]
        )

        return response

    except ValueError as e:
        # Handle configuration errors (e.g., missing API token)
        logger.error("generate_character_reference_config_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ConfigurationError",
                "message": str(e),
                "details": "Check your environment configuration"
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("generate_character_reference_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "An unexpected error occurred during image generation",
                "details": str(e)
            }
        )


@router.post(
    "/upload_character_reference",
    status_code=200,
    responses={
        200: {"description": "Character reference image uploaded successfully"},
        400: {"description": "Invalid file or request"},
        500: {"description": "Internal server error"}
    },
    summary="Upload Character Reference Image",
    description="""
Upload a character reference image file.

This endpoint:
1. Accepts an image file upload (multipart/form-data)
2. Generates a UUID for the image
3. Uploads the image to S3 at `character_references/{uuid}.{ext}`
4. Returns the image ID (UUID) for use in project creation

**File Requirements:**
- Must be a valid image file (PNG, JPEG, WebP)
- Maximum size: 10MB

**Returns:**
- `image_id`: UUID that can be used as `characterReferenceImageId` in project creation
- `image_url`: Optional presigned URL (if cloud storage configured)
"""
)
async def upload_character_reference(
    file: UploadFile = FileParam(..., description="Image file to upload")
):
    """
    Upload a character reference image file.
    
    Args:
        file: Image file to upload
        
    Returns:
        JSON with image_id (UUID) and optional image_url
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid file type",
                    "details": "File must be an image (PNG, JPEG, WebP, etc.)"
                }
            )
        
        # Validate file size (10MB max)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "File too large",
                    "details": f"Maximum file size is {MAX_FILE_SIZE / (1024*1024):.0f}MB"
                }
            )
        
        # Generate UUID for the image
        image_id = str(uuid.uuid4())
        
        # Determine file extension from content type or filename
        ext = "png"  # default
        if file.content_type:
            content_type_lower = file.content_type.lower()
            if "jpeg" in content_type_lower or "jpg" in content_type_lower:
                ext = "jpg"
            elif "png" in content_type_lower:
                ext = "png"
            elif "webp" in content_type_lower:
                ext = "webp"

            logger.debug(
                "extension_detected_from_content_type",
                content_type=file.content_type,
                detected_extension=ext
            )
        elif file.filename:
            # Fallback to filename extension
            ext = Path(file.filename).suffix.lstrip('.').lower() or "png"

            logger.debug(
                "extension_detected_from_filename",
                filename=file.filename,
                detected_extension=ext
            )
        
        # Save to temporary file
        # Use same directory structure as generate_character_reference endpoint
        temp_dir = Path(__file__).parent.parent / "mv" / "outputs" / "character_reference"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_file_path = temp_dir / f"{image_id}.{ext}"
        with open(temp_file_path, "wb") as f:
            f.write(file_content)
        
        logger.info(
            "character_reference_uploaded",
            image_id=image_id,
            filename=file.filename,
            content_type=file.content_type,
            file_size=len(file_content),
            temp_path=str(temp_file_path)
        )
        
        # Upload to S3 if cloud storage is configured
        image_url = None
        if settings.STORAGE_BUCKET:
            try:
                from services.storage_backend import get_storage_backend

                storage = get_storage_backend()
                cloud_path = f"character_references/{image_id}.{ext}"

                # Upload directly - we're already in an async endpoint
                image_url = await storage.upload_file(
                    str(temp_file_path),
                    cloud_path
                )

                logger.info(
                    "character_reference_uploaded_to_cloud",
                    image_id=image_id,
                    cloud_path=cloud_path,
                    extension=ext,
                    image_url=image_url
                )
            except Exception as e:
                logger.error(
                    "character_reference_upload_to_cloud_failed",
                    image_id=image_id,
                    cloud_path=f"character_references/{image_id}.{ext}",
                    extension=ext,
                    error=str(e),
                    exc_info=True
                )
                # Continue without cloud URL - file is still saved locally
                image_url = None
        
        # Clean up temp file after successful upload (or if cloud storage not configured)
        # Only delete if cloud storage succeeded OR cloud storage is not configured
        if image_url or not settings.STORAGE_BUCKET:
            try:
                if temp_file_path.exists():
                    temp_file_path.unlink()
                    logger.debug(
                        "temp_file_cleaned_up",
                        image_id=image_id,
                        temp_path=str(temp_file_path)
                    )
            except Exception as e:
                logger.warning(
                    "failed_to_cleanup_temp_file",
                    image_id=image_id,
                    temp_path=str(temp_file_path),
                    error=str(e)
                )
        else:
            logger.info(
                "temp_file_kept_due_to_upload_failure",
                image_id=image_id,
                temp_path=str(temp_file_path)
            )
        
        return JSONResponse(
            content={
                "image_id": image_id,
                "image_url": image_url,
                "filename": file.filename,
                "content_type": file.content_type,
                "file_size": len(file_content)
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "upload_character_reference_error",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to upload character reference image",
                "details": str(e)
            }
        )


@router.get(
    "/get_character_reference/{image_id}",
    responses={
        200: {"description": "Character reference image or URL", "content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}, "application/json": {}}},
        404: {"description": "Image not found"}
    },
    summary="Retrieve Character Reference Image",
    description="""
Retrieve a character reference image by its UUID.

**Cloud Storage (S3):**
- Returns JSON with presigned URL by default
- Use `?redirect=true` to get 302 redirect to image (for browsers)

**Local Storage:**
- Serves the image file directly

**Query Parameters:**
- `redirect` (optional): Set to "true" for 302 redirect instead of JSON

**Example:**
```
GET /api/mv/get_character_reference/a1b2c3d4-e5f6-7890-abcd-ef1234567890
GET /api/mv/get_character_reference/a1b2c3d4-e5f6-7890-abcd-ef1234567890?redirect=true
```
"""
)
async def get_character_reference(image_id: str, redirect: bool = False):
    """
    Retrieve a character reference image by ID.

    This endpoint:
    1. Validates the image_id format
    2. Checks SERVE_FROM_CLOUD config
    3. If enabled, generates presigned URL and redirects to cloud storage
    4. Otherwise, serves the image file from local storage
    """
    # Validate image_id format (basic UUID validation)
    if not image_id or len(image_id) != 36 or image_id.count("-") != 4:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Invalid image_id format",
                "details": "image_id must be a valid UUID"
            }
        )
    
    # Check if we should serve from cloud storage
    if settings.SERVE_FROM_CLOUD and settings.STORAGE_BUCKET:
        logger.info(
            "get_character_reference_attempting_cloud_serve",
            image_id=image_id,
            serve_from_cloud=settings.SERVE_FROM_CLOUD,
            storage_bucket=settings.STORAGE_BUCKET
        )
        try:
            from services.storage_backend import get_storage_backend, S3StorageBackend
            
            storage = get_storage_backend()
            
            # S3: Generate presigned URL
            # Try multiple extensions since we don't store the extension separately
            if isinstance(storage, S3StorageBackend):
                # Try different extensions (matching local serving behavior)
                for ext in ["png", "jpg", "jpeg", "webp"]:
                    cloud_path = f"character_references/{image_id}.{ext}"

                    # Check if file exists in S3
                    try:
                        if storage.file_exists(cloud_path):
                            presigned_url = storage.generate_presigned_url(
                                cloud_path,
                                expiry=settings.PRESIGNED_URL_EXPIRY
                            )

                            logger.info(
                                "get_character_reference_url_generated",
                                image_id=image_id,
                                storage_backend="s3",
                                cloud_path=cloud_path,
                                extension=ext,
                                redirect_mode=redirect
                            )

                            # Return JSON with URL by default, or redirect if requested
                            if redirect:
                                return RedirectResponse(
                                    url=presigned_url,
                                    status_code=302
                                )
                            else:
                                return JSONResponse(
                                    content={
                                        "image_id": image_id,
                                        "image_url": presigned_url,
                                        "storage_backend": "s3",
                                        "expires_in_seconds": settings.PRESIGNED_URL_EXPIRY,
                                        "cloud_path": cloud_path
                                    },
                                    status_code=200
                                )
                    except Exception as e:
                        logger.debug(
                            "get_character_reference_extension_not_found",
                            image_id=image_id,
                            extension=ext,
                            error=str(e)
                        )
                        continue

                # If we get here, none of the extensions were found in S3
                logger.warning(
                    "get_character_reference_not_found_in_s3",
                    image_id=image_id,
                    tried_extensions=["png", "jpg", "jpeg", "webp"]
                )
            
            # If not S3, fall through to local serving
            logger.debug(
                "get_character_reference_cloud_fallback_to_local",
                image_id=image_id,
                reason="not_s3_backend"
            )
            
        except Exception as e:
            # If cloud serving fails, fall back to local
            logger.warning(
                "get_character_reference_cloud_error_fallback",
                image_id=image_id,
                error=str(e)
            )

    # Local serving: Search for image file (could be png, jpg, or webp)
    image_dir = Path(__file__).parent.parent / "mv" / "outputs" / "character_reference"

    # Try different extensions
    for ext in ["png", "jpg", "jpeg", "webp"]:
        image_path = image_dir / f"{image_id}.{ext}"
        if image_path.exists():
            # Determine media type
            media_type_map = {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "webp": "image/webp"
            }
            media_type = media_type_map.get(ext, "application/octet-stream")

            logger.info("get_character_reference_serving", image_id=image_id, image_path=str(image_path))

            return FileResponse(
                path=str(image_path),
                media_type=media_type,
                filename=f"{image_id}.{ext}"
            )

    # Not found
    logger.warning("get_character_reference_not_found", image_id=image_id)
    raise HTTPException(
        status_code=404,
        detail={
            "error": "NotFound",
            "message": f"Character reference image with ID {image_id} not found",
            "details": "The image may have been deleted or the ID is incorrect"
        }
    )


@router.post(
    "/generate_video",
    response_model=GenerateVideoResponse,
    status_code=200,
    responses={
        200: {"description": "Video generated successfully"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error or API failure"},
        503: {"description": "Backend service unavailable"}
    },
    summary="Generate Video Clip",
    description="""
Generate a single video clip from a text prompt using Replicate or Gemini backends.

**IMPORTANT: This is a synchronous endpoint that may take 20-400+ seconds to complete.**

This endpoint generates individual scene clips. Call it multiple times to create
separate clips for a multi-scene music video.

**Database Integration:**
- If `project_id` and `sequence` are provided together, the endpoint will:
  - Mark the scene as "processing" before generation starts
  - Update the scene record with video S3 key and job ID on success
  - Mark the scene as "completed" when video is ready
  - Mark the scene as "failed" if generation fails
  - Update project counters (completedScenes, failedScenes)
  - Upload video to S3 if storage is configured

**Limitations:**
- Synchronous processing (20-400s response times)
- No progress tracking (client waits for completion)
- File-based storage (videos saved with UUID filenames)
- Base64 reference images (large payload size)
- No authentication (videos accessible by UUID)

**Required Fields:**
- prompt: Text prompt describing the video content

**Optional Fields (defaults from config):**
- negative_prompt: Elements to exclude from the video
- aspect_ratio: Video aspect ratio (default: "16:9")
- duration: Video duration in seconds (default: 8)
- generate_audio: Whether to generate audio (default: true)
- seed: Random seed for reproducibility
- reference_image_base64: Base64 encoded reference image for character consistency
- video_rules_template: Custom rules to append to prompt
- backend: Backend to use - "replicate" (default) or "gemini"
- project_id: Project UUID for DynamoDB integration (requires sequence)
- sequence: Scene sequence number for DynamoDB integration (requires project_id)
"""
)
async def generate_video_endpoint(request: GenerateVideoRequest):
    """
    Generate a single video clip.

    This endpoint:
    1. Validates the request parameters
    2. Applies defaults from YAML config for optional fields
    3. Generates video using selected backend (Replicate or Gemini)
    4. Saves video to filesystem with UUID-based filename
    5. Returns video ID, path, URL, and metadata

    **Example Request:**
    ```json
    {
        "prompt": "A silver robot walks through a futuristic city at sunset",
        "duration": 8,
        "generate_audio": true
    }
    ```

    **Example Response:**
    ```json
    {
        "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "video_path": "/path/to/videos/a1b2c3d4...mp4",
        "video_url": "/api/mv/get_video/a1b2c3d4...",
        "metadata": {
            "prompt": "A silver robot walks...",
            "backend_used": "replicate",
            "model_used": "google/veo-3.1",
            "parameters_used": {...},
            "generation_timestamp": "2025-11-16T10:30:25Z",
            "processing_time_seconds": 45.7
        }
    }
    ```
    """
    try:
        logger.info(
            "generate_video_request_received",
            prompt=request.prompt[:100] + "..." if len(request.prompt) > 100 else request.prompt,
            backend=request.backend,
            character_reference_id=request.character_reference_id,
            has_reference_image_base64=request.reference_image_base64 is not None
        )

        # Validate required fields
        if not request.prompt or not request.prompt.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Prompt is required",
                    "details": "The 'prompt' field cannot be empty"
                }
            )

        # Validate backend
        if request.backend and request.backend not in ["replicate", "gemini"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": f"Invalid backend: {request.backend}",
                    "details": "Supported backends: 'replicate', 'gemini'"
                }
            )

        # Validate project_id and sequence are provided together
        if (request.project_id and not request.sequence) or (request.sequence and not request.project_id):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "project_id and sequence must be provided together",
                    "details": "Both project_id and sequence are required for DynamoDB integration"
                }
            )

        # DynamoDB integration: Mark scene as "processing" before generation starts
        if request.project_id and request.sequence:
            try:
                logger.info(
                    "marking_scene_as_processing",
                    project_id=request.project_id,
                    sequence=request.sequence
                )

                pk = f"PROJECT#{request.project_id}"
                sk = f"SCENE#{request.sequence:03d}"

                try:
                    scene_item = MVProjectItem.get(pk, sk)
                    scene_item.status = "processing"
                    scene_item.updatedAt = datetime.now(timezone.utc)
                    scene_item.save()

                    logger.info(
                        "scene_marked_as_processing",
                        project_id=request.project_id,
                        sequence=request.sequence
                    )
                except DoesNotExist:
                    logger.warning(
                        "scene_not_found_for_processing_status",
                        project_id=request.project_id,
                        sequence=request.sequence
                    )
                    # Don't fail the request, just log warning
            except Exception as e:
                # Log error but don't fail the request
                logger.error(
                    "failed_to_mark_scene_as_processing",
                    project_id=request.project_id,
                    sequence=request.sequence,
                    error=str(e),
                    exc_info=True
                )

        # Generate video
        video_id, video_path, video_url, metadata, character_reference_warning = generate_video(
            prompt=request.prompt.strip(),
            negative_prompt=request.negative_prompt.strip() if request.negative_prompt else None,
            aspect_ratio=request.aspect_ratio.strip() if request.aspect_ratio else None,
            duration=request.duration,
            generate_audio=request.generate_audio,
            seed=request.seed,
            character_reference_id=request.character_reference_id,
            reference_image_base64=request.reference_image_base64,
            video_rules_template=request.video_rules_template.strip() if request.video_rules_template else None,
            backend=request.backend or "replicate",
            config_flavor=request.config_flavor,
        )

        # DynamoDB integration: Update scene record if project_id and sequence provided
        if request.project_id and request.sequence:
            try:
                logger.info(
                    "updating_scene_with_video",
                    project_id=request.project_id,
                    sequence=request.sequence,
                    video_id=video_id
                )

                # Retrieve scene record
                pk = f"PROJECT#{request.project_id}"
                sk = f"SCENE#{request.sequence:03d}"

                try:
                    scene_item = MVProjectItem.get(pk, sk)
                except DoesNotExist:
                    logger.warning(
                        "scene_not_found_for_video_update",
                        project_id=request.project_id,
                        sequence=request.sequence
                    )
                    # Don't fail the request, just log warning
                else:
                    # Upload video to S3 if storage is configured
                    video_s3_key = None
                    if settings.STORAGE_BUCKET:
                        try:
                            s3_service = get_s3_storage_service()
                            video_s3_key = generate_scene_s3_key(
                                request.project_id,
                                request.sequence,
                                "video"
                            )
                            s3_service.upload_file_from_path(
                                video_path,
                                video_s3_key,
                                content_type="video/mp4"
                            )
                            logger.info(
                                "video_uploaded_to_s3",
                                project_id=request.project_id,
                                sequence=request.sequence,
                                s3_key=video_s3_key
                            )
                        except Exception as e:
                            logger.error(
                                "s3_upload_failed_for_scene",
                                project_id=request.project_id,
                                sequence=request.sequence,
                                error=str(e),
                                exc_info=True
                            )
                            # Continue without S3 key - will use local path

                    # Update scene record (validate S3 key to ensure it's not a URL)
                    # Only set S3 key if we have a valid one (S3 upload succeeded or S3 not configured)
                    if video_s3_key:
                        scene_item.videoClipS3Key = validate_s3_key(video_s3_key, "videoClipS3Key")
                    scene_item.videoGenerationJobId = video_id
                    # Only mark completed if S3 upload succeeded or S3 is not configured
                    if video_s3_key or not settings.STORAGE_BUCKET:
                        scene_item.status = "completed"
                    scene_item.updatedAt = datetime.now(timezone.utc)
                    scene_item.save()

                    # Update project counters
                    try:
                        increment_completed_scene(request.project_id)
                    except DoesNotExist:
                        logger.warning(
                            "project_not_found_for_counter_update",
                            project_id=request.project_id
                        )

                    logger.info(
                        "scene_updated_with_video",
                        project_id=request.project_id,
                        sequence=request.sequence,
                        video_s3_key=video_s3_key
                    )

            except Exception as e:
                # Log error but don't fail the request
                logger.error(
                    "dynamodb_update_failed_for_video",
                    project_id=request.project_id,
                    sequence=request.sequence,
                    error=str(e),
                    exc_info=True
                )

        response = GenerateVideoResponse(
            video_id=video_id,
            video_path=video_path,
            video_url=video_url,
            metadata=metadata,
            character_reference_warning=character_reference_warning
        )

        logger.info(
            "generate_video_request_completed",
            video_id=video_id,
            video_path=video_path,
            processing_time_seconds=metadata.get("processing_time_seconds"),
            backend_used=metadata.get("backend_used"),
            character_reference_warning=character_reference_warning,
            has_project_id=request.project_id is not None
        )

        return response

    except ValueError as e:
        # Handle configuration errors (e.g., missing API token)
        logger.error("generate_video_config_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ConfigurationError",
                "message": str(e),
                "details": "Check your environment configuration"
            }
        )

    except HTTPException:
        raise

    except TimeoutError as e:
        logger.error("generate_video_timeout", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ServiceTimeout",
                "message": str(e),
                "details": "Video generation service timed out"
            }
        )

    except Exception as e:
        logger.error("generate_video_unexpected_error", error=str(e), exc_info=True)

        # Update scene status to failed if project_id and sequence provided
        if request.project_id and request.sequence:
            try:
                pk = f"PROJECT#{request.project_id}"
                sk = f"SCENE#{request.sequence:03d}"
                scene_item = MVProjectItem.get(pk, sk)
                scene_item.status = "failed"
                scene_item.errorMessage = str(e)[:500]  # Limit error message length
                scene_item.updatedAt = datetime.now(timezone.utc)
                scene_item.save()

                # Update project counters
                try:
                    increment_failed_scene(request.project_id)
                except DoesNotExist:
                    logger.warning(
                        "project_not_found_for_failed_counter",
                        project_id=request.project_id
                    )

                logger.info(
                    "scene_marked_as_failed",
                    project_id=request.project_id,
                    sequence=request.sequence
                )
            except Exception as db_error:
                # Log but don't fail on DB update errors
                logger.error(
                    "failed_to_update_scene_status_on_error",
                    project_id=request.project_id,
                    sequence=request.sequence,
                    error=str(db_error),
                    exc_info=True
                )

        # Try to provide structured error information
        error_code = "UNKNOWN_ERROR"
        if "content" in str(e).lower() and "policy" in str(e).lower():
            error_code = "CONTENT_POLICY_VIOLATION"
        elif "rate" in str(e).lower() and "limit" in str(e).lower():
            error_code = "RATE_LIMIT_EXCEEDED"
        elif "authentication" in str(e).lower() or "auth" in str(e).lower():
            error_code = "AUTHENTICATION_ERROR"

        raise HTTPException(
            status_code=500,
            detail={
                "error": "VideoGenerationError",
                "error_code": error_code,
                "message": "An unexpected error occurred during video generation",
                "backend_used": request.backend or "replicate",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": str(e)
            }
        )


@router.get(
    "/get_video/{video_id}",
    responses={
        200: {"description": "Video URL or redirect", "content": {"application/json": {}}},
        404: {"description": "Video not found"}
    },
    summary="Retrieve Generated Video URL",
    description="""
Retrieve a generated video URL by its UUID.

**Cloud Storage (S3):**
- Returns JSON with presigned URL by default
- Use `?redirect=true` to get 302 redirect to video (for browsers)

**Local Storage:**
- Serves the video file directly

**Query Parameters:**
- `redirect` (optional): Set to "true" for 302 redirect instead of JSON

**Example:**
```
GET /api/mv/get_video/a1b2c3d4-e5f6-7890-abcd-ef1234567890
GET /api/mv/get_video/a1b2c3d4-e5f6-7890-abcd-ef1234567890?redirect=true
```
"""
)
async def get_video(video_id: str, redirect: bool = False):
    """
    Retrieve a generated video by ID.

    This endpoint:
    1. Validates the video_id format
    2. Checks SERVE_FROM_CLOUD config
    3. If enabled, generates presigned URL and redirects to cloud storage
    4. Otherwise, serves the video file from local storage

    The video is served with Content-Type: video/mp4 (local) or redirected to cloud URL.
    """
    # Validate video_id format (basic UUID validation)
    if not video_id or len(video_id) != 36 or video_id.count("-") != 4:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Invalid video_id format",
                "details": "video_id must be a valid UUID"
            }
        )
    
    # Check if we should serve from cloud storage
    if settings.SERVE_FROM_CLOUD and settings.STORAGE_BUCKET:
        logger.info(
            "get_video_attempting_cloud_serve",
            video_id=video_id,
            serve_from_cloud=settings.SERVE_FROM_CLOUD,
            storage_bucket=settings.STORAGE_BUCKET
        )
        try:
            from services.storage_backend import get_storage_backend, S3StorageBackend
            
            storage = get_storage_backend()
            cloud_path = f"mv/jobs/{video_id}/video.mp4"
            
            # Generate presigned URL (S3)
            # Note: We skip the exists() check for performance (21s -> <100ms)
            # If file doesn't exist, the presigned URL will return 404 when accessed
            if isinstance(storage, S3StorageBackend):
                presigned_url = storage.generate_presigned_url(
                    cloud_path,
                    expiry=settings.PRESIGNED_URL_EXPIRY
                )
                
                logger.info(
                    "get_video_url_generated",
                    video_id=video_id,
                    storage_backend="s3",
                    cloud_path=cloud_path,
                    redirect_mode=redirect
                )
                
                # Return JSON with URL by default, or redirect if requested
                if redirect:
                    return RedirectResponse(
                        url=presigned_url,
                        status_code=302
                    )
                else:
                    return JSONResponse(
                        content={
                            "video_id": video_id,
                            "video_url": presigned_url,
                            "storage_backend": "s3",
                            "expires_in_seconds": settings.PRESIGNED_URL_EXPIRY,
                            "cloud_path": cloud_path
                        },
                        status_code=200
                    )
            
            # Firebase: check existence then return public URL with token
            from services.storage_backend import FirebaseStorageBackend
            if isinstance(storage, FirebaseStorageBackend):
                # Firebase needs existence check as URLs are always valid
                exists = await storage.exists(cloud_path)
                
                if exists:
                    url = storage._get_public_url(cloud_path)
                    
                    logger.info(
                        "get_video_url_generated",
                        video_id=video_id,
                        storage_backend="firebase",
                        redirect_mode=redirect
                    )
                    
                    # Return JSON with URL by default, or redirect if requested
                    if redirect:
                        return RedirectResponse(
                            url=url,
                            status_code=302
                        )
                    else:
                        return JSONResponse(
                            content={
                                "video_id": video_id,
                                "video_url": url,
                                "storage_backend": "firebase",
                                "cloud_path": cloud_path
                            },
                            status_code=200
                        )
            
            # If video not in cloud or storage backend not supported, fall through to local serving
            logger.debug(
                "get_video_cloud_fallback_to_local",
                video_id=video_id,
                reason="not_in_cloud_or_unsupported_backend"
            )
            
        except Exception as e:
            # If cloud serving fails, fall back to local
            logger.warning(
                "get_video_cloud_error_fallback",
                video_id=video_id,
                error=str(e)
            )

    # Check if mock mode is enabled
    if settings.MOCK_VID_GENS:
        # In mock mode, serve from mock directory (return any available mock video)
        mock_dir = Path(__file__).parent.parent / "mv" / "outputs" / "mock"
        mock_videos = list(mock_dir.glob("*.mp4"))

        if not mock_videos:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NotFound",
                    "message": "No mock videos available",
                    "details": "Add .mp4 files to backend/mv/outputs/mock/ for mock mode"
                }
            )

        # Return first available mock video (in real scenario, could track which was assigned)
        video_path = mock_videos[0]
        logger.info("get_video_serving_mock", video_id=video_id, video_path=str(video_path))

        return FileResponse(
            path=str(video_path),
            media_type="video/mp4",
            filename=f"{video_id}.mp4"
        )

    # Normal mode: Construct video path
    video_dir = Path(__file__).parent.parent / "mv" / "outputs" / "videos"
    video_path = video_dir / f"{video_id}.mp4"

    if not video_path.exists():
        logger.warning("get_video_not_found", video_id=video_id)
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NotFound",
                "message": f"Video with ID {video_id} not found",
                "details": "The video may have been deleted or the ID is incorrect"
            }
        )

    logger.info("get_video_serving", video_id=video_id, video_path=str(video_path))

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"{video_id}.mp4"
    )


@router.get(
    "/get_video/{video_id}/info",
    responses={
        200: {"description": "Video metadata"},
        404: {"description": "Video not found"}
    },
    summary="Get Video Information",
    description="""
Get metadata about a generated video without downloading it.

Returns information like file size, creation time, and whether the file exists.

**Example Response:**
```json
{
    "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "file_size_bytes": 15234567,
    "created_at": "2025-11-16T10:30:25Z",
    "exists": true
}
```
"""
)
async def get_video_info(video_id: str):
    """
    Get metadata about a generated video.

    This endpoint:
    1. Validates the video_id format
    2. Checks if the video file exists
    3. Returns metadata about the video (size, creation time)
    """
    # Validate video_id format
    if not video_id or len(video_id) != 36 or video_id.count("-") != 4:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Invalid video_id format",
                "details": "video_id must be a valid UUID"
            }
        )

    # Check if mock mode is enabled
    if settings.MOCK_VID_GENS:
        mock_dir = Path(__file__).parent.parent / "mv" / "outputs" / "mock"
        mock_videos = list(mock_dir.glob("*.mp4"))

        if not mock_videos:
            return {
                "video_id": video_id,
                "exists": False,
                "file_size_bytes": None,
                "created_at": None,
                "is_mock": True
            }

        # Return info for first mock video
        video_path = mock_videos[0]
        stat = video_path.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()

        return {
            "video_id": video_id,
            "exists": True,
            "file_size_bytes": stat.st_size,
            "created_at": created_at,
            "is_mock": True
        }

    # Normal mode: Construct video path
    video_dir = Path(__file__).parent.parent / "mv" / "outputs" / "videos"
    video_path = video_dir / f"{video_id}.mp4"

    if not video_path.exists():
        return {
            "video_id": video_id,
            "exists": False,
            "file_size_bytes": None,
            "created_at": None
        }

    # Get file stats
    stat = video_path.stat()
    created_at = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()

    logger.info("get_video_info", video_id=video_id, file_size_bytes=stat.st_size)

    # Build base response
    response = {
        "video_id": video_id,
        "exists": True,
        "file_size_bytes": stat.st_size,
        "created_at": created_at,
        "serving_mode": "cloud" if settings.SERVE_FROM_CLOUD else "local"
    }
    
    # Add cloud URL if cloud storage is configured
    if settings.STORAGE_BUCKET:
        try:
            from services.storage_backend import get_storage_backend, S3StorageBackend
            
            storage = get_storage_backend()
            cloud_path = f"mv/jobs/{video_id}/video.mp4"
            
            # Check if video exists in cloud
            exists_in_cloud = await storage.exists(cloud_path)
            
            if exists_in_cloud:
                # Generate presigned URL for S3
                if isinstance(storage, S3StorageBackend):
                    presigned_url = storage.generate_presigned_url(
                        cloud_path,
                        expiry=settings.PRESIGNED_URL_EXPIRY
                    )
                    response["cloud_url"] = presigned_url
                    response["cloud_storage"] = {
                        "backend": "s3",
                        "expires_in_seconds": settings.PRESIGNED_URL_EXPIRY
                    }
                else:
                    # Firebase: get public URL with token
                    from services.storage_backend import FirebaseStorageBackend
                    if isinstance(storage, FirebaseStorageBackend):
                        url = storage._get_public_url(cloud_path)
                        response["cloud_url"] = url
                        response["cloud_storage"] = {
                            "backend": "firebase",
                            "expires_in_seconds": None  # Firebase tokens don't expire
                        }
            else:
                response["cloud_url"] = None
                response["cloud_storage"] = {
                    "status": "not_uploaded"
                }
                
        except Exception as e:
            logger.warning("get_video_info_cloud_error", video_id=video_id, error=str(e))
            response["cloud_url"] = None
            response["cloud_storage"] = {
                "status": "error",
                "error": str(e)
            }
    
    return response


@router.post(
    "/lipsync",
    response_model=LipsyncResponse,
    status_code=200,
    responses={
        200: {"description": "Lipsync video generated successfully"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error or API failure"},
        503: {"description": "Backend service unavailable"}
    },
    summary="Generate Lipsync Video",
    description="""
Generate a lip-synced video by syncing audio to a video scene using Sync Labs' Lipsync-2-Pro model.

**IMPORTANT: This is a synchronous endpoint that may take 20-300+ seconds to complete.**

This endpoint takes a video URL (scene) and an audio URL, then generates a lip-synced version
where the video's lip movements match the provided audio track.

**Database Integration:**
- If `project_id` and `sequence` are provided together, the endpoint will:
  - Mark the scene as "processing" before lipsync starts
  - Update the scene record with lipsynced video S3 key and job ID on success
  - Mark the scene as "completed" when lipsynced video is ready
  - Mark the scene as "failed" if lipsync fails
  - Upload lipsynced video to S3 if storage is configured

**Limitations:**
- Synchronous processing (20-300s response times)
- No progress tracking (client waits for completion)
- File-based storage (videos saved with UUID filenames)
- Requires Scale plan or higher for Replicate API access

**Required Fields:**
- video_url: URL to the video file (scene) - supports MP4, MOV, WEBM, M4V, GIF
- audio_url: URL to the audio file - supports MP3, OGG, WAV, M4A, AAC

**Optional Fields:**
- temperature: Control expressiveness of lip movements (0.0 = subtle, 1.0 = exaggerated)
- occlusion_detection_enabled: Enable for complex scenes with obstructions (may slow processing)
- active_speaker_detection: Auto-detect active speaker in multi-person videos
- project_id: Project UUID for DynamoDB integration (requires sequence)
- sequence: Scene sequence number for DynamoDB integration (requires project_id)

**Best Practices:**
- Ensure input video shows the speaker actively talking for natural speaking motion
- For AI-generated videos, include a text prompt like "person is speaking naturally"
- Use occlusion_detection_enabled for scenes with partial face obstructions
"""
)
async def lipsync_video(request: LipsyncRequest):
    """
    Generate a lip-synced video.

    This endpoint:
    1. Validates the request parameters
    2. Calls Replicate's Lipsync-2-Pro model with video and audio URLs
    3. Saves the result to filesystem with UUID-based filename
    4. Returns video ID, path, URL, and metadata

    **Example Request:**
    ```json
    {
        "video_url": "https://example.com/scene.mp4",
        "audio_url": "https://example.com/audio.mp3",
        "temperature": 0.5,
        "active_speaker_detection": true
    }
    ```

    **Example Response:**
    ```json
    {
        "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "video_path": "/path/to/lipsync/a1b2c3d4...mp4",
        "video_url": "/api/mv/get_video/a1b2c3d4...",
        "metadata": {
            "video_url": "https://example.com/scene.mp4",
            "audio_url": "https://example.com/audio.mp3",
            "model_used": "sync/lipsync-2-pro",
            "parameters_used": {
                "temperature": 0.5,
                "active_speaker_detection": true
            },
            "generation_timestamp": "2025-11-16T10:30:25Z",
            "processing_time_seconds": 45.7,
            "file_size_bytes": 15234567
        }
    }
    ```
    """
    try:
        logger.info(
            "lipsync_request_received",
            video_url=request.video_url[:100] + "..." if request.video_url and len(request.video_url) > 100 else request.video_url,
            audio_url=request.audio_url[:100] + "..." if request.audio_url and len(request.audio_url) > 100 else request.audio_url,
            video_id=request.video_id,
            audio_id=request.audio_id,
            start_time=request.start_time,
            end_time=request.end_time,
            temperature=request.temperature,
            occlusion_detection_enabled=request.occlusion_detection_enabled,
            active_speaker_detection=request.active_speaker_detection
        )

        # Validate required fields - either URL or ID must be provided
        if not request.video_url and not request.video_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Either video_url or video_id is required",
                    "details": "Provide either 'video_url' or 'video_id' parameter"
                }
            )

        if not request.audio_url and not request.audio_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Either audio_url or audio_id is required",
                    "details": "Provide either 'audio_url' or 'audio_id' parameter"
                }
            )

        # Validate time parameters if provided
        if request.start_time is not None and request.end_time is not None:
            if request.end_time <= request.start_time:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "end_time must be greater than start_time",
                        "details": f"start_time={request.start_time}, end_time={request.end_time}"
                    }
                )

        # Validate project_id and sequence are provided together
        if (request.project_id and not request.sequence) or (request.sequence and not request.project_id):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "project_id and sequence must be provided together",
                    "details": "Both project_id and sequence are required for DynamoDB integration"
                }
            )

        # DynamoDB integration: Mark scene as "processing" before lipsync starts
        if request.project_id and request.sequence:
            try:
                logger.info(
                    "marking_scene_as_processing_for_lipsync",
                    project_id=request.project_id,
                    sequence=request.sequence
                )

                pk = f"PROJECT#{request.project_id}"
                sk = f"SCENE#{request.sequence:03d}"

                try:
                    scene_item = MVProjectItem.get(pk, sk)
                    scene_item.status = "processing"
                    scene_item.updatedAt = datetime.now(timezone.utc)
                    scene_item.save()

                    logger.info(
                        "scene_marked_as_processing_for_lipsync",
                        project_id=request.project_id,
                        sequence=request.sequence
                    )
                except DoesNotExist:
                    logger.warning(
                        "scene_not_found_for_lipsync_processing_status",
                        project_id=request.project_id,
                        sequence=request.sequence
                    )
                    # Don't fail the request, just log warning
            except Exception as e:
                # Log error but don't fail the request
                logger.error(
                    "failed_to_mark_scene_as_processing_for_lipsync",
                    project_id=request.project_id,
                    sequence=request.sequence,
                    error=str(e),
                    exc_info=True
                )

        # Generate lipsync video
        video_id, video_path, video_url, metadata = generate_lipsync(
            video_url=request.video_url.strip() if request.video_url else None,
            audio_url=request.audio_url.strip() if request.audio_url else None,
            video_id=request.video_id,
            audio_id=request.audio_id,
            start_time=request.start_time,
            end_time=request.end_time,
            temperature=request.temperature,
            occlusion_detection_enabled=request.occlusion_detection_enabled,
            active_speaker_detection=request.active_speaker_detection,
        )

        # DynamoDB integration: Update scene record if project_id and sequence provided
        if request.project_id and request.sequence:
            try:
                logger.info(
                    "updating_scene_with_lipsync",
                    project_id=request.project_id,
                    sequence=request.sequence,
                    video_id=video_id
                )

                # Retrieve scene record
                pk = f"PROJECT#{request.project_id}"
                sk = f"SCENE#{request.sequence:03d}"

                try:
                    scene_item = MVProjectItem.get(pk, sk)
                except DoesNotExist:
                    logger.warning(
                        "scene_not_found_for_lipsync_update",
                        project_id=request.project_id,
                        sequence=request.sequence
                    )
                    # Don't fail the request, just log warning
                else:
                    # Upload lipsynced video to S3 if storage is configured
                    lipsync_s3_key = None
                    if settings.STORAGE_BUCKET:
                        try:
                            s3_service = get_s3_storage_service()
                            lipsync_s3_key = generate_scene_s3_key(
                                request.project_id,
                                request.sequence,
                                "lipsynced"
                            )
                            s3_service.upload_file_from_path(
                                video_path,
                                lipsync_s3_key,
                                content_type="video/mp4"
                            )
                            logger.info(
                                "lipsync_video_uploaded_to_s3",
                                project_id=request.project_id,
                                sequence=request.sequence,
                                s3_key=lipsync_s3_key
                            )
                        except Exception as e:
                            logger.error(
                                "s3_upload_failed_for_lipsync",
                                project_id=request.project_id,
                                sequence=request.sequence,
                                error=str(e),
                                exc_info=True
                            )
                            # Continue without S3 key - will use local path

                    # Update scene record (validate S3 key to ensure it's not a URL)
                    # Only set S3 key if we have a valid one (S3 upload succeeded or S3 not configured)
                    if lipsync_s3_key:
                        scene_item.lipSyncedVideoClipS3Key = validate_s3_key(lipsync_s3_key, "lipSyncedVideoClipS3Key")
                    scene_item.lipsyncJobId = video_id
                    # Only mark completed if S3 upload succeeded or S3 is not configured
                    # Keep existing completed status if already completed
                    if lipsync_s3_key or not settings.STORAGE_BUCKET:
                        if scene_item.status != "completed":
                            scene_item.status = "completed"
                    scene_item.updatedAt = datetime.now(timezone.utc)
                    scene_item.save()

                    logger.info(
                        "scene_updated_with_lipsync",
                        project_id=request.project_id,
                        sequence=request.sequence,
                        lipsync_s3_key=lipsync_s3_key
                    )

            except Exception as e:
                # Log error but don't fail the request
                logger.error(
                    "dynamodb_update_failed_for_lipsync",
                    project_id=request.project_id,
                    sequence=request.sequence,
                    error=str(e),
                    exc_info=True
                )

        response = LipsyncResponse(
            video_id=video_id,
            video_path=video_path,
            video_url=video_url,
            metadata=metadata
        )

        logger.info(
            "lipsync_request_completed",
            video_id=video_id,
            video_path=video_path,
            processing_time_seconds=metadata.get("processing_time_seconds"),
            file_size_bytes=metadata.get("file_size_bytes"),
            has_project_id=request.project_id is not None
        )

        return response

    except ValueError as e:
        # Handle configuration errors (e.g., missing API token)
        logger.error("lipsync_config_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ConfigurationError",
                "message": str(e),
                "details": "Check your environment configuration"
            }
        )

    except HTTPException:
        raise

    except TimeoutError as e:
        logger.error("lipsync_timeout", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ServiceTimeout",
                "message": str(e),
                "details": "Lipsync generation service timed out"
            }
        )

    except Exception as e:
        logger.error("lipsync_unexpected_error", error=str(e), exc_info=True)

        # Update scene status to failed if project_id and sequence provided
        if request.project_id and request.sequence:
            try:
                pk = f"PROJECT#{request.project_id}"
                sk = f"SCENE#{request.sequence:03d}"
                scene_item = MVProjectItem.get(pk, sk)
                scene_item.status = "failed"
                scene_item.errorMessage = str(e)[:500]  # Limit error message length
                scene_item.updatedAt = datetime.now(timezone.utc)
                scene_item.save()

                # Update project counters
                try:
                    increment_failed_scene(request.project_id)
                except DoesNotExist:
                    logger.warning(
                        "project_not_found_for_failed_counter_lipsync",
                        project_id=request.project_id
                    )

                logger.info(
                    "scene_marked_as_failed_lipsync",
                    project_id=request.project_id,
                    sequence=request.sequence
                )
            except Exception as db_error:
                # Log but don't fail on DB update errors
                logger.error(
                    "failed_to_update_scene_status_on_lipsync_error",
                    project_id=request.project_id,
                    sequence=request.sequence,
                    error=str(db_error),
                    exc_info=True
                )

        # Try to provide structured error information
        error_code = "UNKNOWN_ERROR"
        if "content" in str(e).lower() and "policy" in str(e).lower():
            error_code = "CONTENT_POLICY_VIOLATION"
        elif "rate" in str(e).lower() and "limit" in str(e).lower():
            error_code = "RATE_LIMIT_EXCEEDED"
        elif "authentication" in str(e).lower() or "auth" in str(e).lower():
            error_code = "AUTHENTICATION_ERROR"
        elif "plan" in str(e).lower() or "scale" in str(e).lower():
            error_code = "PLAN_REQUIREMENT_ERROR"

        raise HTTPException(
            status_code=500,
            detail={
                "error": "LipsyncGenerationError",
                "error_code": error_code,
                "message": "An unexpected error occurred during lipsync generation",
                "model_used": "sync/lipsync-2-pro",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": str(e)
            }
        )


@router.post(
    "/stitch-videos",
    response_model=StitchVideosResponse,
    status_code=200,
    responses={
        200: {"description": "Videos stitched successfully"},
        400: {"description": "Invalid request parameters"},
        404: {"description": "One or more videos not found"},
        500: {"description": "Internal server error"}
    },
    summary="Stitch Multiple Videos",
    description="""
Stitch multiple video clips into a single video using MoviePy.

**IMPORTANT: This is a synchronous endpoint that may take 30-300+ seconds depending on video count and size.**

This endpoint takes a list of video UUIDs and merges them in the specified order
into a single video file. Supports both local filesystem and S3 storage backends.

**Limitations:**
- Synchronous processing (may take several minutes)
- All videos must exist (fails if any video is missing)
- Videos are concatenated without transitions
- Output uses libx264 codec with AAC audio

**Required Fields:**
- video_ids: List of video UUIDs to stitch together (in order)

**Storage Backend Behavior:**
- SERVE_FROM_CLOUD=false: Reads from and writes to local filesystem
- SERVE_FROM_CLOUD=true: Downloads from S3, stitches locally, uploads result to S3
"""
)
async def stitch_videos_endpoint(request: StitchVideosRequest):
    """
    Stitch multiple video clips into a single video.

    This endpoint:
    1. Validates the video IDs
    2. Retrieves videos (from local or S3)
    3. Merges videos using MoviePy
    4. Saves to appropriate storage (local or S3)
    5. Returns video ID, path, URL, and metadata

    **Example Request:**
    ```json
    {
        "video_ids": [
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "c3d4e5f6-a7b8-9012-cdef-234567890123"
        ]
    }
    ```

    **Example Response:**
    ```json
    {
        "video_id": "d4e5f6a7-b8c9-0123-def1-345678901234",
        "video_path": "/path/to/stitched/d4e5f6a7...mp4",
        "video_url": "https://s3.amazonaws.com/..." or "/api/mv/get_video/d4e5f6a7...",
        "metadata": {
            "input_video_ids": [...],
            "num_videos_stitched": 3,
            "merge_time_seconds": 45.2,
            "total_processing_time_seconds": 120.5,
            "generation_timestamp": "2025-11-16T10:30:25Z",
            "storage_backend": "s3"
        }
    }
    ```
    """
    try:
        logger.info(
            "stitch_videos_request_received",
            video_ids=request.video_ids,
            num_videos=len(request.video_ids),
            audio_overlay_id=request.audio_overlay_id,
            suppress_video_audio=request.suppress_video_audio
        )

        # Validate request
        if not request.video_ids:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "video_ids list cannot be empty",
                    "details": "Provide at least one video ID to stitch"
                }
            )

        # Validate UUID format for each video_id
        for video_id in request.video_ids:
            if not video_id or len(video_id) != 36 or video_id.count("-") != 4:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": f"Invalid video_id format: {video_id}",
                        "details": "All video_ids must be valid UUIDs"
                    }
                )

        # Validate audio_overlay_id format if provided
        if request.audio_overlay_id:
            if len(request.audio_overlay_id) != 36 or request.audio_overlay_id.count("-") != 4:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": f"Invalid audio_overlay_id format: {request.audio_overlay_id}",
                        "details": "audio_overlay_id must be a valid UUID"
                    }
                )

        # Stitch videos with optional audio overlay
        video_id, video_path, video_url, metadata, audio_overlay_applied, audio_overlay_warning = stitch_videos(
            video_ids=request.video_ids,
            audio_overlay_id=request.audio_overlay_id,
            suppress_video_audio=request.suppress_video_audio or False
        )

        response = StitchVideosResponse(
            video_id=video_id,
            video_path=video_path,
            video_url=video_url,
            metadata=metadata,
            audio_overlay_applied=audio_overlay_applied,
            audio_overlay_warning=audio_overlay_warning
        )

        logger.info(
            "stitch_videos_request_completed",
            video_id=video_id,
            num_videos_stitched=len(request.video_ids),
            total_processing_time_seconds=metadata.get("total_processing_time_seconds"),
            storage_backend=metadata.get("storage_backend"),
            audio_overlay_applied=audio_overlay_applied
        )

        return response

    except FileNotFoundError as e:
        logger.error("stitch_videos_not_found", error=str(e))
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NotFound",
                "message": str(e),
                "details": "One or more videos could not be found. Ensure all video IDs exist."
            }
        )

    except ValueError as e:
        logger.error("stitch_videos_validation_error", error=str(e))
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "details": "Invalid request parameters"
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("stitch_videos_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "StitchingError",
                "message": "An unexpected error occurred during video stitching",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": str(e)
            }
        )
