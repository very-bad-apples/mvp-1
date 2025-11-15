"""
Video generation endpoint router

Handles POST /api/generate for creating video generation jobs.
"""

import uuid
import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from pathlib import Path
from sqlalchemy.orm import Session

from schemas import VideoGenerateResponse, ErrorResponse
from models import Job, Stage, JobStatus, StageStatus, StageNames
from database import get_db
from redis_client import redis_client
from pipeline.asset_manager import AssetManager

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["Video Generation"])


# Validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
ESTIMATED_COMPLETION_TIME = 300  # 5 minutes in seconds


async def validate_product_image(file: Optional[UploadFile]) -> None:
    """
    Validate uploaded product image.

    Args:
        file: Uploaded file object

    Raises:
        HTTPException: If validation fails
    """
    if file is None:
        return  # Image is optional

    # Check file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        logger.warning("invalid_file_type", content_type=file.content_type)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "InvalidFileType",
                "message": f"File type must be one of: {', '.join(ALLOWED_IMAGE_TYPES)}",
                "details": f"Received: {file.content_type}"
            }
        )

    # Check file size by reading the content
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        logger.warning("file_too_large", size=file_size, max_size=MAX_FILE_SIZE)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "FileTooLarge",
                "message": f"File size must not exceed {MAX_FILE_SIZE / 1024 / 1024}MB",
                "details": f"File size: {file_size / 1024 / 1024:.2f}MB"
            }
        )

    # Reset file pointer for later use
    await file.seek(0)

    logger.info("product_image_validated", filename=file.filename, size=file_size)


@router.post(
    "/generate",
    response_model=VideoGenerateResponse,
    status_code=202,
    responses={
        202: {"description": "Video generation job created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Generate AI Video",
    description="Create a new video generation job with product details and optional image"
)
async def generate_video(
    product_name: str = Form(..., min_length=1, max_length=100, description="Product name"),
    style: str = Form(..., min_length=1, max_length=50, description="Video style"),
    cta_text: str = Form(..., min_length=1, max_length=50, description="Call-to-action text"),
    video_model: str = Form(default="minimax", description="Video generation model (minimax, seedance-fast, seedance-pro, hailuo, ltxv, veo, sora, etc.)"),
    product_image: Optional[UploadFile] = File(None, description="Product image (optional, max 10MB)"),
    db: Session = Depends(get_db)
):
    """
    Generate a new AI-powered video ad.

    This endpoint:
    1. Validates all inputs including the optional product image
    2. Generates a unique job ID
    3. Saves the product image to the asset manager
    4. Creates a database record with initial stages
    5. Enqueues the job to Redis for processing
    6. Returns the job ID and estimated completion time

    **Request Parameters:**
    - **product_name**: Name of the product (1-100 characters)
    - **style**: Desired video style (e.g., "modern", "minimalist", "energetic")
    - **cta_text**: Call-to-action text (1-50 characters)
    - **product_image**: Optional product image (JPEG, PNG, WebP, max 10MB)

    **Response:**
    - **job_id**: Unique identifier to track the job
    - **status**: Initial status (always "pending")
    - **estimated_completion_time**: Estimated time in seconds (typically 300s)
    - **message**: Confirmation message

    **Example using cURL:**
    ```bash
    curl -X POST "http://localhost:8000/api/generate" \\
      -F "product_name=EcoWater Bottle" \\
      -F "style=modern" \\
      -F "cta_text=Buy Now!" \\
      -F "product_image=@/path/to/image.jpg"
    ```
    """
    try:
        # Subtask 8.1: Multipart form data handling (handled by FastAPI Form)
        logger.info(
            "generate_request_received",
            product_name=product_name,
            style=style,
            cta_text=cta_text,
            video_model=video_model,
            has_image=product_image is not None
        )

        # Subtask 8.2: Input validation
        if not product_name or not product_name.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Product name is required",
                    "details": "Product name cannot be empty"
                }
            )

        if not style or not style.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Style is required",
                    "details": "Style cannot be empty"
                }
            )

        if not cta_text or not cta_text.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "CTA text is required",
                    "details": "CTA text cannot be empty"
                }
            )

        # Validate product image if provided
        await validate_product_image(product_image)

        # Subtask 8.3: Generate unique job ID
        job_id = str(uuid.uuid4())
        logger.info("job_id_generated", job_id=job_id)

        # Save product image if provided
        product_image_path = None
        if product_image:
            try:
                asset_manager = AssetManager(job_id)
                await asset_manager.create_job_directory()

                # Read file content
                content = await product_image.read()

                # Save to asset manager
                file_extension = Path(product_image.filename).suffix or ".jpg"
                filename = f"product{file_extension}"
                product_image_path = await asset_manager.save_file(
                    content,
                    filename,
                    subdir=None  # Save in root job directory
                )

                logger.info("product_image_saved", path=product_image_path, size=len(content))

            except Exception as e:
                logger.error("product_image_save_failed", error=str(e), job_id=job_id)
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "ImageSaveError",
                        "message": "Failed to save product image",
                        "details": str(e)
                    }
                )

        # Create database record
        try:
            # Create job
            job = Job(
                id=job_id,
                status=JobStatus.PENDING,
                product_name=product_name.strip(),
                style=style.strip(),
                cta_text=cta_text.strip(),
                product_image_path=product_image_path
            )
            db.add(job)

            # Create initial stages
            for stage_name in StageNames.all_stages():
                stage = Stage(
                    job_id=job_id,
                    stage_name=stage_name,
                    status=StageStatus.PENDING,
                    progress=0
                )
                db.add(stage)

            db.commit()
            logger.info("job_created_in_database", job_id=job_id)

        except Exception as e:
            db.rollback()
            logger.error("database_error", error=str(e), job_id=job_id)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "DatabaseError",
                    "message": "Failed to create job in database",
                    "details": str(e)
                }
            )

        # Subtask 8.4: Enqueue job to Redis
        try:
            job_data = {
                "job_id": job_id,
                "product_name": product_name.strip(),
                "style": style.strip(),
                "cta_text": cta_text.strip(),
                "video_model": video_model,
                "product_image_path": product_image_path
            }

            success = redis_client.enqueue_job(job_id, job_data)

            if not success:
                # Rollback database changes if Redis enqueue fails
                db.delete(job)
                db.commit()

                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "QueueError",
                        "message": "Failed to enqueue job to processing queue",
                        "details": "Redis enqueue operation failed"
                    }
                )

            logger.info("job_enqueued_to_redis", job_id=job_id)

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error("redis_enqueue_error", error=str(e), job_id=job_id)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "QueueError",
                    "message": "Failed to enqueue job",
                    "details": str(e)
                }
            )

        # Return success response
        response = VideoGenerateResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            estimated_completion_time=ESTIMATED_COMPLETION_TIME,
            message="Video generation job created successfully"
        )

        logger.info(
            "generate_request_completed",
            job_id=job_id,
            estimated_time=ESTIMATED_COMPLETION_TIME
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "An unexpected error occurred",
                "details": str(e)
            }
        )
