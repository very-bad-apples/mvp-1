"""
Video Generator Usage Examples

Demonstrates how to use the VideoGenerator class in various scenarios.
"""

import asyncio
from services.replicate_client import get_replicate_client
from pipeline.video_generator import create_video_generator, VideoGenerationError
from pipeline.script_generator import create_script_generator
from pipeline.asset_manager import AssetManager


async def example_1_single_scene():
    """
    Example 1: Generate a single video scene
    """
    print("Example 1: Generate a single video scene\n")

    # Initialize components
    client = get_replicate_client()
    video_gen = create_video_generator(client, model_preference="minimax")
    asset_manager = AssetManager("example-job-1")
    await asset_manager.create_job_directory()

    # Define scene configuration
    scene_config = {
        "id": 1,
        "duration": 8,
        "type": "video",
        "video_prompt_template": "Close-up of Premium Watch, slow camera tilt, luxury lighting, soft white background",
        "use_product_image": True,
    }

    try:
        # Generate single scene
        video_path = await video_gen.generate_scene(
            scene_config,
            style="luxury",
            asset_manager=asset_manager,
            scene_id=1
        )

        print(f"✓ Generated video: {video_path}")
        print(f"  File size: {await asset_manager.get_disk_usage()} bytes")

    except VideoGenerationError as e:
        print(f"✗ Generation failed: {e}")

    finally:
        await asset_manager.cleanup()


async def example_2_full_pipeline():
    """
    Example 2: Full pipeline with script generation
    """
    print("\nExample 2: Full pipeline with script generation\n")

    # Initialize components
    script_gen = create_script_generator()
    client = get_replicate_client()
    video_gen = create_video_generator(client, model_preference="minimax")
    asset_manager = AssetManager("example-job-2")
    await asset_manager.create_job_directory()

    try:
        # Step 1: Generate script
        print("Step 1: Generating script...")
        script = script_gen.generate_script(
            product_name="Premium Headphones",
            style="luxury",
            cta_text="Shop Now",
            # product_image_path="./product.jpg"  # Optional
        )
        print(f"✓ Script generated with {len(script['scenes'])} scenes")

        # Step 2: Generate all video scenes
        print("\nStep 2: Generating video scenes...")
        video_paths = await video_gen.generate_all_scenes(
            script=script,
            style="luxury",
            asset_manager=asset_manager
        )

        print(f"✓ Generated {len(video_paths)} video scenes:")
        for i, path in enumerate(video_paths, 1):
            print(f"  {i}. {path}")

        # Step 3: Check disk usage
        disk_usage = await asset_manager.get_disk_usage()
        print(f"\nTotal disk usage: {disk_usage / 1024 / 1024:.2f} MB")

    except Exception as e:
        print(f"✗ Pipeline failed: {e}")

    finally:
        await asset_manager.cleanup()


async def example_3_multiple_styles():
    """
    Example 3: Generate videos with different styles
    """
    print("\nExample 3: Generate videos with different styles\n")

    client = get_replicate_client()
    video_gen = create_video_generator(client, model_preference="ltxv")

    scene_config = {
        "id": 1,
        "type": "video",
        "video_prompt_template": "Product showcase with dynamic camera movement",
    }

    styles = ["luxury", "energetic", "minimal", "bold"]

    for style in styles:
        asset_manager = AssetManager(f"example-job-3-{style}")
        await asset_manager.create_job_directory()

        try:
            print(f"Generating {style} style video...")
            video_path = await video_gen.generate_scene(
                scene_config,
                style=style,
                asset_manager=asset_manager,
                scene_id=1
            )
            print(f"  ✓ {style}: {video_path}")

        except VideoGenerationError as e:
            print(f"  ✗ {style}: {e}")

        finally:
            await asset_manager.cleanup()


async def example_4_batch_products():
    """
    Example 4: Generate videos for multiple products in parallel
    """
    print("\nExample 4: Batch generation for multiple products\n")

    client = get_replicate_client()
    video_gen = create_video_generator(client, model_preference="minimax")

    products = [
        {"name": "Premium Watch", "style": "luxury"},
        {"name": "Athletic Shoes", "style": "energetic"},
        {"name": "Desk Lamp", "style": "minimal"},
        {"name": "Sports Car", "style": "bold"},
    ]

    async def generate_product_video(product):
        """Generate video for a single product"""
        asset_manager = AssetManager(f"product-{product['name'].replace(' ', '-')}")
        await asset_manager.create_job_directory()

        try:
            scene_config = {
                "id": 1,
                "type": "video",
                "video_prompt_template": f"Showcase {product['name']} with professional lighting",
            }

            video_path = await video_gen.generate_scene(
                scene_config,
                style=product['style'],
                asset_manager=asset_manager,
                scene_id=1
            )

            print(f"✓ {product['name']} ({product['style']}): {video_path}")
            return {"product": product, "video_path": video_path}

        except Exception as e:
            print(f"✗ {product['name']}: {e}")
            return {"product": product, "error": str(e)}

        finally:
            await asset_manager.cleanup()

    # Generate all products in parallel
    print("Generating videos for all products in parallel...\n")
    results = await asyncio.gather(*[
        generate_product_video(product) for product in products
    ])

    # Summary
    successful = sum(1 for r in results if "video_path" in r)
    print(f"\n✓ Successfully generated {successful}/{len(products)} videos")


async def example_5_error_handling():
    """
    Example 5: Error handling and retry scenarios
    """
    print("\nExample 5: Error handling\n")

    client = get_replicate_client()
    video_gen = create_video_generator(client, model_preference="svd")
    asset_manager = AssetManager("example-job-5")
    await asset_manager.create_job_directory()

    # Example 1: Missing required prompt template
    print("Test 1: Missing video_prompt_template")
    try:
        invalid_config = {"id": 1, "type": "video"}
        await video_gen.generate_scene(
            invalid_config,
            style="luxury",
            asset_manager=asset_manager
        )
    except VideoGenerationError as e:
        print(f"  ✓ Caught expected error: {e}\n")

    # Example 2: SVD without product image
    print("Test 2: Image-to-video model without product image")
    try:
        scene_config = {
            "id": 1,
            "type": "video",
            "video_prompt_template": "Product showcase",
        }
        await video_gen.generate_scene(
            scene_config,
            style="luxury",
            asset_manager=asset_manager
        )
    except VideoGenerationError as e:
        print(f"  ✓ Caught expected error: {e}\n")

    # Example 3: Invalid model preference
    print("Test 3: Invalid model preference")
    try:
        invalid_gen = create_video_generator(client, model_preference="invalid")
    except ValueError as e:
        print(f"  ✓ Caught expected error: {e}\n")

    await asset_manager.cleanup()


async def example_6_model_comparison():
    """
    Example 6: Compare different video generation models
    """
    print("\nExample 6: Model comparison\n")

    client = get_replicate_client()
    models = ["minimax", "ltxv", "zeroscope"]

    scene_config = {
        "id": 1,
        "type": "video",
        "video_prompt_template": "Professional product showcase with elegant lighting and smooth camera movement",
    }

    for model_name in models:
        asset_manager = AssetManager(f"model-comparison-{model_name}")
        await asset_manager.create_job_directory()

        try:
            print(f"Testing {model_name}...")
            video_gen = create_video_generator(client, model_preference=model_name)

            import time
            start = time.time()

            video_path = await video_gen.generate_scene(
                scene_config,
                style="luxury",
                asset_manager=asset_manager,
                scene_id=1
            )

            duration = time.time() - start
            print(f"  ✓ {model_name}: {duration:.1f}s - {video_path}")

        except Exception as e:
            print(f"  ✗ {model_name}: {e}")

        finally:
            await asset_manager.cleanup()


async def main():
    """
    Run all examples
    """
    print("=" * 60)
    print("VIDEO GENERATOR USAGE EXAMPLES")
    print("=" * 60)

    # Uncomment the examples you want to run
    # Note: These require a valid REPLICATE_API_TOKEN

    # await example_1_single_scene()
    # await example_2_full_pipeline()
    # await example_3_multiple_styles()
    # await example_4_batch_products()
    await example_5_error_handling()  # Safe to run without API key
    # await example_6_model_comparison()

    print("\n" + "=" * 60)
    print("EXAMPLES COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
