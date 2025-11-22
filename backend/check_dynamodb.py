#!/usr/bin/env python3
"""
Quick script to check DynamoDB contents for the MV project.
"""
import json
from mv_models import MVProjectItem
from dynamodb_config import init_dynamodb_tables
from pynamodb.exceptions import TableError
import structlog

logger = structlog.get_logger()


def main():
    print("=" * 60)
    print("DynamoDB Table Inspector")
    print("=" * 60)

    # Initialize table if it doesn't exist
    print("\n1. Checking/Creating table...")
    try:
        init_dynamodb_tables()
        print("✓ Table initialized successfully")
    except Exception as e:
        print(f"✗ Error initializing table: {e}")
        return

    # Scan all items
    print("\n2. Scanning table for all items...")
    try:
        items = list(MVProjectItem.scan())
        print(f"✓ Found {len(items)} items\n")

        if len(items) == 0:
            print("   No items in table yet. Create a project via the API to see data here.")
        else:
            # Group by entity type
            projects = []
            scenes = []

            for item in items:
                if item.entityType == "project":
                    projects.append(item)
                elif item.entityType == "scene":
                    scenes.append(item)

            print(f"   Projects: {len(projects)}")
            print(f"   Scenes: {len(scenes)}")

            # Display project details
            if projects:
                print("\n" + "=" * 60)
                print("PROJECTS")
                print("=" * 60)
                for proj in projects:
                    print(f"\n📁 Project ID: {proj.projectId}")
                    print(f"   Status: {proj.status}")
                    concept = getattr(proj, 'conceptPrompt', None)
                    if concept:
                        print(f"   Concept: {concept[:80]}...")
                    scene_count = getattr(proj, 'sceneCount', 0)
                    print(f"   Scene Count: {scene_count}")
                    completed = getattr(proj, 'completedScenes', 0)
                    print(f"   Completed Scenes: {completed}")
                    failed = getattr(proj, 'failedScenes', 0)
                    print(f"   Failed Scenes: {failed}")
                    print(f"   Created: {proj.createdAt}")

                    char_img = getattr(proj, 'characterImageS3Key', None)
                    if char_img:
                        print(f"   Character Image: {char_img}")
                    final_video = getattr(proj, 'finalOutputS3Key', None)
                    if final_video:
                        print(f"   Final Video: {final_video}")

            # Display scene details
            if scenes:
                print("\n" + "=" * 60)
                print("SCENES")
                print("=" * 60)
                for scene in scenes[:10]:  # Show first 10 scenes
                    seq = getattr(scene, 'sequence', '?')
                    print(f"\n🎬 Scene #{seq} (Project: {scene.projectId[:8]}...)")
                    print(f"   Status: {scene.status}")
                    prompt = getattr(scene, 'prompt', 'No prompt')
                    print(f"   Prompt: {prompt[:100]}...")
                    video_key = getattr(scene, 'videoClipS3Key', None)
                    if video_key:
                        print(f"   Video: {video_key}")
                    duration = getattr(scene, 'duration', 0)
                    print(f"   Duration: {duration}s")

                if len(scenes) > 10:
                    print(f"\n   ... and {len(scenes) - 10} more scenes")

    except TableError as e:
        print(f"✗ Table error: {e}")
    except Exception as e:
        print(f"✗ Error scanning table: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
