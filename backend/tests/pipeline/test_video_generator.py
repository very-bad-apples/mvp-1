"""
Unit tests for VideoGenerator

Tests video scene generation with mocked Replicate API calls.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from pipeline.video_generator import (
    VideoGenerator,
    VideoGenerationError,
    create_video_generator,
    STYLE_CONFIGS,
    VIDEO_MODELS
)
from services.replicate_client import ReplicateClient
from pipeline.asset_manager import AssetManager


@pytest.fixture
def mock_replicate_client():
    """Create a mock ReplicateClient"""
    client = Mock(spec=ReplicateClient)
    client.run_model_async = AsyncMock()
    return client


@pytest.fixture
def video_generator(mock_replicate_client):
    """Create VideoGenerator with mocked client"""
    return VideoGenerator(mock_replicate_client, model_preference="minimax")


@pytest.fixture
def mock_asset_manager(tmp_path):
    """Create a mock AssetManager"""
    am = Mock(spec=AssetManager)
    am.scenes_dir = tmp_path / "scenes"
    am.scenes_dir.mkdir(parents=True, exist_ok=True)
    am.download_with_retry = AsyncMock()
    am.validate_file = AsyncMock(return_value=True)
    return am


@pytest.fixture
def sample_scene_config():
    """Sample scene configuration"""
    return {
        "id": 1,
        "duration": 8,
        "type": "video",
        "video_prompt_template": "Close-up of {product_name}, slow camera tilt, luxury lighting",
        "use_product_image": True,
        "voiceover_text": "Discover the ultimate luxury.",
    }


@pytest.fixture
def sample_script():
    """Sample script with multiple scenes"""
    return {
        "total_duration": 30,
        "style": "luxury",
        "product_name": "Premium Watch",
        "scenes": [
            {
                "id": 1,
                "type": "video",
                "video_prompt_template": "Product showcase scene 1",
                "use_product_image": True,
            },
            {
                "id": 2,
                "type": "video",
                "video_prompt_template": "Product showcase scene 2",
                "use_product_image": False,
            },
            {
                "id": 3,
                "type": "video",
                "video_prompt_template": "Product showcase scene 3",
                "use_product_image": True,
            },
            {
                "id": 4,
                "type": "image",  # This should be skipped
                "image_prompt_template": "CTA scene",
            }
        ]
    }


class TestVideoGeneratorInit:
    """Test VideoGenerator initialization"""

    def test_init_with_valid_model(self, mock_replicate_client):
        """Test initialization with valid model preference"""
        vg = VideoGenerator(mock_replicate_client, model_preference="minimax")
        assert vg.model_id == VIDEO_MODELS["minimax"]
        assert vg.model_preference == "minimax"

    def test_init_with_invalid_model(self, mock_replicate_client):
        """Test initialization with invalid model preference"""
        with pytest.raises(ValueError, match="Invalid model preference"):
            VideoGenerator(mock_replicate_client, model_preference="invalid_model")

    def test_init_all_model_preferences(self, mock_replicate_client):
        """Test initialization with all available models"""
        for model_name in VIDEO_MODELS.keys():
            vg = VideoGenerator(mock_replicate_client, model_preference=model_name)
            assert vg.model_id == VIDEO_MODELS[model_name]


class TestPrepareVideoPrompt:
    """Test video prompt preparation"""

    def test_prepare_prompt_luxury_style(self, video_generator):
        """Test prompt preparation for luxury style"""
        template = "Product showcase with smooth camera movement"
        prompt = video_generator._prepare_video_prompt(template, "luxury")

        assert template in prompt
        assert "soft lighting" in prompt
        assert "elegant" in prompt
        assert "premium" in prompt
        assert "24 fps" in prompt

    def test_prepare_prompt_energetic_style(self, video_generator):
        """Test prompt preparation for energetic style"""
        template = "Dynamic product reveal"
        prompt = video_generator._prepare_video_prompt(template, "energetic")

        assert template in prompt
        assert "dynamic" in prompt
        assert "vibrant" in prompt
        assert "30 fps" in prompt

    def test_prepare_prompt_minimal_style(self, video_generator):
        """Test prompt preparation for minimal style"""
        template = "Clean product presentation"
        prompt = video_generator._prepare_video_prompt(template, "minimal")

        assert template in prompt
        assert "clean" in prompt
        assert "minimal" in prompt
        assert "24 fps" in prompt

    def test_prepare_prompt_bold_style(self, video_generator):
        """Test prompt preparation for bold style"""
        template = "Striking product shot"
        prompt = video_generator._prepare_video_prompt(template, "bold")

        assert template in prompt
        assert "bold" in prompt
        assert "dramatic" in prompt
        assert "24 fps" in prompt

    def test_prepare_prompt_with_product_name(self, video_generator):
        """Test prompt preparation with product name"""
        template = "Showcase Premium Watch"
        prompt = video_generator._prepare_video_prompt(
            template,
            "luxury",
            product_name="Premium Watch"
        )

        assert "Premium Watch" in template
        assert "luxury" in prompt.lower() or "elegant" in prompt


class TestGetModelInputParams:
    """Test model-specific input parameter generation"""

    def test_minimax_params(self, video_generator):
        """Test Minimax model parameters"""
        params = video_generator._get_model_input_params(
            "Test prompt",
            "luxury"
        )

        assert "prompt" in params
        assert params["prompt"] == "Test prompt"
        assert "prompt_optimizer" in params
        assert params["prompt_optimizer"] is True

    def test_ltxv_params(self, mock_replicate_client):
        """Test LTX Video model parameters"""
        vg = VideoGenerator(mock_replicate_client, model_preference="ltxv")
        params = vg._get_model_input_params(
            "Test prompt",
            "luxury"
        )

        assert "prompt" in params
        assert "num_frames" in params
        assert "aspect_ratio" in params
        assert params["aspect_ratio"] == "9:16"

    def test_svd_params_without_image(self, mock_replicate_client):
        """Test SVD model parameters without product image"""
        vg = VideoGenerator(mock_replicate_client, model_preference="svd")

        with pytest.raises(VideoGenerationError, match="requires product_image_path"):
            vg._get_model_input_params("Test prompt", "luxury")

    def test_svd_params_with_image(self, mock_replicate_client, tmp_path):
        """Test SVD model parameters with product image"""
        # Create dummy image file
        image_path = tmp_path / "product.jpg"
        image_path.write_bytes(b"fake image data")

        vg = VideoGenerator(mock_replicate_client, model_preference="svd")
        params = vg._get_model_input_params(
            "Test prompt",
            "energetic",
            product_image_path=str(image_path)
        )

        assert "image" in params
        assert "motion_bucket_id" in params
        assert "fps" in params
        # Energetic style should have higher motion
        assert params["motion_bucket_id"] == 127


class TestGenerateScene:
    """Test single scene generation"""

    @pytest.mark.asyncio
    async def test_generate_scene_success(
        self,
        video_generator,
        mock_replicate_client,
        sample_scene_config,
        mock_asset_manager
    ):
        """Test successful scene generation"""
        # Mock Replicate API response
        mock_replicate_client.run_model_async.return_value = [
            "https://replicate.delivery/video.mp4"
        ]
        mock_asset_manager.download_with_retry.return_value = "/tmp/scene_1.mp4"

        video_path = await video_generator.generate_scene(
            sample_scene_config,
            style="luxury",
            asset_manager=mock_asset_manager,
            scene_id=1
        )

        # Verify API was called
        assert mock_replicate_client.run_model_async.called
        call_args = mock_replicate_client.run_model_async.call_args

        # Verify model ID
        assert call_args.kwargs["model_id"] == VIDEO_MODELS["minimax"]

        # Verify input params
        input_params = call_args.kwargs["input_params"]
        assert "prompt" in input_params

        # Verify download was called
        assert mock_asset_manager.download_with_retry.called
        assert mock_asset_manager.validate_file.called

        # Verify return value
        assert video_path == "/tmp/scene_1.mp4"

    @pytest.mark.asyncio
    async def test_generate_scene_without_asset_manager(
        self,
        video_generator,
        mock_replicate_client,
        sample_scene_config
    ):
        """Test scene generation without asset manager returns URL"""
        mock_replicate_client.run_model_async.return_value = [
            "https://replicate.delivery/video.mp4"
        ]

        video_url = await video_generator.generate_scene(
            sample_scene_config,
            style="luxury",
            scene_id=1
        )

        # Should return URL directly
        assert video_url == "https://replicate.delivery/video.mp4"

    @pytest.mark.asyncio
    async def test_generate_scene_missing_template(
        self,
        video_generator,
        mock_asset_manager
    ):
        """Test scene generation with missing video_prompt_template"""
        invalid_config = {"id": 1, "type": "video"}

        with pytest.raises(VideoGenerationError, match="missing 'video_prompt_template'"):
            await video_generator.generate_scene(
                invalid_config,
                style="luxury",
                asset_manager=mock_asset_manager
            )

    @pytest.mark.asyncio
    async def test_generate_scene_api_failure(
        self,
        video_generator,
        mock_replicate_client,
        sample_scene_config,
        mock_asset_manager
    ):
        """Test scene generation with API failure"""
        mock_replicate_client.run_model_async.side_effect = Exception("API Error")

        with pytest.raises(VideoGenerationError, match="Failed to generate scene"):
            await video_generator.generate_scene(
                sample_scene_config,
                style="luxury",
                asset_manager=mock_asset_manager
            )

    @pytest.mark.asyncio
    async def test_generate_scene_with_product_image(
        self,
        video_generator,
        mock_replicate_client,
        sample_scene_config,
        mock_asset_manager,
        tmp_path
    ):
        """Test scene generation with product image"""
        # Create dummy product image
        product_image = tmp_path / "product.jpg"
        product_image.write_bytes(b"fake image")

        mock_replicate_client.run_model_async.return_value = [
            "https://replicate.delivery/video.mp4"
        ]
        mock_asset_manager.download_with_retry.return_value = "/tmp/scene_1.mp4"

        await video_generator.generate_scene(
            sample_scene_config,
            style="luxury",
            product_image_path=str(product_image),
            asset_manager=mock_asset_manager
        )

        # Verify API was called
        assert mock_replicate_client.run_model_async.called


class TestGenerateAllScenes:
    """Test batch scene generation"""

    @pytest.mark.asyncio
    async def test_generate_all_scenes_success(
        self,
        video_generator,
        mock_replicate_client,
        sample_script,
        mock_asset_manager
    ):
        """Test successful batch generation of all scenes"""
        # Mock API responses
        mock_replicate_client.run_model_async.return_value = [
            "https://replicate.delivery/video.mp4"
        ]
        mock_asset_manager.download_with_retry.side_effect = [
            "/tmp/scene_1.mp4",
            "/tmp/scene_2.mp4",
            "/tmp/scene_3.mp4"
        ]

        video_paths = await video_generator.generate_all_scenes(
            sample_script,
            style="luxury",
            asset_manager=mock_asset_manager
        )

        # Should generate 3 video scenes (scene 4 is image type)
        assert len(video_paths) == 3
        assert all("/tmp/scene_" in path for path in video_paths)

        # Verify API was called 3 times (once per video scene)
        assert mock_replicate_client.run_model_async.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_all_scenes_empty_script(
        self,
        video_generator,
        mock_asset_manager
    ):
        """Test batch generation with empty script"""
        empty_script = {"scenes": []}

        with pytest.raises(VideoGenerationError, match="contains no scenes"):
            await video_generator.generate_all_scenes(
                empty_script,
                style="luxury",
                asset_manager=mock_asset_manager
            )

    @pytest.mark.asyncio
    async def test_generate_all_scenes_only_images(
        self,
        video_generator,
        mock_asset_manager
    ):
        """Test batch generation with only image scenes"""
        image_only_script = {
            "scenes": [
                {"id": 1, "type": "image", "image_prompt_template": "CTA"}
            ]
        }

        video_paths = await video_generator.generate_all_scenes(
            image_only_script,
            style="luxury",
            asset_manager=mock_asset_manager
        )

        # Should return empty list (no video scenes)
        assert len(video_paths) == 0

    @pytest.mark.asyncio
    async def test_generate_all_scenes_partial_failure(
        self,
        video_generator,
        mock_replicate_client,
        sample_script,
        mock_asset_manager
    ):
        """Test batch generation with one scene failing"""
        # First call succeeds, second fails
        mock_replicate_client.run_model_async.side_effect = [
            ["https://replicate.delivery/video1.mp4"],
            Exception("API Error"),
            ["https://replicate.delivery/video3.mp4"]
        ]

        # Should raise error if any scene fails
        with pytest.raises(VideoGenerationError):
            await video_generator.generate_all_scenes(
                sample_script,
                style="luxury",
                asset_manager=mock_asset_manager
            )


class TestCompositeProductImage:
    """Test product image compositing (placeholder)"""

    @pytest.mark.asyncio
    async def test_composite_product_image_placeholder(self, video_generator):
        """Test that compositing is a placeholder for now"""
        # Should just return original video path
        result = await video_generator._composite_product_image(
            "/tmp/video.mp4",
            "/tmp/product.jpg",
            "luxury"
        )

        assert result == "/tmp/video.mp4"


class TestCreateVideoGenerator:
    """Test factory function"""

    def test_create_video_generator_default(self, mock_replicate_client):
        """Test factory with default model"""
        vg = create_video_generator(mock_replicate_client)

        assert vg.model_preference == "minimax"
        assert vg.model_id == VIDEO_MODELS["minimax"]

    def test_create_video_generator_custom_model(self, mock_replicate_client):
        """Test factory with custom model"""
        vg = create_video_generator(
            mock_replicate_client,
            model_preference="ltxv"
        )

        assert vg.model_preference == "ltxv"
        assert vg.model_id == VIDEO_MODELS["ltxv"]


class TestStyleConfigs:
    """Test style configuration constants"""

    def test_all_styles_defined(self):
        """Test that all required styles are defined"""
        required_styles = ["luxury", "energetic", "minimal", "bold"]
        for style in required_styles:
            assert style in STYLE_CONFIGS

    def test_style_config_structure(self):
        """Test that each style config has required fields"""
        required_fields = [
            "prompt_suffix",
            "duration",
            "fps",
            "aspect_ratio",
            "motion_intensity"
        ]

        for style, config in STYLE_CONFIGS.items():
            for field in required_fields:
                assert field in config, f"Style '{style}' missing '{field}'"

    def test_aspect_ratio_vertical(self):
        """Test that all styles use vertical 9:16 aspect ratio"""
        for config in STYLE_CONFIGS.values():
            assert config["aspect_ratio"] == "9:16"


class TestVideoModels:
    """Test video model configurations"""

    def test_all_models_defined(self):
        """Test that expected models are defined"""
        expected_models = ["minimax", "ltxv", "svd", "zeroscope", "hotshot"]
        for model in expected_models:
            assert model in VIDEO_MODELS

    def test_model_ids_format(self):
        """Test that model IDs follow expected format"""
        for model_id in VIDEO_MODELS.values():
            # Should be in format "owner/model-name"
            assert "/" in model_id
            parts = model_id.split("/")
            assert len(parts) == 2
            assert len(parts[0]) > 0  # owner
            assert len(parts[1]) > 0  # model name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
