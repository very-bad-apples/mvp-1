"""
Pipeline Orchestrator - Final Integration Component

Coordinates the complete video generation pipeline:
1. Script generation
2. Parallel asset generation (voiceovers, videos, CTA)
3. Video composition
4. Progress tracking and error handling

Features:
- Complete pipeline orchestration
- Parallel asset generation for maximum performance
- Real-time progress updates via Redis pub/sub
- Database status tracking
- Error handling with detailed logging
- Cleanup of temporary files
- Support for horizontal scaling
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

import structlog
from sqlalchemy.orm import Session

from pipeline.asset_manager import AssetManager
from pipeline.script_generator import create_script_generator
from pipeline.voiceover_generator import create_voiceover_generator
from pipeline.video_generator import VideoGenerator
from pipeline.cta_generator import CTAGenerator
from pipeline.video_composer import create_video_composer
from services.replicate_client import get_replicate_client
from models import Job, Stage, JobStatus, StageStatus, StageNames

logger = structlog.get_logger(__name__)


class PipelineOrchestrationError(Exception):
    """Raised when pipeline orchestration fails"""
    pass


class PipelineOrchestrator:
    """
    Orchestrate the complete video generation pipeline.

    Features:
    - Coordinate all pipeline steps (script → assets → composition)
    - Run asset generation in parallel (voiceovers, videos, CTA)
    - Publish real-time progress updates via Redis pub/sub
    - Handle errors with retry logic
    - Update job status in database
    - Clean up temporary files
    - Support horizontal scaling

    Example:
        >>> orchestrator = PipelineOrchestrator(
        ...     job_id="job-123",
        ...     redis_client=redis,
        ...     db_session=session
        ... )
        >>> final_video = await orchestrator.execute_pipeline(
        ...     product_name="Premium Watch",
        ...     style="luxury",
        ...     cta_text="Shop Now",
        ...     product_image_path="./product.jpg"
        ... )
    """

    def __init__(
        self,
        job_id: str,
        redis_client = None,
        db_session: Optional[Session] = None,
        video_model: str = "minimax"
    ):
        """
        Initialize with job ID and connections.

        Args:
            job_id: Unique identifier for this video generation job
            redis_client: Redis client for pub/sub progress updates
            db_session: Database session for status tracking
            video_model: Video generation model to use (minimax, seedance-fast, etc.)
        """
        self.job_id = job_id
        self.redis_client = redis_client
        self.db_session = db_session
        self.video_model = video_model
        self.logger = structlog.get_logger().bind(job_id=job_id, video_model=video_model)

        # Initialize all generators
        self.asset_manager = AssetManager(job_id)
        self.script_generator = create_script_generator()
        self.voiceover_generator = create_voiceover_generator()
        self.video_generator = VideoGenerator(get_replicate_client(), model_preference=video_model)
        self.cta_generator = CTAGenerator(get_replicate_client())
        self.video_composer = create_video_composer(self.asset_manager)

        self.logger.info("pipeline_orchestrator_initialized", video_model=video_model)

    async def execute_pipeline(
        self,
        product_name: str,
        style: str,
        cta_text: str,
        product_image_path: Optional[str] = None
    ) -> str:
        """
        Execute the complete video generation pipeline.

        Steps:
        1. Update job status to "processing"
        2. Generate script (Stage 1: script_gen)
        3. Generate assets in parallel (Stage 2-3: voice_gen, video_gen)
        4. Compose final video (Stage 4: compositing)
        5. Update job status to "completed"
        6. Clean up temporary files

        Args:
            product_name: Name of the product
            style: Visual style (luxury, energetic, minimal, bold)
            cta_text: Call-to-action text
            product_image_path: Optional path to product image

        Returns:
            Path to final video

        Raises:
            PipelineOrchestrationError: If pipeline fails

        Example:
            >>> final_video = await orchestrator.execute_pipeline(
            ...     product_name="Premium Headphones",
            ...     style="luxury",
            ...     cta_text="Shop Now",
            ...     product_image_path="./product.jpg"
            ... )
        """
        self.logger.info(
            "pipeline_execution_started",
            product_name=product_name,
            style=style,
            cta_text=cta_text,
            has_product_image=product_image_path is not None
        )

        try:
            # Create job directory structure
            await self.asset_manager.create_job_directory()

            # Update job status to processing
            await self._update_job_status(JobStatus.PROCESSING)

            # Stage 1: Script Generation (25%)
            self.logger.info("stage_1_script_generation_starting")
            await self._update_stage(StageNames.SCRIPT_GENERATION, StageStatus.PROCESSING, 0)

            script = await self._generate_script(
                product_name, style, cta_text, product_image_path
            )

            await self._update_stage(StageNames.SCRIPT_GENERATION, StageStatus.COMPLETED, 100)
            self.logger.info("stage_1_script_generation_completed")

            # Stage 2-3: Parallel Asset Generation (50%)
            self.logger.info("stage_2_3_asset_generation_starting")
            await self._update_stage(StageNames.VOICE_GENERATION, StageStatus.PROCESSING, 0)
            await self._update_stage(StageNames.VIDEO_GENERATION, StageStatus.PROCESSING, 0)

            voiceovers, videos, cta_image = await self._generate_assets_parallel(
                script, style, product_image_path
            )

            await self._update_stage(StageNames.VOICE_GENERATION, StageStatus.COMPLETED, 100)
            await self._update_stage(StageNames.VIDEO_GENERATION, StageStatus.COMPLETED, 100)
            self.logger.info("stage_2_3_asset_generation_completed")

            # Stage 4: Video Composition (25%)
            self.logger.info("stage_4_compositing_starting")
            await self._update_stage(StageNames.COMPOSITING, StageStatus.PROCESSING, 0)

            final_video = await self._compose_video(videos, voiceovers, cta_image)

            await self._update_stage(StageNames.COMPOSITING, StageStatus.COMPLETED, 100)
            self.logger.info("stage_4_compositing_completed")

            # Update job as completed
            await self._update_job_status(JobStatus.COMPLETED, video_url=final_video)

            self.logger.info(
                "pipeline_execution_completed",
                final_video=final_video
            )

            # Cleanup temporary files (optional - can be done by worker after upload)
            # await self._cleanup_temporary_files()

            return final_video

        except Exception as e:
            self.logger.error(
                "pipeline_execution_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            await self._handle_pipeline_error(e)
            raise PipelineOrchestrationError(f"Pipeline execution failed: {e}") from e

    async def _generate_script(
        self,
        product_name: str,
        style: str,
        cta_text: str,
        product_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate script with progress updates.

        Args:
            product_name: Name of the product
            style: Visual style
            cta_text: Call-to-action text
            product_image_path: Optional product image path

        Returns:
            Script dictionary with scenes and metadata

        Raises:
            PipelineOrchestrationError: If script generation fails
        """
        try:
            self.logger.info("generating_script")
            await self._publish_progress(
                StageNames.SCRIPT_GENERATION, 10, "Analyzing product..."
            )

            # Run script generation (async operation)
            script = await self.script_generator.generate_script(
                product_name=product_name,
                style=style,
                cta_text=cta_text,
                product_image_path=product_image_path
            )

            await self._publish_progress(
                StageNames.SCRIPT_GENERATION, 100, "Script generated"
            )

            self.logger.info(
                "script_generated",
                num_scenes=len(script.get("scenes", []))
            )

            return script

        except Exception as e:
            self.logger.error("script_generation_failed", error=str(e))
            raise PipelineOrchestrationError(f"Script generation failed: {e}") from e

    async def _generate_assets_parallel(
        self,
        script: Dict[str, Any],
        style: str,
        product_image_path: Optional[str] = None
    ) -> Tuple[List[str], List[str], str]:
        """
        Generate all assets in parallel for maximum performance.

        Runs voiceover generation, video generation, and CTA generation
        concurrently using asyncio.gather.

        Args:
            script: Generated script with scenes
            style: Visual style
            product_image_path: Optional product image

        Returns:
            Tuple of (voiceover_paths, video_paths, cta_image_path)

        Raises:
            PipelineOrchestrationError: If any asset generation fails
        """
        self.logger.info("starting_parallel_asset_generation")

        try:
            # Create tasks for parallel execution
            tasks = [
                self._generate_voiceovers(script, style),
                self._generate_videos(script, style, product_image_path),
                self._generate_cta(script, style, product_image_path)
            ]

            # Execute in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    task_names = ["voiceovers", "videos", "cta"]
                    raise PipelineOrchestrationError(
                        f"Failed to generate {task_names[i]}: {result}"
                    )

            voiceovers = results[0]
            videos = results[1]
            cta_image = results[2]

            self.logger.info(
                "parallel_asset_generation_completed",
                num_voiceovers=len(voiceovers),
                num_videos=len(videos),
                cta_image=cta_image
            )

            return voiceovers, videos, cta_image

        except Exception as e:
            self.logger.error("parallel_asset_generation_failed", error=str(e))
            raise PipelineOrchestrationError(f"Asset generation failed: {e}") from e

    async def _generate_voiceovers(
        self,
        script: Dict[str, Any],
        style: str
    ) -> List[str]:
        """
        Generate all voiceovers with progress tracking.

        Args:
            script: Script with voiceover text for each scene
            style: Visual style for voice selection

        Returns:
            List of voiceover file paths

        Raises:
            PipelineOrchestrationError: If voiceover generation fails
        """
        try:
            self.logger.info("generating_voiceovers")
            await self._publish_progress(
                StageNames.VOICE_GENERATION, 10, "Starting voiceover generation..."
            )

            voiceover_paths = await self.voiceover_generator.generate_all_voiceovers(
                script=script,
                asset_manager=self.asset_manager,
                style=style
            )

            await self._publish_progress(
                StageNames.VOICE_GENERATION, 100, "Voiceovers completed"
            )

            self.logger.info(
                "voiceovers_generated",
                num_voiceovers=len(voiceover_paths)
            )

            return voiceover_paths

        except Exception as e:
            self.logger.error("voiceover_generation_failed", error=str(e))
            raise PipelineOrchestrationError(f"Voiceover generation failed: {e}") from e

    async def _generate_videos(
        self,
        script: Dict[str, Any],
        style: str,
        product_image_path: Optional[str] = None
    ) -> List[str]:
        """
        Generate all video scenes with progress tracking.

        Args:
            script: Script with video prompts for each scene
            style: Visual style
            product_image_path: Optional product image

        Returns:
            List of video file paths

        Raises:
            PipelineOrchestrationError: If video generation fails
        """
        try:
            self.logger.info("generating_videos")
            await self._publish_progress(
                StageNames.VIDEO_GENERATION, 10, "Starting video generation..."
            )

            video_paths = await self.video_generator.generate_all_scenes(
                script=script,
                style=style,
                product_image_path=product_image_path,
                asset_manager=self.asset_manager
            )

            await self._publish_progress(
                StageNames.VIDEO_GENERATION, 100, "Videos completed"
            )

            self.logger.info(
                "videos_generated",
                num_videos=len(video_paths)
            )

            return video_paths

        except Exception as e:
            self.logger.error("video_generation_failed", error=str(e))
            raise PipelineOrchestrationError(f"Video generation failed: {e}") from e

    async def _generate_cta(
        self,
        script: Dict[str, Any],
        style: str,
        product_image_path: Optional[str] = None
    ) -> str:
        """
        Generate CTA image with progress tracking.

        Args:
            script: Script with CTA text
            style: Visual style
            product_image_path: Optional product image

        Returns:
            CTA image file path

        Raises:
            PipelineOrchestrationError: If CTA generation fails
        """
        try:
            self.logger.info("generating_cta")
            await self._publish_progress(
                StageNames.VIDEO_GENERATION, 50, "Generating CTA image..."
            )

            cta_path = await self.cta_generator.generate_cta(
                cta_text=script.get("cta", "Shop Now"),
                style=style,
                product_image_path=product_image_path,
                asset_manager=self.asset_manager
            )

            self.logger.info("cta_generated", cta_path=cta_path)

            return cta_path

        except Exception as e:
            self.logger.error("cta_generation_failed", error=str(e))
            raise PipelineOrchestrationError(f"CTA generation failed: {e}") from e

    async def _compose_video(
        self,
        video_paths: List[str],
        voiceover_paths: List[str],
        cta_image_path: str
    ) -> str:
        """
        Compose final video with progress tracking.

        Args:
            video_paths: List of video scene paths
            voiceover_paths: List of voiceover paths
            cta_image_path: CTA image path

        Returns:
            Final video file path

        Raises:
            PipelineOrchestrationError: If composition fails
        """
        try:
            self.logger.info("composing_final_video")
            await self._publish_progress(
                StageNames.COMPOSITING, 10, "Starting video composition..."
            )

            final_video = await self.video_composer.compose_video(
                video_scenes=video_paths,
                voiceovers=voiceover_paths,
                cta_image_path=cta_image_path
            )

            await self._publish_progress(
                StageNames.COMPOSITING, 100, "Video composition completed"
            )

            self.logger.info("video_composed", final_video=final_video)

            return final_video

        except Exception as e:
            self.logger.error("video_composition_failed", error=str(e))
            raise PipelineOrchestrationError(f"Video composition failed: {e}") from e

    async def _publish_progress(
        self,
        stage: str,
        progress: int,
        message: Optional[str] = None
    ):
        """
        Publish progress update to Redis pub/sub.

        Args:
            stage: Stage name (script_gen, voice_gen, video_gen, compositing)
            progress: Progress percentage (0-100)
            message: Optional status message
        """
        if not self.redis_client:
            self.logger.debug("redis_client_not_configured_skipping_progress_update")
            return

        update = {
            "job_id": self.job_id,
            "stage": stage,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

        try:
            # Publish to Redis channel using the wrapper method
            await asyncio.to_thread(
                self.redis_client.get_client().publish,
                "job_progress_updates",
                json.dumps(update)
            )

            self.logger.debug(
                "progress_published",
                stage=stage,
                progress=progress,
                message=message
            )

        except Exception as e:
            self.logger.warning(
                "progress_publish_failed",
                error=str(e),
                stage=stage,
                progress=progress
            )
            # Don't fail pipeline on progress update errors

    async def _update_stage(
        self,
        stage_name: str,
        status: str,
        progress: int
    ):
        """
        Update stage status in database and publish to Redis.

        Args:
            stage_name: Name of the stage
            status: Status (pending, processing, completed, failed)
            progress: Progress percentage (0-100)
        """
        if not self.db_session:
            self.logger.debug("db_session_not_configured_skipping_stage_update")
            return

        try:
            # Find or create stage
            stage = self.db_session.query(Stage).filter(
                Stage.job_id == self.job_id,
                Stage.stage_name == stage_name
            ).first()

            if not stage:
                # Create new stage
                stage = Stage(
                    job_id=self.job_id,
                    stage_name=stage_name,
                    status=status,
                    progress=progress,
                    started_at=datetime.now() if status == StageStatus.PROCESSING else None
                )
                self.db_session.add(stage)
            else:
                # Update existing stage
                stage.status = status
                stage.progress = progress

                if status == StageStatus.PROCESSING and not stage.started_at:
                    stage.started_at = datetime.now()
                elif status in [StageStatus.COMPLETED, StageStatus.FAILED]:
                    stage.completed_at = datetime.now()

            self.db_session.commit()

            self.logger.info(
                "stage_updated",
                stage_name=stage_name,
                status=status,
                progress=progress
            )

            # Publish progress
            await self._publish_progress(stage_name, progress, f"{stage_name} {status}")

        except Exception as e:
            self.logger.error(
                "stage_update_failed",
                error=str(e),
                stage_name=stage_name
            )
            # Rollback on error
            if self.db_session:
                self.db_session.rollback()

    async def _update_job_status(
        self,
        status: str,
        video_url: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Update job status in database.

        Args:
            status: Job status (pending, processing, completed, failed)
            video_url: Optional final video URL
            error_message: Optional error message
        """
        if not self.db_session:
            self.logger.debug("db_session_not_configured_skipping_job_update")
            return

        try:
            job = self.db_session.query(Job).filter(Job.id == self.job_id).first()

            if job:
                job.status = status
                job.updated_at = datetime.now()

                if video_url:
                    job.video_url = video_url

                if error_message:
                    job.error_message = error_message

                self.db_session.commit()

                self.logger.info(
                    "job_status_updated",
                    status=status,
                    video_url=video_url,
                    error_message=error_message
                )

        except Exception as e:
            self.logger.error("job_update_failed", error=str(e))
            if self.db_session:
                self.db_session.rollback()

    async def _handle_pipeline_error(self, error: Exception):
        """
        Handle pipeline errors with logging and status updates.

        Args:
            error: Exception that occurred
        """
        self.logger.error(
            "pipeline_error_handling",
            error=str(error),
            error_type=type(error).__name__
        )

        # Update job status to failed
        await self._update_job_status(
            JobStatus.FAILED,
            error_message=str(error)
        )

        # Publish error via Redis
        await self._publish_progress("error", 0, str(error))

    async def _cleanup_temporary_files(self):
        """
        Clean up temporary files after successful generation.

        This should be called by the worker after uploading the final video
        to permanent storage (S3, etc.)
        """
        try:
            await self.asset_manager.cleanup()
            self.logger.info("temporary_files_cleaned")

        except Exception as e:
            self.logger.warning(
                "cleanup_failed",
                error=str(e)
            )
            # Don't fail pipeline on cleanup errors


def create_pipeline_orchestrator(
    job_id: str,
    redis_client = None,
    db_session: Optional[Session] = None,
    video_model: str = "minimax"
) -> PipelineOrchestrator:
    """
    Factory function to create a PipelineOrchestrator instance.

    Args:
        job_id: Unique identifier for the job
        redis_client: Optional Redis client for progress updates
        db_session: Optional database session for status tracking
        video_model: Video generation model to use

    Returns:
        Configured PipelineOrchestrator instance

    Example:
        >>> orchestrator = create_pipeline_orchestrator(
        ...     job_id="job-123",
        ...     redis_client=redis,
        ...     db_session=session,
        ...     video_model="seedance-fast"
        ... )
        >>> video = await orchestrator.execute_pipeline(...)
    """
    return PipelineOrchestrator(
        job_id=job_id,
        redis_client=redis_client,
        db_session=db_session,
        video_model=video_model
    )
