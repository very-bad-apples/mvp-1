"""
Music Video (MV) endpoint router.

Handles scene generation and related music video pipeline operations.
"""

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from mv.scene_generator import (
    CreateScenesRequest,
    CreateScenesResponse,
    generate_scenes,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/mv", tags=["Music Video"])


@router.post(
    "/create_scenes",
    response_model=CreateScenesResponse,
    status_code=200,
    responses={
        200: {"description": "Scenes generated successfully"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Internal server error or API failure"}
    },
    summary="Generate Scene Descriptions",
    description="""
Generate scene descriptions for a music video based on an idea and character.

This endpoint uses Google's Gemini model to generate structured scene prompts
that can be used for video generation. Each scene includes a description and
negative prompts for what to exclude.

**Limitations:**
- Synchronous processing (may take 10-30+ seconds)
- File-based storage (scenes saved to filesystem)

**Required Fields:**
- idea: The core concept or topic of the video
- character_description: Visual description of the main character

**Optional Fields (defaults from config):**
- character_characteristics: Personality traits
- number_of_scenes: Number of scenes to generate (default: 4)
- video_type: Type of video (default: "video")
- video_characteristics: Visual style (default: "vlogging, realistic, 4k, cinematic")
- camera_angle: Camera perspective (default: "front")
"""
)
async def create_scenes(request: CreateScenesRequest):
    """
    Generate scene descriptions for a music video.

    This endpoint:
    1. Validates the request parameters
    2. Applies defaults from YAML config for optional fields
    3. Generates scene prompts using Gemini 2.5 Pro
    4. Saves scenes to files (JSON and Markdown)
    5. Returns the generated scenes and file paths

    **Example Request:**
    ```json
    {
        "idea": "Tourist exploring Austin, Texas",
        "character_description": "Silver metallic humanoid robot with a red shield"
    }
    ```

    **Example Response:**
    ```json
    {
        "scenes": [
            {
                "description": "A medium shot of a silver metallic humanoid robot...",
                "negative_description": "No other people, no music."
            }
        ],
        "output_files": {
            "json": "/path/to/scenes.json",
            "markdown": "/path/to/scenes.md"
        },
        "metadata": {
            "idea": "Tourist exploring Austin, Texas",
            "number_of_scenes": 4,
            "parameters_used": {...}
        }
    }
    ```
    """
    try:
        logger.info(
            "create_scenes_request_received",
            idea=request.idea,
            character_description=request.character_description[:100] + "..." if len(request.character_description) > 100 else request.character_description,
            number_of_scenes=request.number_of_scenes
        )

        # Validate required fields
        if not request.idea or not request.idea.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Idea is required",
                    "details": "The 'idea' field cannot be empty"
                }
            )

        if not request.character_description or not request.character_description.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "Character description is required",
                    "details": "The 'character_description' field cannot be empty"
                }
            )

        # Generate scenes
        scenes, output_files = generate_scenes(
            idea=request.idea.strip(),
            character_description=request.character_description.strip(),
            character_characteristics=request.character_characteristics.strip() if request.character_characteristics else None,
            number_of_scenes=request.number_of_scenes,
            video_type=request.video_type.strip() if request.video_type else None,
            video_characteristics=request.video_characteristics.strip() if request.video_characteristics else None,
            camera_angle=request.camera_angle.strip() if request.camera_angle else None,
        )

        # Build metadata
        metadata = {
            "idea": request.idea.strip(),
            "number_of_scenes": len(scenes),
            "parameters_used": {
                "character_characteristics": request.character_characteristics or "default from config",
                "video_type": request.video_type or "default from config",
                "video_characteristics": request.video_characteristics or "default from config",
                "camera_angle": request.camera_angle or "default from config",
            }
        }

        response = CreateScenesResponse(
            scenes=scenes,
            output_files=output_files,
            metadata=metadata
        )

        logger.info(
            "create_scenes_request_completed",
            scenes_count=len(scenes),
            output_json=output_files.get("json"),
            output_markdown=output_files.get("markdown")
        )

        return response

    except ValueError as e:
        # Handle configuration errors (e.g., missing API key)
        logger.error("create_scenes_config_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ConfigurationError",
                "message": str(e),
                "details": "Check your environment configuration"
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("create_scenes_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "An unexpected error occurred during scene generation",
                "details": str(e)
            }
        )
