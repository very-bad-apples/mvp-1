"""
Music Video (MV) endpoint router.

Handles scene generation and related music video pipeline operations.
"""

import os
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
from config import settings

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

**Limitations:**
- Synchronous processing (may take 10-30+ seconds)
- File-based storage (scenes saved to filesystem)

**Required Fields:**
- idea: The core concept or topic of the video
- character_description: Visual description of the main character

**Optional Fields (defaults from config):**
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
    2. Applies defaults from YAML config for optional fields
    3. Generates scene prompts using Gemini 2.5 Pro
    4. Saves scenes to files (JSON and Markdown)
    5. Returns the generated scenes and file paths

    **Example Request:**
    ```json
    {
        "idea": "Tourist exploring Austin, Texas",
        "character_description": "Silver metallic humanoid robot with a red shield"
    }
    ```

    **Example Response:**
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
        200: {"description": "Character reference image generated successfully"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error or API failure"}
    },
    summary="Generate Character Reference Image",
    description="""
Generate a character reference image using Google Imagen 4 via Replicate API.

This endpoint creates a full-body character reference image based on a visual
description, suitable for maintaining character consistency across video scenes.

**Limitations:**
- Synchronous processing (may take 10-60+ seconds)
- File-based storage (images saved to filesystem)
- Large response size (base64 encoded image)

**Required Fields:**
- character_description: Visual description of the character

**Optional Fields (defaults from config):**
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
    Generate a character reference image.

    This endpoint:
    1. Validates the request parameters
    2. Applies defaults from YAML config for optional fields
    3. Generates image using Replicate API with Google Imagen 4
    4. Saves image to files with timestamp-based filename
    5. Returns base64-encoded image, file path, and metadata

    **Example Request:**
    ```json
    {
        "character_description": "Silver metallic humanoid robot with a red shield"
    }
    ```

    **Example Response:**
    ```json
    {
        "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
        "output_file": "/path/to/character_ref_20251115_143025.png",
        "metadata": {
            "character_description": "Silver metallic humanoid robot...",
            "model_used": "google/imagen-4",
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

        # Generate character reference image
        image_base64, output_file, metadata = generate_character_reference_image(
            character_description=request.character_description.strip(),
            aspect_ratio=request.aspect_ratio.strip() if request.aspect_ratio else None,
            safety_filter_level=request.safety_filter_level.strip() if request.safety_filter_level else None,
            person_generation=request.person_generation.strip() if request.person_generation else None,
            output_format=request.output_format.strip() if request.output_format else None,
            negative_prompt=request.negative_prompt.strip() if request.negative_prompt else None,
            seed=request.seed,
        )

        response = GenerateCharacterReferenceResponse(
            image_base64=image_base64,
            output_file=output_file,
            metadata=metadata
        )

        logger.info(
            "generate_character_reference_request_completed",
            output_file=output_file,
            image_size_bytes=len(image_base64)
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
            has_reference_image=request.reference_image_base64 is not None
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

        # Generate video
        video_id, video_path, video_url, metadata = generate_video(
            prompt=request.prompt.strip(),
            negative_prompt=request.negative_prompt.strip() if request.negative_prompt else None,
            aspect_ratio=request.aspect_ratio.strip() if request.aspect_ratio else None,
            duration=request.duration,
            generate_audio=request.generate_audio,
            seed=request.seed,
            reference_image_base64=request.reference_image_base64,
            video_rules_template=request.video_rules_template.strip() if request.video_rules_template else None,
            backend=request.backend or "replicate",
        )

        response = GenerateVideoResponse(
            video_id=video_id,
            video_path=video_path,
            video_url=video_url,
            metadata=metadata
        )

        logger.info(
            "generate_video_request_completed",
            video_id=video_id,
            video_path=video_path,
            processing_time_seconds=metadata.get("processing_time_seconds"),
            backend_used=metadata.get("backend_used")
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
