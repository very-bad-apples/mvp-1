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
    get_default_parameters,
    generate_scenes,
    generate_scenes_legacy,
)

# Alias for backward compatibility in tests
# Old tests use generate_scenes() but should use generate_scenes_legacy()
# For now, we'll update the tests to use the correct function
from unittest.mock import patch, MagicMock, mock_open


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

    @patch("mv.config_manager.get_config")
    def test_get_default_parameters_fallback(self, mock_get_config):
        """Test default parameters when config not loaded."""
        # Mock config manager to return empty dict (simulating no config loaded)
        mock_get_config.return_value = {}

        defaults = get_default_parameters()
        assert "character_characteristics" in defaults
        assert "number_of_scenes" in defaults
        assert defaults["number_of_scenes"] == 4  # Default fallback



class TestGenerateScenes:
    """Test scene generation function."""

    @patch("mv.scene_generator.settings")
    def test_generate_scenes_missing_api_key(self, mock_settings):
        """Test error when API key is missing."""
        mock_settings.GEMINI_API_KEY = ""
        mock_settings.MV_DEBUG_MODE = False

        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            generate_scenes_legacy(
                idea="Test idea",
                character_description="Test character"
            )

    @patch("mv.config_manager.get_config")
    @patch("mv.scene_generator.genai.Client")
    @patch("mv.scene_generator.settings")
    @patch("mv.scene_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_scenes_success(self, mock_makedirs, mock_settings, mock_client_class, mock_get_config):
        """Test successful scene generation."""
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.MV_DEBUG_MODE = False

        # Mock config manager
        mock_get_config.return_value = {
            "character_characteristics": "sarcastic, dramatic",
            "number_of_scenes": 4,
            "video_type": "video",
            "video_characteristics": "cinematic, 4k",
            "camera_angle": "front"
        }

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

        scenes, output_files = generate_scenes_legacy(
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


class TestDirectorConfigInjection:
    """Test director config injection into scene generation."""

    @patch("mv.director.prompt_parser.extract_signature_style")
    @patch("mv.config_manager.get_config")
    @patch("mv.scene_generator.genai.Client")
    @patch("mv.scene_generator.settings")
    @patch("mv.scene_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_scenes_with_director_config(self, mock_makedirs, mock_settings, mock_client_class, mock_get_config, mock_extract_style):
        """Test scene generation with director config injects style."""
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.MV_DEBUG_MODE = False

        # Mock config manager
        mock_get_config.return_value = {
            "character_characteristics": "test",
            "number_of_scenes": 1,
            "video_type": "video",
            "video_characteristics": "test",
            "camera_angle": "front",
            "scene_generation_prompt": "Test prompt template"
        }

        # Mock signature style extraction
        mock_extract_style.return_value = "Symmetrical compositions, pastel color palettes, planimetric framing, whimsical precision"

        # Mock Gemini client response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '''
        {
            "scenes": [
                {
                    "description": "A symmetrical shot of a character",
                    "negative_description": "No asymmetry"
                }
            ]
        }
        '''
        mock_client.models.generate_content.return_value = mock_response

        scenes, output_files = generate_scenes_legacy(
            idea="Test idea",
            character_description="Test character",
            director_config="Wes-Anderson"
        )

        assert len(scenes) == 1
        # Verify the prompt was enhanced with director style
        call_args = mock_client.models.generate_content.call_args
        # Check keyword arguments (contents is passed as keyword)
        prompt = call_args.kwargs.get("contents", call_args.args[0] if call_args.args else "")
        
        # Should contain director style injection
        assert "CREATIVE DIRECTION" in prompt
        assert "Symmetrical compositions" in prompt or "symmetrical" in prompt.lower()
        assert "pastel color palettes" in prompt or "pastel" in prompt.lower()

    @patch("mv.config_manager.get_config")
    @patch("mv.scene_generator.genai.Client")
    @patch("mv.scene_generator.settings")
    @patch("mv.scene_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_scenes_without_director_config(self, mock_makedirs, mock_settings, mock_client_class, mock_get_config):
        """Test backward compatibility - no director config."""
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

        scenes, output_files = generate_scenes_legacy(
            idea="Test idea",
            character_description="Test character",
            director_config=None  # No director config
        )

        assert len(scenes) == 1
        # Verify the prompt was NOT enhanced
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents", call_args.args[0] if call_args.args else "")
        
        # Should NOT contain director style injection
        assert "CREATIVE DIRECTION" not in prompt
        assert "Symmetrical compositions" not in prompt

    @patch("mv.config_manager.get_config")
    @patch("mv.scene_generator.genai.Client")
    @patch("mv.scene_generator.settings")
    @patch("mv.scene_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_scenes_with_nonexistent_director(self, mock_makedirs, mock_settings, mock_client_class, mock_get_config):
        """Test graceful handling of non-existent director config."""
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

        scenes, output_files = generate_scenes_legacy(
            idea="Test idea",
            character_description="Test character",
            director_config="NonExistent-Director"
        )

        # Should still generate scenes (graceful fallback)
        assert len(scenes) == 1
        # Should NOT contain director style injection (since config not found)
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents", call_args.args[0] if call_args.args else "")
        assert "CREATIVE DIRECTION" not in prompt

    @patch("mv.director.prompt_parser.extract_signature_style")
    @patch("mv.config_manager.get_config")
    @patch("mv.scene_generator.genai.Client")
    @patch("mv.scene_generator.settings")
    @patch("mv.scene_generator.os.makedirs")
    @patch("builtins.open", mock_open())
    def test_generate_scenes_with_config_flavor_and_director(self, mock_makedirs, mock_settings, mock_client_class, mock_get_config, mock_extract_style):
        """Test that config_flavor and director_config work independently."""
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.MV_DEBUG_MODE = False

        # Mock config manager
        mock_get_config.return_value = {
            "character_characteristics": "test",
            "number_of_scenes": 1,
            "video_type": "video",
            "video_characteristics": "test",
            "camera_angle": "front",
            "scene_generation_prompt": "Test prompt template"
        }

        # Mock signature style extraction
        mock_extract_style.return_value = "Symmetrical compositions, pastel color palettes, planimetric framing, whimsical precision"

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

        scenes, output_files = generate_scenes_legacy(
            idea="Test idea",
            character_description="Test character",
            config_flavor="default",  # Quick-gen workflow
            director_config="Wes-Anderson"  # Director config
        )

        # Should work with both parameters
        assert len(scenes) == 1
        # Should contain director style injection
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents", call_args.args[0] if call_args.args else "")
        assert "CREATIVE DIRECTION" in prompt


class TestGenerateScenesNew:
    """Test new simplified generate_scenes() function with mode-based templates."""

    @patch("mv.scene_generator.settings")
    def test_generate_scenes_missing_api_key(self, mock_settings):
        """Test error when API key is missing."""
        mock_settings.GEMINI_API_KEY = ""

        with pytest.raises(ValueError, match="GEMINI_API_KEY not configured"):
            generate_scenes(
                mode="music-video",
                concept_prompt="Test concept",
                personality_profile="Test personality"
            )

    @patch("mv.scene_generator.load_mode_template")
    @patch("mv.scene_generator.genai.Client")
    @patch("mv.scene_generator.settings")
    @patch("os.makedirs")
    def test_generate_scenes_music_video_mode(
        self, mock_makedirs, mock_settings, mock_client_class, mock_load_template
    ):
        """Test scene generation for music-video mode."""
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.MV_DEBUG_MODE = False

        # Mock template
        mock_template = {
            "prompt_template": "Generate {number_of_scenes} scenes for {concept_prompt} with {personality_profile}. Style: {video_characteristics}. Camera: {camera_angle}. Duration: {duration_per_scene}s. {director_style_section}",
            "number_of_scenes": 8,
            "video_characteristics": "cinematic, music video style",
            "camera_angle": "dynamic",
            "duration_per_scene": 8.0,
        }
        mock_load_template.return_value = mock_template

        # Mock Gemini response
        import json
        mock_client = MagicMock()
        scenes_data = [{"description": f"Scene {i+1}", "negative_description": f"No {i+1}"} for i in range(8)]
        mock_response = MagicMock()
        mock_response.text = json.dumps({"scenes": scenes_data})
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        scenes, output_files = generate_scenes(
            mode="music-video",
            concept_prompt="Indie band performing",
            personality_profile="Edgy, raw, authentic"
        )

        assert len(scenes) == 8
        assert "markdown" in output_files
        assert "json" in output_files
        mock_load_template.assert_called_once_with("music-video")

    @patch("mv.scene_generator.load_mode_template")
    @patch("mv.scene_generator.genai.Client")
    @patch("mv.scene_generator.settings")
    @patch("os.makedirs")
    def test_generate_scenes_ad_creative_mode(
        self, mock_makedirs, mock_settings, mock_client_class, mock_load_template
    ):
        """Test scene generation for ad-creative mode."""
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.MV_DEBUG_MODE = False

        # Mock template
        mock_template = {
            "prompt_template": "Generate {number_of_scenes} scenes for {concept_prompt} with {personality_profile}. Style: {video_characteristics}. Camera: {camera_angle}. Duration: {duration_per_scene}s. {director_style_section}",
            "number_of_scenes": 4,
            "video_characteristics": "professional commercial",
            "camera_angle": "front",
            "duration_per_scene": 8.0,
        }
        mock_load_template.return_value = mock_template

        # Mock Gemini response
        import json
        mock_client = MagicMock()
        scenes_data = [{"description": f"Scene {i+1}", "negative_description": f"No {i+1}"} for i in range(4)]
        mock_response = MagicMock()
        mock_response.text = json.dumps({"scenes": scenes_data})
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        scenes, output_files = generate_scenes(
            mode="ad-creative",
            concept_prompt="Product showcase",
            personality_profile="Eco-conscious, modern"
        )

        assert len(scenes) == 4
        mock_load_template.assert_called_once_with("ad-creative")

    @patch("mv.scene_generator.extract_signature_style")
    @patch("mv.scene_generator.load_mode_template")
    @patch("mv.scene_generator.genai.Client")
    @patch("mv.scene_generator.settings")
    @patch("os.makedirs")
    def test_generate_scenes_with_director_config(
        self, mock_makedirs, mock_settings, mock_client_class, mock_load_template, mock_extract_style
    ):
        """Test scene generation with director config."""
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.MV_DEBUG_MODE = False

        # Mock template
        mock_template = {
            "prompt_template": "Generate {number_of_scenes} scenes. {director_style_section}",
            "number_of_scenes": 8,
            "video_characteristics": "cinematic",
            "camera_angle": "dynamic",
            "duration_per_scene": 8.0,
        }
        mock_load_template.return_value = mock_template

        # Mock director style
        mock_extract_style.return_value = "Symmetrical compositions, pastel colors"

        # Mock Gemini response
        import json
        mock_client = MagicMock()
        scenes_data = [{"description": f"Scene {i+1}", "negative_description": f"No {i+1}"} for i in range(8)]
        mock_response = MagicMock()
        mock_response.text = json.dumps({"scenes": scenes_data})
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        scenes, _ = generate_scenes(
            mode="music-video",
            concept_prompt="Test concept",
            personality_profile="Test personality",
            director_config="Wes-Anderson"
        )

        assert len(scenes) == 8
        mock_extract_style.assert_called_once_with("Wes-Anderson")
        
        # Verify director style was injected into prompt
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents", "")
        assert "CREATIVE DIRECTION" in prompt
        assert "Symmetrical compositions" in prompt

    @patch("mv.scene_generator.load_mode_template")
    @patch("mv.scene_generator.genai.Client")
    @patch("mv.scene_generator.settings")
    @patch("os.makedirs")
    def test_generate_scenes_without_director_config(
        self, mock_makedirs, mock_settings, mock_client_class, mock_load_template
    ):
        """Test scene generation without director config."""
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.MV_DEBUG_MODE = False

        # Mock template
        mock_template = {
            "prompt_template": "Generate {number_of_scenes} scenes. {director_style_section}",
            "number_of_scenes": 8,
            "video_characteristics": "cinematic",
            "camera_angle": "dynamic",
            "duration_per_scene": 8.0,
        }
        mock_load_template.return_value = mock_template

        # Mock Gemini response
        import json
        mock_client = MagicMock()
        scenes_data = [{"description": f"Scene {i+1}", "negative_description": f"No {i+1}"} for i in range(8)]
        mock_response = MagicMock()
        mock_response.text = json.dumps({"scenes": scenes_data})
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        scenes, _ = generate_scenes(
            mode="music-video",
            concept_prompt="Test concept",
            personality_profile="Test personality"
        )

        assert len(scenes) == 8
        
        # Verify no director style section in prompt
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents", "")
        assert "CREATIVE DIRECTION" not in prompt

    @patch("mv.scene_generator.load_mode_template")
    def test_generate_scenes_invalid_mode_raises_error(self, mock_load_template):
        """Test that invalid mode raises TemplateError."""
        from mv.template_loader import TemplateError
        
        mock_load_template.side_effect = TemplateError("Invalid mode: invalid-mode")

        with pytest.raises(TemplateError):
            generate_scenes(
                mode="invalid-mode",
                concept_prompt="Test",
                personality_profile="Test"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
