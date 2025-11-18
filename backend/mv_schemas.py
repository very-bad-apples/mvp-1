"""
Pydantic schemas for Music Video project API endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class SceneResponse(BaseModel):
    """Response model for individual scene."""
    sequence: int
    status: str
    prompt: str
    negativePrompt: Optional[str] = None
    duration: float
    referenceImageUrls: List[str] = Field(default_factory=list)
    audioClipUrl: Optional[str] = None
    videoClipUrl: Optional[str] = None
    needsLipSync: bool
    lipSyncedVideoClipUrl: Optional[str] = None
    retryCount: int = 0
    errorMessage: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "sequence": 1,
                "status": "completed",
                "prompt": "Robot walking through downtown Austin",
                "negativePrompt": "No other people",
                "duration": 8.0,
                "referenceImageUrls": ["https://s3.amazonaws.com/..."],
                "audioClipUrl": "https://s3.amazonaws.com/...",
                "videoClipUrl": "https://s3.amazonaws.com/...",
                "needsLipSync": True,
                "lipSyncedVideoClipUrl": "https://s3.amazonaws.com/...",
                "retryCount": 0,
                "errorMessage": None,
                "createdAt": "2025-11-17T10:00:00Z",
                "updatedAt": "2025-11-17T10:15:00Z"
            }
        }


class ProjectCreateRequest(BaseModel):
    """Request model for creating a new project."""
    mode: str = Field(..., description="Generation mode: 'ad-creative' or 'music-video'")
    prompt: str = Field(..., min_length=1, description="Video concept description")
    characterDescription: str = Field(..., min_length=1, description="Character description")
    characterReferenceImageId: Optional[str] = Field(None, description="UUID of selected character image")
    productDescription: Optional[str] = Field(None, description="Product description (for ad-creative mode)")

    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        if v not in ['ad-creative', 'music-video']:
            raise ValueError("mode must be 'ad-creative' or 'music-video'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "music-video",
                "prompt": "Create a cinematic music video exploring Austin, Texas",
                "characterDescription": "Silver metallic humanoid robot with red shield",
                "characterReferenceImageId": "550e8400-e29b-41d4-a716-446655440000",
                "productDescription": None
            }
        }


class ProjectCreateResponse(BaseModel):
    """Response model for project creation."""
    projectId: str
    status: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "projectId": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "message": "Project created successfully"
            }
        }


class ProjectResponse(BaseModel):
    """Response model for project retrieval."""
    projectId: str
    status: str
    conceptPrompt: str
    characterDescription: str
    characterImageUrl: Optional[str] = None
    productDescription: Optional[str] = None
    productImageUrl: Optional[str] = None
    audioBackingTrackUrl: Optional[str] = None
    finalOutputUrl: Optional[str] = None
    sceneCount: int
    completedScenes: int
    failedScenes: int
    scenes: List[SceneResponse] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "projectId": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "conceptPrompt": "Robot exploring Austin",
                "characterDescription": "Silver robot",
                "characterImageUrl": "https://s3.amazonaws.com/...",
                "productDescription": None,
                "productImageUrl": None,
                "audioBackingTrackUrl": "https://s3.amazonaws.com/...",
                "finalOutputUrl": None,
                "sceneCount": 4,
                "completedScenes": 2,
                "failedScenes": 0,
                "scenes": [],
                "createdAt": "2025-11-17T10:00:00Z",
                "updatedAt": "2025-11-17T10:15:00Z"
            }
        }


class ProjectUpdateRequest(BaseModel):
    """Request model for updating project metadata."""
    status: Optional[str] = Field(None, description="Update project status")
    finalOutputS3Key: Optional[str] = Field(None, description="S3 key for final output")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v and v not in ['pending', 'processing', 'completed', 'failed']:
            raise ValueError("Invalid status value")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "finalOutputS3Key": "mv/projects/550e8400/final.mp4"
            }
        }


class SceneUpdateRequest(BaseModel):
    """Request model for updating scene data."""
    status: Optional[str] = None
    videoClipS3Key: Optional[str] = None
    lipSyncedVideoClipS3Key: Optional[str] = None
    errorMessage: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "videoClipS3Key": "mv/projects/550e8400/scenes/001/video.mp4"
            }
        }


class ComposeRequest(BaseModel):
    """Request model for final video composition."""
    # No additional fields needed - uses project metadata
    pass


class ComposeResponse(BaseModel):
    """Response model for composition job."""
    jobId: str
    projectId: str
    status: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "jobId": "compose_550e8400-e29b-41d4-a716-446655440000",
                "projectId": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "message": "Video composition job queued"
            }
        }


class FinalVideoResponse(BaseModel):
    """Response model for final video retrieval."""
    projectId: str
    videoUrl: str
    expiresInSeconds: int

    class Config:
        json_schema_extra = {
            "example": {
                "projectId": "550e8400-e29b-41d4-a716-446655440000",
                "videoUrl": "https://s3.amazonaws.com/...",
                "expiresInSeconds": 3600
            }
        }
