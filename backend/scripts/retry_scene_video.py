#!/usr/bin/env python3
"""
Script to manually retry video generation for a stuck scene.

Usage:
    python scripts/retry_scene_video.py <project_id> <sequence>

Example:
    python scripts/retry_scene_video.py 523e857c-1543-4af5-8b51-b8d36c376c3d 1
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from datetime import datetime, timezone
from routers.mv_projects import generate_scene_video_background
from mv_models import MVProjectItem
from pynamodb.exceptions import DoesNotExist


async def retry_scene_video(project_id: str, sequence: int):
    """
    Retry video generation for a specific scene.

    Args:
        project_id: Project UUID
        sequence: Scene sequence number
    """
    # Retrieve scene from database
    pk = f"PROJECT#{project_id}"
    sk = f"SCENE#{sequence:03d}"

    try:
        scene_item = MVProjectItem.get(pk, sk)
    except DoesNotExist:
        print(f"❌ Scene not found: project={project_id}, sequence={sequence}")
        return

    print(f"📌 Found scene:")
    print(f"  Project ID: {project_id}")
    print(f"  Sequence: {sequence}")
    print(f"  Status: {scene_item.status}")
    print(f"  Prompt: {scene_item.prompt[:100]}...")
    print()

    # Reset scene status to pending
    scene_item.status = "pending"
    scene_item.errorMessage = None
    scene_item.retryCount = (scene_item.retryCount or 0) + 1
    scene_item.updatedAt = datetime.now(timezone.utc)
    scene_item.save()

    print(f"✅ Scene status reset to 'pending', retry count: {scene_item.retryCount}")
    print()

    # Retrieve project metadata for character reference
    try:
        project_item = MVProjectItem.get(pk, "METADATA")
        character_image_s3_key = project_item.characterImageS3Key
    except DoesNotExist:
        print(f"❌ Project metadata not found: {project_id}")
        return

    # Extract character reference ID from S3 key
    character_reference_id = None
    if character_image_s3_key:
        try:
            parts = character_image_s3_key.split('/')
            if len(parts) >= 4 and parts[-2] == 'character_reference':
                character_reference_id = parts[-1].split('.')[0]  # Remove extension
                print(f"🎭 Character reference ID: {character_reference_id}")
        except Exception:
            pass

    print(f"🎬 Starting video generation...")
    print()

    # Trigger video generation
    await generate_scene_video_background(
        project_id=project_id,
        sequence=sequence,
        prompt=scene_item.prompt,
        negative_prompt=scene_item.negativePrompt,
        character_reference_id=character_reference_id,
        duration=scene_item.duration
    )

    print()
    print(f"✅ Video generation completed for scene {sequence}")

    # Check final status
    scene_item.refresh()
    print(f"  Final status: {scene_item.status}")
    if scene_item.errorMessage:
        print(f"  Error: {scene_item.errorMessage}")
    if scene_item.videoClipS3Key:
        print(f"  Video S3 key: {scene_item.videoClipS3Key}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/retry_scene_video.py <project_id> <sequence>")
        print()
        print("Example:")
        print("  python scripts/retry_scene_video.py 523e857c-1543-4af5-8b51-b8d36c376c3d 1")
        sys.exit(1)

    project_id = sys.argv[1]
    sequence = int(sys.argv[2])

    print(f"🔄 Retrying video generation for scene {sequence} in project {project_id}")
    print()

    asyncio.run(retry_scene_video(project_id, sequence))


if __name__ == "__main__":
    main()
