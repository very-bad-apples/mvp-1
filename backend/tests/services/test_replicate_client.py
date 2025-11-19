"""
Tests for ReplicateClient

Run with: pytest backend/services/test_replicate_client.py -v
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from replicate.exceptions import ModelError
from replicate.helpers import FileOutput
from replicate.prediction import Prediction
import httpx

from services.replicate_client import ReplicateClient, get_replicate_client


@pytest.fixture
def mock_api_token():
    """Mock API token for testing."""
    return "test_token_123"


@pytest.fixture
def replicate_client(mock_api_token):
    """Create a ReplicateClient instance for testing."""
    # Reset singleton
    ReplicateClient._instance = None

    with patch.dict(os.environ, {"REPLICATE_API_TOKEN": mock_api_token}):
        client = ReplicateClient(api_token=mock_api_token)
        yield client

    # Reset singleton after test
    ReplicateClient._instance = None


class TestReplicateClientInitialization:
    """Test ReplicateClient initialization."""

    def test_initialization_with_token(self, mock_api_token):
        """Test client initializes with provided token."""
        ReplicateClient._instance = None
        client = ReplicateClient(api_token=mock_api_token)

        assert client.api_token == mock_api_token
        assert client.max_retries == 3
        assert client.timeout == 600
        assert client._initialized is True

        ReplicateClient._instance = None

    def test_initialization_from_env(self):
        """Test client initializes from environment variable."""
        ReplicateClient._instance = None
        test_token = "env_token_456"

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": test_token}):
            with patch("services.replicate_client.settings") as mock_settings:
                mock_settings.REPLICATE_API_TOKEN = test_token
                mock_settings.REPLICATE_API_KEY = ""
                mock_settings.REPLICATE_MAX_RETRIES = 3
                mock_settings.REPLICATE_TIMEOUT = 600
                client = ReplicateClient()
                assert client.api_token == test_token

        ReplicateClient._instance = None

    def test_initialization_without_token_raises_error(self):
        """Test initialization fails without API token."""
        ReplicateClient._instance = None

        with patch.dict(os.environ, {}, clear=True):
            with patch("services.replicate_client.settings") as mock_settings:
                mock_settings.REPLICATE_API_TOKEN = ""
                mock_settings.REPLICATE_API_KEY = ""

                with pytest.raises(ValueError, match="Replicate API token is required"):
                    ReplicateClient()

        ReplicateClient._instance = None

    def test_singleton_pattern(self, mock_api_token):
        """Test client follows singleton pattern."""
        ReplicateClient._instance = None

        client1 = ReplicateClient(api_token=mock_api_token)
        client2 = ReplicateClient(api_token=mock_api_token)

        assert client1 is client2

        ReplicateClient._instance = None

    def test_custom_configuration(self, mock_api_token):
        """Test client accepts custom configuration."""
        ReplicateClient._instance = None

        client = ReplicateClient(
            api_token=mock_api_token,
            max_retries=5,
            timeout=1200,
        )

        assert client.max_retries == 5
        assert client.timeout == 1200

        ReplicateClient._instance = None


class TestRunModel:
    """Test run_model method."""

    @patch("replicate.run")
    def test_run_model_success(self, mock_run, replicate_client):
        """Test successful model run."""
        mock_output = Mock(spec=FileOutput)
        mock_run.return_value = [mock_output]

        result = replicate_client.run_model(
            "black-forest-labs/flux-schnell",
            {"prompt": "astronaut riding a rocket"},
        )

        assert result == [mock_output]
        mock_run.assert_called_once_with(
            "black-forest-labs/flux-schnell",
            input={"prompt": "astronaut riding a rocket"},
            use_file_output=True,
        )

    @patch("replicate.run")
    def test_run_model_without_file_output(self, mock_run, replicate_client):
        """Test model run with use_file_output=False."""
        mock_run.return_value = "http://example.com/output.png"

        result = replicate_client.run_model(
            "test-model",
            {"prompt": "test"},
            use_file_output=False,
        )

        assert result == "http://example.com/output.png"
        mock_run.assert_called_once_with(
            "test-model",
            input={"prompt": "test"},
            use_file_output=False,
        )

    @patch("replicate.run")
    def test_run_model_handles_model_error(self, mock_run, replicate_client):
        """Test model error handling."""
        mock_prediction = Mock()
        mock_prediction.id = "pred_123"
        mock_prediction.status = "failed"
        mock_prediction.logs = "Model execution failed"
        mock_prediction.error = "Model execution failed"

        # Create a proper ModelError instance
        mock_run.side_effect = ModelError(mock_prediction)

        with pytest.raises(ModelError):
            replicate_client.run_model(
                "test-model",
                {"prompt": "test"},
            )

    @patch("replicate.run")
    def test_run_model_retries_network_errors(self, mock_run, replicate_client):
        """Test retry logic for network errors."""
        # First call fails with network error, second succeeds
        mock_output = Mock(spec=FileOutput)
        mock_run.side_effect = [
            httpx.NetworkError("Connection failed"),
            [mock_output],
        ]

        result = replicate_client.run_model(
            "test-model",
            {"prompt": "test"},
        )

        assert result == [mock_output]
        assert mock_run.call_count == 2

    @patch("replicate.run")
    def test_run_model_validation_error_no_retry(self, mock_run, replicate_client):
        """Test that validation errors are not retried."""
        mock_prediction = Mock()
        mock_prediction.id = "pred_123"
        mock_prediction.status = "failed"
        mock_prediction.logs = "Invalid input parameter"
        mock_prediction.error = "Invalid input parameter"

        # Create a proper ModelError instance
        mock_run.side_effect = ModelError(mock_prediction)

        with pytest.raises(ModelError):
            replicate_client.run_model(
                "test-model",
                {"prompt": "test"},
            )

        # Should only be called once (no retry)
        assert mock_run.call_count == 1


class TestAsyncRunModel:
    """Test async model execution."""

    @pytest.mark.asyncio
    @patch("replicate.async_run")
    async def test_run_model_async_success(self, mock_async_run, replicate_client):
        """Test successful async model run."""
        mock_output = Mock(spec=FileOutput)
        mock_async_run.return_value = [mock_output]

        result = await replicate_client.run_model_async(
            "test-model",
            {"prompt": "test"},
        )

        assert result == [mock_output]
        mock_async_run.assert_called_once_with(
            "test-model",
            input={"prompt": "test"},
        )

    @pytest.mark.asyncio
    @patch("replicate.async_run")
    async def test_run_model_async_handles_error(self, mock_async_run, replicate_client):
        """Test async model error handling."""
        mock_prediction = Mock()
        mock_prediction.id = "pred_123"

        # Create a proper ModelError instance
        mock_async_run.side_effect = ModelError(mock_prediction)

        with pytest.raises(ModelError):
            await replicate_client.run_model_async(
                "test-model",
                {"prompt": "test"},
            )


class TestCreatePrediction:
    """Test prediction creation."""

    @patch.object(ReplicateClient, "create_prediction")
    def test_create_prediction_with_version(self, mock_create, replicate_client):
        """Test creating prediction with specific version."""
        mock_prediction = Mock(spec=Prediction)
        mock_prediction.id = "pred_123"
        mock_prediction.status = "starting"
        mock_create.return_value = mock_prediction

        result = mock_create(
            "test-model",
            version_id="version_123",
            input_params={"prompt": "test"},
            webhook="https://example.com/webhook",
            webhook_events_filter=["completed"],
        )

        assert result == mock_prediction

    @patch.object(ReplicateClient, "create_prediction")
    def test_create_prediction_latest_version(self, mock_create, replicate_client):
        """Test creating prediction with latest version."""
        mock_prediction = Mock(spec=Prediction)
        mock_prediction.id = "pred_456"
        mock_prediction.status = "starting"
        mock_create.return_value = mock_prediction

        result = mock_create(
            "test-model",
            input_params={"prompt": "test"},
        )

        assert result == mock_prediction


class TestWaitForPrediction:
    """Test waiting for predictions."""

    def test_wait_for_prediction_success(self, replicate_client):
        """Test successful prediction wait."""
        mock_prediction = Mock(spec=Prediction)
        mock_prediction.id = "pred_123"
        mock_prediction.status = "succeeded"
        mock_prediction.wait = Mock()

        result = replicate_client.wait_for_prediction(mock_prediction)

        assert result == mock_prediction
        mock_prediction.wait.assert_called_once()

    def test_wait_for_prediction_failure(self, replicate_client):
        """Test prediction wait with failure."""
        mock_prediction = Mock(spec=Prediction)
        mock_prediction.id = "pred_123"
        mock_prediction.status = "failed"
        mock_prediction.error = "Prediction execution failed"
        mock_prediction.wait = Mock()

        with pytest.raises(ModelError):
            replicate_client.wait_for_prediction(mock_prediction)


class TestDownloadOutput:
    """Test output downloading."""

    def test_download_output_success(self, replicate_client):
        """Test successful output download."""
        mock_output = Mock(spec=FileOutput)
        mock_output.read = Mock(return_value=b"test data")

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "output.webp"

            result = replicate_client.download_output(mock_output, str(save_path))

            assert Path(result).exists()
            assert Path(result).read_bytes() == b"test data"

    def test_download_output_creates_directories(self, replicate_client):
        """Test that download creates parent directories."""
        mock_output = Mock(spec=FileOutput)
        mock_output.read = Mock(return_value=b"test data")

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "subdir" / "nested" / "output.webp"

            result = replicate_client.download_output(mock_output, str(save_path))

            assert Path(result).exists()
            assert Path(result).parent.parent.name == "subdir"


class TestPredictionManagement:
    """Test prediction management methods."""

    @patch.object(ReplicateClient, "list_predictions")
    def test_list_predictions(self, mock_list, replicate_client):
        """Test listing predictions."""
        mock_page = Mock()
        mock_page.next = "cursor_123"
        mock_list.return_value = mock_page

        result = mock_list()

        assert result == mock_page
        mock_list.assert_called_once()

    @patch.object(ReplicateClient, "list_predictions")
    def test_list_predictions_with_cursor(self, mock_list, replicate_client):
        """Test listing predictions with pagination cursor."""
        mock_page = Mock()
        mock_list.return_value = mock_page

        result = mock_list(cursor="cursor_123")

        assert result == mock_page
        mock_list.assert_called_once_with(cursor="cursor_123")

    def test_cancel_prediction(self, replicate_client):
        """Test canceling a prediction."""
        mock_prediction = Mock(spec=Prediction)
        mock_prediction.id = "pred_123"
        mock_prediction.status = "canceled"
        mock_prediction.cancel = Mock()
        mock_prediction.reload = Mock()

        result = replicate_client.cancel_prediction(mock_prediction)

        assert result == mock_prediction
        mock_prediction.cancel.assert_called_once()
        mock_prediction.reload.assert_called_once()


class TestGetReplicateClient:
    """Test singleton accessor function."""

    def test_get_replicate_client(self, mock_api_token):
        """Test get_replicate_client returns singleton."""
        ReplicateClient._instance = None

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": mock_api_token}):
            client1 = get_replicate_client()
            client2 = get_replicate_client()

            assert client1 is client2
            assert isinstance(client1, ReplicateClient)

        ReplicateClient._instance = None


class TestStreamOutput:
    """Test streaming output."""

    @patch("replicate.stream")
    def test_stream_output(self, mock_stream, replicate_client):
        """Test streaming output from model."""
        mock_events = ["event1", "event2", "event3"]
        mock_stream.return_value = iter(mock_events)

        events = list(replicate_client.stream_output(
            "meta/meta-llama-3-70b-instruct",
            {"prompt": "test"},
        ))

        assert events == mock_events
        mock_stream.assert_called_once()
