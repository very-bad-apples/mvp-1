"""
Scene generation module for Music Video pipeline.
Ported from .ref-pipeline/src/main.py:generate_scenes
"""

import json
import os
from pathlib import Path
from typing import Optional

import structlog
import yaml
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from config import settings
from mv.debug import (
    log_config_params,
    log_defaults_applied,
    log_full_prompt,
    log_gemini_response,
    log_request_args,
)

logger = structlog.get_logger()

# Config loading has been moved to config_manager.py
# Configs are now loaded per-request based on config_flavor parameter


class Scene(BaseModel):
    """Single scene description for video generation."""
    description: str = Field(..., description="Scene description for video generation")
    negative_description: str = Field(..., description="Elements to exclude from the scene")


class SceneResponse(BaseModel):
    """Response model for scene generation."""
    scenes: list[Scene]


class CreateScenesRequest(BaseModel):
    """Request model for /api/mv/create_scenes endpoint."""
    idea: str = Field(..., description="The core concept or topic of the video")
    character_description: str = Field(..., description="Visual description of main character")
    character_characteristics: Optional[str] = Field(
        None, description="Personality traits of the character"
    )
    number_of_scenes: Optional[int] = Field(
        None, description="Number of scenes to generate"
    )
    video_type: Optional[str] = Field(None, description="Type of video")
    video_characteristics: Optional[str] = Field(None, description="Visual style of the video")
    camera_angle: Optional[str] = Field(None, description="Camera perspective")
    project_id: Optional[str] = Field(
        None,
        description="Optional project ID to associate scenes with a DynamoDB project. When provided, scenes will be saved to DynamoDB."
    )
    config_flavor: Optional[str] = Field(
        None,
        description="Config flavor to use for generation (defaults to 'default')"
    )


class CreateScenesResponse(BaseModel):
    """Response model for /api/mv/create_scenes endpoint."""
    scenes: list[Scene]
    output_files: dict[str, str] = Field(..., description="Paths to saved scene files")
    metadata: dict = Field(..., description="Request metadata and parameters used")


# load_configs() has been deprecated - use config_manager.initialize_config_flavors() instead


def get_default_parameters(config_flavor: Optional[str] = None) -> dict:
    """
    Get default parameters from loaded config.

    Args:
        config_flavor: Optional flavor name to use (defaults to 'default')

    Returns:
        Dictionary of default parameters
    """
    from mv.config_manager import get_config

    parameters_config = get_config(config_flavor, "parameters")

    return {
        "character_characteristics": parameters_config.get(
            "character_characteristics", "sarcastic, dramatic, emotional, and lovable"
        ),
        "number_of_scenes": parameters_config.get("number_of_scenes", 4),
        "video_type": parameters_config.get("video_type", "video"),
        "video_characteristics": parameters_config.get(
            "video_characteristics", "vlogging, realistic, 4k, cinematic"
        ),
        "camera_angle": parameters_config.get("camera_angle", "front"),
    }


def get_prompt_template(config_flavor: Optional[str] = None) -> str:
    """
    Get the scene generation prompt template from loaded config.

    Args:
        config_flavor: Optional flavor name to use (defaults to 'default')

    Returns:
        Scene generation prompt template string
    """
    from mv.config_manager import get_config

    prompts_config = get_config(config_flavor, "scene_prompts")

    return prompts_config.get("scene_generation_prompt", _get_default_prompt_template())


def _get_default_prompt_template() -> str:
    """Default prompt template if config not loaded."""
    return """You are a cinematic video prompt writer for Google Veo 3. Veo 3 is an advanced AI video generation model that transforms text or image prompts into high-definition videos, now with the integrated capability to natively generate synchronized audio, including dialogue, sound effects, and music.

Your task is to generate a series of distinct scene prompts for a {video_type}. These prompts will be used to create a video series centered around a specific character and idea. Each prompt must be a self-contained, detailed description that clearly instructs the video model on what to create. The scenes must be short, visual, simple, cinematic and have a variation of how things are filmed. The character description and locations description should be consistent across all scenes.

**Core Inputs:**
*   **Video Topic:** {idea}
*   **Main Character Description:** {character_description}
*   **Character Personality:** {character_characteristics}
*   **Number of Scenes to Generate:** {number_of_scenes}
*   **Primary Camera Perspective:** {camera_angle}
*   **Overall Video Style:** {video_characteristics}

---

**Instructions & Constraints:**

1.  **Structure:** Generate exactly {number_of_scenes} individual scene prompts.
2.  **Scene Length:** Each prompt should describe an action or a moment lasting approximately 8 seconds.
3.  **Character Consistency:** The main character's core visual description must be included and remain consistent in every scene.
4.  **Detailed Visuals:** Use vivid, specific language.
5.  **Location Consistency:** The location description must be consistent across all scenes if the location is the same.
6.  **Dialogue Formatting:** To include dialogue, use the format: `[verb indicating tone]: "[dialogue text]"`.
7.  **Camera Variation:** While adhering to the primary `{camera_angle}` perspective, introduce variations in shot types.
8.  **Style Integration:** The descriptive language in your prompts must reflect the desired `{video_characteristics}`.
9.  **Self-Contained Prompts:** Each scene prompt must be written in the 3rd person and contain all the necessary information for the video model to generate it independently.

---

**Output Format:**

Provide the output as a single, valid JSON object. The object must contain a single key, `"scenes"`, which holds a list of scene objects. Each scene object in the list must strictly follow this schema:

```json
{{
  "scenes": [
    {{
      "description": "A [shot type] of [main character description], who is [describe action and emotion]. The setting is [describe location]. The character [verb indicating tone]: \\"[dialogue text]\\". The scene is filmed from a {camera_angle} perspective with a {video_characteristics} style.",
      "negative_description": "[Describe elements to exclude from the scene]."
    }}
  ]
}}
```
"""


def generate_scenes(
    idea: str,
    character_description: str,
    character_characteristics: Optional[str] = None,
    number_of_scenes: Optional[int] = None,
    video_type: Optional[str] = None,
    video_characteristics: Optional[str] = None,
    camera_angle: Optional[str] = None,
    prompt_template: Optional[str] = None,
    config_flavor: Optional[str] = None,
) -> tuple[list[Scene], dict[str, str]]:
    """
    Generate scene descriptions for a video based on an idea.

    Args:
        idea: The core concept or topic of the video.
        character_description: A visual description of the main character.
        character_characteristics: The personality traits of the character.
        number_of_scenes: The number of scenes to generate.
        video_type: The type of video (e.g., 'vlog', 'commercial').
        video_characteristics: The overall style of the video.
        camera_angle: The primary camera perspective.
        prompt_template: Custom prompt template for scene generation.
        config_flavor: Config flavor to use (defaults to 'default').

    Returns:
        Tuple of (list of Scene objects, dict of output file paths)

    Raises:
        ValueError: If GEMINI_API_KEY is not configured
        Exception: If Gemini API call fails
    """
    # Log request arguments
    log_request_args({
        "idea": idea,
        "character_description": character_description,
        "character_characteristics": character_characteristics,
        "number_of_scenes": number_of_scenes,
        "video_type": video_type,
        "video_characteristics": video_characteristics,
        "camera_angle": camera_angle,
    })

    # Validate API key
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured. Please set it in your environment.")

    # Apply defaults from config (using specified flavor)
    defaults = get_default_parameters(config_flavor)

    if character_characteristics is None:
        character_characteristics = defaults["character_characteristics"]
    if number_of_scenes is None:
        number_of_scenes = defaults["number_of_scenes"]
    if video_type is None:
        video_type = defaults["video_type"]
    if video_characteristics is None:
        video_characteristics = defaults["video_characteristics"]
    if camera_angle is None:
        camera_angle = defaults["camera_angle"]

    # Fixed output directory
    output_dir = str(Path(__file__).parent / "outputs" / "create_scenes")

    # Log defaults applied
    applied_defaults = {
        k: v for k, v in {
            "character_characteristics": character_characteristics if character_characteristics == defaults["character_characteristics"] else None,
            "number_of_scenes": number_of_scenes if number_of_scenes == defaults["number_of_scenes"] else None,
            "video_type": video_type if video_type == defaults["video_type"] else None,
            "video_characteristics": video_characteristics if video_characteristics == defaults["video_characteristics"] else None,
            "camera_angle": camera_angle if camera_angle == defaults["camera_angle"] else None,
        }.items() if v is not None
    }
    log_defaults_applied(applied_defaults)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get prompt template (using specified flavor)
    if prompt_template is None:
        prompt_template = get_prompt_template(config_flavor)

    # Format the prompt
    prompt = prompt_template.format(
        idea=idea,
        character_description=character_description,
        character_characteristics=character_characteristics,
        number_of_scenes=number_of_scenes,
        camera_angle=camera_angle,
        video_type=video_type,
        video_characteristics=video_characteristics,
    )

    log_full_prompt(prompt)

    # Initialize Gemini client
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Generate scenes using Gemini
    logger.info(
        "gemini_request_started",
        model="gemini-2.5-pro",
        number_of_scenes=number_of_scenes
    )

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SceneResponse,
        ),
    )

    log_gemini_response(response.text)

    # Parse response
    scene_response = SceneResponse.model_validate_json(response.text)
    scenes = scene_response.scenes

    logger.info(
        "gemini_request_completed",
        scenes_generated=len(scenes)
    )

    # Save scenes to files
    output_files = {}

    # Save as markdown
    md_path = os.path.join(output_dir, "scenes.md")
    with open(md_path, "w") as f:
        for n, scene in enumerate(scenes):
            f.write(f"## Scene {n+1}\n\n{scene.description}\n\n")
    output_files["markdown"] = md_path

    # Save as JSON
    json_path = os.path.join(output_dir, "scenes.json")
    with open(json_path, "w") as f:
        json.dump([scene.model_dump() for scene in scenes], f, indent=2)
    output_files["json"] = json_path

    logger.info(
        "scenes_saved",
        markdown_path=md_path,
        json_path=json_path
    )

    return scenes, output_files
