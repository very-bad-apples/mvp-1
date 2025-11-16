"""
SQLAlchemy database models
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from database import Base


class Job(Base):
    """
    Job model for video generation requests

    Tracks the overall status of a video generation job
    """
    __tablename__ = "jobs"

    # Primary key
    id = Column(String, primary_key=True, index=True)  # UUID

    # Job metadata
    status = Column(String, nullable=False, default="pending", index=True)  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Input parameters
    product_name = Column(String, nullable=False)
    style = Column(String, nullable=False)
    cta_text = Column(String, nullable=False)
    product_image_path = Column(String, nullable=True)

    # Output
    video_url = Column(String, nullable=True)  # Cloud storage URL for final video

    # Cloud storage and versioning
    cloud_urls = Column(JSON, nullable=True)  # Dict of all cloud URLs (scenes, audio, etc.)
    version = Column(Integer, default=1, nullable=False)  # Version number for edits
    previous_version_url = Column(String, nullable=True)  # Backup of previous final video
    edit_history = Column(JSON, nullable=True, default=list)  # List of edit operations

    # Error handling
    error_message = Column(Text, nullable=True)

    # Cost tracking
    cost_usd = Column(Float, nullable=True, default=0.0)

    # Relationships
    stages = relationship("Stage", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job(id={self.id}, status={self.status}, product={self.product_name})>"

    def to_dict(self):
        """Convert job to dictionary"""
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "product_name": self.product_name,
            "style": self.style,
            "cta_text": self.cta_text,
            "product_image_path": self.product_image_path,
            "video_url": self.video_url,
            "cloud_urls": self.cloud_urls,
            "version": self.version,
            "previous_version_url": self.previous_version_url,
            "edit_history": self.edit_history,
            "error_message": self.error_message,
            "cost_usd": self.cost_usd,
            "stages": [stage.to_dict() for stage in self.stages] if self.stages else []
        }


class Stage(Base):
    """
    Stage model for tracking individual processing stages

    Each job consists of multiple stages (script generation, voice generation, etc.)
    """
    __tablename__ = "stages"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to Job
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Stage information
    stage_name = Column(String, nullable=False)  # script_gen, voice_gen, video_gen, compositing
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    progress = Column(Integer, default=0, nullable=False)  # 0-100

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Stage-specific data (JSON or text)
    stage_data = Column(Text, nullable=True)  # Can store JSON strings
    error_message = Column(Text, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="stages")

    def __repr__(self):
        return f"<Stage(id={self.id}, job_id={self.job_id}, stage={self.stage_name}, status={self.status})>"

    def to_dict(self):
        """Convert stage to dictionary"""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "stage_name": self.stage_name,
            "status": self.status,
            "progress": self.progress,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stage_data": self.stage_data,
            "error_message": self.error_message
        }


# Stage name constants for reference
class StageNames:
    """Constants for stage names"""
    SCRIPT_GENERATION = "script_gen"
    VOICE_GENERATION = "voice_gen"
    VIDEO_GENERATION = "video_gen"
    COMPOSITING = "compositing"

    @classmethod
    def all_stages(cls):
        """Get list of all stage names in order"""
        return [
            cls.SCRIPT_GENERATION,
            cls.VOICE_GENERATION,
            cls.VIDEO_GENERATION,
            cls.COMPOSITING
        ]


# Job status constants
class JobStatus:
    """Constants for job status values"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Stage status constants
class StageStatus:
    """Constants for stage status values"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
