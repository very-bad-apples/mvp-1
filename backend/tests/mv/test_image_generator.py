"""
Tests for the image generator module.
"""

import base64
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest

from mv.image_generator import (
    CharacterReferenceImage,
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
        assert request.num_images == 4  # Default
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
            num_images=2,
            aspect_ratio="16:9",
            safety_filter_level="block_high_and_above",
            person_generation="dont_allow",
            output_format="jpg",
            negative_prompt="blurry, low quality",
            seed=12345
        )
        assert request.num_images == 2
        assert request.aspect_ratio == "16:9"
        assert request.safety_filter_level == "block_high_and_above"
        assert request.person_generation == "dont_allow"
        assert request.output_format == "jpg"
        assert request.negative_prompt == "blurry, low quality"
        assert request.seed == 12345

    def test_request_model_num_images_validation(self):
        """Test num_images validation (1-4 range)."""
        # Valid values
        for n in [1, 2, 3, 4]:
            request = GenerateCharacterReferenceRequest(
                character_description="test",
                num_images=n
            )
            assert request.num_images == n

        # Invalid values
        with pytest.raises(Exception):  # Pydantic ValidationError
            GenerateCharacterReferenceRequest(
                character_description="test",
                num_images=0
            )

        with pytest.raises(Exception):
            GenerateCharacterReferenceRequest(
                character_description="test",
                num_images=5
            )

    def test_character_reference_image_model(self):
        """Test CharacterReferenceImage model."""
        image = CharacterReferenceImage(
            id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            path="/path/to/image.png",
            base64="dGVzdA=="
        )
        assert image.id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert image.path == "/path/to/image.png"
        assert image.base64 == "dGVzdA=="

    def test_response_model(self):
        """Test GenerateCharacterReferenceResponse model creation."""
        images = [
            CharacterReferenceImage(
                id="uuid-1",
                path="/path/to/image1.png",
                base64="dGVzdDE="
            ),
            CharacterReferenceImage(
                id="uuid-2",
                path="/path/to/image2.png",
                base64="dGVzdDI="
            )
        ]
        response = GenerateCharacterReferenceResponse(
            images=images,
            metadata={
                "character_description": "test",
                "model_used": "google/imagen-4",
                "num_images_requested": 2,
                "num_images_generated": 2,
                "parameters_used": {},
                "generation_timestamp": "2025-11-15T14:30:25Z"
            }
        )
        assert len(response.images) == 2
        assert response.images[0].id == "uuid-1"
        assert response.metadata["num_images_generated"] == 2


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

    @patch("mv.image_generator.settings")
    def test_generate_invalid_num_images(self, mock_settings):
        """Test error when num_images out of range."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        with pytest.raises(ValueError, match="num_images must be between 1 and 4"):
            generate_character_reference_image(
                character_description="Test character",
                num_images=5
            )

        with pytest.raises(ValueError, match="num_images must be between 1 and 4"):
            generate_character_reference_image(
                character_description="Test character",
                num_images=0
            )

    @patch("mv.image_generator.uuid.uuid4")
    @patch("mv.image_generator.replicate.run")
    @patch("mv.image_generator.settings")
    @patch("mv.image_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_single_image(self, mock_makedirs, mock_settings, mock_replicate_run, mock_uuid):
        """Test generating a single image."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        # Reset config
        import mv.image_generator as ig
        ig._image_params_config = {}

        # Mock UUID
        mock_uuid.return_value = "test-uuid-1234"

        # Mock Replicate API response (single image per call)
        mock_file_output = MagicMock()
        mock_file_output.read.return_value = b"fake_image_data"
        mock_replicate_run.return_value = mock_file_output

        images, metadata = generate_character_reference_image(
            character_description="Test character",
            num_images=1
        )

        # Verify single image returned
        assert len(images) == 1
        assert images[0].id == "test-uuid-1234"
        assert "test-uuid-1234.png" in images[0].path
        expected_base64 = base64.b64encode(b"fake_image_data").decode("utf-8")
        assert images[0].base64 == expected_base64

        # Verify metadata
        assert metadata["character_description"] == "Test character"
        assert metadata["num_images_requested"] == 1
        assert metadata["num_images_generated"] == 1

        # Verify replicate.run was called once
        assert mock_replicate_run.call_count == 1

    @patch("mv.image_generator.uuid.uuid4")
    @patch("mv.image_generator.replicate.run")
    @patch("mv.image_generator.settings")
    @patch("mv.image_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_batch_images(self, mock_makedirs, mock_settings, mock_replicate_run, mock_uuid):
        """Test generating multiple images (batch via parallel calls)."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        import mv.image_generator as ig
        ig._image_params_config = {}

        # Mock UUIDs (called 4 times)
        mock_uuid.side_effect = ["uuid-1", "uuid-2", "uuid-3", "uuid-4"]

        # Mock Replicate API response - each call returns single image
        def mock_run_side_effect(*args, **kwargs):
            mock_output = MagicMock()
            # Each call gets unique data based on seed offset
            call_count = mock_replicate_run.call_count
            mock_output.read.return_value = f"fake_image_data_{call_count}".encode()
            return mock_output

        mock_replicate_run.side_effect = mock_run_side_effect

        images, metadata = generate_character_reference_image(
            character_description="Test character",
            num_images=4
        )

        # Verify 4 images returned
        assert len(images) == 4
        # UUIDs may be in any order due to parallel execution
        image_ids = [img.id for img in images]
        assert set(image_ids) == {"uuid-1", "uuid-2", "uuid-3", "uuid-4"}

        # Verify each has unique path
        paths = [img.path for img in images]
        assert len(set(paths)) == 4

        # Verify metadata
        assert metadata["num_images_requested"] == 4
        assert metadata["num_images_generated"] == 4

        # Verify replicate.run was called 4 times (parallel calls)
        assert mock_replicate_run.call_count == 4

    @patch("mv.image_generator.uuid.uuid4")
    @patch("mv.image_generator.replicate.run")
    @patch("mv.image_generator.settings")
    @patch("mv.image_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_with_custom_params(self, mock_makedirs, mock_settings, mock_replicate_run, mock_uuid):
        """Test image generation with custom parameters."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        import mv.image_generator as ig
        ig._image_params_config = {}

        mock_uuid.return_value = "custom-uuid"

        mock_file_output = MagicMock()
        mock_file_output.read.return_value = b"fake_image_data"
        mock_replicate_run.return_value = mock_file_output

        images, metadata = generate_character_reference_image(
            character_description="Custom character",
            num_images=1,
            aspect_ratio="16:9",
            safety_filter_level="block_high_and_above",
            person_generation="dont_allow",
            output_format="jpg",
            negative_prompt="blur",
            seed=42
        )

        # Verify custom parameters in metadata
        assert metadata["parameters_used"]["aspect_ratio"] == "16:9"
        assert metadata["parameters_used"]["safety_filter_level"] == "block_high_and_above"
        assert metadata["parameters_used"]["person_generation"] == "dont_allow"
        assert metadata["parameters_used"]["output_format"] == "jpg"
        assert metadata["parameters_used"]["negative_prompt"] == "blur"
        assert metadata["parameters_used"]["seed"] == 42

        # Verify filename extension matches output_format
        assert images[0].path.endswith(".jpg")

    @patch("mv.image_generator.uuid.uuid4")
    @patch("mv.image_generator.replicate.run")
    @patch("mv.image_generator.settings")
    @patch("mv.image_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_default_num_images(self, mock_makedirs, mock_settings, mock_replicate_run, mock_uuid):
        """Test that default num_images is 4."""
        mock_settings.REPLICATE_API_TOKEN = "test-token"
        mock_settings.REPLICATE_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        import mv.image_generator as ig
        ig._image_params_config = {}

        mock_uuid.side_effect = ["uuid-1", "uuid-2", "uuid-3", "uuid-4"]

        # Each call returns single image
        def mock_run_side_effect(*args, **kwargs):
            mock_output = MagicMock()
            mock_output.read.return_value = b"data"
            return mock_output

        mock_replicate_run.side_effect = mock_run_side_effect

        images, metadata = generate_character_reference_image(
            character_description="Test character"
            # num_images not specified, should default to 4
        )

        assert len(images) == 4
        assert metadata["num_images_requested"] == 4
        assert mock_replicate_run.call_count == 4

    def test_uuid_filename_format(self):
        """Test that UUID follows expected format."""
        import uuid
        test_uuid = str(uuid.uuid4())
        # Should be 36 characters with 4 hyphens
        assert len(test_uuid) == 36
        assert test_uuid.count("-") == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
