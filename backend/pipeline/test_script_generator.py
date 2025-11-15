"""
Test script for ScriptGenerator

Run this to test the Claude integration without an actual product image.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.script_generator import create_script_generator, ScriptGenerationError
from config import settings


def test_without_image():
    """Test script generation without product image"""
    print("=" * 70)
    print("Testing ScriptGenerator WITHOUT product image")
    print("=" * 70)

    try:
        # Create generator
        print("\n1. Creating ScriptGenerator...")
        generator = create_script_generator()
        print(f"   ✓ Using model: {generator.model}")

        # Generate script
        print("\n2. Generating script...")
        script = generator.generate_script(
            product_name="Premium Wireless Headphones",
            style="luxury",
            cta_text="Shop Now"
        )

        print("   ✓ Script generated successfully!")

        # Display results
        print("\n3. Script Details:")
        print(f"   - Total Duration: {script['total_duration']}s")
        print(f"   - Style: {script['style']}")
        print(f"   - Product: {script['product_name']}")
        print(f"   - Number of Scenes: {len(script['scenes'])}")

        print("\n4. Scene Voiceovers:")
        for scene in script['scenes']:
            print(f"\n   Scene {scene['id']} ({scene['duration']}s):")
            print(f"   Type: {scene['type']}")
            if 'voiceover_text' in scene:
                print(f"   Voiceover: {scene['voiceover_text']}")

        print("\n5. Hook & CTA:")
        print(f"   Hook: {script.get('hook', 'N/A')}")
        print(f"   CTA: {script.get('cta', 'N/A')}")

        # Save to file
        output_path = Path(__file__).parent / "test_output_no_image.json"
        with open(output_path, 'w') as f:
            json.dump(script, f, indent=2)
        print(f"\n6. Full script saved to: {output_path}")

        print("\n" + "=" * 70)
        print("✓ TEST PASSED")
        print("=" * 70)
        return True

    except ScriptGenerationError as e:
        print(f"\n✗ Script generation failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_sample_image():
    """Test script generation with a sample product image"""
    print("\n" + "=" * 70)
    print("Testing ScriptGenerator WITH product image")
    print("=" * 70)

    # Note: This requires a real product image
    sample_image = Path(__file__).parent / "sample_product.jpg"

    if not sample_image.exists():
        print(f"\n⚠ Sample image not found at: {sample_image}")
        print("  Skipping image analysis test.")
        print("  To test with an image, place a product image at the path above.")
        return None

    try:
        # Create generator
        print("\n1. Creating ScriptGenerator...")
        generator = create_script_generator()

        # Generate script with image
        print("\n2. Generating script with image analysis...")
        script = generator.generate_script(
            product_name="Premium Watch",
            style="luxury",
            cta_text="Discover Luxury",
            product_image_path=str(sample_image)
        )

        print("   ✓ Script with image analysis generated successfully!")

        # Display product analysis
        if 'product_analysis' in script:
            print("\n3. Product Analysis:")
            analysis = script['product_analysis']
            print(f"   Description: {analysis.get('product_description', 'N/A')}")
            print(f"   Target Audience: {analysis.get('target_audience', 'N/A')}")
            print(f"   Emotional Appeal: {analysis.get('emotional_appeal', 'N/A')}")
            print(f"   Benefits: {', '.join(analysis.get('key_benefits', []))}")

        # Display voiceovers
        print("\n4. Generated Voiceovers:")
        for scene in script['scenes']:
            if 'voiceover_text' in scene:
                print(f"\n   Scene {scene['id']}: {scene['voiceover_text']}")

        # Save to file
        output_path = Path(__file__).parent / "test_output_with_image.json"
        with open(output_path, 'w') as f:
            json.dump(script, f, indent=2)
        print(f"\n5. Full script saved to: {output_path}")

        print("\n" + "=" * 70)
        print("✓ TEST PASSED (with image)")
        print("=" * 70)
        return True

    except ScriptGenerationError as e:
        print(f"\n✗ Script generation failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_styles():
    """Test all available styles"""
    print("\n" + "=" * 70)
    print("Testing all available styles")
    print("=" * 70)

    styles = ["luxury", "energetic", "minimal", "bold"]
    results = {}

    for style in styles:
        print(f"\nTesting style: {style}")
        try:
            generator = create_script_generator()
            script = generator.generate_script(
                product_name="Smart Watch",
                style=style,
                cta_text="Get Yours Today"
            )
            results[style] = "✓ PASS"
            print(f"  Hook: {script.get('hook', 'N/A')[:60]}...")
        except Exception as e:
            results[style] = f"✗ FAIL: {str(e)[:50]}"

    print("\n" + "=" * 70)
    print("Style Test Results:")
    for style, result in results.items():
        print(f"  {style:12s}: {result}")
    print("=" * 70)


def check_api_key():
    """Check if API key is configured"""
    print("Checking API key configuration...")
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "your-anthropic-api-key-here":
        print("✗ ANTHROPIC_API_KEY is not configured!")
        print("  Please set it in backend/.env file")
        return False
    else:
        print("✓ ANTHROPIC_API_KEY is configured")
        return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ScriptGenerator Test Suite")
    print("=" * 70)

    # Check API key first
    if not check_api_key():
        print("\n⚠ Cannot run tests without valid API key")
        sys.exit(1)

    # Run tests
    test_results = []

    # Test 1: Without image
    result = test_without_image()
    test_results.append(("Script generation (no image)", result))

    # Test 2: With image (if available)
    result = test_with_sample_image()
    if result is not None:
        test_results.append(("Script generation (with image)", result))

    # Test 3: All styles
    test_all_styles()

    # Summary
    print("\n\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    for test_name, passed in test_results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:40s}: {status}")
    print("=" * 70)
