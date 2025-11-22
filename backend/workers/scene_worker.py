"""
Worker functions for scene generation.

Handles async scene prompt generation triggered by project creation.
"""

import structlog
from datetime import datetime, timezone
from typing import Dict, Any

from mv_models import MVProjectItem, create_scene_item
from mv.scene_generator import generate_scenes
from pynamodb.exceptions import DoesNotExist

logger = structlog.get_logger()


async def process_scene_generation_job(project_id: str) -> Dict[str, Any]:
    """
    Generate scene prompts for a project.

    This worker:
    1. Retrieves project metadata from DynamoDB
    2. Calls scene generation logic (reuses existing /api/mv/create_scenes)
    3. Creates scene items in DynamoDB
    4. Updates project with scene count

    Args:
        project_id: Project UUID

    Returns:
        Dict with job result
    """
    try:
        logger.info("scene_generation_job_start", project_id=project_id)

        # Retrieve project metadata
        pk = f"PROJECT#{project_id}"

        try:
            project_item = MVProjectItem.get(pk, "METADATA")
        except DoesNotExist:
            logger.error("scene_generation_project_not_found", project_id=project_id)
            return {
                "status": "failed",
                "error": "Project not found"
            }

        # Update project status
        project_item.status = "generating_scenes"
        project_item.GSI1PK = "generating_scenes"
        project_item.updatedAt = datetime.now(timezone.utc)
        project_item.save()

        # Determine number_of_scenes from config flavor (if project has one)
        # For now, use default config flavor since projects don't store config_flavor
        config_flavor = "default"  # TODO: Store config_flavor in project metadata if needed
        from mv.config_manager import get_config
        
        parameters_config = get_config(config_flavor, "parameters")
        number_of_scenes = parameters_config.get("number_of_scenes", 1)
        
        # If number_of_scenes is None or 0, set to None to let Gemini decide
        if number_of_scenes is None or number_of_scenes == 0:
            number_of_scenes = None
        
        # Determine max_scenes based on project mode
        project_mode = project_item.mode or "music-video"  # Default to music-video for backward compatibility
        if project_mode == "music-video":
            max_scenes = 8
        elif project_mode == "ad-creative":
            max_scenes = 4
        else:
            # Fallback to music-video max if mode is invalid
            logger.warning(
                "invalid_project_mode",
                project_id=project_id,
                mode=project_mode,
                defaulting_to="music-video"
            )
            max_scenes = 8
        
        logger.info(
            "scene_generation_parameters",
            project_id=project_id,
            number_of_scenes=number_of_scenes,
            max_scenes=max_scenes,
            project_mode=project_mode,
            config_flavor=config_flavor
        )

        # Generate scenes using existing logic
        # Note: generate_scenes is synchronous and makes external API calls (Gemini)
        # For MVP, blocking is acceptable. Consider async wrapper in Phase 2.
        scenes, _output_files = generate_scenes(
            idea=project_item.conceptPrompt,
            character_description=project_item.characterDescription,
            number_of_scenes=number_of_scenes,
            project_mode=project_mode,
            max_scenes=max_scenes,
            director_config=project_item.directorConfig,
        )

        # Validate scenes were generated
        if not scenes or len(scenes) == 0:
            logger.error("no_scenes_generated", project_id=project_id)
            project_item.status = "failed"
            project_item.GSI1PK = "failed"
            project_item.updatedAt = datetime.now(timezone.utc)
            project_item.save()
            return {
                "status": "failed",
                "error": "No scenes generated"
            }

        logger.info(
            "scenes_generated",
            project_id=project_id,
            scene_count=len(scenes)
        )

        # Create scene items in DynamoDB
        for i, scene_data in enumerate(scenes, start=1):
            scene_item = create_scene_item(
                project_id=project_id,
                sequence=i,
                prompt=scene_data.description,
                negative_prompt=scene_data.negative_description,
                duration=8.0,  # Default duration
                needs_lipsync=True,  # TODO: Determine based on mode
                reference_image_s3_keys=([project_item.characterImageS3Key] 
                    if project_item.characterImageS3Key and project_item.characterImageS3Key.strip() else [])
            )

            scene_item.save()
            logger.info("scene_created", project_id=project_id, sequence=i)

        # Update project with scene count
        project_item.sceneCount = len(scenes)
        project_item.status = "pending"
        project_item.GSI1PK = "pending"
        project_item.updatedAt = datetime.now(timezone.utc)
        project_item.save()

        logger.info(
            "scene_generation_job_complete",
            project_id=project_id,
            scene_count=len(scenes)
        )

        return {
            "status": "completed",
            "project_id": project_id,
            "scene_count": len(scenes)
        }

    except Exception as e:
        logger.error(
            "scene_generation_job_failed",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )

        # Update project status to failed (if project exists)
        try:
            pk = f"PROJECT#{project_id}"
            project_item = MVProjectItem.get(pk, "METADATA")
            project_item.status = "failed"
            project_item.GSI1PK = "failed"
            project_item.updatedAt = datetime.now(timezone.utc)
            project_item.save()
        except Exception as cleanup_error:
            logger.error("failed_to_update_project_status", project_id=project_id, error=str(cleanup_error))

        return {
            "status": "failed",
            "error": str(e)
        }

