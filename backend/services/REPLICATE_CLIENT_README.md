# Replicate API Client

A modular, reusable wrapper class for Replicate API interactions with proper error handling, retry logic, and logging.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Error Handling](#error-handling)
- [Integration Examples](#integration-examples)
- [Testing](#testing)

## Overview

The `ReplicateClient` provides a clean, production-ready interface for interacting with Replicate's AI model platform. It handles common patterns like retries, error handling, file downloads, and async operations.

## Features

- **Singleton Pattern**: Reuses client instance across your application
- **Automatic Retries**: Exponential backoff for transient failures
- **Error Handling**: Comprehensive error handling with `ModelError` exceptions
- **File Management**: Automatic download of `FileOutput` objects
- **Async Support**: Concurrent predictions with `async_run`
- **Structured Logging**: Integration with structlog for detailed logging
- **Webhook Support**: Background predictions with webhook notifications
- **Stream Support**: Real-time output streaming for LLMs

## Installation

### Dependencies

```bash
pip install replicate tenacity structlog
```

These are already included in `requirements.txt`:

```txt
replicate==1.0.7
tenacity==8.2.2
structlog==25.5.0
```

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Replicate API Token (required)
REPLICATE_API_TOKEN=r8_your_token_here

# Optional: Alternative naming
REPLICATE_API_KEY=r8_your_token_here

# Optional: Retry configuration
REPLICATE_MAX_RETRIES=3        # Default: 3
REPLICATE_TIMEOUT=600          # Default: 600 seconds (10 minutes)
```

### Settings

Configuration is automatically loaded from `config.py`:

```python
from config import settings

# Access settings
print(settings.REPLICATE_API_TOKEN)
print(settings.REPLICATE_MAX_RETRIES)
print(settings.REPLICATE_TIMEOUT)
```

## Usage

### Basic Usage

```python
from services.replicate_client import ReplicateClient

# Initialize client (singleton pattern)
client = ReplicateClient()

# Run a model
output = client.run_model(
    "black-forest-labs/flux-schnell",
    input_params={"prompt": "astronaut riding a rocket"}
)

# Download output
if output:
    file_path = client.download_output(output[0], "./outputs/image.webp")
    print(f"Saved to: {file_path}")
```

### Singleton Access

```python
from services.replicate_client import get_replicate_client

# Get the singleton instance
client = get_replicate_client()
```

### File Output Handling

```python
# Default: Returns FileOutput objects
output = client.run_model(
    "stability-ai/sdxl",
    {"prompt": "sunset over mountains"}
)

# Download each output
for i, file_output in enumerate(output):
    path = client.download_output(file_output, f"./outputs/image_{i}.png")
    print(f"Saved: {path}")

# Alternative: Get URLs instead
output_url = client.run_model(
    "stability-ai/sdxl",
    {"prompt": "sunset over mountains"},
    use_file_output=False
)
print(output_url)  # String URL
```

### Background Predictions

```python
# Create a background prediction
prediction = client.create_prediction(
    "ai-forever/kandinsky-2.2",
    version_id="ea1addaab376f4dc...",
    input_params={"prompt": "Watercolor painting of an underwater submarine"},
    webhook="https://example.com/webhook",
    webhook_events_filter=["completed"]
)

print(f"Prediction ID: {prediction.id}")
print(f"Status: {prediction.status}")

# Wait for completion
completed = client.wait_for_prediction(prediction, timeout=300)
print(f"Final status: {completed.status}")

# Download output
if completed.output:
    path = client.download_output(completed.output, "./output.png")
```

### Async Operations

```python
import asyncio
from services.replicate_client import get_replicate_client

async def generate_multiple_images():
    client = get_replicate_client()

    prompts = [
        "A chariot pulled by two rainbow unicorns",
        "A chariot pulled by four rainbow unicorns",
        "A chariot pulled by six rainbow unicorns",
    ]

    # Create async tasks
    tasks = [
        client.run_model_async(
            "stability-ai/sdxl",
            {"prompt": prompt}
        )
        for prompt in prompts
    ]

    # Run concurrently
    results = await asyncio.gather(*tasks)
    return results

# Run
results = asyncio.run(generate_multiple_images())
```

### Streaming Output (LLMs)

```python
# Stream text output
for event in client.stream_output(
    "meta/meta-llama-3-70b-instruct",
    {"prompt": "Write a haiku about llamas"}
):
    print(str(event), end="")
```

### Prediction Management

```python
# List predictions
page1 = client.list_predictions()
for pred in page1:
    print(f"{pred.id}: {pred.status}")

# Pagination
if page1.next:
    page2 = client.list_predictions(cursor=page1.next)

# Cancel a running prediction
prediction = client.create_prediction(...)
canceled = client.cancel_prediction(prediction)
```

## API Reference

### ReplicateClient

#### `__init__(api_token=None, max_retries=None, timeout=None)`

Initialize the Replicate client.

**Parameters:**
- `api_token` (str, optional): Replicate API token. Defaults to `REPLICATE_API_TOKEN` env var
- `max_retries` (int, optional): Maximum retry attempts. Defaults to `REPLICATE_MAX_RETRIES`
- `timeout` (int, optional): Timeout in seconds. Defaults to `REPLICATE_TIMEOUT`

#### `run_model(model_id, input_params, use_file_output=True)`

Run a model synchronously with automatic retries.

**Parameters:**
- `model_id` (str): Model identifier (e.g., "black-forest-labs/flux-schnell")
- `input_params` (dict): Input parameters for the model
- `use_file_output` (bool): Return FileOutput objects vs URLs

**Returns:**
- `Union[FileOutput, List[FileOutput], Any]`: Model output

**Raises:**
- `ModelError`: If prediction fails after retries

#### `run_model_async(model_id, input_params)`

Run a model asynchronously for concurrent predictions.

**Parameters:**
- `model_id` (str): Model identifier
- `input_params` (dict): Input parameters

**Returns:**
- `Any`: Awaitable model output

#### `create_prediction(model_id, version_id=None, input_params=None, webhook=None, webhook_events_filter=None, stream=False)`

Create a background prediction.

**Parameters:**
- `model_id` (str): Model identifier
- `version_id` (str, optional): Specific version ID
- `input_params` (dict, optional): Input parameters
- `webhook` (str, optional): Webhook URL for notifications
- `webhook_events_filter` (List[str], optional): Events to trigger webhook
- `stream` (bool): Enable streaming output

**Returns:**
- `Prediction`: Prediction object

#### `wait_for_prediction(prediction, timeout=None)`

Wait for a prediction to complete.

**Parameters:**
- `prediction` (Prediction): Prediction to wait for
- `timeout` (int, optional): Timeout in seconds

**Returns:**
- `Prediction`: Completed prediction

**Raises:**
- `TimeoutError`: If exceeds timeout
- `ModelError`: If prediction fails

#### `download_output(output, save_path)`

Download FileOutput to local file.

**Parameters:**
- `output` (FileOutput): FileOutput object from model
- `save_path` (str): Local path to save

**Returns:**
- `str`: Absolute path to saved file

#### `list_predictions(limit=20, cursor=None)`

List recent predictions.

**Parameters:**
- `limit` (int): Number to return
- `cursor` (str, optional): Pagination cursor

**Returns:**
- `Any`: Page of predictions

#### `cancel_prediction(prediction)`

Cancel a running prediction.

**Parameters:**
- `prediction` (Prediction): Prediction to cancel

**Returns:**
- `Prediction`: Updated prediction with status 'canceled'

#### `stream_output(model_id, input_params)`

Stream output from a model.

**Parameters:**
- `model_id` (str): Model identifier
- `input_params` (dict): Input parameters

**Yields:**
- Events from the model

## Error Handling

### ModelError

Raised when a prediction fails.

```python
from replicate.exceptions import ModelError

try:
    output = client.run_model("model-id", {"prompt": "test"})
except ModelError as e:
    # Access prediction details
    print(f"Prediction ID: {e.prediction.id}")
    print(f"Status: {e.prediction.status}")
    print(f"Logs: {e.prediction.logs}")
```

### Retry Logic

The client automatically retries on:
- Network errors (`httpx.NetworkError`)
- HTTP status errors (`httpx.HTTPStatusError`)

It does NOT retry on:
- Validation errors (detected via logs)
- Failed predictions with non-transient errors

### Retry Configuration

```python
from tenacity import retry, stop_after_attempt, wait_exponential

# Customized in the decorator:
# - Max 3 attempts
# - Exponential backoff: 2s, 4s, 8s (max 10s)
# - Only retry network/HTTP errors
```

## Integration Examples

### Video Generation (Task 15/16)

```python
from services.replicate_client import get_replicate_client

def generate_video_scene(prompt: str, duration: int = 5) -> str:
    """Generate a video scene using Kling AI."""
    client = get_replicate_client()

    # Run model
    output = client.run_model(
        "kling-ai/kling-video",
        input_params={
            "prompt": prompt,
            "duration": duration
        }
    )

    # Download video
    video_path = client.download_output(
        output[0],
        f"./temp/scene_{hash(prompt)}.mp4"
    )

    return video_path

# Usage
video = generate_video_scene(
    "Luxury product showcase with soft lighting",
    duration=5
)
print(f"Generated: {video}")
```

### Image Generation Pipeline

```python
import asyncio
from services.replicate_client import get_replicate_client

async def generate_image_sequence(prompts: list[str]) -> list[str]:
    """Generate multiple images concurrently."""
    client = get_replicate_client()

    # Create async tasks
    tasks = [
        client.run_model_async(
            "black-forest-labs/flux-schnell",
            {"prompt": prompt}
        )
        for prompt in prompts
    ]

    # Run concurrently
    outputs = await asyncio.gather(*tasks)

    # Download all outputs
    paths = []
    for i, output in enumerate(outputs):
        path = client.download_output(output[0], f"./outputs/image_{i}.webp")
        paths.append(path)

    return paths

# Usage
prompts = [
    "Modern minimalist office",
    "Cozy coffee shop interior",
    "Futuristic tech workspace"
]
images = asyncio.run(generate_image_sequence(prompts))
```

### Background Processing with Webhooks

```python
from services.replicate_client import get_replicate_client

def queue_video_generation(prompt: str, webhook_url: str) -> str:
    """Queue video generation with webhook notification."""
    client = get_replicate_client()

    prediction = client.create_prediction(
        "kling-ai/kling-video",
        input_params={"prompt": prompt, "duration": 5},
        webhook=webhook_url,
        webhook_events_filter=["completed", "failed"]
    )

    return prediction.id

# Usage
pred_id = queue_video_generation(
    "Product showcase video",
    "https://api.example.com/webhooks/replicate"
)
print(f"Queued: {pred_id}")
```

## Testing

### Run Tests

```bash
# Run all tests
pytest backend/services/test_replicate_client.py -v

# Run specific test class
pytest backend/services/test_replicate_client.py::TestRunModel -v

# Run with coverage
pytest backend/services/test_replicate_client.py --cov=services.replicate_client
```

### Test Coverage

The test suite covers:
- Initialization (with/without tokens, singleton pattern)
- Model execution (sync and async)
- Error handling (ModelError, retries, validation errors)
- File downloads
- Prediction management (create, wait, list, cancel)
- Streaming output

### Integration Testing

To test with actual Replicate API:

```python
from services.replicate_client import get_replicate_client

# Use a fast, cheap model for testing
client = get_replicate_client()

# Test with FLUX Schnell (fastest, cheapest)
output = client.run_model(
    "black-forest-labs/flux-schnell",
    {"prompt": "test image"}
)

path = client.download_output(output[0], "./test_output.webp")
print(f"Integration test passed: {path}")
```

## Best Practices

1. **Use Singleton Pattern**: Always use `get_replicate_client()` to reuse the instance
2. **Handle Errors**: Always wrap API calls in try/except for ModelError
3. **Use Async for Batch**: For multiple predictions, use `run_model_async` with `asyncio.gather`
4. **Monitor Timeouts**: Adjust `REPLICATE_TIMEOUT` based on your model's typical runtime
5. **Check Logs**: Use prediction.logs to debug failures
6. **Validate Inputs**: Validate input parameters before calling API to avoid unnecessary retries
7. **Clean Up Files**: Delete downloaded outputs after processing to save disk space

## Troubleshooting

### "Unauthenticated" Error

```python
# Ensure API token is set
import os
print(os.getenv("REPLICATE_API_TOKEN"))  # Should print your token

# Or set it explicitly
client = ReplicateClient(api_token="r8_your_token_here")
```

### Network Timeouts

```python
# Increase timeout for long-running models
client = ReplicateClient(timeout=1200)  # 20 minutes

# Or use background predictions
prediction = client.create_prediction(model_id, input_params)
# Check back later
```

### Rate Limiting

```python
# The client will automatically retry with exponential backoff
# But you can also handle it explicitly:
from time import sleep

for attempt in range(5):
    try:
        output = client.run_model(model_id, params)
        break
    except Exception as e:
        if "rate limit" in str(e).lower():
            sleep(2 ** attempt)  # 1s, 2s, 4s, 8s, 16s
        else:
            raise
```

## Contributing

When adding new features:

1. Add method to `ReplicateClient` class
2. Add corresponding tests to `test_replicate_client.py`
3. Update this README with usage examples
4. Ensure all tests pass: `pytest backend/services/test_replicate_client.py -v`

## License

Part of the Bad Apple Video Generator project.
