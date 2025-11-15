"""
Demo script showing how to use the pipeline core components.

This demonstrates the complete workflow for using:
- Scene templates
- Asset manager
- Error handling
"""

import asyncio
from templates import get_scene_template, fill_template, get_available_styles
from asset_manager import AssetManager
from error_handler import PipelineError, ErrorCode, ValidationError, should_retry


async def demo_templates():
    """Demonstrate scene template system."""
    print("\n" + "="*60)
    print("SCENE TEMPLATE DEMO")
    print("="*60)

    # 1. Get available styles
    print("\n1. Available styles:")
    styles = get_available_styles()
    print(f"   {', '.join(styles)}")

    # 2. Get a template
    print("\n2. Get luxury template:")
    template = get_scene_template("luxury")
    print(f"   Duration: {template['total_duration']}s")
    print(f"   Scenes: {len(template['scenes'])}")
    print(f"   Style: {template['style_keywords']}")

    # 3. Show scene structure
    print("\n3. Scene breakdown:")
    for scene in template['scenes']:
        print(f"   Scene {scene['id']}: {scene['duration']}s {scene['type']}")

    # 4. Fill template with product info
    print("\n4. Fill template with product data:")
    filled = fill_template(template, "Premium Watch", "Shop Now")
    print(f"   Scene 1 voiceover: {filled['scenes'][0]['voiceover_template']}")
    print(f"   Scene 4 CTA: {filled['scenes'][3]['text_overlay']}")


async def demo_asset_manager():
    """Demonstrate asset manager."""
    print("\n" + "="*60)
    print("ASSET MANAGER DEMO")
    print("="*60)

    am = AssetManager("demo-job-123")

    try:
        # 1. Create job directory
        print("\n1. Create job directory:")
        await am.create_job_directory()
        print(f"   Created: {am.job_dir}")
        print(f"   Subdirs: scenes/, audio/, final/")

        # 2. Save some files
        print("\n2. Save test files:")
        scene1 = await am.save_file(b"scene 1 video data", "scene1.mp4", "scenes")
        audio1 = await am.save_file(b"voiceover audio data", "voice.mp3", "audio")
        print(f"   Saved: {scene1}")
        print(f"   Saved: {audio1}")

        # 3. List files
        print("\n3. List files:")
        scenes = await am.list_files("scenes")
        print(f"   Scenes: {[f.name for f in scenes]}")

        # 4. Validate files
        print("\n4. Validate files:")
        valid = await am.validate_file("scene1.mp4", "scenes", min_size=10)
        print(f"   scene1.mp4 valid: {valid}")

        # 5. Check disk usage
        print("\n5. Disk usage:")
        usage = await am.get_disk_usage()
        print(f"   Total: {usage} bytes")

    finally:
        # 6. Cleanup
        print("\n6. Cleanup:")
        await am.cleanup()
        print(f"   Removed: {am.job_dir}")


async def demo_error_handling():
    """Demonstrate error handling."""
    print("\n" + "="*60)
    print("ERROR HANDLING DEMO")
    print("="*60)

    # 1. Create and handle a validation error
    print("\n1. Validation error:")
    try:
        raise ValidationError("Product name is required", field="product_name")
    except PipelineError as e:
        print(f"   Code: {e.code.value}")
        print(f"   Message: {e.message}")
        print(f"   User message: {e.get_user_friendly_message()}")
        print(f"   Should retry: {should_retry(e)}")

    # 2. Create and handle an API error
    print("\n2. API error (transient):")
    try:
        raise PipelineError(
            ErrorCode.CLAUDE_API_ERROR,
            "Claude API returned 503",
            {"status_code": 503}
        )
    except PipelineError as e:
        print(f"   Code: {e.code.value}")
        print(f"   Should retry: {should_retry(e)}")
        print(f"   User message: {e.get_user_friendly_message()}")

    # 3. Serialize error for API response
    print("\n3. Error serialization:")
    error = PipelineError(ErrorCode.FILE_TOO_LARGE, "Image exceeds 10MB")
    error_dict = error.to_dict()
    print(f"   {error_dict}")


async def demo_complete_workflow():
    """Demonstrate a complete workflow."""
    print("\n" + "="*60)
    print("COMPLETE WORKFLOW DEMO")
    print("="*60)

    am = AssetManager("demo-workflow-job")

    try:
        # 1. Validate input (would come from API)
        print("\n1. Validate input:")
        product_name = "Premium Watch"
        style = "luxury"
        cta_text = "Shop Now"

        if style not in get_available_styles():
            raise ValidationError(f"Invalid style: {style}", field="style")
        print(f"   ✓ Product: {product_name}")
        print(f"   ✓ Style: {style}")
        print(f"   ✓ CTA: {cta_text}")

        # 2. Get and fill template
        print("\n2. Prepare scene template:")
        template = get_scene_template(style)
        filled_template = fill_template(template, product_name, cta_text)
        print(f"   ✓ Template: {len(filled_template['scenes'])} scenes")

        # 3. Create job directory
        print("\n3. Setup asset management:")
        await am.create_job_directory()
        print(f"   ✓ Job directory: {am.job_dir}")

        # 4. Simulate saving generated assets
        print("\n4. Save generated assets:")
        await am.save_file(b"generated scene 1 video", "scene1.mp4", "scenes")
        await am.save_file(b"generated scene 2 video", "scene2.mp4", "scenes")
        await am.save_file(b"generated voiceover", "voice.mp3", "audio")
        print(f"   ✓ Saved 2 scene videos")
        print(f"   ✓ Saved 1 audio file")

        # 5. Validate all assets
        print("\n5. Validate assets:")
        scenes = await am.list_files("scenes")
        for scene in scenes:
            valid = await am.validate_file(scene.name, "scenes", min_size=10)
            print(f"   ✓ {scene.name}: {'valid' if valid else 'invalid'}")

        # 6. Get final stats
        print("\n6. Job statistics:")
        usage = await am.get_disk_usage()
        print(f"   ✓ Total size: {usage} bytes")
        print(f"   ✓ Scenes: {len(await am.list_files('scenes'))}")
        print(f"   ✓ Audio: {len(await am.list_files('audio'))}")

        print("\n✓ Workflow completed successfully!")

    except PipelineError as e:
        print(f"\n✗ Workflow failed: {e.get_user_friendly_message()}")
        print(f"  Error code: {e.code.value}")
        if should_retry(e):
            print(f"  This error is retryable")

    finally:
        # Cleanup
        await am.cleanup()


async def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("PIPELINE CORE COMPONENTS DEMO")
    print("="*60)

    await demo_templates()
    await demo_asset_manager()
    await demo_error_handling()
    await demo_complete_workflow()

    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("\nNext Steps:")
    print("- Phase 2: Implement script generator (Task 13)")
    print("- Phase 2: Implement voice generator (Task 14)")
    print("- Phase 2: Implement video generator (Task 15)")
    print("- Phase 2: Implement image generator (Task 16)")
    print("- Phase 2: Implement video compositor (Task 17)")
    print("- Phase 2: Implement media API client (Task 19)")
    print("\nSee PARALLEL-DEVELOPMENT.md for next steps.")


if __name__ == "__main__":
    asyncio.run(main())
