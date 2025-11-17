"""
Initialize DynamoDB tables for local development.

Usage:
    python init_dynamodb.py          # Create tables only
    python init_dynamodb.py --seed   # Create tables and seed test data
"""

import argparse
import uuid
from datetime import datetime, timezone
from mv_models import MVProjectItem, create_project_metadata, create_scene_item
from dynamodb_config import init_dynamodb_tables
import structlog

logger = structlog.get_logger()


def seed_test_data():
    """
    Seed database with test project and scenes.
    """
    logger.info("seed_test_data_start")

    # Create test project
    project_id = str(uuid.uuid4())

    project = create_project_metadata(
        project_id=project_id,
        concept_prompt="A robot exploring Austin, Texas",
        character_description="Silver metallic humanoid robot with red shield",
        product_description="EcoWater sustainable water bottle",
        character_image_s3_key=f"mv/projects/{project_id}/character.png",
        product_image_s3_key=f"mv/projects/{project_id}/product.jpg",
        audio_backing_track_s3_key=f"mv/projects/{project_id}/audio.mp3"
    )

    try:
        project.save()
        logger.info("seed_project_created", project_id=project_id)
    except Exception as e:
        logger.error("seed_project_error", error=str(e), exc_info=True)
        # Don't continue if project creation fails - scenes would be orphaned without a project
        raise

    # Create test scenes
    scenes = [
        {
            "sequence": 1,
            "prompt": "Robot walking through downtown Austin at sunset",
            "negative_prompt": "No other people, no music",
            "duration": 8.0,
            "needs_lipsync": True
        },
        {
            "sequence": 2,
            "prompt": "Close-up of robot holding EcoWater bottle",
            "negative_prompt": "No blur, no distortion",
            "duration": 6.0,
            "needs_lipsync": False
        },
        {
            "sequence": 3,
            "prompt": "Robot at Town Lake with skyline in background",
            "negative_prompt": "No other people, no crowds",
            "duration": 8.0,
            "needs_lipsync": True
        },
        {
            "sequence": 4,
            "prompt": "Robot waving goodbye with Austin Capitol building",
            "negative_prompt": "No distortion, no blur",
            "duration": 6.0,
            "needs_lipsync": False
        }
    ]

    for scene_data in scenes:
        scene = create_scene_item(
            project_id=project_id,
            sequence=scene_data["sequence"],
            prompt=scene_data["prompt"],
            negative_prompt=scene_data["negative_prompt"],
            duration=scene_data["duration"],
            needs_lipsync=scene_data["needs_lipsync"],
            reference_image_s3_keys=[f"mv/projects/{project_id}/character.png"]
        )

        try:
            scene.save()
            logger.info("seed_scene_created", project_id=project_id, sequence=scene_data["sequence"])
        except Exception as e:
            logger.error("seed_scene_error", sequence=scene_data["sequence"], error=str(e), exc_info=True)

    # Update project with scene count
    project.sceneCount = len(scenes)
    project.save()

    logger.info("seed_test_data_complete", project_id=project_id, scene_count=len(scenes))
    print(f"\nTest project created: {project_id}")
    print(f"Scenes created: {len(scenes)}")
    print(f"\nTest the API:")
    print(f"  GET http://localhost:8000/api/mv/projects/{project_id}")


def main():
    """
    Main entry point for database initialization.
    """
    parser = argparse.ArgumentParser(description="Initialize DynamoDB tables")
    parser.add_argument("--seed", action="store_true", help="Seed database with test data")
    args = parser.parse_args()

    logger.info("dynamodb_init_start")

    # Initialize tables
    try:
        init_dynamodb_tables()
        logger.info("dynamodb_init_complete")
        print("DynamoDB tables initialized successfully!")
    except Exception as e:
        logger.error("dynamodb_init_failed", error=str(e), exc_info=True)
        print(f"Failed to initialize DynamoDB tables: {e}")
        return

    # Seed test data if requested
    if args.seed:
        seed_test_data()


if __name__ == "__main__":
    main()

