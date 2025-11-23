"""
Pydantic schemas for Music Video project API endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime


class SceneResponse(BaseModel):
    """
    Response model for individual scene.
    
    Note: All *Url fields contain presigned S3 URLs, NOT S3 object keys.
    These URLs are generated on-demand from S3 keys stored in the database.
    """
    sequence: int
    status: str
    prompt: str
    negativePrompt: Optional[str] = None
    duration: float
    referenceImageUrls: List[str] = Field(default_factory=list, description="List of presigned S3 URLs for reference images")
    audioClipUrl: Optional[str] = Field(None, description="Presigned S3 URL for scene audio clip")
    
    # Video clip fields (NEW)
    originalVideoClipUrl: Optional[str] = Field(None, description="Presigned S3 URL for unmodified Veo-generated clip")
    workingVideoClipUrl: Optional[str] = Field(None, description="Presigned S3 URL for trimmed/edited clip")
    trimPoints: Optional[Dict[str, float]] = Field(None, description="Trim points: {'in': 0.0, 'out': 8.0}")
    
    # Backward compatibility (DEPRECATED)
    videoClipUrl: Optional[str] = Field(None, description="Presigned S3 URL for video clip (alias for workingVideoClipUrl)")
    
    needsLipSync: bool
    lipSyncedVideoClipUrl: Optional[str] = Field(None, description="Presigned S3 URL for lip-synced video clip")
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
                "originalVideoClipUrl": "https://s3.amazonaws.com/...",
                "workingVideoClipUrl": "https://s3.amazonaws.com/...",
                "trimPoints": {"in": 1.5, "out": 7.2},
                "videoClipUrl": "https://s3.amazonaws.com/...",
                "needsLipSync": True,
                "lipSyncedVideoClipUrl": "https://s3.amazonaws.com/...",
                "retryCount": 0,
                "errorMessage": None,
                "createdAt": "2025-11-17T10:00:00Z",
                "updatedAt": "2025-11-17T10:15:00Z"
            }
        }


class SceneUpdateRequest(BaseModel):
    """Request model for updating a scene's editable fields."""
    prompt: Optional[str] = Field(None, min_length=1, max_length=2000, description="Updated scene prompt")
    negativePrompt: Optional[str] = Field(None, max_length=1000, description="Updated negative prompt")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Updated scene description with more details",
                "negativePrompt": "Updated negative prompt"
            }
        }


class TrimSceneRequest(BaseModel):
    """Request model for trimming a scene video."""
    trimPoints: Dict[str, float]

    @field_validator('trimPoints')
    @classmethod
    def validate_trim_points(cls, v):
        """Validate trim points structure and basic constraints."""
        if 'in' not in v or 'out' not in v:
            raise ValueError("trimPoints must contain 'in' and 'out' keys")

        if not isinstance(v['in'], (int, float)) or not isinstance(v['out'], (int, float)):
            raise ValueError("Trim points must be numeric")

        if v['in'] < 0:
            raise ValueError("in point must be >= 0")

        if v['out'] <= v['in']:
            raise ValueError("out point must be > in point")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "trimPoints": {
                    "in": 1.5,
                    "out": 7.2
                }
            }
        }


class AddSceneRequest(BaseModel):
    """Request model for adding a new scene to an existing project."""
    sceneConcept: str = Field(..., min_length=1, max_length=2000, description="User's concept for the new scene")

    class Config:
        json_schema_extra = {
            "example": {
                "sceneConcept": "A dramatic close-up of the artist performing with intense emotion"
            }
        }


class AddSceneResponse(BaseModel):
    """Response model for adding a new scene to a project."""
    scene: SceneResponse = Field(..., description="The newly created scene")
    message: str = Field(default="Scene added successfully", description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "scene": {
                    "sequence": 5,
                    "status": "pending",
                    "prompt": "A dramatic close-up of the artist performing with intense emotion",
                    "negativePrompt": "No background distractions",
                    "duration": 8.0,
                    "referenceImageUrls": ["https://s3.amazonaws.com/..."],
                    "needsLipSync": True,
                    "retryCount": 0,
                    "createdAt": "2025-01-21T10:00:00Z",
                    "updatedAt": "2025-01-21T10:00:00Z"
                },
                "message": "Scene added successfully"
            }
        }


class DeleteSceneResponse(BaseModel):
    """Response model for deleting a scene from a project."""
    message: str = Field(..., description="Success message")
    deletedSequence: int = Field(..., description="Sequence number of the deleted scene")
    remainingSceneCount: int = Field(..., description="Number of scenes remaining in the project")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Scene deleted successfully",
                "deletedSequence": 2,
                "remainingSceneCount": 4
            }
        }


class ProjectCreateRequest(BaseModel):
    """Request model for creating a new project."""
    mode: str = Field(..., description="Generation mode: 'ad-creative' or 'music-video'")
    prompt: str = Field(..., min_length=1, description="Video concept description")
    characterDescription: str = Field(..., min_length=1, description="Character description")
    characterReferenceImageId: Optional[str] = Field(None, description="UUID of selected character image")
    productDescription: Optional[str] = Field(None, description="Product description (for ad-creative mode)")
    directorConfig: Optional[str] = Field(None, description="Director config name (e.g., 'Wes-Anderson')")

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
    """
    Response model for project retrieval.

    Note: All *Url fields contain presigned S3 URLs (e.g., "https://bucket.s3.amazonaws.com/...?X-Amz-Signature=..."),
    NOT S3 object keys. These URLs are generated on-demand from S3 keys stored in the database.
    Presigned URLs expire after a configured time (default: 1 hour).
    """
    projectId: str
    status: str
    conceptPrompt: str
    characterDescription: Optional[str] = None
    characterImageUrl: Optional[str] = Field(None, description="Presigned S3 URL for character image (expires after configured time)")
    productDescription: Optional[str] = None
    productImageUrl: Optional[str] = Field(None, description="Presigned S3 URL for product image (expires after configured time)")
    audioBackingTrackUrl: Optional[str] = Field(None, description="Presigned S3 URL for audio backing track (expires after configured time)")
    finalOutputUrl: Optional[str] = Field(None, description="Presigned S3 URL for final composed video (expires after configured time)")
    directorConfig: Optional[str] = Field(None, description="Director config name used for this project")
    mode: str = Field(..., description="Project mode: 'music-video' or 'ad-creative'")
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


class SceneWorkerUpdateRequest(BaseModel):
    """Request model for updating scene data (used by workers, not user-facing)."""
    status: Optional[str] = None
    workingVideoClipS3Key: Optional[str] = None  # Updated to use new field name
    lipSyncedVideoClipS3Key: Optional[str] = None
    errorMessage: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "workingVideoClipS3Key": "mv/projects/550e8400/scenes/001/video.mp4"
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
    """
    Response model for final video retrieval.
    
    Note: videoUrl contains a presigned S3 URL, NOT an S3 object key.
    The URL expires after expiresInSeconds.
    """
    projectId: str
    videoUrl: str = Field(..., description="Presigned S3 URL for final composed video")
    expiresInSeconds: int = Field(..., description="Number of seconds until the presigned URL expires")

    class Config:
        json_schema_extra = {
            "example": {
                "projectId": "550e8400-e29b-41d4-a716-446655440000",
                "videoUrl": "https://s3.amazonaws.com/...",
                "expiresInSeconds": 3600
            }
        }
