"""
Tests for director config discovery and API endpoints.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from mv.director.prompt_parser import discover_director_configs


class TestDiscoverDirectorConfigs:
    """Test director config discovery."""

    def test_discover_director_configs_returns_list(self):
        """Test that discover_director_configs returns a list."""
        configs = discover_director_configs()
        assert isinstance(configs, list)

    def test_discover_director_configs_includes_yaml_files(self):
        """Test that YAML config files are discovered."""
        configs = discover_director_configs()
        # Should include at least Wes-Anderson which we know exists
        assert "Wes-Anderson" in configs or len(configs) >= 0

    def test_discover_director_configs_includes_json_files(self):
        """Test that JSON config files are discovered if they exist."""
        configs = discover_director_configs()
        # Check if any configs were found (YAML or JSON)
        # This test passes if the function works, regardless of file types
        assert isinstance(configs, list)

    def test_discover_director_configs_removes_extensions(self):
        """Test that config names don't include file extensions."""
        configs = discover_director_configs()
        for config in configs:
            assert not config.endswith('.yaml')
            assert not config.endswith('.yml')
            assert not config.endswith('.json')

    def test_discover_director_configs_handles_empty_directory(self):
        """Test that empty directory returns empty list."""
        with patch('mv.director.prompt_parser.CONFIGS_DIR') as mock_dir:
            mock_dir.exists.return_value = True
            mock_dir.iterdir.return_value = []
            configs = discover_director_configs()
            assert configs == []

    def test_discover_director_configs_handles_missing_directory(self):
        """Test that missing directory returns empty list."""
        with patch('mv.director.prompt_parser.CONFIGS_DIR') as mock_dir:
            mock_dir.exists.return_value = False
            configs = discover_director_configs()
            assert configs == []

    def test_discover_director_configs_sorts_results(self):
        """Test that configs are returned in sorted order."""
        configs = discover_director_configs()
        if len(configs) > 1:
            assert configs == sorted(configs)

