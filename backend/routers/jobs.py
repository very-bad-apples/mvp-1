"""
Job status endpoint router

Handles GET /api/jobs/{job_id} for retrieving job status and progress.
"""

import structlog
from fastapi import APIRouter, HTTPException, Depends, Path
from sqlalchemy.orm import Session
from typing import Optional

from schemas import JobStatusResponse, StageInfo, ErrorResponse
from models import Job, Stage
from database import get_db
from redis_client import redis_client

logger = structlog.get_logger()

router = APIRouter(prefix="/api/jobs", tags=["Job Status"])


def calculate_overall_progress(stages: list) -> int:
    """
    Calculate overall job progress from stages.

    Args:
        stages: List of Stage objects

    Returns:
        Overall progress percentage (0-100)
    """
    if not stages:
        return 0

    total_progress = sum(stage.progress for stage in stages)
    return total_progress // len(stages)


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    status_code=200,
    responses={
        200: {"description": "Job status retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Job not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get Job Status",
    description="Retrieve the current status and progress of a video generation job"
)
async def get_job_status(
    job_id: str = Path(..., description="Unique job identifier (UUID)"),
    db: Session = Depends(get_db)
):
    """
    Get the status and progress of a video generation job.

    This endpoint:
    1. Fetches job data from the database
    2. Retrieves additional status information from Redis (if available)
    3. Calculates overall progress from individual stages
    4. Returns comprehensive job information including:
       - Current status (pending, processing, completed, failed)
       - Overall progress percentage
       - Individual stage progress
       - Video URL (when completed)
       - Error messages (if failed)
       - Cost information

    **Path Parameters:**
    - **job_id**: The unique identifier returned when the job was created

    **Response:**
    - Complete job information with all stages and their progress
    - Video URL will be included when status is "completed"
    - Error message will be included when status is "failed"

    **Example Response:**
    ```json
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "processing",
      "progress": 45,
      "created_at": "2025-01-14T10:00:00",
      "updated_at": "2025-01-14T10:05:00",
      "product_name": "EcoWater Bottle",
      "style": "modern",
      "cta_text": "Buy Now!",
      "video_url": null,
      "stages": [...]
    }
    ```

    **Status Values:**
    - `pending`: Job is queued and waiting to be processed
    - `processing`: Job is currently being processed
    - `completed`: Video generation completed successfully
    - `failed`: Job failed due to an error
    """
    try:
        logger.info("job_status_request", job_id=job_id)

        # Subtask 9.1: Fetch job from database
        job = db.query(Job).filter(Job.id == job_id).first()

        # Subtask 9.2: Handle invalid job IDs with 404
        if not job:
            logger.warning("job_not_found", job_id=job_id)
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "JobNotFound",
                    "message": f"Job with ID '{job_id}' not found",
                    "details": "The specified job ID does not exist in the system"
                }
            )

        # Fetch stages for this job
        stages = db.query(Stage).filter(Stage.job_id == job_id).all()

        # Try to get additional status from Redis (optional, may not be available)
        try:
            redis_status = redis_client.get_job_status(job_id)
            if redis_status:
                logger.debug("redis_status_found", job_id=job_id, status=redis_status)
        except Exception as e:
            logger.warning("redis_status_fetch_failed", job_id=job_id, error=str(e))
            # Continue without Redis data - database is source of truth

        # Calculate overall progress
        overall_progress = calculate_overall_progress(stages)

        # Subtask 9.3: Format API response with job details
        stage_infos = [
            StageInfo(
                id=stage.id,
                stage_name=stage.stage_name,
                status=stage.status,
                progress=stage.progress,
                started_at=stage.started_at,
                completed_at=stage.completed_at,
                error_message=stage.error_message
            )
            for stage in stages
        ]

        response = JobStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=overall_progress,
            created_at=job.created_at,
            updated_at=job.updated_at,
            product_name=job.product_name,
            style=job.style,
            cta_text=job.cta_text,
            video_url=job.video_url,
            error_message=job.error_message,
            cost_usd=job.cost_usd,
            stages=stage_infos
        )

        logger.info(
            "job_status_retrieved",
            job_id=job_id,
            status=job.status,
            progress=overall_progress
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("unexpected_error", job_id=job_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "An unexpected error occurred while retrieving job status",
                "details": str(e)
            }
        )


@router.get(
    "",
    response_model=list[JobStatusResponse],
    status_code=200,
    summary="List All Jobs",
    description="Retrieve a list of all video generation jobs"
)
async def list_jobs(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all video generation jobs with optional filtering.

    **Query Parameters:**
    - **limit**: Maximum number of jobs to return (default: 100)
    - **offset**: Number of jobs to skip (default: 0)
    - **status**: Filter by job status (optional)

    **Example:**
    ```
    GET /api/jobs?limit=10&status=completed
    ```
    """
    try:
        logger.info("list_jobs_request", limit=limit, offset=offset, status=status)

        # Build query
        query = db.query(Job)

        # Filter by status if provided
        if status:
            query = query.filter(Job.status == status)

        # Order by creation date (newest first)
        query = query.order_by(Job.created_at.desc())

        # Apply pagination
        jobs = query.limit(limit).offset(offset).all()

        # Build response for each job
        responses = []
        for job in jobs:
            stages = db.query(Stage).filter(Stage.job_id == job.id).all()
            overall_progress = calculate_overall_progress(stages)

            stage_infos = [
                StageInfo(
                    id=stage.id,
                    stage_name=stage.stage_name,
                    status=stage.status,
                    progress=stage.progress,
                    started_at=stage.started_at,
                    completed_at=stage.completed_at,
                    error_message=stage.error_message
                )
                for stage in stages
            ]

            responses.append(
                JobStatusResponse(
                    job_id=job.id,
                    status=job.status,
                    progress=overall_progress,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                    product_name=job.product_name,
                    style=job.style,
                    cta_text=job.cta_text,
                    video_url=job.video_url,
                    error_message=job.error_message,
                    cost_usd=job.cost_usd,
                    stages=stage_infos
                )
            )

        logger.info("list_jobs_completed", count=len(responses))
        return responses

    except Exception as e:
        logger.error("list_jobs_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "An unexpected error occurred while listing jobs",
                "details": str(e)
            }
        )
