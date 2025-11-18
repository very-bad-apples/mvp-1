"""
Worker functions for video composition.

Handles async video stitching with moviepy.
"""

import structlog
import tempfile
import os
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, List
import requests

from mv_models import MVProjectItem
from services.s3_storage import get_s3_storage_service, generate_s3_key
from pynamodb.exceptions import DoesNotExist

logger = structlog.get_logger()


async def process_composition_job(project_id: str) -> Dict[str, Any]:
    """
    Compose final video from scene clips.

    This worker:
    1. Retrieves project and all scenes from DynamoDB
    2. Downloads scene videos from S3
    3. Stitches videos using moviepy
    4. Adds audio backing track
    5. Uploads final video to S3
    6. Updates project with final output S3 key

    Args:
        project_id: Project UUID

    Returns:
        Dict with job result
    """
    temp_dir = None

    try:
        logger.info("composition_job_start", project_id=project_id)

        # Retrieve project metadata
        pk = f"PROJECT#{project_id}"

        try:
            project_item = MVProjectItem.get(pk, "METADATA")
        except DoesNotExist:
            logger.error("composition_project_not_found", project_id=project_id)
            return {
                "status": "failed",
                "error": "Project not found"
            }

        # Update status
        project_item.status = "composing"
        project_item.GSI1PK = "composing"
        project_item.updatedAt = datetime.now(timezone.utc)
        project_item.save()

        # Retrieve all scenes
        scene_items = list(MVProjectItem.query(
            pk,
            MVProjectItem.SK.begins_with("SCENE#")
        ))

        # Sort by sequence
        scene_items.sort(key=lambda s: s.sequence or 0)

        logger.info("scenes_retrieved", project_id=project_id, scene_count=len(scene_items))

        if len(scene_items) == 0:
            raise Exception("No scenes found for project")

        # Create temporary directory for downloads
        temp_dir = tempfile.mkdtemp(prefix=f"compose_{project_id}_")
        s3_service = get_s3_storage_service()

        # Download scene videos
        scene_paths = []
        for scene in scene_items:
            # Use lipsynced video if available, otherwise use regular video
            s3_key = scene.lipSyncedVideoClipS3Key if scene.lipSyncedVideoClipS3Key else scene.videoClipS3Key

            if not s3_key:
                logger.error("scene_missing_video", project_id=project_id, sequence=scene.sequence)
                raise Exception(f"Scene {scene.sequence} missing video clip")

            # Generate presigned URL and download
            video_url = s3_service.generate_presigned_url(s3_key)
            local_path = os.path.join(temp_dir, f"scene_{scene.sequence:03d}.mp4")

            logger.info("downloading_scene", sequence=scene.sequence, s3_key=s3_key)
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            scene_paths.append(local_path)
            logger.info("scene_downloaded", sequence=scene.sequence, path=local_path)

        # Download audio backing track
        audio_path = None
        if project_item.audioBackingTrackS3Key:
            audio_url = s3_service.generate_presigned_url(project_item.audioBackingTrackS3Key)
            audio_path = os.path.join(temp_dir, "audio.mp3")

            logger.info("downloading_audio", s3_key=project_item.audioBackingTrackS3Key)
            response = requests.get(audio_url, stream=True)
            response.raise_for_status()

            with open(audio_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        # Compose video with moviepy
        output_path = os.path.join(temp_dir, "final.mp4")

        logger.info("composing_video", scene_count=len(scene_paths))
        compose_video_with_moviepy(scene_paths, audio_path, output_path)

        # Upload final video to S3
        final_s3_key = generate_s3_key(project_id, "final_video")

        logger.info("uploading_final_video", s3_key=final_s3_key)
        s3_service.upload_file_from_path(
            output_path,
            final_s3_key,
            content_type="video/mp4"
        )

        # Update project with final output
        project_item.finalOutputS3Key = final_s3_key
        project_item.status = "completed"
        project_item.GSI1PK = "completed"
        project_item.updatedAt = datetime.now(timezone.utc)
        project_item.save()

        logger.info(
            "composition_job_complete",
            project_id=project_id,
            final_s3_key=final_s3_key
        )

        return {
            "status": "completed",
            "project_id": project_id,
            "final_s3_key": final_s3_key
        }

    except Exception as e:
        logger.error(
            "composition_job_failed",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )

        # Update project status (if project exists)
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

    finally:
        # Cleanup temporary files
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info("temp_files_cleaned", temp_dir=temp_dir)
            except Exception as cleanup_error:
                logger.warning("temp_cleanup_failed", temp_dir=temp_dir, error=str(cleanup_error))


def compose_video_with_moviepy(scene_paths: List[str], audio_path: str, output_path: str):
    """
    Compose final video using moviepy.

    Args:
        scene_paths: List of scene video file paths
        audio_path: Path to audio backing track (optional)
        output_path: Output file path
    """
    try:
        from moviepy.editor import (
            VideoFileClip,
            concatenate_videoclips,
            concatenate_audioclips,
            AudioFileClip
        )
    except ImportError:
        raise ImportError("moviepy is required for video composition. Install with: pip install moviepy")

    logger.info("moviepy_compose_start", scene_count=len(scene_paths))

    # Load scene clips
    clips = []
    try:
        for path in scene_paths:
            clip = VideoFileClip(path)
            clips.append(clip)

        # Concatenate clips
        final_clip = concatenate_videoclips(clips, method="compose")

        # Add audio if provided
        if audio_path and os.path.exists(audio_path):
            audio = AudioFileClip(audio_path)

            # Trim or loop audio to match video duration
            if audio.duration < final_clip.duration:
                # Loop audio to match video duration
                loops = int(final_clip.duration / audio.duration) + 1
                audio_loops = [audio] * loops
                audio = concatenate_audioclips(audio_loops)
                audio = audio.subclip(0, final_clip.duration)
            else:
                # Trim audio to match video duration
                audio = audio.subclip(0, final_clip.duration)

            final_clip = final_clip.set_audio(audio)

        # Write output
        final_clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=24,
            preset='medium',
            logger=None  # Suppress MoviePy's verbose logging
        )

        logger.info("moviepy_compose_complete", output_path=output_path)

    finally:
        # Close clips to free resources
        if 'final_clip' in locals():
            final_clip.close()
        for clip in clips:
            clip.close()

