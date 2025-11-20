"""
Tests for the prompt parser module.

Tests loading config files (YAML/JSON), parsing templates, and generating prompts.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from mv.director.prompt_parser import (
    load_config,
    load_template,
    get_nested_value,
    format_array_value,
    parse_template,
    generate_prompt,
)


class TestLoadConfig:
    """Test config file loading."""

    def test_load_yaml_config(self):
        """Test loading a YAML config file."""
        config = load_config("Wes-Anderson")
        assert isinstance(config, dict)
        assert "camera" in config
        assert config["camera"]["shotType"] == "medium_shot"

    def test_load_json_config(self):
        """Test loading a JSON config file (if exists)."""
        # This test will pass if a JSON config exists, skip if not
        config_path = Path(__file__).parent.parent.parent / "mv" / "director" / "configs"
        json_files = list(config_path.glob("*.json"))
        if json_files:
            # Use first JSON file found
            config_name = json_files[0].stem
            config = load_config(config_name)
            assert isinstance(config, dict)
        else:
            pytest.skip("No JSON config files found")

    def test_load_nonexistent_config(self):
        """Test loading a non-existent config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config("NonExistentConfig")

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML raises ValueError."""
        with patch("builtins.open", mock_open(read_data="invalid: yaml: content: [")), \
             patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(ValueError):
                load_config("InvalidConfig")


class TestLoadTemplate:
    """Test template file loading."""

    def test_load_template(self):
        """Test loading the prompt template file."""
        template = load_template()
        assert isinstance(template, str)
        assert "{{camera.shotType}}" in template
        assert "Scene Creative Direction" in template

    def test_load_template_file_not_found(self):
        """Test loading template when file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                load_template()


class TestGetNestedValue:
    """Test nested value access."""

    def test_simple_key(self):
        """Test accessing a simple key."""
        data = {"key": "value"}
        assert get_nested_value(data, "key") == "value"

    def test_nested_key(self):
        """Test accessing a nested key."""
        data = {"camera": {"shotType": "medium_shot"}}
        assert get_nested_value(data, "camera.shotType") == "medium_shot"

    def test_deeply_nested_key(self):
        """Test accessing a deeply nested key."""
        data = {"audio": {"dialogue": {"tone": "calm"}}}
        assert get_nested_value(data, "audio.dialogue.tone") == "calm"

    def test_missing_key(self):
        """Test accessing a missing key returns None."""
        data = {"camera": {"shotType": "medium_shot"}}
        assert get_nested_value(data, "camera.missing") is None

    def test_missing_nested_key(self):
        """Test accessing a missing nested key returns None."""
        data = {"camera": {"shotType": "medium_shot"}}
        assert get_nested_value(data, "missing.key") is None

    def test_empty_path(self):
        """Test accessing with empty path returns None."""
        data = {"key": "value"}
        assert get_nested_value(data, "") is None


class TestFormatArrayValue:
    """Test array formatting."""

    def test_format_simple_array(self):
        """Test formatting a simple array."""
        arr = ["blurry", "low quality", "watermarks"]
        result = format_array_value(arr)
        assert result == "blurry, low quality, watermarks"

    def test_format_empty_array(self):
        """Test formatting an empty array."""
        arr = []
        result = format_array_value(arr)
        assert result == ""

    def test_format_single_item_array(self):
        """Test formatting an array with one item."""
        arr = ["blurry"]
        result = format_array_value(arr)
        assert result == "blurry"

    def test_format_non_array(self):
        """Test formatting a non-array value returns as-is."""
        value = "not an array"
        result = format_array_value(value)
        assert result == "not an array"


class TestParseTemplate:
    """Test template parsing."""

    def test_simple_placeholder(self):
        """Test replacing a simple placeholder."""
        template = "Camera: {{camera.shotType}} shot"
        config = {"camera": {"shotType": "medium_shot"}}
        result = parse_template(template, config)
        assert result == "Camera: medium_shot shot"

    def test_nested_placeholder(self):
        """Test replacing a nested placeholder."""
        template = "Audio: {{audio.dialogue.tone}} dialogue"
        config = {"audio": {"dialogue": {"tone": "calm"}}}
        result = parse_template(template, config)
        assert result == "Audio: calm dialogue"

    def test_array_placeholder(self):
        """Test replacing an array placeholder."""
        template = "Negative: {{quality.negativePrompts}}"
        config = {"quality": {"negativePrompts": ["blurry", "low quality"]}}
        result = parse_template(template, config)
        assert result == "Negative: blurry, low quality"

    def test_multiple_placeholders(self):
        """Test replacing multiple placeholders."""
        template = "Camera: {{camera.shotType}} with {{camera.lens}} lens"
        config = {
            "camera": {
                "shotType": "medium_shot",
                "lens": "standard"
            }
        }
        result = parse_template(template, config)
        assert result == "Camera: medium_shot with standard lens"

    def test_missing_value(self):
        """Test handling missing values (replaced with empty string)."""
        template = "Camera: {{camera.shotType}} shot"
        config = {"camera": {}}  # Missing shotType
        result = parse_template(template, config)
        assert result == "Camera:  shot"  # Empty string replacement

    def test_missing_nested_key(self):
        """Test handling missing nested keys."""
        template = "Audio: {{audio.dialogue.tone}}"
        config = {"audio": {}}  # Missing dialogue
        result = parse_template(template, config)
        assert result == "Audio: "  # Empty string replacement

    def test_empty_template(self):
        """Test parsing an empty template."""
        template = ""
        config = {"camera": {"shotType": "medium_shot"}}
        result = parse_template(template, config)
        assert result == ""

    def test_no_placeholders(self):
        """Test parsing template with no placeholders."""
        template = "This is a plain text template"
        config = {"camera": {"shotType": "medium_shot"}}
        result = parse_template(template, config)
        assert result == "This is a plain text template"

    def test_complex_template(self):
        """Test parsing a complex template with all placeholder types."""
        template = """Camera: {{camera.shotType}} shot with {{camera.lens}} lens.
Lighting: {{lighting.type}} lighting.
Negative: {{quality.negativePrompts}}"""
        config = {
            "camera": {
                "shotType": "medium_shot",
                "lens": "standard"
            },
            "lighting": {
                "type": "soft"
            },
            "quality": {
                "negativePrompts": ["blurry", "low quality"]
            }
        }
        result = parse_template(template, config)
        assert "medium_shot" in result
        assert "standard" in result
        assert "soft" in result
        assert "blurry, low quality" in result


class TestGeneratePrompt:
    """Test complete prompt generation."""

    def test_generate_prompt_with_existing_config(self):
        """Test generating a prompt from an existing config file."""
        # Use Wes-Anderson config which should exist
        prompt = generate_prompt("Wes-Anderson")
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Should contain parsed values
        assert "medium_shot" in prompt or "dolly" in prompt

    def test_generate_prompt_nonexistent_config(self):
        """Test generating prompt with non-existent config raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            generate_prompt("NonExistentConfig")

    def test_generate_prompt_real_template(self):
        """Test generating prompt with real template and config."""
        prompt = generate_prompt("Wes-Anderson")
        # Should contain expected sections from template
        assert "Camera:" in prompt or "Scene Creative Direction" in prompt
        # Should not contain placeholder syntax
        assert "{{" not in prompt
        assert "}}" not in prompt

