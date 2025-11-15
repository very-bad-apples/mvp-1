"""
Example Usage: CTA Image Generator with Replicate/FLUX

This example demonstrates how to use the CTAGenerator to create
professional Call-to-Action images for video advertisements.
"""

import asyncio
from pathlib import Path

from services.replicate_client import get_replicate_client
from pipeline.cta_generator import CTAGenerator, create_cta_generator
from pipeline.asset_manager import AssetManager
from pipeline.script_generator import create_script_generator


async def example_basic_usage():
    """Basic CTA generation example"""
    print("=" * 60)
    print("Example 1: Basic CTA Generation")
    print("=" * 60)

    # Create asset manager for job
    am = AssetManager("example-job-basic")
    await am.create_job_directory()

    try:
        # Create CTA generator
        cta_gen = create_cta_generator()

        # Generate CTA image
        print("\nGenerating luxury-style CTA...")
        cta_path = await cta_gen.generate_cta(
            cta_text="Shop Now",
            style="luxury",
            asset_manager=am
        )

        print(f"✓ CTA image saved to: {cta_path}")
        print(f"  File exists: {Path(cta_path).exists()}")
        print(f"  File size: {Path(cta_path).stat().st_size / 1024:.2f} KB")

    finally:
        # Cleanup (optional - comment out to keep files for inspection)
        print("\nCleaning up temporary files...")
        await am.cleanup()


async def example_all_styles():
    """Generate CTAs for all available styles"""
    print("\n" + "=" * 60)
    print("Example 2: Generate All Styles")
    print("=" * 60)

    am = AssetManager("example-job-styles")
    await am.create_job_directory()

    try:
        cta_gen = create_cta_generator()

        styles = {
            "luxury": "Experience Excellence",
            "energetic": "Join Now!",
            "minimal": "Learn More",
            "bold": "Act Now!"
        }

        results = []

        for style, cta_text in styles.items():
            print(f"\nGenerating {style} style with text: '{cta_text}'")
            cta_path = await cta_gen.generate_cta(
                cta_text=cta_text,
                style=style,
                asset_manager=am
            )

            results.append({
                "style": style,
                "path": cta_path,
                "size": Path(cta_path).stat().st_size / 1024
            })

            print(f"  ✓ Saved to: {cta_path}")
            print(f"  ✓ Size: {results[-1]['size']:.2f} KB")

        print("\n" + "-" * 60)
        print("Summary:")
        for result in results:
            print(f"  {result['style']:12} → {result['size']:6.2f} KB")

    finally:
        print("\nCleaning up temporary files...")
        await am.cleanup()


async def example_with_script_generator():
    """Integration with ScriptGenerator"""
    print("\n" + "=" * 60)
    print("Example 3: Integration with ScriptGenerator")
    print("=" * 60)

    am = AssetManager("example-job-integration")
    await am.create_job_directory()

    try:
        # Generate script first
        print("\nGenerating script for product...")
        script_gen = create_script_generator()

        # Note: This requires ANTHROPIC_API_KEY to be set
        # For demo purposes, we'll use mock data instead
        print("  (Using mock script data - set ANTHROPIC_API_KEY for real generation)")

        # Mock script data
        mock_script = {
            "product_name": "Premium Headphones",
            "style": "luxury",
            "cta": "Shop Now - Limited Time",
            "hook": "Transform your audio experience"
        }

        print(f"  Product: {mock_script['product_name']}")
        print(f"  Style: {mock_script['style']}")
        print(f"  CTA: {mock_script['cta']}")

        # Generate CTA image using script data
        print("\nGenerating CTA image from script...")
        cta_gen = create_cta_generator()

        cta_path = await cta_gen.generate_cta(
            cta_text=mock_script["cta"],
            style=mock_script["style"],
            asset_manager=am
        )

        print(f"\n✓ Script and CTA generation complete!")
        print(f"  CTA Text: {mock_script['cta']}")
        print(f"  CTA Image: {cta_path}")
        print(f"  Ready for video composition!")

    finally:
        print("\nCleaning up temporary files...")
        await am.cleanup()


async def example_custom_client():
    """Using custom ReplicateClient configuration"""
    print("\n" + "=" * 60)
    print("Example 4: Custom ReplicateClient Configuration")
    print("=" * 60)

    am = AssetManager("example-job-custom")
    await am.create_job_directory()

    try:
        # Create custom client with specific settings
        print("\nCreating custom ReplicateClient...")
        from services.replicate_client import ReplicateClient

        client = ReplicateClient(
            max_retries=5,  # More retries
            timeout=900     # 15 minutes timeout
        )

        print("  Max retries: 5")
        print("  Timeout: 900s")

        # Use with CTAGenerator
        cta_gen = CTAGenerator(client)

        print("\nGenerating bold-style CTA...")
        cta_path = await cta_gen.generate_cta(
            cta_text="Limited Offer",
            style="bold",
            asset_manager=am
        )

        print(f"✓ CTA generated with custom client")
        print(f"  Path: {cta_path}")

    finally:
        print("\nCleaning up temporary files...")
        await am.cleanup()


async def example_error_handling():
    """Demonstrate error handling"""
    print("\n" + "=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)

    cta_gen = create_cta_generator()
    am = AssetManager("example-job-errors")
    await am.create_job_directory()

    # Test 1: Invalid style
    print("\nTest 1: Invalid style")
    try:
        await cta_gen.generate_cta(
            cta_text="Shop Now",
            style="invalid_style",
            asset_manager=am
        )
    except ValueError as e:
        print(f"  ✓ Caught ValueError: {e}")

    # Test 2: Missing asset manager
    print("\nTest 2: Missing asset manager")
    try:
        await cta_gen.generate_cta(
            cta_text="Shop Now",
            style="luxury"
            # Missing asset_manager
        )
    except ValueError as e:
        print(f"  ✓ Caught ValueError: {e}")

    print("\n✓ Error handling works correctly!")

    await am.cleanup()


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("CTA Image Generator - Usage Examples")
    print("=" * 60)
    print("\nThese examples demonstrate the CTAGenerator capabilities:")
    print("  1. Basic CTA generation")
    print("  2. Generate all styles")
    print("  3. Integration with ScriptGenerator")
    print("  4. Custom ReplicateClient configuration")
    print("  5. Error handling")
    print("\n" + "=" * 60)

    try:
        # Run examples
        await example_basic_usage()
        await example_all_styles()
        await example_with_script_generator()
        await example_custom_client()
        await example_error_handling()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
