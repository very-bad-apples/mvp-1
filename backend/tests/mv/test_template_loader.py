"""
Tests for the template loader module.
"""

import pytest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
import yaml

from mv.template_loader import (
    TemplateError,
    load_mode_template,
    validate_template,
    get_available_modes,
    MODE_TEMPLATE_MAP,
)


class TestGetAvailableModes:
    """Test get_available_modes function."""

    def test_get_available_modes_returns_both(self):
        """Test that get_available_modes returns both modes."""
        modes = get_available_modes()
        assert len(modes) == 2
        assert "music-video" in modes
        assert "ad-creative" in modes
        assert modes == list(MODE_TEMPLATE_MAP.keys())


class TestLoadModeTemplate:
    """Test load_mode_template function."""

    def test_load_music_video_template_success(self):
        """Test successfully loading music video template."""
        template = load_mode_template("music-video")
        
        assert template is not None
        assert "prompt_template" in template
        assert "number_of_scenes" in template
        assert "video_characteristics" in template
        assert "camera_angle" in template
        assert "duration_per_scene" in template
        
        assert template["number_of_scenes"] == 8
        assert isinstance(template["prompt_template"], str)
        assert "{concept_prompt}" in template["prompt_template"]
        assert "{director_style_section}" in template["prompt_template"]

    def test_load_ad_creative_template_success(self):
        """Test successfully loading ad creative template."""
        template = load_mode_template("ad-creative")
        
        assert template is not None
        assert "prompt_template" in template
        assert "number_of_scenes" in template
        assert "video_characteristics" in template
        assert "camera_angle" in template
        assert "duration_per_scene" in template
        
        assert template["number_of_scenes"] == 4
        assert isinstance(template["prompt_template"], str)
        assert "{concept_prompt}" in template["prompt_template"]
        assert "{director_style_section}" in template["prompt_template"]

    def test_load_invalid_mode_raises_error(self):
        """Test that loading invalid mode raises TemplateError."""
        with pytest.raises(TemplateError) as exc_info:
            load_mode_template("invalid-mode")
        
        assert "Invalid mode" in str(exc_info.value)
        assert "invalid-mode" in str(exc_info.value)

    @patch("mv.template_loader.Path.exists")
    def test_load_missing_template_file_raises_error(self, mock_exists):
        """Test that missing template file raises TemplateError."""
        mock_exists.return_value = False
        
        with pytest.raises(TemplateError) as exc_info:
            load_mode_template("music-video")
        
        assert "Template file not found" in str(exc_info.value)

    @patch("mv.template_loader.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    def test_load_invalid_yaml_raises_error(self, mock_yaml_load, mock_file, mock_exists):
        """Test that invalid YAML raises TemplateError."""
        mock_exists.return_value = True
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")
        
        with pytest.raises(TemplateError) as exc_info:
            load_mode_template("music-video")
        
        assert "Failed to parse template YAML" in str(exc_info.value)


class TestValidateTemplate:
    """Test validate_template function."""

    def test_validate_template_with_all_required_fields(self):
        """Test validation passes with all required fields."""
        template = {
            "prompt_template": "Test prompt with {concept_prompt} and {personality_profile} and {video_characteristics} and {camera_angle} and {number_of_scenes} and {duration_per_scene} and {director_style_section}",
            "number_of_scenes": 8,
            "video_characteristics": "cinematic, 4k",
            "camera_angle": "dynamic",
            "duration_per_scene": 8.0,
        }
        
        # Should not raise
        validate_template(template, "music-video")

    def test_validate_template_missing_field_raises_error(self):
        """Test validation fails when required field is missing."""
        template = {
            "prompt_template": "Test",
            "number_of_scenes": 8,
            # Missing video_characteristics, camera_angle, duration_per_scene
        }
        
        with pytest.raises(TemplateError) as exc_info:
            validate_template(template, "music-video")
        
        assert "missing required fields" in str(exc_info.value).lower()

    def test_validate_template_none_raises_error(self):
        """Test validation fails when template is None."""
        with pytest.raises(TemplateError) as exc_info:
            validate_template(None, "music-video")
        
        assert "None or empty" in str(exc_info.value)

    def test_validate_template_prompt_not_string_raises_error(self):
        """Test validation fails when prompt_template is not a string."""
        template = {
            "prompt_template": 123,  # Should be string
            "number_of_scenes": 8,
            "video_characteristics": "cinematic",
            "camera_angle": "dynamic",
            "duration_per_scene": 8.0,
        }
        
        with pytest.raises(TemplateError) as exc_info:
            validate_template(template, "music-video")
        
        assert "prompt_template must be a string" in str(exc_info.value)

    def test_validate_template_number_of_scenes_not_int_raises_error(self):
        """Test validation fails when number_of_scenes is not an integer."""
        template = {
            "prompt_template": "Test {concept_prompt} {personality_profile} {video_characteristics} {camera_angle} {number_of_scenes} {duration_per_scene} {director_style_section}",
            "number_of_scenes": "8",  # Should be int
            "video_characteristics": "cinematic",
            "camera_angle": "dynamic",
            "duration_per_scene": 8.0,
        }
        
        with pytest.raises(TemplateError) as exc_info:
            validate_template(template, "music-video")
        
        assert "number_of_scenes must be an integer" in str(exc_info.value)

    def test_validate_template_number_of_scenes_less_than_one_raises_error(self):
        """Test validation fails when number_of_scenes < 1."""
        template = {
            "prompt_template": "Test {concept_prompt} {personality_profile} {video_characteristics} {camera_angle} {number_of_scenes} {duration_per_scene} {director_style_section}",
            "number_of_scenes": 0,  # Should be >= 1
            "video_characteristics": "cinematic",
            "camera_angle": "dynamic",
            "duration_per_scene": 8.0,
        }
        
        with pytest.raises(TemplateError) as exc_info:
            validate_template(template, "music-video")
        
        assert "number_of_scenes must be >= 1" in str(exc_info.value)

    def test_validate_template_duration_not_number_raises_error(self):
        """Test validation fails when duration_per_scene is not a number."""
        template = {
            "prompt_template": "Test {concept_prompt} {personality_profile} {video_characteristics} {camera_angle} {number_of_scenes} {duration_per_scene} {director_style_section}",
            "number_of_scenes": 8,
            "video_characteristics": "cinematic",
            "camera_angle": "dynamic",
            "duration_per_scene": "8.0",  # Should be number
        }
        
        with pytest.raises(TemplateError) as exc_info:
            validate_template(template, "music-video")
        
        assert "duration_per_scene must be a number" in str(exc_info.value)

    def test_validate_template_duration_zero_or_negative_raises_error(self):
        """Test validation fails when duration_per_scene <= 0."""
        template = {
            "prompt_template": "Test {concept_prompt} {personality_profile} {video_characteristics} {camera_angle} {number_of_scenes} {duration_per_scene} {director_style_section}",
            "number_of_scenes": 8,
            "video_characteristics": "cinematic",
            "camera_angle": "dynamic",
            "duration_per_scene": 0,  # Should be > 0
        }
        
        with pytest.raises(TemplateError) as exc_info:
            validate_template(template, "music-video")
        
        assert "duration_per_scene must be > 0" in str(exc_info.value)

    def test_validate_template_missing_placeholder_raises_error(self):
        """Test validation fails when prompt_template missing required placeholder."""
        template = {
            "prompt_template": "Test {concept_prompt} but missing {personality_profile}",  # Missing other placeholders
            "number_of_scenes": 8,
            "video_characteristics": "cinematic",
            "camera_angle": "dynamic",
            "duration_per_scene": 8.0,
        }
        
        with pytest.raises(TemplateError) as exc_info:
            validate_template(template, "music-video")
        
        assert "missing required placeholders" in str(exc_info.value).lower()

    def test_validate_template_accepts_float_duration(self):
        """Test validation accepts float for duration_per_scene."""
        template = {
            "prompt_template": "Test {concept_prompt} {personality_profile} {video_characteristics} {camera_angle} {number_of_scenes} {duration_per_scene} {director_style_section}",
            "number_of_scenes": 8,
            "video_characteristics": "cinematic",
            "camera_angle": "dynamic",
            "duration_per_scene": 8.5,  # Float is valid
        }
        
        # Should not raise
        validate_template(template, "music-video")

    def test_validate_template_accepts_int_duration(self):
        """Test validation accepts int for duration_per_scene."""
        template = {
            "prompt_template": "Test {concept_prompt} {personality_profile} {video_characteristics} {camera_angle} {number_of_scenes} {duration_per_scene} {director_style_section}",
            "number_of_scenes": 8,
            "video_characteristics": "cinematic",
            "camera_angle": "dynamic",
            "duration_per_scene": 8,  # Int is valid
        }
        
        # Should not raise
        validate_template(template, "music-video")


class TestTemplateError:
    """Test TemplateError exception."""

    def test_template_error_is_exception(self):
        """Test that TemplateError is an Exception."""
        assert issubclass(TemplateError, Exception)

    def test_template_error_can_be_raised(self):
        """Test that TemplateError can be raised and caught."""
        with pytest.raises(TemplateError):
            raise TemplateError("Test error")

