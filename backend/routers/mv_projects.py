"""
Music Video Projects API Router.

Implements CRUD endpoints for project management with DynamoDB.
"""

import uuid
import asyncio
import re
import structlog
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional, List

# File upload validation constants
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav"}

from mv_schemas import (
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectResponse,
    ProjectUpdateRequest,
    ComposeRequest,
    ComposeResponse,
    FinalVideoResponse,
    SceneResponse
)
from mv_models import (
    MVProjectItem,
    create_project_metadata,
    create_scene_item
)
from services.s3_storage import (
    get_s3_storage_service,
    generate_s3_key
)
from pynamodb.exceptions import DoesNotExist, PutError

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
        images: Optional list of product images
        audio: Optional audio file

    Returns:
        ProjectCreateResponse with project ID
    """
    logger.info(
        "create_project_request",
        mode=mode,
        has_images=bool(images),
        has_audio=audio is not None,
        has_character_ref=characterReferenceImageId is not None
    )

    # Validate input lengths and content (Pydantic model not used with Form fields)
    # Sanitize inputs: strip whitespace and remove control characters
    prompt = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', prompt.strip())
    characterDescription = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', characterDescription.strip())
    if productDescription:
        productDescription = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', productDescription.strip())

    if not prompt or len(prompt) < 10:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Prompt too short",
                "details": "Prompt must be at least 10 characters"
            }
        )
    if not characterDescription or len(characterDescription) < 20:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Character description too short",
                "details": "Character description must be at least 20 characters"
            }
        )
    if len(prompt) > 2000:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Prompt too long",
                "details": "Maximum length is 2000 characters"
            }
        )
    if len(characterDescription) > 1000:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Character description too long",
                "details": "Maximum length is 1000 characters"
            }
        )
    if productDescription and len(productDescription) > 1000:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ValidationError",
                "message": "Product description too long",
                "details": "Maximum length is 1000 characters"
            }
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

    # Generate project ID (canonical UUID format)
    project_id = str(uuid.uuid4())
    s3_service = get_s3_storage_service()

    # Track uploaded files for cleanup on failure
    uploaded_keys = []
    cleanup_needed = False

    try:
        # Upload files to S3
        character_image_s3_key = None
        product_image_s3_key = None
        audio_s3_key = None

        # Handle character reference image
        if characterReferenceImageId:
            # Validate UUID format to prevent path traversal attacks
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
            # Validate character reference exists
            # TODO: Add ownership validation when authentication is implemented
            # Currently accepts any existing character reference (acceptable for MVP)
            # UUID validation above ensures no path traversal in ID
            source_key = f"mv/outputs/character_reference/{characterReferenceImageId}.png"
            try:
                # Use async wrapper for S3 operation to avoid blocking event loop
                file_exists = await asyncio.to_thread(s3_service.file_exists, source_key)
                if not file_exists:
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "NotFound",
                            "message": f"Character reference {characterReferenceImageId} not found",
                            "details": "The specified character image does not exist"
                        }
                    )
            except HTTPException:
                raise
            except Exception as s3_error:
                logger.error("s3_validation_failed", error=str(s3_error), source_key=source_key)
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "ServiceUnavailable",
                        "message": "Unable to validate character reference",
                        "details": "Storage service temporarily unavailable"
                    }
                )
            character_image_s3_key = source_key
            logger.info(
                "character_reference_used",
                project_id=project_id,
                character_ref_id=characterReferenceImageId,
                s3_key=character_image_s3_key
            )

        # Upload product images with validation
        if images and len(images) > 0:
            # For simplicity, use first image as primary
            product_image = images[0]

            # Read file content once for both size check and upload
            file_content = await product_image.read()
            file_size = len(file_content)

            if file_size > MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "Image file too large",
                        "details": f"Maximum size is {MAX_IMAGE_SIZE / (1024*1024)}MB"
                    }
                )

            # Validate content type
            content_type = product_image.content_type or "image/jpeg"
            if content_type not in ALLOWED_IMAGE_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "Invalid image format",
                        "details": f"Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
                    }
                )

            # Generate S3 key with proper file extension
            # Don't use user-supplied filename - derive extension from content type only
            # This prevents any path traversal or filename-based attacks
            # TODO: Add magic number validation (PIL/python-magic) to verify actual file format
            # Currently trusts Content-Type header which can be spoofed (acceptable for MVP)
            if 'png' in content_type:
                file_ext = '.png'
            elif 'webp' in content_type:
                file_ext = '.webp'
            else:
                file_ext = '.jpg'

            # Generate S3 key with server-controlled extension
            base_key = generate_s3_key(project_id, "product")
            product_image_s3_key = str(Path(base_key).with_suffix(file_ext))

            # Upload in thread pool to avoid blocking event loop
            buffer = BytesIO(file_content)
            try:
                await asyncio.to_thread(
                    s3_service.upload_file,
                    buffer,
                    product_image_s3_key,
                    content_type=content_type
                )
            finally:
                buffer.close()
            uploaded_keys.append(product_image_s3_key)
            cleanup_needed = True

            logger.info(
                "product_image_uploaded",
                project_id=project_id,
                s3_key=product_image_s3_key,
                size=file_size
            )

        # Upload audio file with validation
        if audio:
            # Read file content once for both size check and upload
            file_content = await audio.read()
            file_size = len(file_content)

            if file_size > MAX_AUDIO_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "Audio file too large",
                        "details": f"Maximum size is {MAX_AUDIO_SIZE / (1024*1024)}MB"
                    }
                )

            # Validate content type
            content_type = audio.content_type or "audio/mpeg"
            if content_type not in ALLOWED_AUDIO_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": "Invalid audio format",
                        "details": f"Allowed types: {', '.join(ALLOWED_AUDIO_TYPES)}"
                    }
                )

            # Generate S3 key with proper file extension
            # Don't use user-supplied filename - derive extension from content type only
            # This prevents any path traversal or filename-based attacks
            # TODO: Add magic number validation to verify actual file format
            # Currently trusts Content-Type header which can be spoofed (acceptable for MVP)
            if 'wav' in content_type:
                file_ext = '.wav'
            else:
                file_ext = '.mp3'

            # Generate S3 key with server-controlled extension
            base_key = generate_s3_key(project_id, "audio")
            audio_s3_key = str(Path(base_key).with_suffix(file_ext))

            # Upload in thread pool to avoid blocking event loop
            buffer = BytesIO(file_content)
            try:
                await asyncio.to_thread(
                    s3_service.upload_file,
                    buffer,
                    audio_s3_key,
                    content_type=content_type
                )
            finally:
                buffer.close()
            uploaded_keys.append(audio_s3_key)
            cleanup_needed = True

            logger.info(
                "audio_uploaded",
                project_id=project_id,
                s3_key=audio_s3_key,
                size=file_size
            )

        # Create project metadata in DynamoDB
        project = create_project_metadata(
            project_id=project_id,
            concept_prompt=prompt,
            character_description=characterDescription,
            product_description=productDescription,
            character_image_s3_key=character_image_s3_key,
            product_image_s3_key=product_image_s3_key,
            audio_backing_track_s3_key=audio_s3_key
        )

        # Ensure status is explicitly set to pending with GSI attributes
        # Always set GSI attributes for consistency (even if status is already pending)
        project.status = "pending"
        project.GSI1PK = "pending"
        project.GSI1SK = project.createdAt.isoformat()  # Required for GSI queries

        try:
            project.save()
            logger.info("project_created", project_id=project_id)
            # Only mark cleanup as not needed AFTER successful save
            # This ensures cleanup happens if save fails or if exception occurs before this point
            cleanup_needed = False
        except PutError as e:
            # Save failed - need to cleanup uploaded files
            cleanup_needed = True
            logger.error("project_save_failed", project_id=project_id, error=str(e))
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "DatabaseError",
                    "message": "Failed to create project",
                    "details": "Unable to save project to database"
                }
            )

        # Return success response (in outer try block, after inner try/except completes)
        return ProjectCreateResponse(
            projectId=project_id,
            status="pending",
            message="Project created successfully"
        )

    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper error responses)
        raise
    except Exception as e:
        # Log unexpected errors (with full details in logs, not exposed to client)
        logger.error("create_project_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to create project",
                "details": "An internal error occurred"
            }
        )
    finally:
        # Cleanup uploaded files and project metadata if operation failed
        # Note: character_image_s3_key (if from characterReferenceImageId) is NOT in uploaded_keys
        # and is NOT cleaned up, as it's a shared reference that may be used by other projects
        if cleanup_needed:
            # Cleanup uploaded S3 files first (only files uploaded in this request)
            # Character reference images are explicitly excluded from uploaded_keys
            # Do this before DB cleanup to avoid orphaned S3 files if DB cleanup fails
            if uploaded_keys:
                for key in uploaded_keys:
                    try:
                        await asyncio.to_thread(s3_service.delete_file, key)
                        logger.info("cleanup_uploaded_file", s3_key=key)
                    except Exception as cleanup_error:
                        logger.error("cleanup_failed", s3_key=key, error=str(cleanup_error))
            
            # Attempt to delete project metadata if it was created
            # This handles the case where save() succeeded but an exception occurred after
            # Use conditional delete to only remove if still in pending state (prevents race conditions)
            try:
                pk = f"PROJECT#{project_id}"
                try:
                    project_item = MVProjectItem.get(pk, "METADATA")
                    # Only delete if still in pending state (not yet processed)
                    if project_item.status == "pending":
                        project_item.delete()
                        logger.info("cleanup_project_metadata", project_id=project_id)
                    else:
                        logger.warning("cleanup_skipped_non_pending", project_id=project_id, status=project_item.status)
                except DoesNotExist:
                    pass  # Project wasn't created yet, nothing to clean up
            except Exception as project_cleanup_error:
                logger.error("project_cleanup_failed", project_id=project_id, error=str(project_cleanup_error))


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
        # Validate and sanitize project_id format (canonicalize UUID)
        try:
            project_id = str(uuid.UUID(project_id))  # Re-serialize to canonical form
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Invalid project ID format",
                    "details": "Project ID must be a valid UUID"
                }
            )

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
                needsLipSync=scene_item.needsLipSync or False,
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
                "details": "An internal error occurred"
            }
        )

