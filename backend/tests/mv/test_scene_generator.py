"""
Tests for the scene generator module.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from mv.scene_generator import (
    Scene,
    SceneResponse,
    CreateScenesRequest,
    CreateScenesResponse,
    load_configs,
    get_default_parameters,
    generate_scenes,
)


class TestModels:
    """Test Pydantic models."""

    def test_scene_model(self):
        """Test Scene model creation."""
        scene = Scene(
            description="A test scene description",
            negative_description="No test elements"
        )
        assert scene.description == "A test scene description"
        assert scene.negative_description == "No test elements"

    def test_scene_response_model(self):
        """Test SceneResponse model creation."""
        scenes = [
            Scene(description="Scene 1", negative_description="No 1"),
            Scene(description="Scene 2", negative_description="No 2"),
        ]
        response = SceneResponse(scenes=scenes)
        assert len(response.scenes) == 2
        assert response.scenes[0].description == "Scene 1"

    def test_create_scenes_request_required_fields(self):
        """Test CreateScenesRequest with only required fields."""
        request = CreateScenesRequest(
            idea="Test idea",
            character_description="A test character"
        )
        assert request.idea == "Test idea"
        assert request.character_description == "A test character"
        assert request.number_of_scenes is None
        assert request.video_type is None

    def test_create_scenes_request_all_fields(self):
        """Test CreateScenesRequest with all fields."""
        request = CreateScenesRequest(
            idea="Test idea",
            character_description="A test character",
            character_characteristics="funny and witty",
            number_of_scenes=3,
            video_type="commercial",
            video_characteristics="professional, clean",
            camera_angle="side"
        )
        assert request.number_of_scenes == 3
        assert request.video_type == "commercial"


class TestConfigLoading:
    """Test configuration loading."""

    def test_get_default_parameters_fallback(self):
        """Test default parameters when config not loaded."""
        # Reset configs
        import mv.scene_generator as sg
        sg._parameters_config = {}

        defaults = get_default_parameters()
        assert "character_characteristics" in defaults
        assert "number_of_scenes" in defaults
        assert defaults["number_of_scenes"] == 4  # Default fallback

    @patch("mv.scene_generator.yaml.safe_load")
    @patch("builtins.open", mock_open())
    @patch("pathlib.Path.exists")
    def test_load_configs_success(self, mock_exists, mock_yaml_load):
        """Test successful config loading."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            "number_of_scenes": 6,
            "video_type": "music_video"
        }

        import mv.scene_generator as sg
        sg._parameters_config = {}
        sg._prompts_config = {}

        load_configs()

        # Config should be loaded (mock returns same for both calls)
        assert sg._parameters_config.get("number_of_scenes") == 6


class TestGenerateScenes:
    """Test scene generation function."""

    @patch("mv.scene_generator.settings")
    def test_generate_scenes_missing_api_key(self, mock_settings):
        """Test error when API key is missing."""
        mock_settings.GEMINI_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            generate_scenes(
                idea="Test idea",
                character_description="Test character"
            )

    @patch("mv.scene_generator.genai.Client")
    @patch("mv.scene_generator.settings")
    @patch("mv.scene_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_scenes_success(self, mock_makedirs, mock_settings, mock_client_class):
        """Test successful scene generation."""
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.MV_DEBUG_MODE = False

        # Mock Gemini client response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '''
        {
            "scenes": [
                {
                    "description": "A test scene",
                    "negative_description": "No test elements"
                }
            ]
        }
        '''
        mock_client.models.generate_content.return_value = mock_response

        scenes, output_files = generate_scenes(
            idea="Test idea",
            character_description="Test character"
        )

        assert len(scenes) == 1
        assert scenes[0].description == "A test scene"
        assert "json" in output_files
        assert "markdown" in output_files

        # Verify client was called
        mock_client.models.generate_content.assert_called_once()
        call_kwargs = mock_client.models.generate_content.call_args[1]
        assert call_kwargs["model"] == "gemini-2.5-pro"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
