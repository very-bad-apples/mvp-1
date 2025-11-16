"""
Tests for the image generator module.
"""

import base64
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest

from mv.image_generator import (
    GenerateCharacterReferenceRequest,
    GenerateCharacterReferenceResponse,
    generate_character_reference_image,
    get_character_reference_prompt_template,
    get_default_image_parameters,
    load_image_configs,
)


class TestModels:
    """Test Pydantic models."""

    def test_request_model_required_fields(self):
        """Test GenerateCharacterReferenceRequest with only required fields."""
        request = GenerateCharacterReferenceRequest(
            character_description="A test character"
        )
        assert request.character_description == "A test character"
        assert request.aspect_ratio is None
        assert request.safety_filter_level is None
        assert request.person_generation is None
        assert request.output_format is None
        assert request.negative_prompt is None
        assert request.seed is None

    def test_request_model_all_fields(self):
        """Test GenerateCharacterReferenceRequest with all fields."""
        request = GenerateCharacterReferenceRequest(
            character_description="A test character",
            aspect_ratio="16:9",
            safety_filter_level="block_high_and_above",
            person_generation="dont_allow",
            output_format="jpg",
            negative_prompt="blurry, low quality",
            seed=12345
        )
        assert request.aspect_ratio == "16:9"
        assert request.safety_filter_level == "block_high_and_above"
        assert request.person_generation == "dont_allow"
        assert request.output_format == "jpg"
        assert request.negative_prompt == "blurry, low quality"
        assert request.seed == 12345

    def test_response_model(self):
        """Test GenerateCharacterReferenceResponse model creation."""
        response = GenerateCharacterReferenceResponse(
            image_base64="dGVzdA==",
            output_file="/path/to/image.png",
            metadata={
                "character_description": "test",
                "model_used": "google/imagen-4",
                "parameters_used": {},
                "generation_timestamp": "2025-11-15T14:30:25Z"
            }
        )
        assert response.image_base64 == "dGVzdA=="
        assert response.output_file == "/path/to/image.png"
        assert response.metadata["model_used"] == "google/imagen-4"


class TestConfigLoading:
    """Test configuration loading."""

    def test_get_default_image_parameters_fallback(self):
        """Test default parameters when config not loaded."""
        import mv.image_generator as ig
        ig._image_params_config = {}

        defaults = get_default_image_parameters()
        assert defaults["model"] == "google/imagen-4"
        assert defaults["aspect_ratio"] == "1:1"
        assert defaults["safety_filter_level"] == "block_medium_and_above"
        assert defaults["person_generation"] == "allow_adult"
        assert defaults["output_format"] == "png"

    def test_get_character_reference_prompt_template_fallback(self):
        """Test default prompt template when config not loaded."""
        import mv.image_generator as ig
        ig._image_prompts_config = {}

        template = get_character_reference_prompt_template()
        assert "full-body character reference image" in template
        assert "{character_description}" in template

    @patch("mv.image_generator.yaml.safe_load")
    @patch("builtins.open", mock_open())
    @patch("pathlib.Path.exists")
    def test_load_image_configs_success(self, mock_exists, mock_yaml_load):
        """Test successful config loading."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            "aspect_ratio": "16:9",
            "model": "custom/model"
        }

        import mv.image_generator as ig
        ig._image_params_config = {}
        ig._image_prompts_config = {}

        load_image_configs()

        # Config should be loaded (mock returns same for both calls)
        assert ig._image_params_config.get("aspect_ratio") == "16:9"


class TestGenerateCharacterReferenceImage:
    """Test character reference image generation function."""

    @patch("mv.image_generator.settings")
    def test_generate_missing_api_token(self, mock_settings):
        """Test error when API token is missing."""
        mock_settings.REPLICATE_API_TOKEN = ""
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        with pytest.raises(ValueError, match="REPLICATE_API_TOKEN"):
            generate_character_reference_image(
                character_description="Test character"
            )

    @patch("mv.image_generator.replicate.run")
    @patch("mv.image_generator.settings")
    @patch("mv.image_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_success(self, mock_makedirs, mock_settings, mock_replicate_run):
        """Test successful image generation."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        # Reset config to defaults to avoid test pollution
        import mv.image_generator as ig
        ig._image_params_config = {}

        # Mock Replicate API response
        mock_file_output = MagicMock()
        mock_file_output.read.return_value = b"fake_image_data"
        mock_replicate_run.return_value = [mock_file_output]

        image_base64, output_file, metadata = generate_character_reference_image(
            character_description="Test character"
        )

        # Verify base64 encoding
        expected_base64 = base64.b64encode(b"fake_image_data").decode("utf-8")
        assert image_base64 == expected_base64

        # Verify output file has timestamp pattern
        assert "character_ref_" in output_file
        assert output_file.endswith(".png")

        # Verify metadata
        assert metadata["character_description"] == "Test character"
        assert metadata["model_used"] == "google/imagen-4"
        assert "generation_timestamp" in metadata
        assert metadata["parameters_used"]["aspect_ratio"] == "1:1"

        # Verify replicate.run was called
        mock_replicate_run.assert_called_once()
        call_args = mock_replicate_run.call_args
        assert call_args[0][0] == "google/imagen-4"
        assert "prompt" in call_args[1]["input"]
        assert "Test character" in call_args[1]["input"]["prompt"]

    @patch("mv.image_generator.replicate.run")
    @patch("mv.image_generator.settings")
    @patch("mv.image_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_with_custom_params(self, mock_makedirs, mock_settings, mock_replicate_run):
        """Test image generation with custom parameters."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        mock_file_output = MagicMock()
        mock_file_output.read.return_value = b"fake_image_data"
        mock_replicate_run.return_value = mock_file_output  # Single output, not list

        image_base64, output_file, metadata = generate_character_reference_image(
            character_description="Custom character",
            aspect_ratio="16:9",
            safety_filter_level="block_high_and_above",
            person_generation="dont_allow",
            output_format="jpg",
            negative_prompt="blur",
            seed=42
        )

        # Verify custom parameters were used
        assert metadata["parameters_used"]["aspect_ratio"] == "16:9"
        assert metadata["parameters_used"]["safety_filter_level"] == "block_high_and_above"
        assert metadata["parameters_used"]["person_generation"] == "dont_allow"
        assert metadata["parameters_used"]["output_format"] == "jpg"
        assert metadata["parameters_used"]["negative_prompt"] == "blur"
        assert metadata["parameters_used"]["seed"] == 42

        # Verify filename extension matches output_format
        assert output_file.endswith(".jpg")

    def test_timestamp_filename_format(self):
        """Test that timestamp follows expected format."""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Should be 8 digits underscore 6 digits
        assert len(timestamp_str) == 15
        assert timestamp_str[8] == "_"
        assert timestamp_str[:8].isdigit()
        assert timestamp_str[9:].isdigit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
