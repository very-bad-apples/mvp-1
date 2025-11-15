"""
Tests for Pipeline Orchestrator

Tests the complete video generation pipeline orchestration including:
- Full pipeline execution
- Error handling at each stage
- Progress updates
- Parallel asset generation
- Database updates
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from pipeline.orchestrator import PipelineOrchestrator, PipelineOrchestrationError, create_pipeline_orchestrator
from models import Job, Stage, JobStatus, StageStatus, StageNames


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = Mock()
    redis.publish = Mock(return_value=1)
    return redis


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock()
    session.query = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def mock_job():
    """Mock Job instance"""
    job = Mock(spec=Job)
    job.id = "job-123"
    job.status = JobStatus.PENDING
    job.video_url = None
    job.error_message = None
    job.updated_at = datetime.now()
    return job


@pytest.fixture
def mock_stage():
    """Mock Stage instance"""
    stage = Mock(spec=Stage)
    stage.job_id = "job-123"
    stage.stage_name = StageNames.SCRIPT_GENERATION
    stage.status = StageStatus.PENDING
    stage.progress = 0
    stage.started_at = None
    stage.completed_at = None
    return stage


@pytest.fixture
def orchestrator(mock_redis, mock_db_session):
    """Create orchestrator instance with mocks"""
    with patch('pipeline.orchestrator.create_script_generator'), \
         patch('pipeline.orchestrator.create_voiceover_generator'), \
         patch('pipeline.orchestrator.VideoGenerator'), \
         patch('pipeline.orchestrator.CTAGenerator'), \
         patch('pipeline.orchestrator.create_video_composer'), \
         patch('pipeline.orchestrator.get_replicate_client'):

        orchestrator = PipelineOrchestrator(
            job_id="job-123",
            redis_client=mock_redis,
            db_session=mock_db_session
        )

        # Mock generator attributes
        orchestrator.script_generator = Mock()
        orchestrator.voiceover_generator = Mock()
        orchestrator.video_generator = Mock()
        orchestrator.cta_generator = Mock()
        orchestrator.video_composer = Mock()

        return orchestrator


@pytest.fixture
def mock_script():
    """Mock script data"""
    return {
        "total_duration": 30,
        "style": "luxury",
        "product_name": "Premium Watch",
        "cta": "Shop Now",
        "scenes": [
            {
                "id": 1,
                "type": "video",
                "duration": 8,
                "voiceover_text": "Introducing the future of luxury timepieces",
                "video_prompt_template": "Elegant watch showcase with soft lighting"
            },
            {
                "id": 2,
                "type": "video",
                "duration": 8,
                "voiceover_text": "Crafted with precision and care",
                "video_prompt_template": "Close-up of watch mechanism"
            },
            {
                "id": 3,
                "type": "video",
                "duration": 10,
                "voiceover_text": "Trusted by thousands worldwide",
                "video_prompt_template": "Customer testimonial scene"
            },
            {
                "id": 4,
                "type": "video",
                "duration": 4,
                "voiceover_text": "Get yours today",
                "video_prompt_template": "Final product shot"
            }
        ]
    }


class TestPipelineOrchestrator:
    """Test suite for PipelineOrchestrator"""

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization"""
        assert orchestrator.job_id == "job-123"
        assert orchestrator.redis_client is not None
        assert orchestrator.db_session is not None
        assert orchestrator.asset_manager is not None
        assert orchestrator.script_generator is not None
        assert orchestrator.voiceover_generator is not None
        assert orchestrator.video_generator is not None
        assert orchestrator.cta_generator is not None
        assert orchestrator.video_composer is not None

    def test_factory_function(self, mock_redis, mock_db_session):
        """Test factory function"""
        with patch('pipeline.orchestrator.create_script_generator'), \
             patch('pipeline.orchestrator.create_voiceover_generator'), \
             patch('pipeline.orchestrator.VideoGenerator'), \
             patch('pipeline.orchestrator.CTAGenerator'), \
             patch('pipeline.orchestrator.create_video_composer'), \
             patch('pipeline.orchestrator.get_replicate_client'):

            orchestrator = create_pipeline_orchestrator(
                job_id="job-456",
                redis_client=mock_redis,
                db_session=mock_db_session
            )

            assert isinstance(orchestrator, PipelineOrchestrator)
            assert orchestrator.job_id == "job-456"

    @pytest.mark.asyncio
    async def test_publish_progress(self, orchestrator, mock_redis):
        """Test progress publishing to Redis"""
        await orchestrator._publish_progress(
            stage=StageNames.SCRIPT_GENERATION,
            progress=50,
            message="Generating script..."
        )

        # Verify Redis publish was called
        assert mock_redis.publish.call_count >= 1
        call_args = mock_redis.publish.call_args

        # Check channel name
        assert call_args[0][0] == "job_progress_updates"

        # Check message contains expected data
        import json
        message = json.loads(call_args[0][1])
        assert message["job_id"] == "job-123"
        assert message["stage"] == StageNames.SCRIPT_GENERATION
        assert message["progress"] == 50
        assert message["message"] == "Generating script..."

    @pytest.mark.asyncio
    async def test_update_stage_create_new(self, orchestrator, mock_db_session, mock_stage):
        """Test stage update creates new stage"""
        # Mock query to return None (no existing stage)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        await orchestrator._update_stage(
            stage_name=StageNames.SCRIPT_GENERATION,
            status=StageStatus.PROCESSING,
            progress=50
        )

        # Verify stage was added
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_stage_update_existing(self, orchestrator, mock_db_session, mock_stage):
        """Test stage update modifies existing stage"""
        # Mock query to return existing stage
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_stage
        mock_db_session.query.return_value = mock_query

        await orchestrator._update_stage(
            stage_name=StageNames.SCRIPT_GENERATION,
            status=StageStatus.COMPLETED,
            progress=100
        )

        # Verify stage was updated
        assert mock_stage.status == StageStatus.COMPLETED
        assert mock_stage.progress == 100
        assert mock_stage.completed_at is not None
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_job_status(self, orchestrator, mock_db_session, mock_job):
        """Test job status update"""
        # Mock query to return job
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_job
        mock_db_session.query.return_value = mock_query

        await orchestrator._update_job_status(
            status=JobStatus.COMPLETED,
            video_url="https://example.com/video.mp4"
        )

        # Verify job was updated
        assert mock_job.status == JobStatus.COMPLETED
        assert mock_job.video_url == "https://example.com/video.mp4"
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_script(self, orchestrator, mock_script):
        """Test script generation"""
        with patch.object(orchestrator.script_generator, 'generate_script', return_value=mock_script):
            script = await orchestrator._generate_script(
                product_name="Premium Watch",
                style="luxury",
                cta_text="Shop Now",
                product_image_path=None
            )

            assert script == mock_script
            assert len(script["scenes"]) == 4

    @pytest.mark.asyncio
    async def test_generate_script_with_image(self, orchestrator, mock_script):
        """Test script generation with product image"""
        with patch.object(orchestrator.script_generator, 'generate_script', return_value=mock_script):
            script = await orchestrator._generate_script(
                product_name="Premium Watch",
                style="luxury",
                cta_text="Shop Now",
                product_image_path="/path/to/image.jpg"
            )

            assert script == mock_script

    @pytest.mark.asyncio
    async def test_generate_voiceovers(self, orchestrator, mock_script):
        """Test voiceover generation"""
        mock_paths = [
            "/tmp/scene_1_voiceover.mp3",
            "/tmp/scene_2_voiceover.mp3",
            "/tmp/scene_3_voiceover.mp3",
            "/tmp/scene_4_voiceover.mp3"
        ]

        orchestrator.voiceover_generator.generate_all_voiceovers = AsyncMock(return_value=mock_paths)

        voiceovers = await orchestrator._generate_voiceovers(mock_script, "luxury")

        assert len(voiceovers) == 4
        assert voiceovers == mock_paths

    @pytest.mark.asyncio
    async def test_generate_videos(self, orchestrator, mock_script):
        """Test video generation"""
        mock_paths = [
            "/tmp/scene_1.mp4",
            "/tmp/scene_2.mp4",
            "/tmp/scene_3.mp4",
            "/tmp/scene_4.mp4"
        ]

        orchestrator.video_generator.generate_all_scenes = AsyncMock(return_value=mock_paths)

        videos = await orchestrator._generate_videos(
            mock_script, "luxury", None
        )

        assert len(videos) == 4
        assert videos == mock_paths

    @pytest.mark.asyncio
    async def test_generate_cta(self, orchestrator, mock_script):
        """Test CTA generation"""
        mock_path = "/tmp/cta_final.png"

        orchestrator.cta_generator.generate_cta = AsyncMock(return_value=mock_path)

        cta = await orchestrator._generate_cta(
            mock_script, "luxury", None
        )

        assert cta == mock_path

    @pytest.mark.asyncio
    async def test_compose_video(self, orchestrator):
        """Test video composition"""
        video_paths = ["/tmp/scene_1.mp4", "/tmp/scene_2.mp4"]
        voiceover_paths = ["/tmp/vo_1.mp3", "/tmp/vo_2.mp3"]
        cta_path = "/tmp/cta.png"
        final_path = "/tmp/final_video.mp4"

        orchestrator.video_composer.compose_video = AsyncMock(return_value=final_path)

        result = await orchestrator._compose_video(
            video_paths, voiceover_paths, cta_path
        )

        assert result == final_path

    @pytest.mark.asyncio
    async def test_parallel_asset_generation(self, orchestrator, mock_script):
        """Test parallel asset generation"""
        mock_voiceovers = ["/tmp/vo_1.mp3", "/tmp/vo_2.mp3"]
        mock_videos = ["/tmp/scene_1.mp4", "/tmp/scene_2.mp4"]
        mock_cta = "/tmp/cta.png"

        with patch.object(orchestrator, '_generate_voiceovers', return_value=mock_voiceovers), \
             patch.object(orchestrator, '_generate_videos', return_value=mock_videos), \
             patch.object(orchestrator, '_generate_cta', return_value=mock_cta):

            voiceovers, videos, cta = await orchestrator._generate_assets_parallel(
                mock_script, "luxury", None
            )

            assert voiceovers == mock_voiceovers
            assert videos == mock_videos
            assert cta == mock_cta

    @pytest.mark.asyncio
    async def test_parallel_asset_generation_with_error(self, orchestrator, mock_script):
        """Test parallel asset generation handles errors"""
        async def failing_task():
            raise Exception("Generation failed")

        with patch.object(orchestrator, '_generate_voiceovers', side_effect=failing_task):
            with pytest.raises(PipelineOrchestrationError) as exc_info:
                await orchestrator._generate_assets_parallel(
                    mock_script, "luxury", None
                )

            assert "Failed to generate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self, orchestrator, mock_script, mock_db_session, mock_job):
        """Test full pipeline execution"""
        # Mock database queries
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_job
        mock_db_session.query.return_value = mock_query

        # Mock all generator methods
        mock_voiceovers = ["/tmp/vo_1.mp3", "/tmp/vo_2.mp3"]
        mock_videos = ["/tmp/scene_1.mp4", "/tmp/scene_2.mp4"]
        mock_cta = "/tmp/cta.png"
        mock_final = "/tmp/final_video.mp4"

        with patch.object(orchestrator.asset_manager, 'create_job_directory'), \
             patch.object(orchestrator, '_generate_script', return_value=mock_script), \
             patch.object(orchestrator, '_generate_voiceovers', return_value=mock_voiceovers), \
             patch.object(orchestrator, '_generate_videos', return_value=mock_videos), \
             patch.object(orchestrator, '_generate_cta', return_value=mock_cta), \
             patch.object(orchestrator, '_compose_video', return_value=mock_final):

            final_video = await orchestrator.execute_pipeline(
                product_name="Premium Watch",
                style="luxury",
                cta_text="Shop Now",
                product_image_path=None
            )

            assert final_video == mock_final
            assert mock_job.status == JobStatus.COMPLETED
            assert mock_job.video_url == mock_final

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, orchestrator, mock_db_session, mock_job):
        """Test pipeline error handling"""
        # Mock database queries
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_job
        mock_db_session.query.return_value = mock_query

        # Mock script generation to fail
        with patch.object(orchestrator.asset_manager, 'create_job_directory'), \
             patch.object(orchestrator, '_generate_script', side_effect=Exception("Script failed")):

            with pytest.raises(PipelineOrchestrationError) as exc_info:
                await orchestrator.execute_pipeline(
                    product_name="Premium Watch",
                    style="luxury",
                    cta_text="Shop Now"
                )

            assert "Pipeline execution failed" in str(exc_info.value)
            assert mock_job.status == JobStatus.FAILED
            assert mock_job.error_message is not None

    @pytest.mark.asyncio
    async def test_cleanup_temporary_files(self, orchestrator):
        """Test cleanup of temporary files"""
        with patch.object(orchestrator.asset_manager, 'cleanup') as mock_cleanup:
            await orchestrator._cleanup_temporary_files()
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_failure_does_not_raise(self, orchestrator):
        """Test cleanup failure doesn't crash pipeline"""
        with patch.object(
            orchestrator.asset_manager,
            'cleanup',
            side_effect=Exception("Cleanup failed")
        ):
            # Should not raise exception
            await orchestrator._cleanup_temporary_files()

    @pytest.mark.asyncio
    async def test_orchestrator_without_redis(self, mock_db_session):
        """Test orchestrator works without Redis client"""
        with patch('pipeline.orchestrator.create_script_generator'), \
             patch('pipeline.orchestrator.create_voiceover_generator'), \
             patch('pipeline.orchestrator.VideoGenerator'), \
             patch('pipeline.orchestrator.CTAGenerator'), \
             patch('pipeline.orchestrator.create_video_composer'), \
             patch('pipeline.orchestrator.get_replicate_client'):

            orchestrator = PipelineOrchestrator(
                job_id="job-123",
                redis_client=None,
                db_session=mock_db_session
            )

            # Should not raise exception when publishing progress
            await orchestrator._publish_progress("script_gen", 50, "Testing")

    @pytest.mark.asyncio
    async def test_orchestrator_without_database(self, mock_redis):
        """Test orchestrator works without database session"""
        with patch('pipeline.orchestrator.create_script_generator'), \
             patch('pipeline.orchestrator.create_voiceover_generator'), \
             patch('pipeline.orchestrator.VideoGenerator'), \
             patch('pipeline.orchestrator.CTAGenerator'), \
             patch('pipeline.orchestrator.create_video_composer'), \
             patch('pipeline.orchestrator.get_replicate_client'):

            orchestrator = PipelineOrchestrator(
                job_id="job-123",
                redis_client=mock_redis,
                db_session=None
            )

            # Should not raise exception when updating stage
            await orchestrator._update_stage("script_gen", "processing", 50)

    @pytest.mark.asyncio
    async def test_stage_timing_tracking(self, orchestrator, mock_db_session):
        """Test stage timing is tracked correctly"""
        mock_stage = Mock(spec=Stage)
        mock_stage.started_at = None
        mock_stage.completed_at = None

        # Mock query to return stage
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_stage
        mock_db_session.query.return_value = mock_query

        # Start processing
        await orchestrator._update_stage(
            StageNames.SCRIPT_GENERATION,
            StageStatus.PROCESSING,
            0
        )
        assert mock_stage.started_at is not None

        # Complete stage
        await orchestrator._update_stage(
            StageNames.SCRIPT_GENERATION,
            StageStatus.COMPLETED,
            100
        )
        assert mock_stage.completed_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
