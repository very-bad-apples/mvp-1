"""
Music Video (MV) endpoint router.

Handles scene generation and related music video pipeline operations.
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException
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
    generate_s3_key,
    generate_scene_s3_key,
    validate_s3_key,
)
from pynamodb.exceptions import DoesNotExist, PutError

logger = structlog.get_logger()

router = APIRouter(prefix="/api/mv", tags=["Music Video"])


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
            
            # S3: Generate presigned URL without exists() check (performance optimization)
            # Note: We skip the exists() check for performance (like video endpoint)
            # If file doesn't exist, the presigned URL will return 404 when accessed
            if isinstance(storage, S3StorageBackend):
                # Default to png, but will work with any extension in S3
                cloud_path = f"character_references/{image_id}.png"
                
                presigned_url = storage.generate_presigned_url(
                    cloud_path,
                    expiry=settings.PRESIGNED_URL_EXPIRY
                )
                
                logger.info(
                    "get_character_reference_url_generated",
                    image_id=image_id,
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
                            "image_id": image_id,
                            "image_url": presigned_url,
                            "storage_backend": "s3",
                            "expires_in_seconds": settings.PRESIGNED_URL_EXPIRY,
                            "cloud_path": cloud_path
                        },
                        status_code=200
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

**Two Usage Modes:**

1. **Direct URLs Mode:**
   - Provide `video_url` and `audio_url` directly
   - URLs can be HTTP/HTTPS URLs or S3 presigned URLs
   - No DynamoDB integration

2. **DynamoDB Mode (Recommended):**
   - Provide `project_id` and `sequence` (scene number)
   - Endpoint automatically fetches:
     - Audio from `project.audioBackingTrackS3Key` (from YouTube URL or uploaded audio)
     - Video from `scene.videoClipS3Key` (generated scene video)
   - Generates presigned URLs and sends to Replicate
   - Saves result to `scene.lipSyncedVideoClipS3Key` in DynamoDB

**Database Integration:**
- If `project_id` and `sequence` are provided together, the endpoint will:
  - Fetch audio S3 key from project metadata
  - Fetch video S3 key from scene record
  - Generate presigned URLs from S3 keys
  - Mark the scene as "processing" before lipsync starts
  - Update the scene record with lipsynced video S3 key and job ID on success
  - Mark the scene as "completed" when lipsynced video is ready
  - Mark the scene as "failed" if lipsync fails
  - Upload lipsynced video to S3 if storage is configured

**Limitations:**
- Synchronous processing (20-300s response times)
- No progress tracking (client waits for completion)
- Requires Scale plan or higher for Replicate API access

**Required Fields (choose one mode):**
- Mode 1: `video_url` + `audio_url` (direct URLs)
- Mode 2: `project_id` + `sequence` (fetch from DynamoDB)

**Optional Fields:**
- temperature: Control expressiveness of lip movements (0.0 = subtle, 1.0 = exaggerated)
- occlusion_detection_enabled: Enable for complex scenes with obstructions (may slow processing)
- active_speaker_detection: Auto-detect active speaker in multi-person videos

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
            video_url=request.video_url[:100] + "..." if len(request.video_url) > 100 else request.video_url,
            audio_url=request.audio_url[:100] + "..." if len(request.audio_url) > 100 else request.audio_url,
            temperature=request.temperature,
            occlusion_detection_enabled=request.occlusion_detection_enabled,
            active_speaker_detection=request.active_speaker_detection
        )

        # Determine video_url and audio_url
        video_url = None
        audio_url = None
        
        # If project_id and sequence provided, fetch from DynamoDB
        if request.project_id and request.sequence:
            try:
                # Fetch project and scene from DynamoDB
                pk = f"PROJECT#{request.project_id}"
                
                # Get project for audio
                try:
                    project_item = MVProjectItem.get(pk, "METADATA")
                    if not project_item.audioBackingTrackS3Key:
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": "ValidationError",
                                "message": "Project audio not found",
                                "details": "Project does not have audioBackingTrackS3Key. Please ensure audio was uploaded when creating the project."
                            }
                        )
                except DoesNotExist:
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "NotFound",
                            "message": f"Project {request.project_id} not found",
                            "details": "The specified project does not exist in the database"
                        }
                    )
                
                # Get scene for video
                sk = f"SCENE#{request.sequence:03d}"
                try:
                    scene_item = MVProjectItem.get(pk, sk)
                    if not scene_item.videoClipS3Key:
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": "ValidationError",
                                "message": "Scene video not found",
                                "details": f"Scene {request.sequence} does not have videoClipS3Key. Please generate the video first."
                            }
                        )
                except DoesNotExist:
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "NotFound",
                            "message": f"Scene {request.sequence} not found for project {request.project_id}",
                            "details": "The specified scene does not exist in the database"
                        }
                    )
                
                # Generate presigned URLs from S3 keys
                from services.s3_storage import get_s3_storage_service
                s3_service = get_s3_storage_service()
                
                audio_url = s3_service.generate_presigned_url(project_item.audioBackingTrackS3Key)
                video_url = s3_service.generate_presigned_url(scene_item.videoClipS3Key)
                
                logger.info(
                    "lipsync_urls_from_dynamodb",
                    project_id=request.project_id,
                    sequence=request.sequence,
                    audio_s3_key=project_item.audioBackingTrackS3Key,
                    video_s3_key=scene_item.videoClipS3Key
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "failed_to_fetch_urls_from_dynamodb",
                    project_id=request.project_id,
                    sequence=request.sequence,
                    error=str(e),
                    exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "InternalError",
                        "message": "Failed to fetch audio/video URLs from DynamoDB",
                        "details": str(e)
                    }
                )
        else:
            # Use provided URLs directly
            if not request.video_url or not request.video_url.strip():
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "Video URL is required",
                        "details": "Either provide video_url and audio_url, or provide project_id and sequence to fetch from DynamoDB"
                    }
                )

            if not request.audio_url or not request.audio_url.strip():
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "Audio URL is required",
                        "details": "Either provide video_url and audio_url, or provide project_id and sequence to fetch from DynamoDB"
                    }
                )
            
            video_url = request.video_url.strip()
            audio_url = request.audio_url.strip()

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

        # Generate lipsync video (uploads directly to S3, returns S3 URLs)
        video_id, video_s3_url, audio_s3_url, audio_s3_key, metadata = generate_lipsync(
            video_url=video_url,
            audio_url=audio_url,
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
                    # Extract S3 key from S3 URL (if it's a presigned URL, we need the key)
                    # The video is already uploaded to mv/jobs/{video_id}/lipsync.mp4
                    # For DynamoDB, we can optionally copy to scene-specific path or use the generic path
                    lipsync_s3_key = None
                    if settings.STORAGE_BUCKET:
                        try:
                            # Use scene-specific S3 key for better organization
                            scene_s3_key = generate_scene_s3_key(
                                request.project_id,
                                request.sequence,
                                "lipsynced"
                            )
                            
                            # Use S3 server-side copy (no download/upload needed)
                            from services.storage_backend import get_storage_backend
                            import asyncio
                            import concurrent.futures
                            
                            async def copy_to_scene_path():
                                storage = get_storage_backend()
                                generic_path = f"mv/jobs/{video_id}/lipsync.mp4"
                                
                                # Direct S3-to-S3 copy (fast, no temp files)
                                await storage.copy_file(generic_path, scene_s3_key)
                                
                                return scene_s3_key
                            
                            def run_copy():
                                return asyncio.run(copy_to_scene_path())
                            
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(run_copy)
                                lipsync_s3_key = future.result(timeout=120)  # 2 min timeout
                            
                            logger.info(
                                "lipsync_video_copied_to_scene_path",
                                project_id=request.project_id,
                                sequence=request.sequence,
                                s3_key=lipsync_s3_key
                            )
                        except Exception as e:
                            logger.warning(
                                "lipsync_copy_to_scene_path_failed",
                                project_id=request.project_id,
                                sequence=request.sequence,
                                error=str(e)
                            )
                            # Continue without scene-specific path - generic path is still available

                    # Update scene record with S3 keys (only existing fields, no new fields)
                    if lipsync_s3_key:
                        scene_item.lipSyncedVideoClipS3Key = validate_s3_key(lipsync_s3_key, "lipSyncedVideoClipS3Key")
                    
                    scene_item.lipsyncJobId = video_id
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
            video_url=video_s3_url,
            audio_url=audio_s3_url,
            metadata=metadata
        )

        logger.info(
            "lipsync_request_completed",
            video_id=video_id,
            video_s3_url=video_s3_url[:100] + "..." if len(video_s3_url) > 100 else video_s3_url,
            audio_s3_url=audio_s3_url[:100] + "..." if len(audio_s3_url) > 100 else audio_s3_url,
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
