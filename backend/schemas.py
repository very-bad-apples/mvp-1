"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class VideoGenerateRequest(BaseModel):
    """Request model for video generation"""
    product_name: str = Field(..., min_length=1, max_length=100, description="Name of the product")
    style: str = Field(..., min_length=1, description="Video style (e.g., 'modern', 'minimalist', 'energetic')")
    cta_text: str = Field(..., min_length=1, max_length=50, description="Call-to-action text")
    video_model: str = Field(
        default="minimax",
        description="Video generation model to use (minimax, seedance-fast, seedance-pro, hailuo, ltxv, veo, sora, svd, zeroscope, hotshot)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "product_name": "EcoWater Bottle",
                "style": "modern",
                "cta_text": "Buy Now!",
                "video_model": "minimax"
            }
        }


class VideoGenerateResponse(BaseModel):
    """Response model for video generation endpoint"""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Initial job status")
    estimated_completion_time: int = Field(..., description="Estimated completion time in seconds")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "estimated_completion_time": 300,
                "message": "Video generation job created successfully"
            }
        }


class StageInfo(BaseModel):
    """Stage information for job status"""
    id: int
    stage_name: str
    status: str
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Response model for job status endpoint"""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Overall job status")
    progress: int = Field(..., ge=0, le=100, description="Overall progress percentage")
    created_at: datetime
    updated_at: datetime
    product_name: str
    style: str
    cta_text: str
    video_url: Optional[str] = Field(None, description="URL to the generated video (available when completed)")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    cost_usd: Optional[float] = Field(None, description="Total cost in USD")
    stages: List[StageInfo] = Field(default_factory=list, description="List of processing stages")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "progress": 45,
                "created_at": "2025-01-14T10:00:00",
                "updated_at": "2025-01-14T10:05:00",
                "product_name": "EcoWater Bottle",
                "style": "modern",
                "cta_text": "Buy Now!",
                "video_url": None,
                "error_message": None,
                "cost_usd": 0.0,
                "stages": [
                    {
                        "id": 1,
                        "stage_name": "script_gen",
                        "status": "completed",
                        "progress": 100,
                        "started_at": "2025-01-14T10:00:00",
                        "completed_at": "2025-01-14T10:02:00",
                        "error_message": None
                    }
                ]
            }
        }


class ProgressUpdate(BaseModel):
    """WebSocket progress update message"""
    job_id: str
    stage: str
    progress: int = Field(..., ge=0, le=100)
    status: str
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "stage": "video_gen",
                "progress": 75,
                "status": "processing",
                "message": "Generating video scenes...",
                "timestamp": "2025-01-14T10:05:00"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[str] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid input data",
                "details": "Product name is required"
            }
        }
