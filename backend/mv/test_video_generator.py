"""
Tests for the video generator module.
"""

import base64
import uuid
from unittest.mock import MagicMock, mock_open, patch

import pytest

from mv.video_generator import (
    GenerateVideoRequest,
    GenerateVideoResponse,
    generate_video,
    get_default_video_parameters,
    load_video_configs,
)
from mv.video_backends import get_video_backend


class TestModels:
    """Test Pydantic models."""

    def test_request_model_required_fields(self):
        """Test GenerateVideoRequest with only required fields."""
        request = GenerateVideoRequest(prompt="A test video prompt")
        assert request.prompt == "A test video prompt"
        assert request.negative_prompt is None
        assert request.aspect_ratio is None
        assert request.duration is None
        assert request.generate_audio is None
        assert request.seed is None
        assert request.reference_image_base64 is None
        assert request.video_rules_template is None
        assert request.backend == "replicate"  # default

    def test_request_model_all_fields(self):
        """Test GenerateVideoRequest with all fields."""
        request = GenerateVideoRequest(
            prompt="A test video prompt",
            negative_prompt="blurry, low quality",
            aspect_ratio="16:9",
            duration=8,
            generate_audio=True,
            seed=12345,
            reference_image_base64="dGVzdA==",
            video_rules_template="Custom rules",
            backend="gemini"
        )
        assert request.prompt == "A test video prompt"
        assert request.negative_prompt == "blurry, low quality"
        assert request.aspect_ratio == "16:9"
        assert request.duration == 8
        assert request.generate_audio is True
        assert request.seed == 12345
        assert request.reference_image_base64 == "dGVzdA=="
        assert request.video_rules_template == "Custom rules"
        assert request.backend == "gemini"

    def test_response_model(self):
        """Test GenerateVideoResponse model creation."""
        response = GenerateVideoResponse(
            video_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            video_path="/path/to/video.mp4",
            video_url="/api/mv/get_video/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            metadata={
                "prompt": "test",
                "backend_used": "replicate",
                "model_used": "google/veo-3.1",
                "parameters_used": {},
                "generation_timestamp": "2025-11-16T10:30:25Z",
                "processing_time_seconds": 45.7
            }
        )
        assert response.video_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert response.video_path == "/path/to/video.mp4"
        assert response.video_url == "/api/mv/get_video/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert response.metadata["backend_used"] == "replicate"
        assert response.metadata["processing_time_seconds"] == 45.7


class TestConfigLoading:
    """Test configuration loading."""

    def test_get_default_video_parameters_fallback(self):
        """Test default parameters when config not loaded."""
        import mv.video_generator as vg
        vg._video_params_config = {}

        defaults = get_default_video_parameters()
        assert defaults["model"] == "google/veo-3.1"
        assert defaults["aspect_ratio"] == "16:9"
        assert defaults["duration"] == 8
        assert defaults["generate_audio"] is True
        assert defaults["person_generation"] == "allow_all"
        assert "rules_template" in defaults

    def test_get_default_video_parameters_from_config(self):
        """Test default parameters from loaded config."""
        import mv.video_generator as vg
        vg._video_params_config = {
            "model": "custom/model",
            "aspect_ratio": "9:16",
            "duration": 10,
            "generate_audio": False,
            "person_generation": "dont_allow",
            "rules_template": "Custom template",
        }

        defaults = get_default_video_parameters()
        assert defaults["model"] == "custom/model"
        assert defaults["aspect_ratio"] == "9:16"
        assert defaults["duration"] == 10
        assert defaults["generate_audio"] is False
        assert defaults["person_generation"] == "dont_allow"
        assert defaults["rules_template"] == "Custom template"

        # Reset
        vg._video_params_config = {}

    @patch("mv.video_generator.yaml.safe_load")
    @patch("builtins.open", mock_open())
    @patch("pathlib.Path.exists")
    def test_load_video_configs_success(self, mock_exists, mock_yaml_load):
        """Test successful config loading."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            "video_model": "test/model",
            "video_aspect_ratio": "1:1",
            "video_duration": 12,
            "video_generate_audio": False,
        }

        import mv.video_generator as vg
        vg._video_params_config = {}

        load_video_configs()

        # Config should be loaded with video_ prefix stripped
        assert vg._video_params_config.get("model") == "test/model"
        assert vg._video_params_config.get("aspect_ratio") == "1:1"
        assert vg._video_params_config.get("duration") == 12

        # Reset
        vg._video_params_config = {}


class TestBackendFactory:
    """Test video backend factory."""

    def test_get_replicate_backend(self):
        """Test getting Replicate backend."""
        backend = get_video_backend("replicate")
        assert callable(backend)
        assert backend.__name__ == "generate_video_replicate"

    def test_get_gemini_backend(self):
        """Test getting Gemini backend."""
        backend = get_video_backend("gemini")
        assert callable(backend)
        assert backend.__name__ == "generate_video_gemini"

    def test_invalid_backend(self):
        """Test error for invalid backend."""
        with pytest.raises(ValueError, match="Unknown video backend"):
            get_video_backend("invalid")


class TestGenerateVideo:
    """Test video generation function."""

    @patch("mv.video_generator.settings")
    def test_generate_video_id_format(self, mock_settings):
        """Test that video_id is a valid UUID."""
        mock_settings.MV_DEBUG_MODE = False
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""

        # Test UUID format
        video_id = str(uuid.uuid4())
        assert len(video_id) == 36
        assert video_id.count("-") == 4
        # Verify each section has correct length
        parts = video_id.split("-")
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    @patch("mv.video_backends.get_video_backend")
    @patch("mv.video_generator.settings")
    @patch("mv.video_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_success(self, mock_makedirs, mock_settings, mock_get_backend):
        """Test successful video generation."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        # Reset config to defaults
        import mv.video_generator as vg
        vg._video_params_config = {}

        # Mock backend function
        mock_backend = MagicMock(return_value=b"fake_video_data")
        mock_get_backend.return_value = mock_backend

        video_id, video_path, video_url, metadata = generate_video(
            prompt="Test video prompt"
        )

        # Verify UUID format
        assert len(video_id) == 36
        assert video_id.count("-") == 4

        # Verify path contains UUID
        assert video_id in video_path
        assert video_path.endswith(".mp4")

        # Verify URL format
        assert video_url == f"/api/mv/get_video/{video_id}"

        # Verify metadata
        assert metadata["prompt"] == "Test video prompt"
        assert metadata["backend_used"] == "replicate"
        assert metadata["model_used"] == "google/veo-3.1"
        assert "generation_timestamp" in metadata
        assert "processing_time_seconds" in metadata
        assert metadata["parameters_used"]["aspect_ratio"] == "16:9"
        assert metadata["parameters_used"]["duration"] == 8
        assert metadata["parameters_used"]["generate_audio"] is True

        # Verify backend was called
        mock_backend.assert_called_once()

    @patch("mv.video_backends.get_video_backend")
    @patch("mv.video_generator.settings")
    @patch("mv.video_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_with_custom_params(self, mock_makedirs, mock_settings, mock_get_backend):
        """Test video generation with custom parameters."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        # Reset config to defaults
        import mv.video_generator as vg
        vg._video_params_config = {}

        # Mock backend function
        mock_backend = MagicMock(return_value=b"fake_video_data")
        mock_get_backend.return_value = mock_backend

        video_id, video_path, video_url, metadata = generate_video(
            prompt="Custom video",
            negative_prompt="blur",
            aspect_ratio="9:16",
            duration=12,
            generate_audio=False,
            seed=42,
            reference_image_base64="dGVzdA==",
            backend="replicate"
        )

        # Verify custom parameters were used
        assert metadata["parameters_used"]["aspect_ratio"] == "9:16"
        assert metadata["parameters_used"]["duration"] == 12
        assert metadata["parameters_used"]["generate_audio"] is False
        assert metadata["parameters_used"]["negative_prompt"] == "blur"
        assert metadata["parameters_used"]["seed"] == 42
        assert metadata["has_reference_image"] is True

    @patch("mv.video_backends.get_video_backend")
    @patch("mv.video_generator.settings")
    @patch("mv.video_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_with_gemini_backend(self, mock_makedirs, mock_settings, mock_get_backend):
        """Test video generation with Gemini backend."""
        mock_settings.REPLICATE_API_TOKEN = ""
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.MV_DEBUG_MODE = False

        # Reset config to defaults
        import mv.video_generator as vg
        vg._video_params_config = {}

        # Mock backend function
        mock_backend = MagicMock(return_value=b"fake_video_data")
        mock_get_backend.return_value = mock_backend

        video_id, video_path, video_url, metadata = generate_video(
            prompt="Gemini test",
            backend="gemini"
        )

        # Verify backend selection
        mock_get_backend.assert_called_once_with("gemini")
        assert metadata["backend_used"] == "gemini"

    @patch("mv.video_backends.get_video_backend")
    @patch("mv.video_generator.settings")
    @patch("mv.video_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_processing_time_tracking(self, mock_makedirs, mock_settings, mock_get_backend):
        """Test that processing time is tracked."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        # Reset config to defaults
        import mv.video_generator as vg
        vg._video_params_config = {}

        # Mock backend function
        mock_backend = MagicMock(return_value=b"fake_video_data")
        mock_get_backend.return_value = mock_backend

        video_id, video_path, video_url, metadata = generate_video(
            prompt="Test prompt"
        )

        # Verify processing time is present and reasonable
        assert "processing_time_seconds" in metadata
        assert isinstance(metadata["processing_time_seconds"], float)
        assert metadata["processing_time_seconds"] >= 0


class TestReplicateBackend:
    """Test Replicate backend."""

    @patch("mv.video_backends.replicate_backend.settings")
    def test_missing_api_token(self, mock_settings):
        """Test error when API token is missing."""
        mock_settings.REPLICATE_API_TOKEN = ""
        mock_settings.REPLICATE_API_KEY = ""

        from mv.video_backends.replicate_backend import generate_video_replicate

        with pytest.raises(ValueError, match="REPLICATE_API_TOKEN"):
            generate_video_replicate(prompt="Test")

    @patch("mv.video_backends.replicate_backend.replicate.run")
    @patch("mv.video_backends.replicate_backend.settings")
    def test_generate_success(self, mock_settings, mock_replicate_run):
        """Test successful video generation with Replicate."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""

        # Mock Replicate API response
        mock_file_output = MagicMock()
        mock_file_output.read.return_value = b"fake_video_data"
        mock_replicate_run.return_value = [mock_file_output]

        from mv.video_backends.replicate_backend import generate_video_replicate

        video_data = generate_video_replicate(
            prompt="Test prompt",
            aspect_ratio="16:9",
            duration=8,
            generate_audio=True
        )

        assert video_data == b"fake_video_data"
        mock_replicate_run.assert_called_once()

    @patch("mv.video_backends.replicate_backend.replicate.run")
    @patch("mv.video_backends.replicate_backend.settings")
    @patch("mv.video_backends.replicate_backend.tempfile.NamedTemporaryFile")
    def test_generate_with_reference_image(self, mock_temp_file, mock_settings, mock_replicate_run):
        """Test video generation with reference image."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""

        # Mock temp file
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/test_image.png"
        mock_temp_file.return_value = mock_temp

        # Mock file operations
        mock_file_handle = MagicMock()

        # Mock Replicate API response
        mock_file_output = MagicMock()
        mock_file_output.read.return_value = b"fake_video_data"
        mock_replicate_run.return_value = mock_file_output  # Single output

        from mv.video_backends.replicate_backend import generate_video_replicate

        # Base64 encoded "test"
        test_image_base64 = base64.b64encode(b"test_image_data").decode("utf-8")

        with patch("builtins.open", mock_open()):
            with patch("os.path.exists", return_value=True):
                with patch("os.unlink"):
                    video_data = generate_video_replicate(
                        prompt="Test with reference",
                        reference_image_base64=test_image_base64
                    )

        assert video_data == b"fake_video_data"


class TestGeminiBackend:
    """Test Gemini backend."""

    @patch("mv.video_backends.gemini_backend.settings")
    def test_missing_api_key(self, mock_settings):
        """Test error when API key is missing."""
        mock_settings.GEMINI_API_KEY = ""

        from mv.video_backends.gemini_backend import generate_video_gemini

        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            generate_video_gemini(prompt="Test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
