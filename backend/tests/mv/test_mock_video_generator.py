"""
Tests for the mock video generator module.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mv.mock_video_generator import (
    generate_mock_video,
    get_mock_videos_directory,
    list_available_mock_videos,
    select_random_mock_video,
    simulate_processing_delay,
)


class TestMockVideoDirectory:
    """Test mock video directory functions."""

    def test_get_mock_videos_directory(self):
        """Test getting the mock videos directory path."""
        mock_dir = get_mock_videos_directory()
        assert mock_dir.name == "mock"
        assert mock_dir.parent.name == "outputs"
        assert "mv" in str(mock_dir)

    @patch("mv.mock_video_generator.get_mock_videos_directory")
    def test_list_available_mock_videos_empty(self, mock_get_dir):
        """Test listing when no mock videos exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_get_dir.return_value = Path(tmpdir)
            videos = list_available_mock_videos()
            assert videos == []

    @patch("mv.mock_video_generator.get_mock_videos_directory")
    def test_list_available_mock_videos_with_files(self, mock_get_dir):
        """Test listing when mock videos exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create mock video files
            (tmppath / "video1.mp4").touch()
            (tmppath / "video2.mp4").touch()
            (tmppath / "not_a_video.txt").touch()  # Should be ignored

            mock_get_dir.return_value = tmppath
            videos = list_available_mock_videos()

            assert len(videos) == 2
            assert "video1.mp4" in videos
            assert "video2.mp4" in videos
            assert "not_a_video.txt" not in videos

    @patch("mv.mock_video_generator.list_available_mock_videos")
    def test_select_random_mock_video_no_videos(self, mock_list):
        """Test error when no mock videos available."""
        mock_list.return_value = []

        with pytest.raises(FileNotFoundError, match="No mock videos found"):
            select_random_mock_video()

    @patch("mv.mock_video_generator.list_available_mock_videos")
    def test_select_random_mock_video_success(self, mock_list):
        """Test random selection from available videos."""
        mock_list.return_value = ["video1.mp4", "video2.mp4", "video3.mp4"]

        selected = select_random_mock_video()
        assert selected in ["video1.mp4", "video2.mp4", "video3.mp4"]


class TestSimulateDelay:
    """Test processing delay simulation."""

    @patch("mv.mock_video_generator.settings")
    @patch("mv.mock_video_generator.time.sleep")
    def test_simulate_delay_range(self, mock_sleep, mock_settings):
        """Test that delay is within configured range."""
        mock_settings.MV_DEBUG_MODE = False
        mock_settings.MOCK_VIDEO_DELAY_MIN = 5.0
        mock_settings.MOCK_VIDEO_DELAY_MAX = 10.0

        # Run multiple times to check range
        for _ in range(10):
            delay = simulate_processing_delay()
            assert 5.0 <= delay <= 10.0

        # Verify sleep was called
        assert mock_sleep.call_count == 10

    @patch("mv.mock_video_generator.settings")
    @patch("mv.mock_video_generator.time.sleep")
    def test_simulate_delay_custom_range(self, mock_sleep, mock_settings):
        """Test that delay respects custom configured range."""
        mock_settings.MV_DEBUG_MODE = False
        mock_settings.MOCK_VIDEO_DELAY_MIN = 2.0
        mock_settings.MOCK_VIDEO_DELAY_MAX = 4.0

        # Run multiple times to check custom range
        for _ in range(10):
            delay = simulate_processing_delay()
            assert 2.0 <= delay <= 4.0

        # Verify sleep was called
        assert mock_sleep.call_count == 10

    @patch("mv.debug.log_mock_delay")
    @patch("mv.mock_video_generator.settings")
    @patch("mv.mock_video_generator.time.sleep")
    def test_simulate_delay_with_debug_logging(self, mock_sleep, mock_settings, mock_log):
        """Test delay simulation with debug mode enabled."""
        mock_settings.MV_DEBUG_MODE = True
        mock_settings.MOCK_VIDEO_DELAY_MIN = 5.0
        mock_settings.MOCK_VIDEO_DELAY_MAX = 10.0

        delay = simulate_processing_delay()
        mock_log.assert_called_once()
        call_arg = mock_log.call_args[0][0]
        assert 5.0 <= call_arg <= 10.0


class TestGenerateMockVideo:
    """Test mock video generation function."""

    @patch("mv.mock_video_generator.settings")
    @patch("mv.mock_video_generator.simulate_processing_delay")
    @patch("mv.mock_video_generator.select_random_mock_video")
    def test_generate_mock_video_success(
        self, mock_select, mock_delay, mock_settings
    ):
        """Test successful mock video generation."""
        mock_settings.MV_DEBUG_MODE = False
        mock_settings.MOCK_VID_GENS = True
        mock_select.return_value = "mock_video_1.mp4"
        mock_delay.return_value = 7.5

        video_id, video_path, video_url, metadata = generate_mock_video(
            prompt="Test prompt"
        )

        # Verify UUID format
        assert len(video_id) == 36
        assert video_id.count("-") == 4

        # Verify path points to mock directory
        assert "mock" in video_path
        assert "mock_video_1.mp4" in video_path

        # Verify URL format
        assert video_url == f"/api/mv/get_video/{video_id}"

        # Verify metadata
        assert metadata["prompt"] == "Test prompt"
        assert metadata["backend_used"] == "mock"
        assert metadata["model_used"] == "mock"
        assert metadata["is_mock"] is True
        assert metadata["mock_video_source"] == "mock_video_1.mp4"
        assert metadata["processing_time_seconds"] == 7.5
        assert "generation_timestamp" in metadata
        assert metadata["parameters_used"]["aspect_ratio"] == "16:9"
        assert metadata["parameters_used"]["duration"] == 8
        assert metadata["parameters_used"]["generate_audio"] is True

    @patch("mv.mock_video_generator.settings")
    @patch("mv.mock_video_generator.simulate_processing_delay")
    @patch("mv.mock_video_generator.select_random_mock_video")
    def test_generate_mock_video_with_custom_params(
        self, mock_select, mock_delay, mock_settings
    ):
        """Test mock video generation preserves custom parameters."""
        mock_settings.MV_DEBUG_MODE = False
        mock_settings.MOCK_VID_GENS = True
        mock_select.return_value = "mock_video_2.mp4"
        mock_delay.return_value = 6.2

        video_id, video_path, video_url, metadata = generate_mock_video(
            prompt="Custom prompt",
            negative_prompt="blur, noise",
            aspect_ratio="9:16",
            duration=12,
            generate_audio=False,
            seed=42,
            reference_image_base64="dGVzdA==",
        )

        # Verify custom parameters preserved
        assert metadata["parameters_used"]["aspect_ratio"] == "9:16"
        assert metadata["parameters_used"]["duration"] == 12
        assert metadata["parameters_used"]["generate_audio"] is False
        assert metadata["parameters_used"]["negative_prompt"] == "blur, noise"
        assert metadata["parameters_used"]["seed"] == 42
        assert metadata["has_reference_image"] is True

    @patch("mv.debug.log_mock_video_selected")
    @patch("mv.debug.log_mock_mode_enabled")
    @patch("mv.mock_video_generator.settings")
    @patch("mv.mock_video_generator.simulate_processing_delay")
    @patch("mv.mock_video_generator.select_random_mock_video")
    def test_generate_mock_video_with_debug_logging(
        self, mock_select, mock_delay, mock_settings, mock_log_enabled, mock_log_selected
    ):
        """Test mock video generation with debug mode."""
        mock_settings.MV_DEBUG_MODE = True
        mock_settings.MOCK_VID_GENS = True
        mock_select.return_value = "mock_video_1.mp4"
        mock_delay.return_value = 8.0

        video_id, video_path, video_url, metadata = generate_mock_video(
            prompt="Debug test"
        )

        mock_log_enabled.assert_called_once()
        mock_log_selected.assert_called_once_with("mock_video_1.mp4")

    @patch("mv.mock_video_generator.select_random_mock_video")
    def test_generate_mock_video_no_videos_error(self, mock_select):
        """Test error when no mock videos available."""
        mock_select.side_effect = FileNotFoundError("No mock videos found")

        with pytest.raises(FileNotFoundError, match="No mock videos found"):
            generate_mock_video(prompt="Test")


class TestMockModeToggle:
    """Test mock mode toggle functionality."""

    @patch("mv.video_generator.settings")
    @patch("mv.video_backends.get_video_backend")
    @patch("mv.video_generator.os.makedirs")
    @patch("builtins.open")
    def test_real_mode_when_mock_disabled(
        self, mock_open, mock_makedirs, mock_get_backend, mock_settings
    ):
        """Test that real backend is used when MOCK_VID_GENS is false."""
        mock_settings.MOCK_VID_GENS = False
        mock_settings.MV_DEBUG_MODE = False
        mock_settings.REPLICATE_API_TOKEN = "test"
        mock_settings.REPLICATE_API_KEY = ""

        mock_backend = MagicMock(return_value=b"fake_video")
        mock_get_backend.return_value = mock_backend

        from mv.video_generator import generate_video

        # Reset config
        import mv.video_generator as vg
        vg._video_params_config = {}

        # This would call real backend
        try:
            generate_video(prompt="Test")
        except Exception:
            pass  # May fail due to mocking, but should attempt real backend

        # Verify real backend was called (or attempted)
        mock_get_backend.assert_called_once()

    @patch("mv.video_generator.settings")
    @patch("mv.mock_video_generator.generate_mock_video")
    def test_mock_mode_when_mock_enabled(self, mock_generate, mock_settings):
        """Test that mock generator is used when MOCK_VID_GENS is true."""
        mock_settings.MOCK_VID_GENS = True

        mock_generate.return_value = (
            "uuid",
            "/path/to/mock.mp4",
            "/api/mv/get_video/uuid",
            {"is_mock": True}
        )

        from mv.video_generator import generate_video

        result = generate_video(prompt="Test")

        assert result[3]["is_mock"] is True
        mock_generate.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
