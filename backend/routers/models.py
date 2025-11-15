"""
Model Configuration API Router

Provides endpoints for:
- Listing available models for each task
- Getting model details
- Configuring runtime model selection
"""

import structlog
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from pydantic import BaseModel

from services.model_registry import ModelRegistry, ModelTask, ModelConfig

logger = structlog.get_logger()

router = APIRouter(prefix="/api/models", tags=["Models"])


class ModelInfo(BaseModel):
    """Model information response"""
    model_id: str
    display_name: str
    description: str
    cost_per_run: float
    avg_duration: float
    is_default: bool


class TaskModelsResponse(BaseModel):
    """Response containing available models for a task"""
    task: str
    default_model: str
    models: List[ModelInfo]


@router.get(
    "/tasks/{task}/models",
    response_model=TaskModelsResponse,
    summary="List Available Models for Task",
    description="Get all available models for a specific AI task (script, voiceover, video, cta)"
)
async def list_task_models(task: str):
    """
    List all available models for a specific task.

    **Path Parameters:**
    - **task**: Task type (script_generation, voiceover, video_scene, cta_image)

    **Response:**
    ```json
    {
      "task": "script_generation",
      "default_model": "claude-3.5-sonnet",
      "models": [
        {
          "model_id": "anthropic/claude-3.5-sonnet",
          "display_name": "Claude 3.5 Sonnet",
          "description": "Best for creative script generation",
          "cost_per_run": 0.015,
          "avg_duration": 5.0,
          "is_default": true
        },
        ...
      ]
    }
    ```
    """
    try:
        # Validate task type
        try:
            task_enum = ModelTask(task)
        except ValueError:
            valid_tasks = [t.value for t in ModelTask]
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "InvalidTask",
                    "message": f"Invalid task type: {task}",
                    "valid_tasks": valid_tasks
                }
            )

        # Get models for task
        models_dict = ModelRegistry.list_models(task_enum)
        default_model_name = ModelRegistry.get_default_model_name(task_enum)

        # Convert to response format
        models_list = []
        for model_name, model_config in models_dict.items():
            models_list.append(
                ModelInfo(
                    model_id=model_config.model_id,
                    display_name=model_config.display_name,
                    description=model_config.description,
                    cost_per_run=model_config.cost_per_run,
                    avg_duration=model_config.avg_duration,
                    is_default=(model_name == default_model_name)
                )
            )

        logger.info("models_listed", task=task, count=len(models_list))

        return TaskModelsResponse(
            task=task,
            default_model=default_model_name,
            models=models_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_models_error", task=task, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Failed to list models",
                "details": str(e)
            }
        )


@router.get(
    "/tasks",
    summary="List All Tasks",
    description="Get list of all available AI tasks"
)
async def list_tasks():
    """
    List all available AI tasks.

    **Response:**
    ```json
    {
      "tasks": [
        {
          "id": "script_generation",
          "name": "Script Generation",
          "description": "Generate video scripts with AI"
        },
        ...
      ]
    }
    ```
    """
    tasks = [
        {
            "id": ModelTask.SCRIPT_GENERATION.value,
            "name": "Script Generation",
            "description": "Generate video scripts with AI"
        },
        {
            "id": ModelTask.VOICEOVER.value,
            "name": "Voiceover",
            "description": "Text-to-speech voiceover generation"
        },
        {
            "id": ModelTask.VIDEO_SCENE.value,
            "name": "Video Scenes",
            "description": "AI-generated video scenes"
        },
        {
            "id": ModelTask.CTA_IMAGE.value,
            "name": "CTA Images",
            "description": "Call-to-action image generation"
        }
    ]

    return {"tasks": tasks}


@router.get(
    "/estimate-cost",
    summary="Estimate Job Cost",
    description="Estimate total cost for a video generation job with specific models"
)
async def estimate_cost(
    script_model: Optional[str] = None,
    voiceover_model: Optional[str] = None,
    video_model: Optional[str] = None,
    cta_model: Optional[str] = None,
    num_scenes: int = 4,
    num_voiceovers: int = 4
):
    """
    Estimate cost for a video generation job.

    **Query Parameters:**
    - **script_model**: Model name for script generation (uses default if None)
    - **voiceover_model**: Model name for voiceovers (uses default if None)
    - **video_model**: Model name for video scenes (uses default if None)
    - **cta_model**: Model name for CTA image (uses default if None)
    - **num_scenes**: Number of video scenes (default: 4)
    - **num_voiceovers**: Number of voiceovers (default: 4)

    **Response:**
    ```json
    {
      "breakdown": {
        "script_generation": 0.015,
        "voiceovers": 0.0004,
        "video_scenes": 0.48,
        "cta_image": 0.003
      },
      "total_usd": 0.4984,
      "estimated_duration_seconds": 240
    }
    ```
    """
    try:
        # Get model costs
        script_cost = ModelRegistry.estimate_cost(ModelTask.SCRIPT_GENERATION, script_model)
        voiceover_cost = ModelRegistry.estimate_cost(ModelTask.VOICEOVER, voiceover_model) * num_voiceovers
        video_cost = ModelRegistry.estimate_cost(ModelTask.VIDEO_SCENE, video_model) * num_scenes
        cta_cost = ModelRegistry.estimate_cost(ModelTask.CTA_IMAGE, cta_model)

        total_cost = script_cost + voiceover_cost + video_cost + cta_cost

        # Estimate duration (rough approximation)
        script_duration = ModelRegistry.get_model(ModelTask.SCRIPT_GENERATION, script_model).avg_duration
        voiceover_duration = ModelRegistry.get_model(ModelTask.VOICEOVER, voiceover_model).avg_duration * num_voiceovers
        video_duration = ModelRegistry.get_model(ModelTask.VIDEO_SCENE, video_model).avg_duration * num_scenes
        cta_duration = ModelRegistry.get_model(ModelTask.CTA_IMAGE, cta_model).avg_duration

        total_duration = script_duration + voiceover_duration + video_duration + cta_duration

        return {
            "breakdown": {
                "script_generation": round(script_cost, 4),
                "voiceovers": round(voiceover_cost, 4),
                "video_scenes": round(video_cost, 4),
                "cta_image": round(cta_cost, 4)
            },
            "total_usd": round(total_cost, 4),
            "estimated_duration_seconds": int(total_duration)
        }

    except Exception as e:
        logger.error("cost_estimation_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "CostEstimationError",
                "message": "Failed to estimate cost",
                "details": str(e)
            }
        )
