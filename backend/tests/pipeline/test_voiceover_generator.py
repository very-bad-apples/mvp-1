"""
Tests for VoiceoverGenerator

Tests cover:
- Single voiceover generation
- Batch generation from script
- Duration validation
- Voice selection
- Error handling
- API retry logic
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pipeline.voiceover_generator import (
    VoiceoverGenerator,
    VoiceoverGenerationError,
    create_voiceover_generator
)
from pipeline.asset_manager import AssetManager


@pytest.fixture
def mock_api_key():
    """Provide a mock API key"""
    return "test-api-key-123"


@pytest.fixture
def mock_asset_manager():
    """Create a mock AssetManager"""
    am = Mock(spec=AssetManager)
    am.job_id = "test-job-123"
    am.audio_dir = Path("/tmp/test-job-123/audio")

    # Mock save_file to return a path
    async def mock_save_file(content, filename, subdir=None):
        return f"/tmp/test-job-123/audio/{filename}"

    am.save_file = AsyncMock(side_effect=mock_save_file)
    return am


@pytest.fixture
def voiceover_generator(mock_api_key):
    """Create VoiceoverGenerator with mock API key"""
    with patch('pipeline.voiceover_generator.settings') as mock_settings:
        mock_settings.ELEVENLABS_API_KEY = mock_api_key
        mock_settings.ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

        # Mock ElevenLabs client
        with patch('pipeline.voiceover_generator.ElevenLabs'):
            generator = VoiceoverGenerator(api_key=mock_api_key)
            return generator


class TestVoiceoverGeneratorInit:
    """Test VoiceoverGenerator initialization"""

    def test_init_with_api_key(self, mock_api_key):
        """Test initialization with API key"""
        with patch('pipeline.voiceover_generator.ElevenLabs'):
            generator = VoiceoverGenerator(api_key=mock_api_key)
            assert generator.api_key == mock_api_key
            assert generator.default_voice_id == "EXAVITQu4vr4xnSDxMaL"

    def test_init_without_api_key(self):
        """Test that missing API key raises ValueError"""
        with patch('pipeline.voiceover_generator.settings') as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = ""

            with pytest.raises(ValueError, match="ELEVENLABS_API_KEY not configured"):
                VoiceoverGenerator()

    def test_init_with_custom_voice(self, mock_api_key):
        """Test initialization with custom voice ID"""
        custom_voice = "custom-voice-id"
        with patch('pipeline.voiceover_generator.ElevenLabs'):
            generator = VoiceoverGenerator(api_key=mock_api_key, voice_id=custom_voice)
            assert generator.default_voice_id == custom_voice


class TestVoiceSelection:
    """Test voice selection for different styles"""

    def test_get_voice_for_luxury(self, voiceover_generator):
        """Test voice selection for luxury style"""
        voice_id = voiceover_generator.get_voice_for_style("luxury")
        assert voice_id == "EXAVITQu4vr4xnSDxMaL"  # Sarah

    def test_get_voice_for_energetic(self, voiceover_generator):
        """Test voice selection for energetic style"""
        voice_id = voiceover_generator.get_voice_for_style("energetic")
        assert voice_id == "ErXwobaYiN019PkySvjV"  # Antoni

    def test_get_voice_for_minimal(self, voiceover_generator):
        """Test voice selection for minimal style"""
        voice_id = voiceover_generator.get_voice_for_style("minimal")
        assert voice_id == "21m00Tcm4TlvDq8ikWAM"  # Rachel

    def test_get_voice_for_bold(self, voiceover_generator):
        """Test voice selection for bold style"""
        voice_id = voiceover_generator.get_voice_for_style("bold")
        assert voice_id == "pNInz6obpgDQGcFmaJgB"  # Adam

    def test_get_voice_for_unknown_style(self, voiceover_generator):
        """Test voice selection for unknown style returns default"""
        voice_id = voiceover_generator.get_voice_for_style("unknown")
        assert voice_id == "EXAVITQu4vr4xnSDxMaL"  # Default


class TestVoiceoverGeneration:
    """Test voiceover generation"""

    @pytest.mark.asyncio
    async def test_generate_voiceover_success(self, voiceover_generator, mock_asset_manager):
        """Test successful voiceover generation"""
        # Mock the ElevenLabs API call
        mock_audio_data = b"mock audio data"

        with patch.object(
            voiceover_generator,
            '_call_elevenlabs_with_retry',
            return_value=AsyncMock()
        ):
            with patch('pipeline.voiceover_generator.save') as mock_save:
                with patch('builtins.open', create=True) as mock_open:
                    mock_file = MagicMock()
                    mock_file.read.return_value = mock_audio_data
                    mock_file.__enter__.return_value = mock_file
                    mock_open.return_value = mock_file

                    with patch('pathlib.Path.unlink'):
                        audio_path = await voiceover_generator.generate_voiceover(
                            text="Hello world",
                            asset_manager=mock_asset_manager,
                            scene_number=1
                        )

                        assert audio_path.startswith("/tmp/test-job-123/audio/")
                        assert "scene_1_voiceover" in audio_path
                        assert audio_path.endswith(".mp3")

                        # Verify save was called
                        mock_asset_manager.save_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_voiceover_with_duration(self, voiceover_generator, mock_asset_manager):
        """Test voiceover generation with duration validation"""
        mock_audio_data = b"mock audio data"

        with patch.object(
            voiceover_generator,
            '_call_elevenlabs_with_retry',
            return_value=AsyncMock()
        ):
            with patch('pipeline.voiceover_generator.save'):
                with patch('builtins.open', create=True) as mock_open:
                    mock_file = MagicMock()
                    mock_file.read.return_value = mock_audio_data
                    mock_file.__enter__.return_value = mock_file
                    mock_open.return_value = mock_file

                    with patch('pathlib.Path.unlink'):
                        # Mock duration validation
                        with patch.object(
                            voiceover_generator,
                            '_validate_audio_duration',
                            return_value=True
                        ) as mock_validate:
                            audio_path = await voiceover_generator.generate_voiceover(
                                text="Hello world",
                                asset_manager=mock_asset_manager,
                                target_duration=2.0,
                                scene_number=1
                            )

                            # Verify duration validation was called
                            mock_validate.assert_called_once()
                            assert audio_path is not None

    @pytest.mark.asyncio
    async def test_generate_voiceover_api_error(self, voiceover_generator, mock_asset_manager):
        """Test handling of API errors"""
        with patch.object(
            voiceover_generator,
            '_call_elevenlabs_with_retry',
            side_effect=Exception("API Error")
        ):
            with pytest.raises(VoiceoverGenerationError, match="Failed to generate voiceover"):
                await voiceover_generator.generate_voiceover(
                    text="Hello world",
                    asset_manager=mock_asset_manager
                )


class TestBatchGeneration:
    """Test batch voiceover generation"""

    @pytest.mark.asyncio
    async def test_generate_all_voiceovers_success(self, voiceover_generator, mock_asset_manager):
        """Test successful batch generation"""
        script = {
            "scenes": [
                {"voiceover_text": "Scene 1 text", "duration": 8},
                {"voiceover_text": "Scene 2 text", "duration": 8},
                {"voiceover_text": "Scene 3 text", "duration": 10},
                {"voiceover_text": "Scene 4 text", "duration": 4}
            ]
        }

        # Mock generate_voiceover to return paths
        async def mock_generate(text, asset_manager, target_duration=None, voice_id=None, scene_number=None):
            return f"/tmp/test-job-123/audio/scene_{scene_number}_voiceover.mp3"

        with patch.object(
            voiceover_generator,
            'generate_voiceover',
            side_effect=mock_generate
        ):
            audio_paths = await voiceover_generator.generate_all_voiceovers(
                script=script,
                asset_manager=mock_asset_manager
            )

            assert len(audio_paths) == 4
            assert all("scene_" in path for path in audio_paths)
            assert all(path.endswith(".mp3") for path in audio_paths)

    @pytest.mark.asyncio
    async def test_generate_all_voiceovers_with_style(self, voiceover_generator, mock_asset_manager):
        """Test batch generation with style"""
        script = {
            "scenes": [
                {"voiceover_text": "Scene 1 text", "duration": 8}
            ]
        }

        async def mock_generate(text, asset_manager, target_duration=None, voice_id=None, scene_number=None):
            # Verify correct voice was selected
            assert voice_id == "EXAVITQu4vr4xnSDxMaL"  # Sarah for luxury
            return f"/tmp/test-job-123/audio/scene_{scene_number}_voiceover.mp3"

        with patch.object(
            voiceover_generator,
            'generate_voiceover',
            side_effect=mock_generate
        ):
            audio_paths = await voiceover_generator.generate_all_voiceovers(
                script=script,
                asset_manager=mock_asset_manager,
                style="luxury"
            )

            assert len(audio_paths) == 1

    @pytest.mark.asyncio
    async def test_generate_all_voiceovers_empty_script(self, voiceover_generator, mock_asset_manager):
        """Test batch generation with empty script"""
        script = {"scenes": []}

        with pytest.raises(VoiceoverGenerationError, match="No scenes found"):
            await voiceover_generator.generate_all_voiceovers(
                script=script,
                asset_manager=mock_asset_manager
            )


class TestDurationValidation:
    """Test audio duration validation"""

    @pytest.mark.asyncio
    async def test_validate_audio_duration_success(self, voiceover_generator):
        """Test duration validation when audio matches target"""
        with patch('pipeline.voiceover_generator.AudioSegment') as mock_audio:
            # Mock audio segment with 8 seconds duration (8000ms)
            mock_segment = MagicMock()
            mock_segment.__len__.return_value = 8000
            mock_audio.from_mp3.return_value = mock_segment

            is_valid = await voiceover_generator._validate_audio_duration(
                audio_path="/tmp/test.mp3",
                target_duration=8.0,
                tolerance=0.5
            )

            assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_audio_duration_failure(self, voiceover_generator):
        """Test duration validation when audio doesn't match target"""
        with patch('pipeline.voiceover_generator.AudioSegment') as mock_audio:
            # Mock audio segment with 10 seconds duration (10000ms)
            mock_segment = MagicMock()
            mock_segment.__len__.return_value = 10000
            mock_audio.from_mp3.return_value = mock_segment

            is_valid = await voiceover_generator._validate_audio_duration(
                audio_path="/tmp/test.mp3",
                target_duration=8.0,
                tolerance=0.5
            )

            assert is_valid is False

    @pytest.mark.asyncio
    async def test_get_audio_duration(self, voiceover_generator):
        """Test getting audio duration"""
        with patch('pipeline.voiceover_generator.AudioSegment') as mock_audio:
            # Mock audio segment with 5.5 seconds duration (5500ms)
            mock_segment = MagicMock()
            mock_segment.__len__.return_value = 5500
            mock_audio.from_mp3.return_value = mock_segment

            duration = await voiceover_generator.get_audio_duration("/tmp/test.mp3")

            assert duration == 5.5


class TestRetryLogic:
    """Test API retry logic"""

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, voiceover_generator):
        """Test retry on rate limit error"""
        # Mock API to fail twice then succeed
        call_count = 0

        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                error = Exception("Rate limit")
                error.status_code = 429
                raise error
            return MagicMock()

        with patch.object(
            voiceover_generator.client.text_to_speech,
            'convert',
            side_effect=mock_api_call
        ):
            result = await voiceover_generator._call_elevenlabs_with_retry(
                text="Test",
                voice_id="test-voice"
            )

            assert result is not None
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, voiceover_generator):
        """Test that retries are exhausted and error is raised"""
        def mock_api_call(*args, **kwargs):
            error = Exception("Server error")
            error.status_code = 500
            raise error

        with patch.object(
            voiceover_generator.client.text_to_speech,
            'convert',
            side_effect=mock_api_call
        ):
            with pytest.raises(VoiceoverGenerationError, match="Failed after .* retries"):
                await voiceover_generator._call_elevenlabs_with_retry(
                    text="Test",
                    voice_id="test-voice"
                )


class TestFactoryFunction:
    """Test factory function"""

    def test_create_voiceover_generator(self, mock_api_key):
        """Test factory function creates generator"""
        with patch('pipeline.voiceover_generator.ElevenLabs'):
            with patch('pipeline.voiceover_generator.settings') as mock_settings:
                mock_settings.ELEVENLABS_API_KEY = mock_api_key
                mock_settings.ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

                generator = create_voiceover_generator()

                assert isinstance(generator, VoiceoverGenerator)
                assert generator.api_key == mock_api_key


# Integration test helper (requires actual API key)
class TestIntegration:
    """
    Integration tests (requires actual ElevenLabs API key)

    These tests are skipped by default. To run them:
    1. Set ELEVENLABS_API_KEY in .env
    2. Run with: pytest -k integration --elevenlabs
    """

    @pytest.mark.asyncio
    async def test_real_api_generation(self, mock_asset_manager, request):
        """Test with real ElevenLabs API (short text to minimize cost)"""
        # Skip if --elevenlabs flag not provided
        if not request.config.getoption("--elevenlabs", default=False):
            pytest.skip("Requires --elevenlabs flag")

        from config import settings

        if not settings.ELEVENLABS_API_KEY or settings.ELEVENLABS_API_KEY == "your-elevenlabs-api-key-here":
            pytest.skip("ELEVENLABS_API_KEY not configured")

        generator = create_voiceover_generator()

        # Use very short text to minimize API cost
        audio_path = await generator.generate_voiceover(
            text="Test.",
            asset_manager=mock_asset_manager,
            scene_number=1
        )

        assert audio_path is not None
        assert "scene_1_voiceover" in audio_path


def pytest_addoption(parser):
    """Add custom pytest option for integration tests"""
    parser.addoption(
        "--elevenlabs",
        action="store_true",
        default=False,
        help="Run ElevenLabs integration tests (requires API key)"
    )
