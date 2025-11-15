"""
Example: Using VideoComposer to create final video

This example demonstrates how to use VideoComposer to assemble
all generated assets into a final polished video.

Run with:
    python -m pipeline.video_composer_example
"""

import asyncio
from pathlib import Path
from pipeline.video_composer import create_video_composer
from pipeline.asset_manager import AssetManager


async def example_basic_composition():
    """
    Example 1: Basic video composition without background music.
    """
    print("=" * 60)
    print("Example 1: Basic Video Composition")
    print("=" * 60)

    # Setup AssetManager
    job_id = "example-basic-001"
    am = AssetManager(job_id=job_id)
    await am.create_job_directory()

    print(f"\n✓ Created job directory: {am.job_dir}")

    # Create composer
    composer = create_video_composer(asset_manager=am)

    # Note: In a real scenario, these files would exist from previous pipeline steps
    # For demonstration, we're showing the expected file paths
    video_scenes = [
        str(am.scenes_dir / "scene_1.mp4"),
        str(am.scenes_dir / "scene_2.mp4"),
        str(am.scenes_dir / "scene_3.mp4"),
        str(am.scenes_dir / "scene_4.mp4"),
    ]

    voiceovers = [
        str(am.audio_dir / "scene_1_voiceover.mp3"),
        str(am.audio_dir / "scene_2_voiceover.mp3"),
        str(am.audio_dir / "scene_3_voiceover.mp3"),
        str(am.audio_dir / "scene_4_voiceover.mp3"),
    ]

    cta_image = str(am.job_dir / "cta_final.png")

    print("\nExpected input files:")
    print("  Video scenes:")
    for scene in video_scenes:
        print(f"    - {scene}")
    print("  Voiceovers:")
    for vo in voiceovers:
        print(f"    - {vo}")
    print(f"  CTA image: {cta_image}")

    # In a real scenario, you would compose the video like this:
    # final_video = await composer.compose_video(
    #     video_scenes=video_scenes,
    #     voiceovers=voiceovers,
    #     cta_image_path=cta_image
    # )
    # print(f"\n✓ Final video created: {final_video}")

    print("\n⚠️  Note: This is a demonstration. Run after generating actual assets.")

    # Cleanup (optional - comment out to inspect directory structure)
    # await am.cleanup()


async def example_with_background_music():
    """
    Example 2: Video composition with background music.
    """
    print("\n" + "=" * 60)
    print("Example 2: Composition with Background Music")
    print("=" * 60)

    job_id = "example-music-002"
    am = AssetManager(job_id=job_id)
    await am.create_job_directory()

    composer = create_video_composer(asset_manager=am)

    video_scenes = [
        str(am.scenes_dir / "scene_1.mp4"),
        str(am.scenes_dir / "scene_2.mp4"),
    ]

    voiceovers = [
        str(am.audio_dir / "scene_1_voiceover.mp3"),
        str(am.audio_dir / "scene_2_voiceover.mp3"),
    ]

    cta_image = str(am.job_dir / "cta_final.png")
    background_music = str(am.audio_dir / "background_music.mp3")

    print("\nConfiguration:")
    print(f"  Background music: {background_music}")
    print("  Music volume: 10% (subtle background)")
    print("  Transition duration: 0.5s (default)")
    print("  CTA duration: 4s (default)")

    # In a real scenario:
    # final_video = await composer.compose_video(
    #     video_scenes=video_scenes,
    #     voiceovers=voiceovers,
    #     cta_image_path=cta_image,
    #     background_music_path=background_music,
    #     background_music_volume=0.1  # 10% volume
    # )
    # print(f"\n✓ Final video created: {final_video}")

    print("\n⚠️  Note: This is a demonstration. Run after generating actual assets.")


async def example_custom_transitions():
    """
    Example 3: Custom transition settings for different styles.
    """
    print("\n" + "=" * 60)
    print("Example 3: Custom Transitions")
    print("=" * 60)

    job_id = "example-transitions-003"
    am = AssetManager(job_id=job_id)
    await am.create_job_directory()

    composer = create_video_composer(asset_manager=am)

    video_scenes = [str(am.scenes_dir / f"scene_{i}.mp4") for i in range(1, 5)]
    voiceovers = [str(am.audio_dir / f"scene_{i}_voiceover.mp3") for i in range(1, 5)]
    cta_image = str(am.job_dir / "cta_final.png")

    # Different transition styles for different brand personalities
    styles = {
        "luxury": {
            "transition_duration": 0.8,  # Slower, elegant transitions
            "cta_duration": 5.0,  # Display CTA longer
            "description": "Slow, elegant fades for luxury brands"
        },
        "energetic": {
            "transition_duration": 0.3,  # Quick, snappy transitions
            "cta_duration": 3.0,  # Brief CTA for fast-paced
            "description": "Quick fades for energetic content"
        },
        "minimal": {
            "transition_duration": 0.5,  # Balanced transitions
            "cta_duration": 4.0,  # Standard CTA
            "description": "Balanced fades for minimal aesthetic"
        }
    }

    print("\nTransition Styles:")
    for style_name, style_config in styles.items():
        print(f"\n  {style_name.upper()}:")
        print(f"    Transition: {style_config['transition_duration']}s")
        print(f"    CTA: {style_config['cta_duration']}s")
        print(f"    {style_config['description']}")

        # In a real scenario:
        # final_video = await composer.compose_video(
        #     video_scenes=video_scenes,
        #     voiceovers=voiceovers,
        #     cta_image_path=cta_image,
        #     transition_duration=style_config['transition_duration'],
        #     cta_duration=style_config['cta_duration']
        # )

    print("\n⚠️  Note: This is a demonstration. Adjust transitions to match brand.")


async def example_full_pipeline():
    """
    Example 4: Complete pipeline showing all steps.
    """
    print("\n" + "=" * 60)
    print("Example 4: Full Pipeline Integration")
    print("=" * 60)

    print("\nComplete Video Generation Pipeline:")
    print("""
    1. ScriptGenerator → Generate script with scene breakdowns
    2. VoiceoverGenerator → Create voiceovers for all scenes
    3. VideoGenerator → Generate video clips for each scene
    4. CTAGenerator → Create call-to-action image
    5. VideoComposer → Assemble everything into final video ← YOU ARE HERE

    VideoComposer Steps:
    ├─ Load & sync video scenes with voiceovers
    ├─ Add fade transitions between scenes
    ├─ Create CTA scene from static image
    ├─ Append CTA as final scene
    ├─ (Optional) Add background music
    ├─ Ensure 9:16 aspect ratio
    └─ Export optimized MP4
    """)

    job_id = "example-pipeline-004"
    am = AssetManager(job_id=job_id)
    await am.create_job_directory()

    print(f"Job Directory Structure:")
    print(f"  {am.job_dir}/")
    print(f"    ├─ scenes/       (video clips)")
    print(f"    ├─ audio/        (voiceovers + music)")
    print(f"    └─ final/        (composed video) ← Output here")

    # Simulate file paths
    video_scenes = [str(am.scenes_dir / f"scene_{i}.mp4") for i in range(1, 5)]
    voiceovers = [str(am.audio_dir / f"scene_{i}_voiceover.mp3") for i in range(1, 5)]
    cta_image = str(am.job_dir / "cta_final.png")

    composer = create_video_composer(asset_manager=am)

    print("\nFinal Composition Settings:")
    print("  Resolution: 1080x1920 (9:16 vertical)")
    print("  FPS: 30")
    print("  Video codec: H.264 (libx264)")
    print("  Audio codec: AAC")
    print("  Video bitrate: 5 Mbps")
    print("  Audio bitrate: 192 kbps")
    print("  Preset: medium (balance speed/quality)")

    print("\nOptimized for:")
    print("  ✓ Instagram Reels")
    print("  ✓ TikTok")
    print("  ✓ YouTube Shorts")

    # In a real scenario:
    # final_video = await composer.compose_video(
    #     video_scenes=video_scenes,
    #     voiceovers=voiceovers,
    #     cta_image_path=cta_image
    # )
    # print(f"\n✓ Final video ready: {final_video}")

    print("\n⚠️  Note: This is a demonstration of the full pipeline.")


async def example_performance_metrics():
    """
    Example 5: Performance expectations and optimization tips.
    """
    print("\n" + "=" * 60)
    print("Example 5: Performance Metrics")
    print("=" * 60)

    print("\nTypical Processing Times:")
    print("  4 scenes (20-30s total):  30-45 seconds")
    print("  4 scenes + music:         35-50 seconds")
    print("  6 scenes (30-40s total):  45-60 seconds")
    print("  6 scenes + music:         50-70 seconds")

    print("\nMemory Usage:")
    print("  Baseline:                 ~200 MB")
    print("  Per scene:                +50-100 MB")
    print("  With background music:    +20-50 MB")
    print("  Peak (4-6 scenes):        500 MB - 1 GB")

    print("\nPerformance Tips:")
    print("  1. Process videos in batches for large-scale operations")
    print("  2. Use 'fast' preset for quicker encoding (lower quality)")
    print("  3. Reduce bitrate for smaller file sizes")
    print("  4. Monitor memory usage in production")
    print("  5. Consider GPU acceleration for high-volume processing")

    print("\nEncoding Presets (speed vs quality):")
    print("  ultrafast  - Fastest, lowest quality")
    print("  fast       - Quick encoding, good quality")
    print("  medium     - Balanced (default)")
    print("  slow       - Better compression, slower")
    print("  veryslow   - Best quality, very slow")


async def main():
    """
    Run all examples.
    """
    print("\n" + "=" * 60)
    print("VideoComposer Examples")
    print("=" * 60)

    await example_basic_composition()
    await example_with_background_music()
    await example_custom_transitions()
    await example_full_pipeline()
    await example_performance_metrics()

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Generate assets using previous pipeline steps")
    print("  2. Run VideoComposer.compose_video() with actual files")
    print("  3. Check output in asset_manager.final_dir")
    print("  4. Test on target platforms (Instagram, TikTok, etc.)")
    print("\nFor more information, see:")
    print("  - VIDEO_COMPOSER_README.md")
    print("  - test_video_composer.py")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
