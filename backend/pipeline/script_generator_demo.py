#!/usr/bin/env python3
"""
ScriptGenerator Usage Demo

Demonstrates how to use the ScriptGenerator in your application.
"""

import json
from pathlib import Path
from script_generator import create_script_generator, ScriptGenerationError


def demo_basic_usage():
    """Basic usage example"""
    print("=" * 70)
    print("DEMO: Basic ScriptGenerator Usage")
    print("=" * 70)

    # Create generator instance
    generator = create_script_generator()

    # Generate script without product image
    script = generator.generate_script(
        product_name="Eco-Friendly Water Bottle",
        style="minimal",
        cta_text="Shop Sustainable"
    )

    # Access generated content
    print(f"\nGenerated script for: {script['product_name']}")
    print(f"Style: {script['style']}")
    print(f"Total duration: {script['total_duration']}s")
    print(f"\nHook: {script['hook']}")
    print(f"CTA: {script['cta']}")

    # Access individual scenes
    print("\nScene breakdown:")
    for scene in script['scenes']:
        print(f"\nScene {scene['id']} ({scene['duration']}s):")
        print(f"  Voiceover: {scene.get('voiceover_text', 'N/A')}")

    return script


def demo_with_image():
    """Usage with product image analysis"""
    print("\n" + "=" * 70)
    print("DEMO: ScriptGenerator with Image Analysis")
    print("=" * 70)

    generator = create_script_generator()

    # Path to your product image
    image_path = "./my_product.jpg"

    try:
        script = generator.generate_script(
            product_name="Premium Coffee Maker",
            style="luxury",
            cta_text="Experience Excellence",
            product_image_path=image_path
        )

        # Access product analysis
        if 'product_analysis' in script:
            analysis = script['product_analysis']
            print("\nProduct Analysis:")
            print(f"  Description: {analysis['product_description']}")
            print(f"  Benefits: {', '.join(analysis['key_benefits'])}")
            print(f"  USPs: {', '.join(analysis['unique_selling_points'])}")

        return script

    except FileNotFoundError:
        print(f"⚠ Image not found: {image_path}")
        print("  Skipping image analysis demo")
        return None
    except ScriptGenerationError as e:
        print(f"✗ Script generation failed: {e}")
        return None


def demo_all_styles():
    """Generate scripts for all available styles"""
    print("\n" + "=" * 70)
    print("DEMO: All Available Styles")
    print("=" * 70)

    styles = ["luxury", "energetic", "minimal", "bold"]
    generator = create_script_generator()

    for style in styles:
        print(f"\n{style.upper()} Style:")
        script = generator.generate_script(
            product_name="Wireless Earbuds",
            style=style,
            cta_text="Order Now"
        )
        print(f"  Hook: {script['hook']}")


def demo_error_handling():
    """Demonstrate error handling"""
    print("\n" + "=" * 70)
    print("DEMO: Error Handling")
    print("=" * 70)

    generator = create_script_generator()

    # Example 1: Invalid style
    print("\n1. Testing invalid style:")
    try:
        script = generator.generate_script(
            product_name="Test Product",
            style="invalid_style",  # This will fail
            cta_text="Buy Now"
        )
    except ValueError as e:
        print(f"   ✓ Caught expected error: {e}")

    # Example 2: Invalid image path
    print("\n2. Testing invalid image path:")
    try:
        script = generator.generate_script(
            product_name="Test Product",
            style="luxury",
            cta_text="Buy Now",
            product_image_path="./nonexistent_image.jpg"
        )
    except ScriptGenerationError as e:
        print(f"   ✓ Caught expected error: {e}")


def demo_save_to_file():
    """Save generated script to file"""
    print("\n" + "=" * 70)
    print("DEMO: Saving Script to File")
    print("=" * 70)

    generator = create_script_generator()

    script = generator.generate_script(
        product_name="Fitness Tracker",
        style="energetic",
        cta_text="Start Your Journey"
    )

    # Save as JSON
    output_file = Path("./generated_script.json")
    with open(output_file, 'w') as f:
        json.dump(script, f, indent=2)

    print(f"\n✓ Script saved to: {output_file}")
    print(f"  File size: {output_file.stat().st_size} bytes")

    return output_file


if __name__ == "__main__":
    """
    Run all demos

    Note: Requires ANTHROPIC_API_KEY to be set in .env file
    """
    print("\n" + "=" * 70)
    print("ScriptGenerator Demo Suite")
    print("=" * 70)

    try:
        # Run demos
        demo_basic_usage()
        demo_with_image()
        demo_all_styles()
        demo_error_handling()
        demo_save_to_file()

        print("\n" + "=" * 70)
        print("✓ All demos completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
