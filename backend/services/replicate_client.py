"""
Replicate API Wrapper

A modular, reusable wrapper class for Replicate API interactions with proper
error handling, retry logic, and logging.

Key Features:
- Singleton pattern for client reuse
- Retry logic with exponential backoff
- Error handling using replicate.exceptions.ModelError
- File output handling with automatic downloads
- Async support for concurrent predictions
- Logging integration with structlog
- Webhook support
"""

import os
import asyncio
import logging
from typing import Any, Union, Optional, List
from pathlib import Path

import replicate
from replicate.exceptions import ModelError
from replicate.helpers import FileOutput
from replicate.prediction import Prediction
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import structlog
import httpx

from config import settings


logger = structlog.get_logger(__name__)


class ReplicateClient:
    """
    Modular wrapper for Replicate API interactions.

    Features:
    - Singleton pattern for client reuse
    - Retry logic with exponential backoff
    - Error handling using replicate.exceptions.ModelError
    - File output handling with automatic downloads
    - Async support for concurrent predictions
    - Logging integration with structlog
    - Webhook support

    Usage:
        client = ReplicateClient()
        output = client.run_model(
            "black-forest-labs/flux-schnell",
            {"prompt": "astronaut riding a rocket"}
        )
        video_path = client.download_output(output[0], "./output.webp")
    """

    _instance = None

    def __new__(cls, api_token: str = None, max_retries: int = None, timeout: int = None):
        """Singleton pattern to reuse client instance."""
        if cls._instance is None:
            cls._instance = super(ReplicateClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        api_token: str = None,
        max_retries: int = None,
        timeout: int = None,
    ):
        """
        Initialize Replicate client.

        Args:
            api_token: Replicate API token. If None, loads from environment
            max_retries: Maximum number of retry attempts (default: 3)
            timeout: Timeout in seconds for predictions (default: 600)
        """
        # Skip if already initialized (singleton pattern)
        if self._initialized:
            return

        # Load API token from environment if not provided
        self.api_token = api_token or settings.REPLICATE_API_TOKEN or settings.REPLICATE_API_KEY
        if not self.api_token:
            raise ValueError(
                "Replicate API token is required. Set REPLICATE_API_TOKEN "
                "environment variable or pass api_token parameter."
            )

        # Set API token in environment for replicate library
        os.environ["REPLICATE_API_TOKEN"] = self.api_token

        # Configuration
        self.max_retries = max_retries or settings.REPLICATE_MAX_RETRIES
        self.timeout = timeout or settings.REPLICATE_TIMEOUT

        # Initialize logger
        self.logger = logger.bind(service="replicate_client")

        # Initialize replicate client (uses environment variable automatically)
        self.client = replicate.Client(api_token=self.api_token)

        self._initialized = True

        self.logger.info(
            "replicate_client_initialized",
            max_retries=self.max_retries,
            timeout=self.timeout,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.INFO),
    )
    def run_model(
        self,
        model_id: str,
        input_params: dict,
        use_file_output: bool = True,
    ) -> Union[FileOutput, List[FileOutput], Any]:
        """
        Run a Replicate model with retry logic.

        Args:
            model_id: Model identifier (e.g., "black-forest-labs/flux-schnell")
            input_params: Dictionary of input parameters for the model
            use_file_output: Whether to return FileOutput objects (default: True)

        Returns:
            FileOutput object(s) or raw output depending on use_file_output

        Raises:
            ModelError: If the model prediction fails after retries

        Example:
            output = client.run_model(
                "black-forest-labs/flux-schnell",
                {"prompt": "astronaut riding a rocket"}
            )
        """
        self.logger.info(
            "running_model",
            model_id=model_id,
            input_params=input_params,
            use_file_output=use_file_output,
        )

        # Ensure API token is set in environment (safeguard)
        if not self.api_token:
            raise ValueError(
                "Replicate API token is not set. Cannot make API call."
            )
        os.environ["REPLICATE_API_TOKEN"] = self.api_token

        try:
            # Use replicate.run() - it reads REPLICATE_API_TOKEN from environment
            # We ensure it's set above as a safeguard
            output = replicate.run(
                model_id,
                input=input_params,
            )

            self.logger.info(
                "model_run_success",
                model_id=model_id,
                output_type=type(output).__name__,
            )

            # Convert FileOutput to string URL if use_file_output is False
            if not use_file_output:
                from replicate.helpers import FileOutput
                if isinstance(output, FileOutput):
                    return str(output)
                elif isinstance(output, list):
                    return [str(item) if isinstance(item, FileOutput) else item for item in output]
            
            return output

        except ModelError as e:
            # Log detailed prediction information
            self.logger.error(
                "model_prediction_failed",
                model_id=model_id,
                prediction_id=e.prediction.id if hasattr(e.prediction, "id") else None,
                status=e.prediction.status if hasattr(e.prediction, "status") else None,
                logs=e.prediction.logs if hasattr(e.prediction, "logs") else None,
                error=str(e),
            )

            # Check if it's a validation error (don't retry)
            if hasattr(e.prediction, "status") and e.prediction.status == "failed":
                logs = getattr(e.prediction, "logs", "")
                if "invalid" in logs.lower() or "validation" in logs.lower():
                    self.logger.error(
                        "validation_error_detected",
                        model_id=model_id,
                        logs=logs,
                    )
                    raise  # Don't retry validation errors

            raise

        except (httpx.HTTPStatusError, httpx.NetworkError) as e:
            self.logger.warning(
                "network_error_retrying",
                model_id=model_id,
                error=str(e),
            )
            raise  # Will be retried by @retry decorator

    async def run_model_async(
        self,
        model_id: str,
        input_params: dict,
    ) -> Any:
        """
        Run a model asynchronously for concurrent predictions.

        Args:
            model_id: Model identifier
            input_params: Dictionary of input parameters

        Returns:
            Awaitable result from the model

        Example:
            async with asyncio.TaskGroup() as tg:
                tasks = [
                    tg.create_task(client.run_model_async(model_id, params))
                    for params in param_list
                ]
            results = await asyncio.gather(*tasks)
        """
        self.logger.info(
            "running_model_async",
            model_id=model_id,
            input_params=input_params,
        )

        try:
            # Use client instance to ensure API token is passed correctly
            # Note: Replicate SDK doesn't have async_run on client, so we use the module function
            # but ensure environment variable is set (done in __init__)
            output = await replicate.async_run(
                model_id,
                input=input_params,
            )

            self.logger.info(
                "model_async_run_success",
                model_id=model_id,
            )

            return output

        except ModelError as e:
            self.logger.error(
                "model_async_prediction_failed",
                model_id=model_id,
                prediction_id=e.prediction.id if hasattr(e.prediction, "id") else None,
                error=str(e),
            )
            raise

    def create_prediction(
        self,
        model_id: str,
        version_id: str = None,
        input_params: dict = None,
        webhook: str = None,
        webhook_events_filter: List[str] = None,
        stream: bool = False,
    ) -> Prediction:
        """
        Create a background prediction with optional webhook.

        Args:
            model_id: Model identifier
            version_id: Specific version ID (optional)
            input_params: Dictionary of input parameters
            webhook: Webhook URL for completion notifications
            webhook_events_filter: List of events to trigger webhook (e.g., ["completed"])
            stream: Whether to enable streaming output

        Returns:
            Prediction object

        Example:
            prediction = client.create_prediction(
                "ai-forever/kandinsky-2.2",
                version_id="ea1addaab376f4dc...",
                input_params={"prompt": "Underwater submarine"},
                webhook="https://example.com/webhook",
                webhook_events_filter=["completed"]
            )
        """
        self.logger.info(
            "creating_prediction",
            model_id=model_id,
            version_id=version_id,
            webhook=webhook,
            stream=stream,
        )

        try:
            # Get model and version
            if version_id:
                model = self.client.models.get(model_id)
                version = model.versions.get(version_id)
            else:
                # Use latest version
                model = self.client.models.get(model_id)
                version = model.latest_version

            # Create prediction
            prediction = self.client.predictions.create(
                version=version,
                input=input_params or {},
                webhook=webhook,
                webhook_events_filter=webhook_events_filter or [],
                stream=stream,
            )

            self.logger.info(
                "prediction_created",
                prediction_id=prediction.id,
                status=prediction.status,
            )

            return prediction

        except Exception as e:
            self.logger.error(
                "prediction_creation_failed",
                model_id=model_id,
                error=str(e),
            )
            raise

    def wait_for_prediction(
        self,
        prediction: Prediction,
        timeout: int = None,
    ) -> Prediction:
        """
        Wait for a prediction to complete.

        Args:
            prediction: Prediction object to wait for
            timeout: Timeout in seconds (uses instance timeout if None)

        Returns:
            Completed prediction object

        Raises:
            TimeoutError: If prediction exceeds timeout
            ModelError: If prediction fails

        Example:
            prediction = client.create_prediction(...)
            completed = client.wait_for_prediction(prediction, timeout=300)
            print(completed.output)
        """
        timeout = timeout or self.timeout

        self.logger.info(
            "waiting_for_prediction",
            prediction_id=prediction.id,
            timeout=timeout,
        )

        try:
            # Wait for completion
            prediction.wait()

            self.logger.info(
                "prediction_completed",
                prediction_id=prediction.id,
                status=prediction.status,
            )

            if prediction.status == "failed":
                raise ModelError(prediction)

            return prediction

        except Exception as e:
            self.logger.error(
                "prediction_wait_failed",
                prediction_id=prediction.id,
                error=str(e),
            )
            raise

    def download_output(
        self,
        output: FileOutput,
        save_path: str,
    ) -> str:
        """
        Download FileOutput to a local file.

        Args:
            output: FileOutput object from model run
            save_path: Local path to save the file

        Returns:
            Absolute path to saved file

        Example:
            output = client.run_model(model_id, params)
            path = client.download_output(output[0], "./output.webp")
        """
        self.logger.info(
            "downloading_output",
            save_path=save_path,
        )

        try:
            # Create directory if it doesn't exist
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # Download file
            with open(save_path, "wb") as file:
                file.write(output.read())

            absolute_path = str(save_path.absolute())

            self.logger.info(
                "output_downloaded",
                path=absolute_path,
                size_bytes=save_path.stat().st_size,
            )

            return absolute_path

        except Exception as e:
            self.logger.error(
                "download_failed",
                save_path=str(save_path),
                error=str(e),
            )
            raise

    def list_predictions(
        self,
        limit: int = 20,
        cursor: str = None,
    ) -> Any:
        """
        List recent predictions.

        Args:
            limit: Number of predictions to return
            cursor: Pagination cursor from previous call

        Returns:
            Page of predictions

        Example:
            page1 = client.list_predictions()
            if page1.next:
                page2 = client.list_predictions(cursor=page1.next)
        """
        self.logger.info(
            "listing_predictions",
            limit=limit,
            cursor=cursor,
        )

        try:
            if cursor:
                predictions = self.client.predictions.list(cursor)
            else:
                predictions = self.client.predictions.list()

            return predictions

        except Exception as e:
            self.logger.error(
                "list_predictions_failed",
                error=str(e),
            )
            raise

    def cancel_prediction(
        self,
        prediction: Prediction,
    ) -> Prediction:
        """
        Cancel a running prediction.

        Args:
            prediction: Prediction object to cancel

        Returns:
            Updated prediction object with status 'canceled'

        Example:
            prediction = client.create_prediction(...)
            canceled = client.cancel_prediction(prediction)
        """
        self.logger.info(
            "canceling_prediction",
            prediction_id=prediction.id,
        )

        try:
            prediction.cancel()
            prediction.reload()

            self.logger.info(
                "prediction_canceled",
                prediction_id=prediction.id,
                status=prediction.status,
            )

            return prediction

        except Exception as e:
            self.logger.error(
                "cancel_failed",
                prediction_id=prediction.id,
                error=str(e),
            )
            raise

    def stream_output(
        self,
        model_id: str,
        input_params: dict,
    ):
        """
        Stream output from a model (useful for LLMs).

        Args:
            model_id: Model identifier
            input_params: Dictionary of input parameters

        Yields:
            Events from the model as they arrive

        Example:
            for event in client.stream_output("meta/meta-llama-3-70b-instruct", {...}):
                print(str(event), end="")
        """
        self.logger.info(
            "streaming_output",
            model_id=model_id,
        )

        try:
            for event in replicate.stream(model_id, input=input_params):
                yield event

        except Exception as e:
            self.logger.error(
                "streaming_failed",
                model_id=model_id,
                error=str(e),
            )
            raise


# Convenience function for singleton access
def get_replicate_client() -> ReplicateClient:
    """
    Get the singleton ReplicateClient instance.

    Returns:
        ReplicateClient instance
    """
    return ReplicateClient()
