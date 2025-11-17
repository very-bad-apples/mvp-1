"""
Regeneration API endpoints for editing and re-rendering video components.

Allows users to:
- Regenerate specific scenes with new prompts
- Regenerate voiceover with different voice
- Recompose video with timing adjustments
- View version history
- Rollback to previous versions
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
import structlog

from database import get_db
from models import Job, JobStatus
from redis_client import redis_client
from services.asset_persistence import AssetPersistenceService

logger = structlog.get_logger()

router = APIRouter(prefix="/jobs", tags=["regeneration"])


# Request/Response Models

class RegenerateSceneRequest(BaseModel):
    """Request body for regenerating a scene"""
    scene_id: int = Field(..., description="Scene number to regenerate (1-based)", ge=1, le=10)
    new_prompt: str = Field(..., description="New video prompt for the scene", min_length=10)
    preserve_duration: bool = Field(True, description="Keep the same duration as original")


class RegenerateVoiceoverRequest(BaseModel):
    """Request body for regenerating voiceover"""
    voice_id: str = Field(..., description="ElevenLabs voice ID to use")
    scenes: Optional[List[int]] = Field(None, description="Specific scenes to regenerate (null = all)")


class RecomposeVideoRequest(BaseModel):
    """Request body for recomposing video"""
    timing_adjustments: Optional[Dict[int, float]] = Field(
        None,
        description="Scene duration adjustments {scene_id: new_duration_seconds}"
    )
    add_logo: Optional[str] = Field(None, description="URL/path to logo image to overlay")
    logo_position: Optional[str] = Field("bottom-right", description="Logo position")


class JobVersionResponse(BaseModel):
    """Response for job version info"""
    job_id: str
    current_version: int
    versions: List[Dict]
    can_rollback: bool


class RegenerationResponse(BaseModel):
    """Response for regeneration operations"""
    job_id: str
    status: str
    message: str
    new_version: Optional[int] = None
    video_url: Optional[str] = None
    previous_version_url: Optional[str] = None


# Endpoints

@router.post("/{job_id}/regenerate-scene", response_model=RegenerationResponse)
async def regenerate_scene(
    job_id: str,
    request: RegenerateSceneRequest,
    db: Session = Depends(get_db)
):
    """
    Regenerate a specific scene with a new prompt.
    
    This will:
    1. Download existing assets from cloud storage
    2. Backup the current scene
    3. Generate new scene with updated prompt
    4. Recompose final video
    5. Upload new version to cloud storage
    
    Args:
        job_id: Job identifier
        request: Scene regeneration parameters
        
    Returns:
        Regeneration status and new video URL
    """
    logger.info("regenerate_scene_requested", job_id=job_id, scene_id=request.scene_id)
    
    # Check if job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Check if job has completed successfully
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot regenerate scene for job with status: {job.status}"
        )
    
    # Check if cloud URLs exist
    if not job.cloud_urls:
        raise HTTPException(
            status_code=400,
            detail="Job assets not found in cloud storage. Cannot regenerate."
        )
    
    try:
        # Create a regeneration job in Redis
        # This will be processed by a worker similar to initial generation
        regen_job_data = {
            "type": "regenerate_scene",
            "parent_job_id": job_id,
            "scene_id": request.scene_id,
            "new_prompt": request.new_prompt,
            "preserve_duration": request.preserve_duration,
            "cloud_urls": job.cloud_urls
        }
        
        # Queue the regeneration job
        regen_job_id = f"{job_id}_regen_scene_{request.scene_id}"
        redis_client.enqueue_job(regen_job_id, regen_job_data)
        
        logger.info("regeneration_job_queued", regen_job_id=regen_job_id)
        
        return RegenerationResponse(
            job_id=job_id,
            status="queued",
            message=f"Scene {request.scene_id} regeneration queued. Check job status for updates.",
            new_version=job.version + 1
        )
        
    except Exception as e:
        logger.error("regenerate_scene_failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to queue regeneration: {str(e)}")


@router.post("/{job_id}/regenerate-voiceover", response_model=RegenerationResponse)
async def regenerate_voiceover(
    job_id: str,
    request: RegenerateVoiceoverRequest,
    db: Session = Depends(get_db)
):
    """
    Regenerate voiceover with a different voice.
    
    Args:
        job_id: Job identifier
        request: Voiceover regeneration parameters
        
    Returns:
        Regeneration status
    """
    logger.info("regenerate_voiceover_requested", job_id=job_id, voice_id=request.voice_id)
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot regenerate voiceover for job with status: {job.status}"
        )
    
    try:
        regen_job_data = {
            "type": "regenerate_voiceover",
            "parent_job_id": job_id,
            "voice_id": request.voice_id,
            "scenes": request.scenes,
            "cloud_urls": job.cloud_urls
        }
        
        regen_job_id = f"{job_id}_regen_voice"
        redis_client.enqueue_job(regen_job_id, regen_job_data)
        
        logger.info("voiceover_regeneration_queued", regen_job_id=regen_job_id)
        
        return RegenerationResponse(
            job_id=job_id,
            status="queued",
            message="Voiceover regeneration queued.",
            new_version=job.version + 1
        )
        
    except Exception as e:
        logger.error("regenerate_voiceover_failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/recompose", response_model=RegenerationResponse)
async def recompose_video(
    job_id: str,
    request: RecomposeVideoRequest,
    db: Session = Depends(get_db)
):
    """
    Recompose video with timing adjustments or additional overlays.
    
    Does not regenerate any assets, just re-runs the composition step.
    
    Args:
        job_id: Job identifier
        request: Recomposition parameters
        
    Returns:
        Recomposition status
    """
    logger.info("recompose_video_requested", job_id=job_id)
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot recompose video for job with status: {job.status}"
        )
    
    try:
        regen_job_data = {
            "type": "recompose",
            "parent_job_id": job_id,
            "timing_adjustments": request.timing_adjustments,
            "add_logo": request.add_logo,
            "logo_position": request.logo_position,
            "cloud_urls": job.cloud_urls
        }
        
        regen_job_id = f"{job_id}_recompose"
        redis_client.enqueue_job(regen_job_id, regen_job_data)
        
        logger.info("recompose_job_queued", regen_job_id=regen_job_id)
        
        return RegenerationResponse(
            job_id=job_id,
            status="queued",
            message="Video recomposition queued.",
            new_version=job.version + 1
        )
        
    except Exception as e:
        logger.error("recompose_failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/versions", response_model=JobVersionResponse)
async def get_job_versions(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get version history for a job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Version information including available backups
    """
    logger.info("get_versions_requested", job_id=job_id)
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Build version list
    versions = []
    
    # Current version
    versions.append({
        "version": job.version,
        "url": job.video_url,
        "created_at": job.updated_at.isoformat() if job.updated_at else None,
        "is_current": True
    })
    
    # Previous version if exists
    if job.previous_version_url:
        versions.append({
            "version": job.version - 1,
            "url": job.previous_version_url,
            "created_at": None,  # Would need to track this separately
            "is_current": False
        })
    
    return JobVersionResponse(
        job_id=job_id,
        current_version=job.version,
        versions=versions,
        can_rollback=job.previous_version_url is not None
    )


@router.post("/{job_id}/rollback", response_model=RegenerationResponse)
async def rollback_version(
    job_id: str,
    to_version: int,
    db: Session = Depends(get_db)
):
    """
    Rollback to a previous version.
    
    Args:
        job_id: Job identifier
        to_version: Version number to rollback to
        
    Returns:
        Rollback status
    """
    logger.info("rollback_requested", job_id=job_id, to_version=to_version)
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Check if we can rollback
    if not job.previous_version_url:
        raise HTTPException(
            status_code=400,
            detail="No previous version available for rollback"
        )
    
    if to_version != job.version - 1:
        raise HTTPException(
            status_code=400,
            detail=f"Can only rollback to version {job.version - 1}"
        )
    
    try:
        # Perform rollback using asset persistence service
        persistence_service = AssetPersistenceService()
        
        # Backup current version
        await persistence_service.backup_final_video(job_id)
        
        # Swap URLs (simplified - would need more complex logic in production)
        current_url = job.video_url
        job.video_url = job.previous_version_url
        job.previous_version_url = current_url
        job.version = to_version
        
        # Update edit history
        if not job.edit_history:
            job.edit_history = []
        job.edit_history.append({
            "action": "rollback",
            "from_version": job.version + 1,
            "to_version": to_version,
            "timestamp": "utcnow"  # Would use actual timestamp
        })
        
        db.commit()
        
        logger.info("rollback_completed", job_id=job_id, version=to_version)
        
        return RegenerationResponse(
            job_id=job_id,
            status="completed",
            message=f"Rolled back to version {to_version}",
            new_version=to_version,
            video_url=job.video_url
        )
        
    except Exception as e:
        logger.error("rollback_failed", job_id=job_id, error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



