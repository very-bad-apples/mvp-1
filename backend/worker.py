"""
Queue Worker for Video Generation Pipeline

This worker:
- Listens to Redis job queue (BLPOP)
- Processes video generation jobs sequentially
- Handles failures with exponential backoff retry logic
- Publishes progress updates via Redis pub/sub
- Updates job status in database
- Supports graceful shutdown (SIGTERM, SIGINT)
- Provides health check endpoint
- Designed for horizontal scaling (multiple workers)
"""

import signal
import sys
import time
import traceback
import structlog
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from redis_client import redis_client
from database import get_db_context, init_db
from models import Job, Stage, JobStatus, StageStatus, StageNames
from config import settings
from pipeline.error_handler import (
    PipelineError,
    ErrorCode,
    should_retry,
    get_retry_delay,
    categorize_error
)
from pipeline.orchestrator import create_pipeline_orchestrator
from services.asset_persistence import AssetPersistenceService
import asyncio

logger = structlog.get_logger()


class WorkerState:
    """Worker state management for graceful shutdown"""

    def __init__(self):
        self.running = True
        self.current_job_id: Optional[str] = None
        self.shutdown_requested = False

    def request_shutdown(self):
        """Request graceful shutdown"""
        self.shutdown_requested = True
        logger.info("shutdown_requested")

    def is_running(self) -> bool:
        """Check if worker should continue running"""
        return self.running and not self.shutdown_requested

    def stop(self):
        """Stop the worker"""
        self.running = False
        logger.info("worker_stopped")


class VideoGenerationWorker:
    """
    Worker for processing video generation jobs from Redis queue

    Features:
    - Blocking queue pop with timeout (BLPOP)
    - Exponential backoff retry logic for transient errors
    - Progress updates via Redis pub/sub
    - Database persistence of job status
    - Graceful shutdown handling
    - Health check support
    """

    def __init__(self, worker_id: Optional[str] = None):
        """
        Initialize worker

        Args:
            worker_id: Optional worker identifier for multi-worker setups
        """
        self.worker_id = worker_id or f"worker-{id(self)}"
        self.state = WorkerState()
        self.max_retries = 3
        self.health_check_interval = 30  # seconds
        self.last_health_check = time.time()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)

        logger.info(
            "worker_initialized",
            worker_id=self.worker_id,
            max_retries=self.max_retries
        )

    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals (SIGTERM, SIGINT)"""
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        logger.info(
            "shutdown_signal_received",
            signal=signal_name,
            current_job=self.state.current_job_id
        )
        self.state.request_shutdown()

    def run(self):
        """
        Main worker loop

        Continuously polls Redis queue for jobs and processes them.
        Exits gracefully on shutdown signal.
        """
        logger.info("worker_started", worker_id=self.worker_id)

        # Initialize database
        try:
            init_db()
        except Exception as e:
            logger.error("database_init_failed", error=str(e))
            return

        while self.state.is_running():
            try:
                # Periodic health check
                self._perform_health_check()

                # Dequeue job from Redis (blocking with timeout)
                job_data = redis_client.dequeue_job()

                if job_data is None:
                    # No job available, continue polling
                    continue

                # Extract job ID
                job_id = job_data.get("job_id")
                if not job_id:
                    logger.error("job_missing_id", job_data=job_data)
                    continue

                # Process the job
                self.state.current_job_id = job_id
                self._process_job(job_id, job_data)
                self.state.current_job_id = None

            except KeyboardInterrupt:
                logger.info("keyboard_interrupt_received")
                break
            except Exception as e:
                logger.error(
                    "worker_loop_error",
                    error=str(e),
                    traceback=traceback.format_exc()
                )
                # Continue processing despite errors
                time.sleep(1)

        logger.info("worker_shutdown_complete", worker_id=self.worker_id)

    def _process_job(self, job_id: str, job_data: Dict[str, Any]):
        """
        Process a single job with retry logic

        Args:
            job_id: Unique job identifier
            job_data: Job parameters and metadata
        """
        logger.info("job_processing_started", job_id=job_id, worker_id=self.worker_id)

        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            try:
                # Check for shutdown during retry loop
                if self.state.shutdown_requested:
                    logger.info("job_interrupted_by_shutdown", job_id=job_id)
                    self._update_job_status_in_db(
                        job_id,
                        JobStatus.PENDING,
                        error_message="Worker shutdown during processing"
                    )
                    # Re-enqueue job for another worker
                    redis_client.enqueue_job(job_id, job_data)
                    return

                # Attempt to process the job
                self._execute_job(job_id, job_data)

                # Success - job completed
                logger.info(
                    "job_completed",
                    job_id=job_id,
                    worker_id=self.worker_id,
                    attempts=attempt + 1
                )
                return

            except Exception as e:
                attempt += 1
                last_error = e

                # Convert to PipelineError if needed
                if not isinstance(e, PipelineError):
                    error_code = categorize_error(e)
                    pipeline_error = PipelineError(
                        error_code,
                        str(e),
                        {"original_exception": type(e).__name__}
                    )
                else:
                    pipeline_error = e

                # Log the error
                pipeline_error.log_error()

                # Check if error is retryable
                if not should_retry(pipeline_error):
                    logger.error(
                        "job_failed_non_retryable",
                        job_id=job_id,
                        error_code=pipeline_error.code.value,
                        attempts=attempt
                    )
                    self._handle_job_failure(job_id, pipeline_error)
                    return

                # Check if max retries reached
                if attempt >= self.max_retries:
                    logger.error(
                        "job_failed_max_retries",
                        job_id=job_id,
                        error_code=pipeline_error.code.value,
                        attempts=attempt
                    )
                    self._handle_job_failure(job_id, pipeline_error)
                    return

                # Calculate retry delay
                delay = get_retry_delay(attempt - 1)
                logger.warning(
                    "job_retry_scheduled",
                    job_id=job_id,
                    attempt=attempt,
                    max_retries=self.max_retries,
                    retry_delay=delay,
                    error_code=pipeline_error.code.value
                )

                # Update Redis and publish retry status
                redis_client.update_job_status(
                    job_id,
                    "retrying",
                    attempt=attempt,
                    max_retries=self.max_retries,
                    retry_delay=delay
                )
                redis_client.publish_status(
                    job_id,
                    "retrying",
                    attempt=attempt,
                    max_retries=self.max_retries,
                    error=pipeline_error.code.value
                )

                # Wait before retry
                time.sleep(delay)

        # Should not reach here, but handle it
        if last_error:
            logger.error("job_failed_unexpected", job_id=job_id)
            self._handle_job_failure(
                job_id,
                last_error if isinstance(last_error, PipelineError)
                else PipelineError(ErrorCode.STORAGE_ERROR, str(last_error))
            )

    def _execute_job(self, job_id: str, job_data: Dict[str, Any]):
        """
        Execute the actual job processing

        This is a placeholder for the actual pipeline orchestration.
        Task 19 (Pipeline Orchestrator) will implement the full processing logic.

        Args:
            job_id: Unique job identifier
            job_data: Job parameters
        """
        logger.info("job_execution_started", job_id=job_id)

        # Update job status to processing
        self._update_job_status_in_db(job_id, JobStatus.PROCESSING)
        redis_client.update_job_status(job_id, JobStatus.PROCESSING)
        redis_client.publish_status(job_id, JobStatus.PROCESSING, worker_id=self.worker_id)

        # Extract job parameters
        product_name = job_data.get("product_name", "Unknown")
        style = job_data.get("style", "minimal")
        cta_text = job_data.get("cta_text", "Learn More")
        product_image_path = job_data.get("product_image_path")
        video_model = job_data.get("video_model", "minimax")

        # Run the pipeline orchestrator
        with get_db_context() as db:
            # Create orchestrator with video model
            orchestrator = create_pipeline_orchestrator(
                job_id=job_id,
                redis_client=redis_client,
                db_session=db,
                video_model=video_model
            )

            # Execute the pipeline (async)
            try:
                final_video = asyncio.run(orchestrator.execute_pipeline(
                    product_name=product_name,
                    style=style,
                    cta_text=cta_text,
                    product_image_path=product_image_path
                ))

                logger.info(
                    "pipeline_execution_success",
                    job_id=job_id,
                    final_video=final_video
                )
                
                # Persist assets to cloud storage
                cloud_urls = asyncio.run(self._persist_job_assets(job_id, final_video))
                
                # Update job with cloud URLs
                self._update_job_with_cloud_urls(job_id, cloud_urls)
                
            except Exception as e:
                logger.error(
                    "pipeline_execution_failed",
                    job_id=job_id,
                    error=str(e)
                )
                raise

        # Update Redis and publish completion
        redis_client.update_job_status(job_id, JobStatus.COMPLETED)
        redis_client.publish_status(
            job_id,
            JobStatus.COMPLETED,
            worker_id=self.worker_id
        )
        redis_client.publish_progress(job_id, "complete", 100, worker_id=self.worker_id)

        logger.info("job_execution_completed", job_id=job_id)

    def _handle_job_failure(self, job_id: str, error: PipelineError):
        """
        Handle job failure - update status in database and Redis

        Args:
            job_id: Job identifier
            error: Pipeline error that caused failure
        """
        logger.error("job_failed", job_id=job_id, error_code=error.code.value)

        # Update database
        self._update_job_status_in_db(
            job_id,
            JobStatus.FAILED,
            error_message=error.message
        )

        # Update Redis
        redis_client.update_job_status(
            job_id,
            JobStatus.FAILED,
            error_code=error.code.value,
            error_message=error.get_user_friendly_message()
        )

        # Publish failure status
        redis_client.publish_status(
            job_id,
            JobStatus.FAILED,
            error_code=error.code.value,
            error_message=error.get_user_friendly_message(),
            worker_id=self.worker_id
        )

    def _update_job_status_in_db(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None
    ):
        """
        Update job status in database

        Args:
            job_id: Job identifier
            status: New status
            error_message: Optional error message
        """
        try:
            with get_db_context() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = status
                    job.updated_at = datetime.utcnow()
                    if error_message:
                        job.error_message = error_message
                    db.commit()
                    logger.info(
                        "job_status_updated_in_db",
                        job_id=job_id,
                        status=status
                    )
                else:
                    logger.warning(
                        "job_not_found_in_db",
                        job_id=job_id
                    )
        except Exception as e:
            logger.error(
                "database_update_failed",
                job_id=job_id,
                error=str(e),
                traceback=traceback.format_exc()
            )

    async def _persist_job_assets(self, job_id: str, final_video_path: str) -> Dict[str, any]:
        """
        Persist all job assets to cloud storage.
        
        Args:
            job_id: Job identifier
            final_video_path: Path to final video (may be relative or absolute)
            
        Returns:
            Dict with cloud URLs for all assets
        """
        try:
            logger.info("persisting_job_assets", job_id=job_id)
            
            # Determine local base path from final_video_path
            # final_video_path is like "/tmp/video_jobs/job-123/final/video.mp4"
            # We need "/tmp/video_jobs/job-123"
            from pathlib import Path
            video_path = Path(final_video_path)
            
            # Go up from final/video.mp4 to job directory
            if video_path.parent.name == "final":
                local_base_path = str(video_path.parent.parent)
            else:
                # Assume it's directly in job directory
                local_base_path = str(video_path.parent)
            
            # Create persistence service and upload assets
            persistence_service = AssetPersistenceService()
            cloud_urls = await persistence_service.persist_job_assets(
                job_id=job_id,
                local_base_path=local_base_path
            )
            
            logger.info(
                "job_assets_persisted",
                job_id=job_id,
                final_video_url=cloud_urls.get("final_video")
            )
            
            return cloud_urls
            
        except Exception as e:
            logger.error(
                "asset_persistence_failed",
                job_id=job_id,
                error=str(e),
                traceback=traceback.format_exc()
            )
            # Don't fail the job if cloud upload fails
            # The local video is still available
            return {"error": str(e)}

    def _update_job_with_cloud_urls(self, job_id: str, cloud_urls: Dict[str, any]):
        """
        Update job record with cloud storage URLs.
        
        Args:
            job_id: Job identifier
            cloud_urls: Dict of cloud URLs from persistence service
        """
        try:
            with get_db_context() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    # Store cloud URLs in job metadata
                    # Note: This requires the Job model to have appropriate fields
                    # For now, we'll store in a JSON field if available
                    if hasattr(job, 'cloud_urls'):
                        job.cloud_urls = cloud_urls
                    
                    # Store final video URL as primary video_url
                    if cloud_urls.get("final_video"):
                        job.video_url = cloud_urls["final_video"]
                    
                    # Initialize version tracking
                    if hasattr(job, 'version') and job.version is None:
                        job.version = 1
                    
                    job.updated_at = datetime.utcnow()
                    db.commit()
                    
                    logger.info(
                        "job_cloud_urls_updated",
                        job_id=job_id,
                        video_url=cloud_urls.get("final_video")
                    )
                else:
                    logger.warning("job_not_found_for_url_update", job_id=job_id)
                    
        except Exception as e:
            logger.error(
                "cloud_url_update_failed",
                job_id=job_id,
                error=str(e),
                traceback=traceback.format_exc()
            )

    def _perform_health_check(self):
        """
        Perform periodic health check

        Verifies:
        - Redis connection is alive
        - Database connection is alive
        """
        current_time = time.time()
        if current_time - self.last_health_check < self.health_check_interval:
            return

        self.last_health_check = current_time

        # Check Redis
        try:
            redis_healthy = redis_client.ping()
            if not redis_healthy:
                logger.error("health_check_redis_failed", worker_id=self.worker_id)
        except Exception as e:
            logger.error(
                "health_check_redis_error",
                worker_id=self.worker_id,
                error=str(e)
            )

        # Check Database
        try:
            with get_db_context() as db:
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
            logger.info("health_check_passed", worker_id=self.worker_id)
        except Exception as e:
            logger.error(
                "health_check_database_error",
                worker_id=self.worker_id,
                error=str(e)
            )

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status

        Returns:
            Dictionary with health status information
        """
        redis_healthy = False
        db_healthy = False

        # Check Redis
        try:
            redis_healthy = redis_client.ping()
        except Exception:
            pass

        # Check Database
        try:
            with get_db_context() as db:
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
            db_healthy = True
        except Exception:
            pass

        return {
            "worker_id": self.worker_id,
            "running": self.state.is_running(),
            "current_job": self.state.current_job_id,
            "redis_healthy": redis_healthy,
            "database_healthy": db_healthy,
            "healthy": redis_healthy and db_healthy and self.state.is_running(),
            "timestamp": datetime.utcnow().isoformat()
        }


def main():
    """
    Main entry point for worker

    Usage:
        python worker.py [worker_id]

    Example:
        python worker.py worker-1
    """
    import sys

    worker_id = sys.argv[1] if len(sys.argv) > 1 else None

    worker = VideoGenerationWorker(worker_id=worker_id)

    try:
        worker.run()
    except Exception as e:
        logger.error(
            "worker_fatal_error",
            error=str(e),
            traceback=traceback.format_exc()
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
