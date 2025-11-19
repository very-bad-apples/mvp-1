"""
Tests for VideoComposer

Tests video composition functionality including:
- Audio-video synchronization
- Transitions
- CTA scene creation
- Background music mixing
- Export settings
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
import shutil

from pipeline.video_composer import (
    VideoComposer,
    VideoCompositionError,
    create_video_composer
)
from pipeline.asset_manager import AssetManager


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def asset_manager(temp_dir):
    """Create AssetManager for testing."""
    am = AssetManager(job_id="test-job", base_path=str(temp_dir))
    return am


@pytest.fixture
async def setup_asset_dirs(asset_manager):
    """Setup asset manager directories."""
    await asset_manager.create_job_directory()
    return asset_manager


@pytest.fixture
def mock_video_clip():
    """Mock MoviePy VideoFileClip."""
    mock_clip = MagicMock()
    mock_clip.duration = 5.0
    mock_clip.size = (1080, 1920)
    mock_clip.w = 1080
    mock_clip.h = 1920
    mock_clip.fps = 30
    mock_clip.audio = None
    mock_clip.get_frame = MagicMock(return_value=[[0, 0, 0]])
    mock_clip.subclip = MagicMock(return_value=mock_clip)
    mock_clip.set_audio = MagicMock(return_value=mock_clip)
    mock_clip.resize = MagicMock(return_value=mock_clip)
    mock_clip.close = MagicMock()
    return mock_clip


@pytest.fixture
def mock_audio_clip():
    """Mock MoviePy AudioFileClip."""
    mock_clip = MagicMock()
    mock_clip.duration = 5.0
    mock_clip.volumex = MagicMock(return_value=mock_clip)
    return mock_clip


@pytest.fixture
def mock_image_clip():
    """Mock MoviePy ImageClip."""
    mock_clip = MagicMock()
    mock_clip.duration = 4.0
    mock_clip.w = 1080
    mock_clip.h = 1920
    mock_clip.resize = MagicMock(return_value=mock_clip)
    mock_clip.set_fps = MagicMock(return_value=mock_clip)
    mock_clip.close = MagicMock()
    return mock_clip


class TestVideoComposer:
    """Test VideoComposer class."""

    def test_initialization(self):
        """Test VideoComposer initialization."""
        composer = VideoComposer()

        assert composer.asset_manager is None
        assert composer.default_settings["fps"] == 30
        assert composer.default_settings["codec"] == "libx264"
        assert composer.default_settings["target_resolution"] == (1080, 1920)

    def test_initialization_with_asset_manager(self, asset_manager):
        """Test initialization with AssetManager."""
        composer = VideoComposer(asset_manager=asset_manager)

        assert composer.asset_manager == asset_manager

    @pytest.mark.asyncio
    async def test_compose_video_validation_mismatch(self, asset_manager):
        """Test compose_video raises error when scenes/voiceovers mismatch."""
        composer = VideoComposer(asset_manager=asset_manager)

        with pytest.raises(VideoCompositionError) as exc_info:
            await composer.compose_video(
                video_scenes=["scene1.mp4", "scene2.mp4"],
                voiceovers=["vo1.mp3"],  # Only 1 voiceover for 2 scenes
                cta_image_path="cta.png"
            )

        assert "Mismatch" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_compose_video_validation_empty(self, asset_manager):
        """Test compose_video raises error when no scenes provided."""
        composer = VideoComposer(asset_manager=asset_manager)

        with pytest.raises(VideoCompositionError) as exc_info:
            await composer.compose_video(
                video_scenes=[],
                voiceovers=[],
                cta_image_path="cta.png"
            )

        assert "No video scenes" in str(exc_info.value)

    @patch('pipeline.video_composer.VideoFileClip')
    @patch('pipeline.video_composer.AudioFileClip')
    def test_load_video_clip(self, mock_audio_class, mock_video_class, mock_video_clip):
        """Test loading video clip."""
        mock_video_class.return_value = mock_video_clip
        composer = VideoComposer()

        clip = composer._load_video_clip("test.mp4")

        mock_video_class.assert_called_once_with("test.mp4")
        assert clip == mock_video_clip

    @patch('pipeline.video_composer.VideoFileClip')
    def test_load_video_clip_error(self, mock_video_class):
        """Test error handling when loading video fails."""
        mock_video_class.side_effect = Exception("File not found")
        composer = VideoComposer()

        with pytest.raises(VideoCompositionError) as exc_info:
            composer._load_video_clip("missing.mp4")

        assert "Failed to load video" in str(exc_info.value)

    @patch('pipeline.video_composer.VideoFileClip')
    @patch('pipeline.video_composer.AudioFileClip')
    @patch('pipeline.video_composer.ImageClip')
    @patch('pipeline.video_composer.concatenate_videoclips')
    def test_sync_audio_to_video_extend(
        self,
        mock_concat,
        mock_image_class,
        mock_audio_class,
        mock_video_class,
        mock_video_clip,
        mock_audio_clip,
        mock_image_clip
    ):
        """Test syncing audio when video is shorter (extends with freeze frame)."""
        # Setup: video 3s, audio 5s -> should extend video
        mock_video_clip.duration = 3.0
        mock_audio_clip.duration = 5.0

        mock_video_class.return_value = mock_video_clip
        mock_audio_class.return_value = mock_audio_clip
        mock_image_class.return_value = mock_image_clip
        mock_concat.return_value = mock_video_clip

        composer = VideoComposer()
        result = composer._sync_audio_to_video("video.mp4", "audio.mp3")

        # Should create freeze frame for 2 seconds
        mock_image_class.assert_called_once()
        call_args = mock_image_class.call_args
        assert call_args[1]['duration'] == 2.0  # 5s - 3s

        # Should concatenate original + freeze
        mock_concat.assert_called_once()

        # Should set audio
        mock_video_clip.set_audio.assert_called()

    @patch('pipeline.video_composer.VideoFileClip')
    @patch('pipeline.video_composer.AudioFileClip')
    def test_sync_audio_to_video_trim(
        self,
        mock_audio_class,
        mock_video_class,
        mock_video_clip,
        mock_audio_clip
    ):
        """Test syncing audio when video is longer (trims video)."""
        # Setup: video 5s, audio 3s -> should trim video
        mock_video_clip.duration = 5.0
        mock_audio_clip.duration = 3.0

        mock_video_class.return_value = mock_video_clip
        mock_audio_class.return_value = mock_audio_clip

        composer = VideoComposer()
        result = composer._sync_audio_to_video("video.mp4", "audio.mp3")

        # Should trim video to 3 seconds
        mock_video_clip.subclip.assert_called_once_with(0, 3.0)

        # Should set audio
        mock_video_clip.set_audio.assert_called()

    def test_add_transitions(self, mock_video_clip):
        """Test adding fade transitions between clips."""
        # Create 3 mock clips with fade methods
        clip1 = MagicMock()
        clip2 = MagicMock()
        clip3 = MagicMock()

        clip1.fadein = MagicMock(return_value=clip1)
        clip1.fadeout = MagicMock(return_value=clip1)
        clip2.fadein = MagicMock(return_value=clip2)
        clip2.fadeout = MagicMock(return_value=clip2)
        clip3.fadein = MagicMock(return_value=clip3)
        clip3.fadeout = MagicMock(return_value=clip3)

        clips = [clip1, clip2, clip3]

        composer = VideoComposer()
        result = composer._add_transitions(clips, transition_duration=0.5)

        # First clip: no fade in, has fade out
        clip1.fadein.assert_not_called()
        clip1.fadeout.assert_called_once()

        # Middle clip: has both
        clip2.fadein.assert_called_once()
        clip2.fadeout.assert_called_once()

        # Last clip: has fade in, no fade out
        clip3.fadein.assert_called_once()
        clip3.fadeout.assert_not_called()

        assert len(result) == 3

    @patch('pipeline.video_composer.ImageClip')
    def test_create_cta_scene(self, mock_image_class, mock_image_clip):
        """Test creating CTA scene from image."""
        mock_image_class.return_value = mock_image_clip
        mock_image_clip.w = 1080
        mock_image_clip.h = 1920

        composer = VideoComposer()
        result = composer._create_cta_scene("cta.png", duration=4.0)

        # Should create ImageClip with duration
        mock_image_class.assert_called_once_with("cta.png", duration=4.0)

        # Should resize to target resolution
        mock_image_clip.resize.assert_called()

    @patch('pipeline.video_composer.AudioFileClip')
    @patch('pipeline.video_composer.CompositeAudioClip')
    def test_add_background_music(
        self,
        mock_composite_class,
        mock_audio_class,
        mock_video_clip,
        mock_audio_clip
    ):
        """Test adding background music to video."""
        mock_video_clip.duration = 10.0
        mock_video_clip.audio = MagicMock()
        mock_audio_clip.duration = 10.0

        # Setup mock chain for volumex
        volumed_clip = MagicMock()
        mock_audio_clip.subclip = MagicMock(return_value=mock_audio_clip)
        mock_audio_clip.volumex = MagicMock(return_value=volumed_clip)

        mock_audio_class.return_value = mock_audio_clip
        mock_composite_audio = MagicMock()
        mock_composite_class.return_value = mock_composite_audio

        composer = VideoComposer()
        result = composer._add_background_music(
            mock_video_clip,
            "music.mp3",
            volume=0.1
        )

        # Should load music
        mock_audio_class.assert_called_once_with("music.mp3")

        # Should trim music to video duration
        mock_audio_clip.subclip.assert_called_once_with(0, 10.0)

        # Should adjust volume
        mock_audio_clip.volumex.assert_called_once_with(0.1)

        # Should create composite audio
        mock_composite_class.assert_called_once()

    def test_ensure_aspect_ratio_correct(self, mock_video_clip):
        """Test aspect ratio when already correct."""
        mock_video_clip.size = (1080, 1920)  # Already 9:16
        mock_video_clip.w = 1080
        mock_video_clip.h = 1920

        composer = VideoComposer()
        result = composer._ensure_aspect_ratio(mock_video_clip)

        # Should not resize if already correct
        assert result == mock_video_clip

    def test_ensure_aspect_ratio_wrong(self, mock_video_clip):
        """Test aspect ratio adjustment when wrong."""
        mock_video_clip.size = (1920, 1080)  # Wrong aspect ratio (16:9)
        mock_video_clip.w = 1920
        mock_video_clip.h = 1080

        composer = VideoComposer()
        result = composer._ensure_aspect_ratio(mock_video_clip)

        # Should resize
        mock_video_clip.resize.assert_called()

    @patch('pipeline.video_composer.VideoFileClip.write_videofile')
    def test_export_video(self, mock_write, mock_video_clip, temp_dir):
        """Test exporting video to file."""
        output_path = str(temp_dir / "output.mp4")

        # Create the file so validation passes
        Path(output_path).touch()

        composer = VideoComposer()

        # Mock write_videofile to avoid actual encoding
        mock_video_clip.write_videofile = MagicMock()

        result = composer._export_video(mock_video_clip, output_path)

        assert result == output_path
        mock_video_clip.write_videofile.assert_called_once()

        # Check export parameters
        call_kwargs = mock_video_clip.write_videofile.call_args[1]
        assert call_kwargs['fps'] == 30
        assert call_kwargs['codec'] == 'libx264'
        assert call_kwargs['audio_codec'] == 'aac'
        assert call_kwargs['preset'] == 'medium'
        assert call_kwargs['bitrate'] == '5000k'

    @patch('pipeline.video_composer.VideoFileClip')
    @patch('pipeline.video_composer.AudioFileClip')
    @patch('pipeline.video_composer.ImageClip')
    @patch('pipeline.video_composer.concatenate_videoclips')
    @pytest.mark.asyncio
    async def test_compose_video_full_flow(
        self,
        mock_concat,
        mock_image_class,
        mock_audio_class,
        mock_video_class,
        asset_manager,
        temp_dir,
        mock_video_clip,
        mock_audio_clip,
        mock_image_clip
    ):
        """Test full video composition flow (integration test with mocks)."""
        await asset_manager.create_job_directory()

        # Setup mocks
        mock_video_class.return_value = mock_video_clip
        mock_audio_class.return_value = mock_audio_clip
        mock_image_class.return_value = mock_image_clip

        # Mock concatenate to return a clip
        mock_concat.return_value = mock_video_clip

        # Mock fade functions on the clip itself
        mock_video_clip.fadein = MagicMock(return_value=mock_video_clip)
        mock_video_clip.fadeout = MagicMock(return_value=mock_video_clip)
        mock_image_clip.fadein = MagicMock(return_value=mock_image_clip)

        # Mock write_videofile
        def mock_write(*args, **kwargs):
            # Create the output file
            output_file = Path(args[0])
            output_file.touch()

        mock_video_clip.write_videofile = MagicMock(side_effect=mock_write)

        # Setup test data
        video_scenes = ["scene1.mp4", "scene2.mp4"]
        voiceovers = ["vo1.mp3", "vo2.mp3"]
        cta_image = "cta.png"

        composer = VideoComposer(asset_manager=asset_manager)

        # Run composition
        result = await composer.compose_video(
            video_scenes=video_scenes,
            voiceovers=voiceovers,
            cta_image_path=cta_image
        )

        # Verify result
        assert result is not None
        assert "final_video" in result
        assert Path(result).exists()

        # Verify clips were loaded
        assert mock_video_class.call_count == 2  # 2 scenes

        # Verify clips were concatenated
        assert mock_concat.call_count >= 1

        # Verify export was called
        mock_video_clip.write_videofile.assert_called()


class TestFactoryFunction:
    """Test factory function."""

    def test_create_video_composer(self):
        """Test creating VideoComposer with factory."""
        composer = create_video_composer()

        assert isinstance(composer, VideoComposer)
        assert composer.asset_manager is None

    def test_create_video_composer_with_asset_manager(self, asset_manager):
        """Test creating VideoComposer with AssetManager."""
        composer = create_video_composer(asset_manager=asset_manager)

        assert isinstance(composer, VideoComposer)
        assert composer.asset_manager == asset_manager


class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch('pipeline.video_composer.VideoFileClip')
    @patch('pipeline.video_composer.AudioFileClip')
    def test_audio_load_failure(self, mock_audio_class, mock_video_class, mock_video_clip):
        """Test handling when audio file fails to load."""
        mock_video_class.return_value = mock_video_clip
        mock_audio_class.side_effect = Exception("Audio file corrupted")

        composer = VideoComposer()

        with pytest.raises(VideoCompositionError) as exc_info:
            composer._sync_audio_to_video("video.mp4", "audio.mp3")

        assert "Failed to load audio" in str(exc_info.value)

    def test_add_transitions_empty_list(self):
        """Test transitions with empty clip list."""
        composer = VideoComposer()
        result = composer._add_transitions([])

        assert result == []

    def test_add_transitions_single_clip(self, mock_video_clip):
        """Test transitions with single clip (no transitions needed)."""
        composer = VideoComposer()
        result = composer._add_transitions([mock_video_clip])

        assert len(result) == 1

    @patch('pipeline.video_composer.ImageClip')
    def test_cta_scene_creation_error(self, mock_image_class):
        """Test error handling in CTA scene creation."""
        mock_image_class.side_effect = Exception("Image file not found")

        composer = VideoComposer()

        with pytest.raises(VideoCompositionError) as exc_info:
            composer._create_cta_scene("missing.png")

        assert "Failed to create CTA scene" in str(exc_info.value)

    @patch('pipeline.video_composer.AudioFileClip')
    def test_background_music_failure_non_critical(
        self,
        mock_audio_class,
        mock_video_clip
    ):
        """Test that background music failure doesn't crash composition."""
        mock_audio_class.side_effect = Exception("Music file error")

        composer = VideoComposer()

        # Should return original clip without crashing
        result = composer._add_background_music(mock_video_clip, "music.mp3")

        assert result == mock_video_clip

    @patch('pipeline.video_composer.VideoFileClip')
    def test_export_validation_failure(self, mock_video_class, mock_video_clip, temp_dir):
        """Test export validation when file not created."""
        output_path = str(temp_dir / "output.mp4")

        # Don't create file - validation should fail
        mock_video_clip.write_videofile = MagicMock()

        composer = VideoComposer()

        with pytest.raises(VideoCompositionError) as exc_info:
            composer._export_video(mock_video_clip, output_path)

        assert "Export failed" in str(exc_info.value)
