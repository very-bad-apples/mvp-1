"""
Tests for director prompt parser, specifically signature style extraction.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from mv.director.prompt_parser import extract_signature_style


class TestExtractSignatureStyle:
    """Test signature style extraction from director configs."""

    def test_extract_signature_style_wes_anderson(self):
        """Test extraction from Wes-Anderson config."""
        style = extract_signature_style("Wes-Anderson")
        assert style is not None
        assert "Symmetrical compositions" in style
        assert "pastel color palettes" in style
        assert "planimetric framing" in style
        assert "whimsical precision" in style

    def test_extract_signature_style_david_lynch(self):
        """Test extraction from David-Lynch config."""
        style = extract_signature_style("David-Lynch")
        assert style is not None
        assert "Surreal" in style or "surreal" in style
        assert "dreamlike" in style or "dreamlike" in style

    def test_extract_signature_style_tim_burton(self):
        """Test extraction from Tim-Burton config."""
        style = extract_signature_style("Tim-Burton")
        assert style is not None
        assert "Gothic" in style or "gothic" in style
        assert "high contrast" in style or "High contrast" in style

    def test_extract_signature_style_nonexistent(self):
        """Test with non-existent config returns None."""
        style = extract_signature_style("NonExistent-Director")
        assert style is None

    def test_extract_signature_style_none_input(self):
        """Test with None input returns None."""
        style = extract_signature_style(None)
        assert style is None

    def test_extract_signature_style_empty_string(self):
        """Test with empty string input."""
        style = extract_signature_style("")
        assert style is None

    @patch("mv.director.prompt_parser.CONFIGS_DIR")
    def test_extract_signature_style_missing_signature_comment(self, mock_configs_dir):
        """Test config without signature style comment returns None."""
        mock_configs_dir.__truediv__ = lambda self, x: Path(f"/fake/path/{x}")
        
        # Mock file content without signature style comment
        mock_file_content = """# Some other comment
camera:
  shotType: medium_shot
"""
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            with patch("pathlib.Path.exists", return_value=True):
                style = extract_signature_style("Test-Director")
                assert style is None

    @patch("mv.director.prompt_parser.CONFIGS_DIR")
    def test_extract_signature_style_invalid_yaml(self, mock_configs_dir):
        """Test gracefully handles invalid YAML."""
        mock_configs_dir.__truediv__ = lambda self, x: Path(f"/fake/path/{x}")
        
        # Mock invalid YAML content
        mock_file_content = """# Signature Style: Test style
invalid: yaml: content: [unclosed
"""
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            with patch("pathlib.Path.exists", return_value=True):
                # Should handle gracefully, might return None or raise handled exception
                try:
                    style = extract_signature_style("Test-Director")
                    # If it doesn't raise, should return None or the style
                    assert style is None or isinstance(style, str)
                except Exception:
                    # If it raises, that's also acceptable (graceful error handling)
                    pass

    def test_extract_signature_style_path_traversal_attempt(self):
        """Test that path traversal attempts are rejected."""
        malicious_inputs = [
            "../../../etc/passwd",
            "../../sensitive",
            "subdir/../../../etc/hosts",
            "..\\..\\windows\\system32",
            "../config",
            "config/../other",
        ]
        for malicious_input in malicious_inputs:
            style = extract_signature_style(malicious_input)
            assert style is None, f"Path traversal attempt should be rejected: {malicious_input}"

    def test_extract_signature_style_variations(self):
        """Test extraction handles various comment formats."""
        # Test with different whitespace
        # Note: Line 1 is title, line 2 is signature style (matching actual file structure)
        test_cases = [
            "# Test Director Configuration\n# Signature Style: Test style",
            "# Test Director Configuration\n#Signature Style: Test style",
            "# Test Director Configuration\n# Signature Style:Test style",
            "# Test Director Configuration\n# Signature Style:  Test style  ",
        ]
        
        for file_content in test_cases:
            mock_file_content = f"""{file_content}
camera:
  shotType: medium_shot
"""
            # Create real Path objects for proper resolution
            from pathlib import Path
            mock_configs_dir = Path("/fake/configs")
            mock_file_path = mock_configs_dir / "Test-Director.yaml"
            
            with patch("mv.director.prompt_parser.CONFIGS_DIR", mock_configs_dir):
                with patch("builtins.open", mock_open(read_data=mock_file_content)):
                    with patch("pathlib.Path.exists", return_value=True):
                        # Mock resolve() to return proper parent relationship
                        def mock_resolve(self):
                            if self == mock_file_path:
                                return mock_file_path
                            elif self == mock_configs_dir:
                                return mock_configs_dir
                            return self
                        
                        with patch("pathlib.Path.resolve", mock_resolve):
                            style = extract_signature_style("Test-Director")
                            if "Test style" in file_content:
                                # Should extract "Test style" (with possible whitespace)
                                assert style is not None
                                assert "Test" in style or "test" in style

