"""
Demo script for ReplicateClient

This script demonstrates basic usage of the ReplicateClient.
Run with: python backend/services/demo_replicate_client.py
"""

import os
import asyncio
from pathlib import Path

from replicate_client import get_replicate_client


def demo_basic_usage():
    """Demonstrate basic model execution."""
    print("\n=== Basic Usage Demo ===")

    client = get_replicate_client()

    # Use FLUX Schnell (fastest model for testing)
    print("Generating image with FLUX Schnell...")
    output = client.run_model(
        "black-forest-labs/flux-schnell",
        input_params={"prompt": "A beautiful sunset over mountains"}
    )

    print(f"Output type: {type(output)}")
    print(f"Number of outputs: {len(output) if hasattr(output, '__len__') else 1}")

    # Download output
    if output:
        output_dir = Path("./demo_outputs")
        output_dir.mkdir(exist_ok=True)

        path = client.download_output(output[0], str(output_dir / "demo_image.webp"))
        print(f"Saved to: {path}")
        print(f"File size: {Path(path).stat().st_size / 1024:.2f} KB")


async def demo_async_usage():
    """Demonstrate async execution for concurrent predictions."""
    print("\n=== Async Usage Demo ===")

    client = get_replicate_client()

    prompts = [
        "A serene lake at dawn",
        "A bustling city at night",
        "A peaceful forest path",
    ]

    print(f"Generating {len(prompts)} images concurrently...")

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

    print(f"Generated {len(outputs)} images")

    # Download all
    output_dir = Path("./demo_outputs")
    output_dir.mkdir(exist_ok=True)

    for i, output in enumerate(outputs):
        if output:
            path = client.download_output(
                output[0],
                str(output_dir / f"async_image_{i}.webp")
            )
            print(f"  [{i+1}] Saved: {path}")


def demo_background_prediction():
    """Demonstrate background prediction creation."""
    print("\n=== Background Prediction Demo ===")

    client = get_replicate_client()

    # Create prediction
    print("Creating background prediction...")
    prediction = client.create_prediction(
        "black-forest-labs/flux-schnell",
        input_params={"prompt": "A futuristic cityscape"}
    )

    print(f"Prediction ID: {prediction.id}")
    print(f"Initial status: {prediction.status}")

    # Wait for completion
    print("Waiting for completion...")
    completed = client.wait_for_prediction(prediction, timeout=300)

    print(f"Final status: {completed.status}")

    if completed.output and completed.status == "succeeded":
        output_dir = Path("./demo_outputs")
        output_dir.mkdir(exist_ok=True)

        path = client.download_output(
            completed.output[0],
            str(output_dir / "background_prediction.webp")
        )
        print(f"Saved: {path}")


def demo_error_handling():
    """Demonstrate error handling."""
    print("\n=== Error Handling Demo ===")

    client = get_replicate_client()

    try:
        # Try with invalid parameters
        print("Attempting invalid model call...")
        output = client.run_model(
            "nonexistent/model",
            {"invalid_param": "test"}
        )
    except Exception as e:
        print(f"Caught error: {type(e).__name__}")
        print(f"Error message: {str(e)[:100]}...")


def demo_prediction_management():
    """Demonstrate prediction listing and management."""
    print("\n=== Prediction Management Demo ===")

    client = get_replicate_client()

    # List recent predictions
    print("Listing recent predictions...")
    try:
        predictions = client.list_predictions()

        print(f"Found {len(list(predictions.results))} predictions")

        # Show first 3
        for i, pred in enumerate(list(predictions.results)[:3]):
            print(f"  [{i+1}] {pred.id}: {pred.status}")

    except Exception as e:
        print(f"Error listing predictions: {e}")


def main():
    """Run all demos."""
    print("=" * 60)
    print("Replicate Client Demo")
    print("=" * 60)

    # Check for API token
    if not os.getenv("REPLICATE_API_TOKEN"):
        print("\nERROR: REPLICATE_API_TOKEN not found in environment")
        print("Please set it in your .env file or export it:")
        print("  export REPLICATE_API_TOKEN=r8_your_token_here")
        return

    # Run demos
    try:
        # Basic usage
        demo_basic_usage()

        # Async usage
        print("\nRunning async demo...")
        asyncio.run(demo_async_usage())

        # Background prediction
        demo_background_prediction()

        # Error handling
        demo_error_handling()

        # Prediction management
        demo_prediction_management()

        print("\n" + "=" * 60)
        print("All demos completed!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
